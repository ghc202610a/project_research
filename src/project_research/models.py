"""Canonical records used by provider adapters and application services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    provider: str
    host: str
    owner: str
    name: str
    native_id: int | None = None
    html_url: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.host.lower()}:{self.full_name.lower()}"


@dataclass(frozen=True, slots=True)
class TagRecord:
    provider: str
    repository_key: str
    name: str
    commit_sha: str | None
    zipball_url: str | None
    tarball_url: str | None
    retrieved_at: str = field(default_factory=utc_now)
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    provider: str
    native_id: int
    name: str
    label: str | None
    content_type: str | None
    size: int | None
    state: str | None
    download_count: int | None
    created_at: str | None
    updated_at: str | None
    browser_download_url: str | None
    digest: str | None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("raw", None)
        return result


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    provider: str
    repository_key: str
    native_id: int
    tag_name: str
    name: str | None
    body: str | None
    target_commitish: str | None
    draft: bool
    prerelease: bool
    created_at: str | None
    published_at: str | None
    html_url: str | None
    author_login: str | None
    assets: tuple[ReleaseAsset, ...] = ()
    retrieved_at: str = field(default_factory=utc_now)
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def effective_date(self) -> str | None:
        return self.published_at or self.created_at

    def to_dict(self, *, include_body: bool = True, include_assets: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider": self.provider,
            "repository_key": self.repository_key,
            "native_id": self.native_id,
            "tag_name": self.tag_name,
            "name": self.name,
            "target_commitish": self.target_commitish,
            "draft": self.draft,
            "prerelease": self.prerelease,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "html_url": self.html_url,
            "author_login": self.author_login,
            "retrieved_at": self.retrieved_at,
        }
        if include_body:
            result["body"] = self.body
        if include_assets:
            result["assets"] = [asset.to_dict() for asset in self.assets]
        return result


def normalize_github_asset(payload: dict[str, Any]) -> ReleaseAsset:
    return ReleaseAsset(
        provider="github",
        native_id=int(payload["id"]),
        name=str(payload.get("name") or ""),
        label=payload.get("label"),
        content_type=payload.get("content_type"),
        size=_optional_int(payload.get("size")),
        state=payload.get("state"),
        download_count=_optional_int(payload.get("download_count")),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        browser_download_url=payload.get("browser_download_url"),
        digest=payload.get("digest"),
        raw=payload,
    )


def normalize_github_release(payload: dict[str, Any], repository: RepositoryRef, retrieved_at: str | None = None) -> ReleaseRecord:
    author = payload.get("author") or {}
    assets = tuple(normalize_github_asset(item) for item in payload.get("assets", []) if isinstance(item, dict))
    return ReleaseRecord(
        provider="github",
        repository_key=repository.key,
        native_id=int(payload["id"]),
        tag_name=str(payload.get("tag_name") or ""),
        name=payload.get("name"),
        body=payload.get("body"),
        target_commitish=payload.get("target_commitish"),
        draft=bool(payload.get("draft", False)),
        prerelease=bool(payload.get("prerelease", False)),
        created_at=payload.get("created_at"),
        published_at=payload.get("published_at"),
        html_url=payload.get("html_url"),
        author_login=author.get("login"),
        assets=assets,
        retrieved_at=retrieved_at or utc_now(),
        raw=payload,
    )


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
