# Concepts to explore

Research backlog, not requirements. Promote ideas into roadmap/ADRs only after investigation and a concrete use case.

## External datasets
Evaluate ecosyste.ms repository/package/timeline/commit/issue/SBOM services; GH Archive; Libraries.io; deps.dev; and forge/distribution indexes. Investigate API health, cadence, history, host coverage, limits, licensing, attribution, exports, identifiers, completeness, and whether each source is useful for discovery, enrichment, or authoritative retrieval.

## Project intelligence and manifests
Explore versioned claims for purpose, domains, capabilities, non-goals, languages, OS/distributions, architectures, runtimes, hardware, build systems, toolchains, dependencies, package ecosystems, databases, frameworks, protocols, integrations, security, licensing, maintenance, maturity, health, limitations, and incompatibilities.

Define statuses such as documented, source-observed, tested, user-reported, inferred, planned, deprecated, contradicted, unknown, and not investigated. A generated manifest is not authoritative by default.

## Semantic knowledge representation
Research foundational ontologies; RDF, RDFS, OWL, SHACL, SPARQL, JSON-LD; property graphs; CodeMeta, schema.org, SPDX, and package vocabularies; ontology alignment and identity resolution; open-world/closed-world assumptions; temporal and provenance-aware assertions; named graphs and qualified relations; validation; reasoning profiles; triple-store and graph-database tradeoffs.

Start from representative queries and validation requirements, not technology fashion.

## Retrieval and AI/ML
Explore hybrid retrieval: exact lexical search for identifiers/versions/symbols/errors; metadata filters and relational joins; graph traversal; embeddings; clustering; reranking; LLM synthesis with citations to evidence. Evaluate reproducibility, model drift, embedding versioning, privacy, cost, local inference, and unsupported-claim risk.

## Project discovery
Explore natural-language query expansion into synonyms, topics, package ecosystems, and project categories. Preserve discovery paths and inclusion/exclusion reasons. Keep prominence, maintenance, maturity, technical fit, platform evidence, health, and usability as separate dimensions.

## Issue/discussion research
Investigate adaptive collection depth, comment sampling, bot/maintainer/user role classification, thread expansion, edit history, attachments, and completeness indicators. A search miss in an uncollected thread must not imply no relevant discussion exists.

## Service and agent interfaces
Evaluate REST pagination; MCP Streamable HTTP interoperability; optional stdio; authentication, authorization, audit; container/systemd deployment; asynchronous collection and status. Do not expose unauthenticated services publicly.

## Data governance
Investigate source licenses, API terms, attribution, retention, deletion/tombstone propagation, rate budgets, reproducible snapshots, backup/restore. Public availability does not imply permission to redistribute a dataset.
