"""Deterministic release archive renderers."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import quote, urlsplit
import json

from .models import RepositoryRef, ReleaseRecord
from .selection import chronological_key


def _ordered(releases: Iterable[ReleaseRecord]) -> list[ReleaseRecord]:
    return sorted(releases, key=chronological_key, reverse=True)


def _safe_http_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return value


def _release_slug(release: ReleaseRecord) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", release.tag_name).strip(".-") or str(release.native_id)


def render_json(repository: RepositoryRef, releases: Iterable[ReleaseRecord]) -> str:
    payload = {
        "schema_version": 1,
        "source": {"provider": repository.provider, "host": repository.host,
                   "repository": repository.full_name, "repository_key": repository.key,
                   "repository_url": repository.html_url,
                   "api_url": f"https://api.github.com/repos/{repository.owner}/{repository.name}/releases"},
        "releases": [release.to_dict() for release in _ordered(releases)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_markdown(repository: RepositoryRef, releases: Iterable[ReleaseRecord]) -> str:
    items = _ordered(releases)
    lines = [f"# Releases: {repository.full_name}", "",
             f"Source: [{repository.html_url}]({repository.html_url})", "",
             f"Collected releases: {len(items)}", ""]
    for release in items:
        title = release.name or release.tag_name
        lines.extend([f"## {title}", "",
                      f"- Tag: `{release.tag_name}`",
                      f"- Published: {release.published_at or 'not published'}",
                      f"- Created: {release.created_at or 'unknown'}",
                      f"- Prerelease: {'yes' if release.prerelease else 'no'}",
                      f"- Draft: {'yes' if release.draft else 'no'}"])
        if release.html_url:
            lines.append(f"- Source: {release.html_url}")
        if release.author_login:
            lines.append(f"- Author: {release.author_login}")
        lines.append("")
        if release.body:
            lines.extend([release.body.rstrip(), ""])
        if release.assets:
            lines.extend(["### Assets", "", "| Name | Size | Downloads | Content type |", "|---|---:|---:|---|"])
            for asset in release.assets:
                size = str(asset.size) if asset.size is not None else "unknown"
                count = str(asset.download_count) if asset.download_count is not None else "unknown"
                name = asset.name.replace("|", "\\|").replace("]", "\\]")
                content_type = (asset.content_type or "unknown").replace("|", "\\|")
                url = quote(_safe_http_url(asset.browser_download_url), safe=":/?#[]@!$&'*,;=%")
                link = f"[{name}]({url})" if url else f"`{name}`"
                lines.append(f"| {link} | {size} | {count} | {content_type} |")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_text(repository: RepositoryRef, releases: Iterable[ReleaseRecord]) -> str:
    lines = [f"Releases: {repository.full_name}", f"Source: {repository.html_url}", ""]
    for release in _ordered(releases):
        lines.extend([f"{release.name or release.tag_name} ({release.tag_name})",
                      f"Published: {release.published_at or 'not published'}",
                      f"URL: {release.html_url or ''}", release.body or "", ""])
    return "\n".join(lines)


def render_html(repository: RepositoryRef, releases: Iterable[ReleaseRecord]) -> str:
    sections: list[str] = []
    for release in _ordered(releases):
        title = escape(release.name or release.tag_name)
        body = escape(release.body or "")
        url = escape(_safe_http_url(release.html_url), quote=True)
        assets = "".join(
            (f'<li><a href="{escape(_safe_http_url(a.browser_download_url), quote=True)}">{escape(a.name)}</a> '
             if _safe_http_url(a.browser_download_url) else f"<li>{escape(a.name)} ") +
            f'({a.size if a.size is not None else "unknown"} bytes)</li>' for a in release.assets
        )
        sections.append(
            f"<article><h2>{title}</h2><p><code>{escape(release.tag_name)}</code> · "
            f"{escape(release.published_at or release.created_at or 'undated')} · "
            f"<a href=\"{url}\">source</a></p><pre>{body}</pre>"
            f"<h3>Assets</h3><ul>{assets}</ul></article>"
        )
    return "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>" + escape(repository.full_name) + \
        " releases</title><body><h1>" + escape(repository.full_name) + " releases</h1>" + \
        "\n".join(sections) + "</body></html>\n"


def write_per_release_markdown(directory: str | Path, repository: RepositoryRef,
                               releases: Iterable[ReleaseRecord]) -> list[Path]:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    items = _ordered(releases)
    written: list[Path] = []
    for release in items:
        path = target_dir / f"release-{release.native_id}-{_release_slug(release)}.md"
        path.write_text(render_markdown(repository, [release]), encoding="utf-8")
        written.append(path)
    index = target_dir / "README.md"
    lines = [f"# Release archive: {repository.full_name}", ""]
    lines.extend(f"- [{release.name or release.tag_name}](release-{release.native_id}-{_release_slug(release)}.md)"
                 for release in items)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return written + [index]


def write_export(path: str | Path, fmt: str, repository: RepositoryRef,
                 releases: Iterable[ReleaseRecord]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        content = render_json(repository, releases)
    elif fmt == "md":
        content = render_markdown(repository, releases)
    elif fmt == "txt":
        content = render_text(repository, releases)
    elif fmt == "html":
        content = render_html(repository, releases)
    elif fmt == "pdf":
        try:
            from weasyprint import HTML  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("PDF export requires the optional 'weasyprint' package") from exc
        HTML(string=render_html(repository, releases), base_url=str(target.parent.resolve())).write_pdf(str(target))
        return
    else:
        raise ValueError(f"unsupported export format: {fmt}")
    target.write_text(content, encoding="utf-8")
