# Vision

## Summary
Build useful, composable utilities that can grow into a provider-neutral software-project research and information system. The first practical application is release tracking and archival. Longer-term capabilities include cross-forge project discovery, issue/change-request research, evidence-backed project manifests, and semantic knowledge representation.

GitHub is an initial provider, not the system's identity or permanent boundary.

## Problems
Software-project information is fragmented across forges, Git repositories, package registries, documentation sites, issue trackers, mailing lists, release announcements, and third-party datasets. One project may use several systems.

Native forge metadata often cannot reliably answer what a project does; which languages, platforms, architectures, runtimes, databases, protocols, and frameworks it uses or supports; which capabilities are implemented, experimental, planned, deprecated, or unsupported; what dependencies and integrations it has; what evidence supports compatibility claims; how it has changed; or which projects are similar.

Keyword search is inadequate when projects use different terminology. Generated summaries are inadequate when claims cannot be traced to evidence.

## Long-term direction
1. Collect from multiple source providers and public datasets.
2. Maintain a canonical, extensible representation of projects and related objects.
3. Preserve raw source records and normalized records.
4. Search metadata, documents, comments, releases, and source-derived text.
5. Generate evidence-backed manifests that can be reviewed, corrected, and regenerated.
6. Support lexical, semantic, graph, and statistical retrieval.
7. Compare projects and investigate compatibility and suitability.
8. Expose functionality through CLI, HTTP APIs, and agent interfaces such as MCP.
9. Support local/self-hosted deployment and replaceable services.

## Principles
- **Interoperability:** GitHub-specific identifiers, APIs, and assumptions must not define the domain model.
- **Evidence before interpretation:** source observations, source claims, derived claims, and research judgments remain distinct.
- **Preservation:** retain raw responses, original Markdown, media, references, and retrieval timestamps where practical and permitted.
- **Useful without AI:** deterministic collection, filtering, lexical search, structured queries, and APIs remain useful without LLMs or embeddings.
- **Incremental delivery:** validate abstractions against real use rather than building a universal platform prematurely.

## Non-goals
Replacing forges or package registries; treating an external catalog as complete or authoritative; treating generated claims as verified facts by default; requiring one cloud, LLM, vector, or graph vendor; automatically executing downloaded artifacts; or implementing every provider and semantic capability in the first release.

Success means answering practical questions with traceable evidence, distinguishing unknown from false, preserving history, and adding providers without rewriting core logic.
