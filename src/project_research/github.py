"""GitHub REST adapter. Provider-specific HTTP and payload handling stays here."""

from __future__ import annotations

from dataclasses import dataclass, replace
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, unquote
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import json
import os
import re
import time

from .models import RepositoryRef, ReleaseRecord, TagRecord, normalize_github_release, utc_now

API_ROOT = "https://api.github.com"
MAX_API_RESPONSE_BYTES = 32 * 1024 * 1024
GITHUB_HOSTS = {"github.com", "www.github.com"}


class GitHubError(RuntimeError):
    """A GitHub API or transport failure with a safe, user-facing message."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, dict[str, str], float], HttpResponse]


def resolve_repository(value: str) -> RepositoryRef:
    """Resolve owner/repo or a nested github.com repository URL."""
    candidate = value.strip()
    if not candidate:
        raise ValueError("repository reference is empty")
    if re.fullmatch(r"[^/\s]+/[^/\s]+", candidate):
        owner, name = candidate.split("/", 1)
    else:
        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        host = (parsed.hostname or "").lower()
        if host not in GITHUB_HOSTS:
            raise ValueError("only github.com repository URLs are supported by the initial adapter")
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("URL does not contain an owner and repository")
        owner, name = parts[0], parts[1]
    name = name.removesuffix(".git")
    if not owner or not name or owner in {".", ".."} or name in {".", ".."}:
        raise ValueError("invalid owner/repository reference")
    if not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError("repository owner or name contains unsupported characters")
    return RepositoryRef(provider="github", host="github.com", owner=owner, name=name,
                         html_url=f"https://github.com/{owner}/{name}")


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: float = 30.0,
                 max_retries: int = 3, transport: Transport | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.token = token if token is not None else (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.transport = transport or _urlopen_transport
        self.sleep = sleep

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "project-research/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_json(self, url: str) -> tuple[Any, dict[str, str]]:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.transport(url, self._headers(), self.timeout)
                if response.status >= 400:
                    raise _http_error(response.status, response.headers, response.body)
                try:
                    return json.loads(response.body.decode("utf-8")), response.headers
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise GitHubError(f"GitHub returned invalid JSON for {url}") from exc
            except HTTPError as exc:
                status = exc.code
                headers = {k.lower(): v for k, v in exc.headers.items()}
                body = exc.read(4096)
                error = _http_error(status, headers, body)
                if not _is_retryable(status, headers) or attempt >= self.max_retries:
                    raise error from exc
                self.sleep(_retry_delay(attempt, headers))
            except (URLError, TimeoutError, OSError) as exc:
                if attempt >= self.max_retries:
                    raise GitHubError(f"GitHub request failed: {type(exc).__name__}: {exc}") from exc
                self.sleep(min(2 ** attempt, 8))
            except GitHubError as exc:
                status = getattr(exc, "status", None)
                headers = getattr(exc, "headers", {})
                if not status or not _is_retryable(status, headers) or attempt >= self.max_retries:
                    raise
                self.sleep(_retry_delay(attempt, headers))
        raise GitHubError("GitHub request exhausted retries")

    def get_repository(self, repository: RepositoryRef) -> RepositoryRef:
        payload, _ = self.get_json(f"{API_ROOT}/repos/{repository.owner}/{repository.name}")
        owner = (payload.get("owner") or {}).get("login") or repository.owner
        name = payload.get("name") or repository.name
        return replace(repository, owner=owner, name=name, native_id=int(payload["id"]),
                       html_url=payload.get("html_url") or repository.html_url)

    def list_releases(self, repository: RepositoryRef, *, max_pages: int | None = None) -> list[ReleaseRecord]:
        url = f"{API_ROOT}/repos/{repository.owner}/{repository.name}/releases?per_page=100&page=1"
        records: list[ReleaseRecord] = []
        pages = 0
        while url:
            payload, headers = self.get_json(url)
            if not isinstance(payload, list):
                raise GitHubError("GitHub releases endpoint returned an unexpected response")
            retrieved = utc_now()
            records.extend(normalize_github_release(item, repository, retrieved) for item in payload if isinstance(item, dict))
            pages += 1
            if max_pages is not None and pages >= max_pages:
                break
            url = _next_link(headers.get("link", ""))
        return records

    def list_tags(self, repository: RepositoryRef, *, max_pages: int | None = None) -> list[TagRecord]:
        url = f"{API_ROOT}/repos/{repository.owner}/{repository.name}/tags?per_page=100&page=1"
        records: list[TagRecord] = []
        pages = 0
        while url:
            payload, headers = self.get_json(url)
            if not isinstance(payload, list):
                raise GitHubError("GitHub tags endpoint returned an unexpected response")
            retrieved = utc_now()
            for item in payload:
                if not isinstance(item, dict):
                    continue
                commit = item.get("commit") or {}
                records.append(TagRecord(
                    provider="github", repository_key=repository.key,
                    name=str(item.get("name") or ""), commit_sha=commit.get("sha"),
                    zipball_url=item.get("zipball_url"), tarball_url=item.get("tarball_url"),
                    retrieved_at=retrieved, raw=item))
            pages += 1
            if max_pages is not None and pages >= max_pages:
                break
            url = _next_link(headers.get("link", ""))
        return records

    def download_asset(self, asset_api_url: str, destination, *, max_bytes: int) -> tuple[str, int]:
        """Stream an asset to a caller-owned temporary path and return sha256/size."""
        import hashlib
        from pathlib import Path

        headers = self._headers("application/octet-stream")
        request = Request(asset_api_url, headers=headers)
        digest = hashlib.sha256()
        total = 0
        try:
            opener = build_opener(_GitHubAssetRedirectHandler())
            with opener.open(request, timeout=self.timeout) as response, Path(destination).open("wb") as output:
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_bytes:
                    raise GitHubError(f"asset exceeds configured size limit ({max_bytes} bytes)")
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > max_bytes:
                        raise GitHubError(f"asset exceeds configured size limit ({max_bytes} bytes)")
                    digest.update(block)
                    output.write(block)
        except HTTPError as exc:
            raise _http_error(exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(4096)) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubError(f"asset download failed: {type(exc).__name__}: {exc}") from exc
        return digest.hexdigest(), total


class _GitHubAssetRedirectHandler(HTTPRedirectHandler):
    """Drop bearer credentials when GitHub redirects an asset to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = urlparse(req.full_url).hostname
        new_host = urlparse(newurl).hostname
        if old_host != new_host:
            redirected.remove_header("Authorization")
            redirected.unredirected_hdrs.pop("Authorization", None)
            redirected.headers.pop("Authorization", None)
        return redirected


def _urlopen_transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_API_RESPONSE_BYTES + 1)
            if len(body) > MAX_API_RESPONSE_BYTES:
                raise GitHubError(f"GitHub API response exceeded {MAX_API_RESPONSE_BYTES} bytes")
            return HttpResponse(response.status, {k.lower(): v for k, v in response.headers.items()}, body)
    except HTTPError as exc:
        return HttpResponse(exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(4096))


def _http_error(status: int, headers: dict[str, str], body: bytes) -> GitHubError:
    try:
        message = json.loads(body.decode("utf-8")).get("message", "")
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        message = ""
    safe_message = str(message)[:300]
    if status == 401:
        detail = "authentication failed; check GH_TOKEN or GITHUB_TOKEN"
    elif status == 403 and ("rate limit" in safe_message.lower() or headers.get("x-ratelimit-remaining") == "0"):
        detail = "GitHub API rate limit exceeded"
    elif status == 404:
        detail = "repository or resource not found (or access is denied)"
    else:
        detail = safe_message or f"HTTP {status}"
    error = GitHubError(f"GitHub API error {status}: {detail}")
    error.status = status  # type: ignore[attr-defined]
    error.headers = headers  # type: ignore[attr-defined]
    return error


def _is_retryable(status: int, headers: dict[str, str]) -> bool:
    return status in {500, 502, 503, 504} or (status == 403 and (
        headers.get("x-ratelimit-remaining") == "0" or "retry-after" in headers))


def _retry_delay(attempt: int, headers: dict[str, str]) -> float:
    retry_after = headers.get("retry-after")
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            try:
                return min(max((parsedate_to_datetime(retry_after).timestamp() - time.time()), 0.0), 60.0)
            except (TypeError, ValueError, OverflowError):
                pass
    reset = headers.get("x-ratelimit-reset")
    if reset and headers.get("x-ratelimit-remaining") == "0":
        try:
            return min(max(float(reset) - time.time(), 0.0), 60.0)
        except ValueError:
            pass
    return min(2 ** attempt, 8)


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="?([^";]+)', part)
        if match and match.group(2) == "next":
            next_url = match.group(1)
            parsed = urlparse(next_url)
            if parsed.scheme != "https" or parsed.hostname != "api.github.com" or parsed.port not in (None, 443) or parsed.username or parsed.password:
                raise GitHubError("GitHub returned an unsafe pagination URL")
            return next_url
    return None
