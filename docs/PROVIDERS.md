# Provider and source integration model

## Principle
GitHub is the first provider, not the canonical domain model. Core application logic consumes provider-neutral records and explicit capability declarations.

Candidate providers include GitHub.com/Enterprise, GitLab.com/self-hosted GitLab, Forgejo, Gitea, SourceHut, Pagure, Launchpad, and other project infrastructure.

## Source categories
1. Forge APIs: repository metadata, releases, issues, pull/merge requests, discussions, comments, labels, attachments.
2. Git transport: commits, branches, tags, trees, source snapshots.
3. Project-maintained sources: release pages, documentation, mailing lists, forums, websites.
4. Package ecosystems: registries, manifests, dependency metadata, artifacts.
5. Distribution/ecosystem sources: package metadata, build systems, compatibility reports, downstream patches.
6. External aggregators: repository catalogs, event archives, dependency datasets, project indexes.
7. Web discovery: search results and pages used to discover or corroborate information.

A logical project may link to multiple repositories, providers, trackers, package namespaces, and documentation sources.

## Adapter responsibilities
Handle provider-specific URL parsing and identity; authentication without exposing credentials; API calls and pagination; rate limits, retries, conditional requests, and error mapping; capability discovery; canonical translation; raw payload and native ID retention.

Adapters do not own general selection policy, cross-provider ranking, rendering, ontology semantics, or suitability judgments.

## Capabilities
Capabilities vary by provider and installation. Examples: repository metadata, tags, commits, releases, artifacts, issues, change requests, discussions, comments, attachments, repository search, and event history.

A missing capability is not an empty result. Distinguish unsupported, unavailable, permission-denied, not collected, and successfully collected with no results. Discover capabilities at runtime where practical.

## Git versus forge
Git provides portable commits, refs, tags, and trees. It does not standardize forge releases, issue trackers, discussions, reviews, labels, or project metadata. Do not equate a tag with a published release.

## External datasets
ecosyste.ms, GH Archive, Libraries.io, and deps.dev are candidate sources, not required dependencies or authorities. Assess current coverage/update cadence, hosts/object types, limits, licensing/attribution, identifier stability, provenance/freshness, and suitability for discovery versus authoritative retrieval. Preserve external identifiers and retrieval context.

## Initial boundary
The first release-tracking increment uses a GitHub adapter. Selection, storage, rendering, search, and artifact handling operate on canonical records. Add another provider after exercising the initial boundary.
