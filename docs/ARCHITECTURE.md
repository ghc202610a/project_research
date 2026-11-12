# Architecture

## Status
Target logical architecture, broader than the first implementation. Components are introduced when a concrete use case justifies them. Initially this may be one modular application, not distributed services.

## Logical layers
1. **Source adapters:** forges, Git, package registries, project websites, search engines, external datasets.
2. **Collection and normalization:** pagination, retries, incremental sync, parsing, canonical mapping.
3. **Preservation and provenance:** original payloads, documents, media, references, retrieval timestamps, collection status.
4. **Canonical domain services:** project/repository identity, releases, tags, commits, issues, change requests, discussions, artifacts, observations.
5. **Storage and indexes:** relational records, object storage, full-text indexes, optional graph and vector indexes.
6. **Analysis and enrichment:** extraction, classification, entity resolution, embeddings, clustering, LLM-assisted manifest generation, validation.
7. **Interfaces:** CLI, HTTP REST API, MCP over Streamable HTTP, optional local integrations.
8. **Applications:** release tracking, project discovery/research, comparisons, evidence-backed dossiers.

## Boundaries
Provider adapters translate source-specific behavior into canonical records. They do not own selection policy, rendering, general search semantics, or domain-wide business logic. Domain services do not depend on GitHub response shapes; they consume canonical objects and provider capability declarations.

Storage implementations should be replaceable behind small interfaces. Introduce shared components after concrete use cases demonstrate common behavior. Analysis output retains input evidence, model/ruleset identity, generation time, and review state.

## Interfaces and deployment
CLI is first-class. A conventional HTTP API exposes core operations independently of agent protocols. The intended agent direction is network-first MCP Streamable HTTP over TCP/IP; stdio may be optional compatibility, not the only integration path.

A future service needs explicit bind address, port, authentication, and access policy. Do not expose an unauthenticated service publicly by default. Separate read-only search from permissioned collection and download actions.

## Storage strategy
- Relational storage: normalized entities, relationships, synchronization state, transactions.
- Object storage/filesystem: original payloads, documents, media, artifacts.
- Full-text search: exact terms, identifiers, errors, phrases.
- Optional vector indexes: semantic retrieval.
- Optional RDF/triple or property graph: ontology-backed relationships and reasoning.
- Temporal observations/events: historical state.

Stable internal identifiers and provenance connect stores. Search indexes are rebuildable; preserved source records are durable.

## Typical flow
Resolve project reference; select adapter and discover capabilities; fetch with pagination/rate-limit handling; preserve original records; normalize canonical entities; record observations and completeness; update indexes; optionally derive assertions; expose through CLI, REST, and agent interfaces.

## Reliability and security
Never log credentials. Respect rate limits and retry guidance. Treat remote content, filenames, archives, and attachments as untrusted. Bound downloads and parsing. Never execute downloaded artifacts or embedded content. Preserve incomplete collection status. Record dataset licensing constraints. Avoid destructive sync and retain meaningful history.

The first release tracker validates architecture seams; it is not a distributed platform.
