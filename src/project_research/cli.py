"""Command-line interface for collecting and researching project releases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .assets import AssetDownloadError, download_asset
from .github import GitHubClient, GitHubError, resolve_repository
from .models import RepositoryRef, utc_now
from .media import collect_release_images
from .render import write_export, write_per_release_markdown
from .selection import select_releases
from .storage import ReleaseStore, default_database_path


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=None, help=f"SQLite database (default: {default_database_path()})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project-research", description="Collect and search provider-neutral software project data.")
    parser.add_argument("--version", action="version", version=f"project-research {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="collect GitHub releases and preserve source records")
    sync.add_argument("repository", help="GitHub owner/repo or repository/nested GitHub URL")
    sync.add_argument("--max-pages", type=int, default=None, help="optional page cap for controlled collection")
    sync.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    sync.add_argument("--download-images", action="store_true", help="opt in to bounded retrieval of raster images in release descriptions")
    sync.add_argument("--max-image-bytes", type=int, default=8 * 1024 * 1024)
    sync.add_argument("--max-total-image-bytes", type=int, default=24 * 1024 * 1024)
    _add_db(sync)

    listing = sub.add_parser("list", help="list locally collected releases")
    listing.add_argument("repository")
    _add_selection(listing)
    _add_db(listing)

    export = sub.add_parser("export", help="write a release archive from locally collected records")
    export.add_argument("repository")
    export.add_argument("--format", choices=("md", "txt", "json", "html", "pdf"), default="md")
    export.add_argument("--output", "-o", type=Path, required=True)
    export.add_argument("--per-release", action="store_true", help="write one Markdown file per release plus an index")
    _add_selection(export)
    _add_db(export)

    rebuild = sub.add_parser("rebuild-index", help="rebuild the derived FTS5 index from canonical release records")
    rebuild.add_argument("--repository", help="optional owner/repo filter")
    _add_db(rebuild)

    search = sub.add_parser("search", help="full-text search collected release descriptions")
    search.add_argument("query")
    search.add_argument("--repository", help="optional owner/repo filter")
    search.add_argument("--limit", type=int, default=50)
    _add_db(search)

    assets = sub.add_parser("assets", help="list locally collected release assets")
    assets.add_argument("repository")
    _add_db(assets)

    tags = sub.add_parser("tags", help="list collected Git tags and distinguish tags without releases")
    tags.add_argument("repository")
    _add_db(tags)

    asset = sub.add_parser("asset", help="explicit release asset operations")
    asset_sub = asset.add_subparsers(dest="asset_command", required=True)
    download = asset_sub.add_parser("download", help="download one exact asset by name or numeric asset ID")
    download.add_argument("repository")
    download.add_argument("selector", help="exact asset filename or GitHub asset ID")
    download.add_argument("--output", "-o", type=Path, required=True, help="destination file path")
    download.add_argument("--max-bytes", type=int, default=512 * 1024 * 1024)
    download.add_argument("--force", action="store_true", help="replace an existing regular file")
    download.add_argument("--timeout", type=float, default=60.0)
    _add_db(download)
    return parser


def _add_selection(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--last", type=int, help="select the newest N matching releases")
    group.add_argument("--all", action="store_true", help="include every matching collected release")
    parser.add_argument("--since", help="inclusive lower date/time bound (ISO 8601)")
    parser.add_argument("--until", help="inclusive upper date/time bound (ISO 8601)")
    parser.add_argument("--min-version", help="inclusive numeric tag/version lower bound")
    parser.add_argument("--max-version", help="inclusive numeric tag/version upper bound")
    parser.add_argument("--include-prereleases", action="store_true")
    parser.add_argument("--include-drafts", action="store_true")


def _repository_from_store(store: ReleaseStore, value: str) -> RepositoryRef:
    requested = resolve_repository(value)
    repository = store.find_repository(requested.key)
    if repository is None:
        raise RuntimeError(f"no local collection for {requested.full_name}; run 'project-research sync {requested.full_name}' first")
    return repository


def _selected(args: argparse.Namespace, store: ReleaseStore, repository: RepositoryRef):
    return select_releases(
        store.list_releases(repository.key), since=args.since, until=args.until, last=args.last,
        include_prereleases=args.include_prereleases, include_drafts=args.include_drafts,
        min_version=args.min_version, max_version=args.max_version, all_releases=args.all,
    )


def _run(args: argparse.Namespace) -> int:
    if args.command == "sync":
        if args.max_pages is not None and args.max_pages < 1:
            raise ValueError("--max-pages must be at least 1")
        client = GitHubClient(timeout=args.timeout)
        repository = client.get_repository(resolve_repository(args.repository))
        releases = client.list_releases(repository, max_pages=args.max_pages)
        tags = client.list_tags(repository, max_pages=args.max_pages)
        with ReleaseStore(args.db) as store:
            synced_at = utc_now()
            store.save_releases(repository, releases, synced_at)
            store.save_tags(repository, tags, synced_at)
            if args.download_images:
                if args.max_image_bytes < 1 or args.max_total_image_bytes < 1:
                    raise ValueError("image size limits must be positive")
                remaining = args.max_total_image_bytes
                media_count = 0
                cached_count = 0
                for release in releases:
                    existing = {str(row["source_url"]): row for row in store.list_media(repository.key, release.native_id)}
                    results = collect_release_images(
                        release.body, store.path.parent, release.native_id,
                        repository_key=repository.key, existing_media=existing,
                        max_file_bytes=args.max_image_bytes, remaining_total_bytes=remaining,
                        timeout=args.timeout)
                    store.record_media(repository.key, release.native_id, results, synced_at)
                    media_count += sum(1 for result in results if result.status == "downloaded")
                    cached_count += sum(1 for result in results if result.status == "cached")
                    remaining -= sum(result.size or 0 for result in results if result.status == "downloaded")
                print(f"Downloaded {media_count} embedded image(s); reused {cached_count} cached image(s); total limit {args.max_total_image_bytes} bytes")
            release_tags = {release.tag_name for release in releases}
            unmatched_tags = sum(1 for tag in tags if tag.name not in release_tags)
            print(f"Synced {len(releases)} releases and {len(tags)} tags from {repository.full_name}")
            print(f"Tags without published releases: {unmatched_tags}")
            print(f"Database: {store.path}")
        return 0

    with ReleaseStore(args.db) as store:
        if args.command in {"list", "export", "assets", "tags"}:
            repository = _repository_from_store(store, args.repository)
            if args.command == "list":
                releases = _selected(args, store, repository)
                for release in releases:
                    date = release.published_at or release.created_at or "undated"
                    flags = "".join((" draft" if release.draft else "", " prerelease" if release.prerelease else ""))
                    print(f"{date:25} {release.tag_name:24} {(release.name or '')[:60]}{flags}")
                print(f"{len(releases)} release(s)")
            elif args.command == "export":
                releases = _selected(args, store, repository)
                if args.per_release:
                    if args.format != "md":
                        raise ValueError("--per-release is supported only with --format md")
                    written = write_per_release_markdown(args.output, repository, releases)
                    print(f"Wrote {len(releases)} per-release Markdown files and an index under {args.output}")
                else:
                    write_export(args.output, args.format, repository, releases)
                    print(f"Wrote {len(releases)} releases to {args.output}")
            elif args.command == "assets":
                releases = store.list_releases(repository.key)
                count = 0
                for release in releases:
                    for item in release.assets:
                        print(f"{item.native_id}\t{item.name}\t{item.size if item.size is not None else '?'}\t{release.tag_name}\t{item.content_type or '?'}")
                        count += 1
                print(f"{count} asset(s)")
            else:
                rows = store.list_tags(repository.key)
                for tag in rows:
                    status = "release" if tag["has_release"] else "tag only"
                    print(f"{status:9} {tag['name']:32} {tag.get('commit_sha') or ''}")
                print(f"{len(rows)} tag(s)")
            return 0
        if args.command == "rebuild-index":
            key = resolve_repository(args.repository).key if args.repository else None
            count = store.rebuild_search_index(key)
            print(f"Rebuilt FTS5 index for {count} release(s)")
            return 0
        if args.command == "search":
            key = resolve_repository(args.repository).key if args.repository else None
            results = store.search(args.query, key, args.limit)
            for result in results:
                snippet = (result.get("body") or "").replace("\n", " ")[:240]
                print(f"{result['repository_key']} {result['tag_name']} {result.get('name') or ''}")
                print(f"  {result.get('html_url') or ''}")
                if snippet:
                    print(f"  {snippet}")
            print(f"{len(results)} result(s)")
            return 0
        if args.command == "asset" and args.asset_command == "download":
            repository = _repository_from_store(store, args.repository)
            matches = store.find_asset(repository.key, args.selector)
            if not matches:
                raise RuntimeError(f"no exact asset match for {args.selector!r}")
            if len(matches) > 1:
                choices = ", ".join(f"{row['native_id']} ({row['tag_name']})" for row in matches)
                raise RuntimeError(f"asset name is ambiguous across releases; select its numeric asset ID. Matches: {choices}")
            row = matches[0]
            asset_record = dict(row)
            release_record = {"native_id": row["release_native_id"], "tag_name": row["tag_name"], "release_url": row["release_url"]}
            result = download_asset(GitHubClient(timeout=args.timeout), repository, asset_record, release_record,
                                    args.output, max_bytes=args.max_bytes, force=args.force)
            print(json.dumps(result, indent=2))
            return 0
    raise RuntimeError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ValueError, RuntimeError, GitHubError, AssetDownloadError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
