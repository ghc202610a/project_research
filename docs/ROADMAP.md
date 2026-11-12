# Roadmap

Directional plan; ordering may change. Items become commitments only when scoped into an increment.

## Stage 0 — Architecture/documentation baseline
Record provider-neutral direction, release-tracker scope, agent guidance, and decisions.

## Stage 1 — GitHub release tracker
Repository resolution; release collection; canonical release/artifact records and raw preservation; historical selection; archive rendering; SQLite/FTS; bounded image collection; incremental sync; explicit verified asset downloads; tests and CLI docs.

## Stage 2 — Validate provider abstraction
Review adapter boundary; evaluate GitLab or Forgejo/Gitea; compare release/tag/asset semantics and capabilities; refine identity and mappings from real differences.

## Stage 3 — Shared retrieval and service foundation
Consolidate genuinely shared API, persistence, provenance, and search components. Provide HTTP API. Evaluate network-first MCP Streamable HTTP over TCP, with optional stdio. Separate read-only search from permissioned collection/download. Support self-hosting and access controls.

## Stage 4 — Project research
Cross-forge repository metadata; issues and change requests with configurable depth; index plus original post and sampled comments; on-demand full-thread expansion; historical state/edit observations; discussions where supported.

## Stage 5 — External datasets and discovery
Evaluate ecosyste.ms, GH Archive, Libraries.io, deps.dev, and other datasets for freshness, coverage, licensing, and API suitability. Use as discovery/enrichment, not canonical truth. Resolve projects across forges, registries, sites, and trackers. Support unseeded natural-language exploration.

## Stage 6 — Project manifests and intelligence
Versioned evidence-backed manifests; languages, platforms, architectures, build systems, capabilities, dependencies, integrations, limitations; distinguish claims, observations, tests, reports, inferences, and unknowns; human review; lexical/structured filtering before optional embeddings/clustering.

## Stage 7 — Semantic knowledge layer
Survey vocabularies; foundational entity/property/relation/assertion/evidence concepts; evaluate RDF/RDFS/OWL/SHACL/SPARQL/JSON-LD and property graphs; domain ontologies and mappings; graph reasoning against concrete queries; connect graph with relational, full-text, vector, and temporal stores through IDs and provenance.

## Stage 8 — Research synthesis and reassessment
Evidence-ranked comparison and dossiers; optional LLM-assisted planning/synthesis/manifests; periodic reassessment; reproducible snapshots and model/ruleset versions.

## Cross-cutting constraints
No mandatory LLM/embedding provider. No single forge or external dataset is authoritative. Keep evidence separate from interpretation. Prefer local/self-hosted operation and replaceable dependencies. Each stage delivers useful capabilities independently.
