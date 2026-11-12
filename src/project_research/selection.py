"""Deterministic release filtering and ordering."""

from __future__ import annotations

from datetime import datetime, timezone, time
import re

from .models import ReleaseRecord


_VERSION_RE = re.compile(r"^[vV]?(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


def _version_parts(value: str) -> tuple[tuple[int, ...], tuple[tuple[int, int | str], ...]] | None:
    if len(value) > 128:
        return None
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    core_parts = match.group(1).split(".")
    if any(len(part) > 18 for part in core_parts):
        return None
    core = tuple(int(part) for part in core_parts)
    prerelease = match.group(2)
    if prerelease is None:
        pre: tuple[tuple[int, int | str], ...] = ()
    else:
        pieces: list[tuple[int, int | str]] = []
        for item in prerelease.split("."):
            if item.isdigit() and len(item) > 18:
                return None
            pieces.append((0, int(item)) if item.isdigit() else (1, item.lower()))
        pre = tuple(pieces)
    return core, pre


def compare_versions(left: str, right: str) -> int:
    """Compare simple numeric release tags with SemVer-like prerelease ordering."""
    a, b = _version_parts(left), _version_parts(right)
    if a is None or b is None:
        raise ValueError(f"version bound requires numeric version tags; cannot compare {left!r} and {right!r}")
    acore, apre = a
    bcore, bpre = b
    width = max(len(acore), len(bcore))
    acore += (0,) * (width - len(acore))
    bcore += (0,) * (width - len(bcore))
    if acore != bcore:
        return -1 if acore < bcore else 1
    if not apre and bpre:
        return 1
    if apre and not bpre:
        return -1
    if apre == bpre:
        return 0
    for ai, bi in zip(apre, bpre):
        if ai == bi:
            continue
        # Numeric prerelease identifiers sort before textual identifiers.
        if ai[0] != bi[0]:
            return -1 if ai[0] < bi[0] else 1
        return -1 if ai[1] < bi[1] else 1
    return -1 if len(apre) < len(bpre) else 1


def _parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        if len(value) == 10 and end_of_day:
            parsed = datetime.combine(datetime.fromisoformat(value).date(), time.max, tzinfo=timezone.utc)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def chronological_key(release: ReleaseRecord) -> tuple[datetime, int]:
    date = _parse_date(release.published_at) or _parse_date(release.created_at)
    return (date or datetime.min.replace(tzinfo=timezone.utc), release.native_id)


def select_releases(
    releases: list[ReleaseRecord], *, since: str | None = None, until: str | None = None,
    last: int | None = None, include_prereleases: bool = False, include_drafts: bool = False,
    min_version: str | None = None, max_version: str | None = None,
    default_limit: int = 20, all_releases: bool = False,
) -> list[ReleaseRecord]:
    if last is not None and last < 1:
        raise ValueError("--last must be at least 1")
    if min_version and _version_parts(min_version) is None:
        raise ValueError(f"invalid minimum version bound: {min_version}")
    if max_version and _version_parts(max_version) is None:
        raise ValueError(f"invalid maximum version bound: {max_version}")
    if min_version and max_version and compare_versions(min_version, max_version) > 0:
        raise ValueError("minimum version is greater than maximum version")
    lower_date = _parse_date(since) if since else None
    upper_date = _parse_date(until, end_of_day=True) if until else None
    if since and lower_date is None:
        raise ValueError(f"invalid --since date: {since}")
    if until and upper_date is None:
        raise ValueError(f"invalid --until date: {until}")
    if lower_date and upper_date and lower_date > upper_date:
        raise ValueError("--since must not be later than --until")

    selected: list[ReleaseRecord] = []
    for release in releases:
        if release.draft and not include_drafts:
            continue
        if release.prerelease and not include_prereleases:
            continue
        date = _parse_date(release.effective_date)
        if lower_date and (date is None or date < lower_date):
            continue
        if upper_date and (date is None or date > upper_date):
            continue
        if min_version or max_version:
            parsed = _version_parts(release.tag_name)
            if parsed is None:
                continue
            if min_version and compare_versions(release.tag_name, min_version) < 0:
                continue
            if max_version and compare_versions(release.tag_name, max_version) > 0:
                continue
        selected.append(release)

    selected.sort(key=chronological_key)
    if last is not None:
        return selected[-last:]
    if all_releases:
        return selected
    if since or until or min_version or max_version:
        return selected
    if include_prereleases or include_drafts:
        return selected[-default_limit:]

    # Prefer the latest two stable numeric major lines where the tags permit it.
    versioned = [(release, _version_parts(release.tag_name)) for release in selected]
    numeric = [(release, parsed) for release, parsed in versioned if parsed is not None]
    if numeric:
        current_major = max(parsed[0][0] for _, parsed in numeric if parsed[0])
        majors = {current_major, max(0, current_major - 1)}
        preferred = [release for release, parsed in numeric if parsed and parsed[0] and parsed[0][0] in majors]
        if preferred:
            return preferred
    return selected[-default_limit:]
