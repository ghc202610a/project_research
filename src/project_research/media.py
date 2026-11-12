"""Opt-in, bounded retrieval of raster images embedded in release descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import os
import tempfile
import hashlib
import ipaddress
import re
import socket


RASTER_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


@dataclass(frozen=True, slots=True)
class MediaResult:
    source_url: str
    status: str
    local_path: str | None = None
    content_type: str | None = None
    size: int | None = None
    sha256: str | None = None
    detail: str | None = None


def extract_image_urls(body: str | None) -> list[str]:
    if not body:
        return []
    found: list[tuple[int, str]] = []
    for match in re.finditer(r"!\[[^\]]*\]\(\s*<?([^\s)>]+)>?(?:\s+[^)]*)?\)", body):
        found.append((match.start(), match.group(1)))
    for match in re.finditer(r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1", body, re.IGNORECASE | re.DOTALL):
        found.append((match.start(), match.group(2)))
    result: list[str] = []
    seen: set[str] = set()
    for _, value in sorted(found, key=lambda item: item[0]):
        value = value.strip().replace("&amp;", "&")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            continue
        normalized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("image URL must be an absolute HTTP(S) URL without embedded credentials")
    host = parsed.hostname
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except OSError as exc:
            raise ValueError(f"could not resolve image host {host}") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("image URL resolves to a non-public network address")


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url).scheme == "https" and urlsplit(newurl).scheme != "https":
            raise ValueError("refusing an HTTPS-to-HTTP image redirect")
        _validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _raster_extension(content_type: str, data: bytes) -> str | None:
    mime = content_type.split(";", 1)[0].strip().lower()
    ext = RASTER_TYPES.get(mime)
    if ext is None:
        return None
    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".gif": data.startswith((b"GIF87a", b"GIF89a")),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    return ext if signatures.get(ext, False) else None


def _fetch_image(url: str, timeout: float, max_bytes: int) -> tuple[str, bytes]:
    _validate_public_url(url)
    opener = build_opener(_SafeRedirectHandler())
    request = Request(url, headers={"User-Agent": "project-research/0.1.0", "Accept": ", ".join(RASTER_TYPES)})
    try:
        with opener.open(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                raise OverflowError("image exceeds per-file size limit")
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise OverflowError("image exceeds per-file size limit")
            return content_type, data
    except HTTPError as exc:
        raise OSError(f"HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise OSError(f"network error: {type(exc).__name__}") from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def collect_release_images(body: str | None, destination_root: str | Path, release_id: int, *,
                           repository_key: str = "repository",
                           existing_media: dict[str, dict] | None = None,
                           max_file_bytes: int = 8 * 1024 * 1024,
                           remaining_total_bytes: int = 24 * 1024 * 1024,
                           timeout: float = 20.0) -> list[MediaResult]:
    root = Path(destination_root).resolve()
    media_root = (root / "media").resolve()
    results: list[MediaResult] = []
    consumed = 0
    for url in extract_image_urls(body):
        cached = (existing_media or {}).get(url)
        if cached and cached.get("status") in {"downloaded", "cached"} and cached.get("local_path"):
            cached_path = Path(str(cached["local_path"]))
            safe_cached_path = (not cached_path.is_symlink() and cached_path.is_file()
                                and cached_path.resolve().is_relative_to(media_root))
            if safe_cached_path:
                expected_hash = cached.get("sha256")
                if expected_hash:
                    digest = _file_sha256(cached_path)
                    if digest != expected_hash:
                        cached_path.unlink(missing_ok=True)
                    else:
                        results.append(MediaResult(url, "cached", str(cached_path), cached.get("content_type"),
                                                   cached.get("size"), digest, "reused verified local copy"))
                        continue
                else:
                    results.append(MediaResult(url, "cached", str(cached_path), cached.get("content_type"),
                                               cached.get("size"), cached.get("sha256"), "reused prior download"))
                    continue
        if remaining_total_bytes - consumed <= 0:
            results.append(MediaResult(url, "skipped-total-limit", detail="per-sync total image limit reached"))
            continue
        try:
            content_type, data = _fetch_image(url, timeout, min(max_file_bytes, remaining_total_bytes - consumed))
            extension = _raster_extension(content_type, data)
            if extension is None:
                results.append(MediaResult(url, "skipped-invalid-image", content_type=content_type,
                                           size=len(data), detail="content type and raster signature did not match"))
                continue
            digest = hashlib.sha256(data).hexdigest()
            namespace = hashlib.sha256(repository_key.encode("utf-8")).hexdigest()[:16]
            target = root / "media" / namespace / f"release-{release_id}" / f"{digest}{extension}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                if not target.is_file():
                    raise OSError("media destination exists and is not a regular file")
                if _file_sha256(target) != digest:
                    target.unlink()
            if not target.exists():
                fd, temporary = tempfile.mkstemp(prefix=f".{digest}.", suffix=".part", dir=target.parent)
                try:
                    with os.fdopen(fd, "wb") as output:
                        output.write(data)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, target)
                except Exception:
                    Path(temporary).unlink(missing_ok=True)
                    raise
            consumed += len(data)
            results.append(MediaResult(url, "downloaded", str(target), content_type, len(data), digest))
        except OverflowError as exc:
            results.append(MediaResult(url, "skipped-size-limit", detail=str(exc)))
        except ValueError as exc:
            results.append(MediaResult(url, "blocked", detail=str(exc)))
        except OSError as exc:
            results.append(MediaResult(url, "failed", detail=str(exc)))
    return results
