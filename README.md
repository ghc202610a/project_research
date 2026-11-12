# project_research

A provider-neutral system for collecting, preserving, searching, and researching software-project information. GitHub is the first source adapter; the initial application is a local release tracker.

## Current implementation

The first CLI increment collects GitHub releases and Git tags, preserves normalized records and raw release payload observations in SQLite, indexes release text with FTS5, and exports deterministic archives. Release assets are inventoried but are not downloaded automatically. A selected asset can be downloaded explicitly with a size limit, SHA-256 calculation, optional publisher-digest verification, and a provenance sidecar.

The application is a conventional local CLI. It does not require an LLM, hosted service, or runtime Python dependency beyond the standard library. PDF output is optional and requires WeasyPrint. GitHub API credentials are read from GH_TOKEN or GITHUB_TOKEN; they are never written to the database or printed.

## Install

Requires Python 3.11 or later and SQLite with FTS5 support (included in most current Python distributions).

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    project-research --help

For public repositories, unauthenticated API access may be sufficient within GitHub's rate limits. For authenticated access, set a token in the environment:

    export GH_TOKEN=...  # or GITHUB_TOKEN

Do not put tokens on the command line or in project files.

## Typical workflow

    # Collect releases and tags. This does not download release binaries or images.
    project-research sync owner/repository

    # List the default selection (latest releases in the current/previous numeric major lines).
    project-research list owner/repository

    # Include all stable releases; explicitly opt in to prereleases/drafts when needed.
    project-research list owner/repository --all
    project-research list owner/repository --all --include-prereleases --include-drafts

    # Export an aggregate Markdown archive or separate per-release Markdown files.
    project-research export owner/repository --format md --output releases.md --all
    project-research export owner/repository --format md --output release-files/ --per-release --all

    # Other archive formats.
    project-research export owner/repository --format json --output releases.json --all
    project-research export owner/repository --format html --output releases.html --all

    # Search locally collected release descriptions and metadata.
    project-research search 'security fix'

    # Distinguish Git tags that have no published release.
    project-research tags owner/repository

    # Inspect the asset inventory, then download one exact asset by ID or unique filename.
    project-research assets owner/repository
    project-research asset download owner/repository 123456 --output ./downloads/source.tar.gz

Date bounds are inclusive. Version bounds compare numeric version components (v1.9 sorts before v1.10); non-version tags are omitted when a version bound is active. The default selection prefers stable releases in the latest and previous numeric major lines when version tags make that unambiguous, otherwise it falls back to the newest 20 stable releases. Use --last N or --all to override that default.

Embedded raster-image retrieval is separate and opt-in:

    project-research sync owner/repository --download-images

It accepts PNG, JPEG, GIF, and WebP only, validates both content type and file signature, blocks non-public network addresses and unsafe redirects, and defaults to 8 MiB per image / 24 MiB total per sync. Skipped or failed source references remain in the original release body and their collection status is recorded locally.

## Local data

The default database is $XDG_DATA_HOME/project-research/releases.sqlite3, or ~/.local/share/project-research/releases.sqlite3 when XDG_DATA_HOME is unset. Override it with --db PATH on each command. The database stores canonical repository/release/tag/asset records, raw release payloads, distinct changed-payload observations, image retrieval status, and a rebuildable FTS5 index. Image files are stored beside the database under media/. No generated databases, archives, downloaded images, or release binaries belong in this repository.

Asset downloads require an explicit destination. The default maximum is 512 MiB; --max-bytes changes it. Existing files are not replaced unless --force is supplied. The tool never extracts or executes downloaded files. A .provenance.json sidecar records the source, release and asset IDs, local SHA-256, and publisher digest verification result when GitHub provides a supported digest.

## Development and tests

    python -m unittest discover -v
    python -m compileall -q src tests

Normal tests are offline and use mocked transport. Live GitHub collection is an explicit user-invoked operation, not part of the test suite. See docs/RELEASE_TRACKER.md and docs/PR1_SCOPE.md.
