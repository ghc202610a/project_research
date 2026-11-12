# Release tracker: implementation notes

## Status

Initial local CLI implementation. GitHub is the only implemented provider. The data model and application interfaces remain provider-neutral where they have a real first consumer; this is not yet a general forge abstraction framework.

## Commands

- sync REPOSITORY: fetch repository metadata, paginated GitHub releases, and paginated Git tags. Store normalized records and raw release payloads. Repeated syncs update current records and add a raw observation only when a release payload changes.
- list REPOSITORY: display the default stable selection or a user-defined date/version/last-N/all selection.
- tags REPOSITORY: show tags and whether each tag has a corresponding published release.
- assets REPOSITORY: inspect asset metadata without downloading binaries.
- search QUERY: FTS5 search over locally collected release text and metadata.
- rebuild-index: rebuild the derived FTS5 index from canonical release records.
- export REPOSITORY: generate aggregate Markdown, text, JSON, HTML, optional PDF, or per-release Markdown files.
- asset download REPOSITORY SELECTOR: explicitly download one exact asset by numeric ID or unique filename.

REPOSITORY accepts owner/repo, a repository URL, or a nested GitHub URL such as a release/tag page. The initial adapter supports github.com only; enterprise hosts and other forges are future work.

## Collection and provenance

The adapter uses GitHub REST API v3 with the 2022-11-28 API version header. GH_TOKEN takes precedence over GITHUB_TOKEN. API requests have timeouts, bounded retries for transient server errors and rate limits, conservative retry delays, and pagination-link validation. Tokens are not logged or persisted. API responses are bounded to 32 MiB.

The SQLite database separates current canonical release records from raw release payloads and changed-payload observations. Repository identity includes provider and host; native GitHub IDs and source URLs are retained. Release assets are normalized into an inventory. Git tags are stored separately because a tag does not imply a published release. Release collection is additive: records no longer returned by the provider are not silently deleted. Tag records are also additive; deletion reconciliation and tag history are not yet implemented, so a tag removed upstream can remain in the local inventory.

The FTS5 table is a derived index and can be rebuilt from canonical release records with rebuild-index. It is not evidence storage. Search results retain repository, tag, release URL, title, and a body snippet for provenance.

## Selection

Date bounds are inclusive; a date-only --until YYYY-MM-DD includes the entire date. Version comparison uses numeric components and SemVer-like prerelease ordering. Non-numeric tags are excluded when version bounds are used. Releases are ordered by publication timestamp, falling back to creation timestamp, then native ID; version strings are never sorted lexically.

The default excludes drafts and prereleases. It prefers stable releases in the newest numeric major and the immediately preceding major, where tags make that meaningful; otherwise it falls back to the newest 20 stable releases. --last N and --all override the default selection. --include-prereleases and --include-drafts are explicit.

## Archives

Aggregate formats: Markdown, text, JSON, HTML, and optional PDF (requires WeasyPrint; install with the pdf extra). --per-release with Markdown writes one Markdown file per release plus an index. Release descriptions are preserved as source text; HTML rendering escapes release body content rather than interpreting untrusted HTML as markup.

## Embedded images

Image collection is opt-in with sync --download-images. It recognizes common Markdown and HTML image references and retrieves only PNG, JPEG, GIF, or WebP. Defaults are 8 MiB per image and 24 MiB total per sync. Content type and file signature must agree. The collector rejects embedded credentials, blocks non-public resolved addresses, and validates redirects to reduce SSRF risk. It uses content hashes for local filenames and reuses previously downloaded images when the local copy still exists. The original release body and image URL remain preserved if an image is skipped or fails; status and provenance are stored in SQLite. This is bounded retrieval, not a general web crawler.

## Explicit asset downloads

Asset binaries are never fetched during sync. The user must select an asset by numeric GitHub asset ID or an exact filename that resolves to one record. Ambiguous filenames are rejected. The destination is explicit, existing files require --force, and downloads are streamed to a temporary file with a configurable size cap. A local SHA-256 is calculated; GitHub's publisher digest is checked when it is present and supported. The file is atomically published after successful checks, with a JSON provenance sidecar. The tool never extracts or executes the result.

## Known limitations and next review points

- Only GitHub.com is implemented; no GitLab, Forgejo, Gitea, Git transport, package registries, or external dataset adapters.
- Collection currently fetches the full paginated releases and tags listings each time; local writes are idempotent for unchanged release payloads, but API-side incremental/conditional requests are not implemented.
- Git tag deletion reconciliation and tag history are not yet tracked.
- Release-media status is stored separately, but archive renderers currently retain the original external image references rather than rewriting them to local media paths.
- HTML output is deliberately conservative; it presents release descriptions as escaped text rather than rendering full Markdown.
- PDF output depends on optional WeasyPrint and its system dependencies.
- There is no automatic artifact extraction, installation, execution, or bulk binary download.
- No REST service, MCP server, embeddings, graph store, LLM integration, or multi-user service is included.

These boundaries keep the first increment local, deterministic, auditable, and useful without AI services.
