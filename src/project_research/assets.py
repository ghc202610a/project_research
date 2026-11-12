"""Explicit, bounded release-asset downloads with provenance sidecars."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import re
import tempfile

from .github import GitHubClient, API_ROOT
from .models import RepositoryRef


class AssetDownloadError(RuntimeError):
    pass


def validate_asset_filename(name: str) -> str:
    if not name or name in {".", ".."} or Path(name).name != name:
        raise AssetDownloadError("asset filename is not a safe single path component")
    if any(char in name for char in ("/", "\\", "\x00", "\r", "\n")):
        raise AssetDownloadError("asset filename contains a path separator or control character")
    if re.match(r"^[A-Za-z]:", name):
        raise AssetDownloadError("asset filename must not be a drive-qualified path")
    return name


def download_asset(client: GitHubClient, repository: RepositoryRef, asset: dict[str, Any],
                   release: dict[str, Any], output: str | Path, *, max_bytes: int = 512 * 1024 * 1024,
                   force: bool = False) -> dict[str, Any]:
    validate_asset_filename(str(asset.get("name") or ""))
    if asset.get("size") is not None and int(asset["size"]) > max_bytes:
        raise AssetDownloadError(f"asset metadata size exceeds configured limit ({max_bytes} bytes)")
    target = Path(output).expanduser()
    if target.exists() and target.is_symlink():
        raise AssetDownloadError("refusing to replace a symbolic link")
    if target.exists() and not force:
        raise AssetDownloadError(f"destination already exists: {target} (use --force to replace)")
    if max_bytes < 1:
        raise AssetDownloadError("maximum download size must be positive")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".part", dir=target.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        api_url = f"{API_ROOT}/repos/{repository.owner}/{repository.name}/releases/assets/{int(asset['native_id'])}"
        local_sha, size = client.download_asset(api_url, temp_path, max_bytes=max_bytes)
        expected_size = asset.get("size")
        if expected_size is not None and size != int(expected_size):
            raise AssetDownloadError(f"downloaded size ({size}) does not match provider metadata ({expected_size})")
        publisher_digest = asset.get("digest")
        verified: bool | None = None
        if publisher_digest:
            if not str(publisher_digest).startswith("sha256:"):
                raise AssetDownloadError(f"unsupported publisher digest format: {publisher_digest}")
            expected = str(publisher_digest).split(":", 1)[1].lower()
            verified = local_sha.lower() == expected
            if not verified:
                raise AssetDownloadError("downloaded asset SHA-256 does not match the publisher digest")
        os.replace(temp_path, target)
        sidecar = {
            "schema_version": 1,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "provider": repository.provider,
            "repository": repository.full_name,
            "repository_url": repository.html_url,
            "release_native_id": release.get("native_id"),
            "release_tag": release.get("tag_name"),
            "release_url": release.get("release_url"),
            "asset_native_id": asset.get("native_id"),
            "asset_name": asset.get("name"),
            "source_url": asset.get("browser_download_url"),
            "local_file": target.name,
            "size_bytes": size,
            "local_sha256": local_sha,
            "publisher_digest": publisher_digest,
            "publisher_digest_verified": verified,
        }
        sidecar_path = target.with_name(target.name + ".provenance.json")
        sidecar_fd, sidecar_tmp_name = tempfile.mkstemp(
            prefix=f".{sidecar_path.name}.", suffix=".tmp", dir=sidecar_path.parent)
        sidecar_tmp = Path(sidecar_tmp_name)
        try:
            with os.fdopen(sidecar_fd, "w", encoding="utf-8") as sidecar_file:
                json.dump(sidecar, sidecar_file, indent=2, ensure_ascii=False)
                sidecar_file.write("\n")
                sidecar_file.flush()
                os.fsync(sidecar_file.fileno())
            os.replace(sidecar_tmp, sidecar_path)
        except Exception:
            sidecar_tmp.unlink(missing_ok=True)
            raise
        return sidecar
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
