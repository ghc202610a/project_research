# PR1 scope: release-tracker foundation

## Purpose and user outcome
Deliver the first practical vertical capability while establishing limited architecture seams that avoid GitHub-specific domain logic. Given a repository URL (including a nested GitHub URL) or owner/repository identifier, a user can collect and inspect GitHub releases, select historical ranges, preserve descriptions and metadata, generate archives, search release text, and explicitly download a selected asset with integrity checks where supported.

The tool works through a conventional CLI without an LLM or hosted service.

## Included

### Resolution and collection
- Accept GitHub repository URLs, nested URLs, and owner/repo notation.
- Use GitHub REST API through a provider adapter.
- Support GH_TOKEN and GITHUB_TOKEN; never print or persist credentials.
- Retrieve paginated releases and embedded asset metadata.
- Preserve raw payloads and normalized records.
- Handle errors, pagination, rate limits, and conservative retries.
- Distinguish published releases from tags without releases.

### Selection
- Inclusive date bounds; component-aware version/tag bounds.
- Last-N and all-release policies.
- Prerelease/draft controls.
- Default: prefer a clear current/previous major window where possible; otherwise bounded recent stable history with deterministic fallback.
- Sort chronologically by publication time, falling back to creation time; never sort versions lexically.

### Archive and search
- Per-release Markdown and aggregate Markdown/text/JSON.
- HTML index and PDF where a supported renderer is installed.
- Preserve source URLs, dates, tags, bodies, artifact metadata, and provenance.
- Optional bounded download of ordinary raster images embedded in release descriptions. Enforce per-file and total limits; validate content type and file signature; preserve external references when skipped.
- SQLite and full-text search over collected release text.
- Raw records separate from rebuildable indexes.
- Incremental sync detects new/changed releases and retains meaningful prior snapshots.

### Artifact inventory and explicit retrieval
- Index asset name, URL, size, content type, timestamps, publisher digest where available.
- No bulk binary downloads by default.
- Explicit asset selection/download; tentative command name evince needs review because of GNOME document viewer name collision.
- Reject ambiguous matches; validate destination paths and filenames.
- Stream to temporary files, enforce limits, compute local SHA-256, verify publisher digest when supplied, atomically publish verified files.
- Write provenance sidecar. Never automatically extract or execute artifacts.

## Architectural requirements
Provider API calls and response parsing remain in the GitHub adapter. Selection, storage, rendering, search, and artifact handling use canonical records. Preserve native IDs, original payloads, stable internal identifiers, source URLs, and retrieval timestamps. Optional dependencies remain optional. No mandatory LLM, embedding, graph database, or network-service dependency. Keep interfaces small.

## Explicit exclusions
Other forge implementations; full commit mining; issues, PRs/MRs, discussions, comments; global discovery and external dataset ingestion; automatic manifest generation; RDF/OWL implementation or triple store; vector search, embeddings, clustering, LLM synthesis; MCP server and multi-user service; automatic artifact extraction/installation/execution; general package manager or dependency resolver.

These are future directions, not hidden PR1 requirements.

## Suggested boundaries
Provider interface and GitHub adapter; URL/repository resolution; canonical models and normalization; collection/sync; selection; persistence/search; Markdown/HTML/PDF rendering; bounded media handling; artifact inventory and verified downloads; CLI/tests. Exact module layout may change. Do not add abstractions without a current consumer.

## Acceptance criteria
1. Clean install and CLI help.
2. Tests for URL parsing, normalization, date/version selection, pagination, media validation, asset matching, path validation, digest verification.
3. Mocked API collection without credentials/network.
4. Live checks opt-in; ordinary tests offline.
5. Repeat sync avoids duplicates and needless media downloads.
6. Search returns release text and provenance.
7. Explicit asset download is safe and records local digest; publisher digest checked only when available.
8. Syntax checks, tests, and git diff --check pass.
9. Docs explain limitations, selection, data layout, rate limits, generated-data exclusions.
10. No generated archive/database/artifact files committed.

PR1 should be one coherent feature. Prefer small clear interfaces over speculative framework code; record material deviations.
