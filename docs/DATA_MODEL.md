# Data and knowledge model

Conceptual direction, not a finalized ontology or migration-ready schema.

## Core entities
- **Project:** logical software product or coordinated effort.
- **Repository:** source-control repository associated with a project.
- **Provider instance:** particular forge/service host.
- **Release:** provider-published release or equivalent announcement.
- **Tag/reference:** Git reference, with or without a published release.
- **Commit:** source-control change identified by immutable object ID.
- **Change request:** pull request, merge request, or equivalent proposal.
- **Issue / discussion / comment:** tracked work, general thread, and response.
- **Artifact / attachment:** downloadable output or embedded media.
- **Package:** published package in an ecosystem.
- **Observation:** time-stamped observation of an entity or relationship.
- **Assertion:** statement about an entity, relation, or attribute, with provenance and epistemic status.
- **Evidence:** source material supporting, qualifying, or contradicting an assertion.

A project may have multiple repositories and provider representations. Project identity and repository identity are distinct.

## Identity
Use stable internal identifiers independent of URLs. Preserve provider-native identifiers in a namespace containing provider instance, object type, and native ID. URLs are locators, not sufficient identity. Model aliases, redirects, and migrations. Do not merge projects solely because names/descriptions match; retain candidate matches and evidence.

## Canonical and source records
Store normalized fields alongside original source payloads where practical and permitted. Preserve provider-specific extensions. Include provider identity, native identifier, canonical URL where known, retrieved-at timestamp, and collection status. Missing, unavailable, unsupported, not collected, and explicitly negative values are distinct.

## Assertions and provenance
An assertion should support subject, predicate, object/value, assertion kind (observed, source-claimed, inferred, tested, reported, reviewed), evidence references, observation and validity times, confidence with documented meaning, extraction method/model version, generation time, review state, and contradiction links.

Do not collapse evidence confidence, model confidence, and practical suitability into one score. A documentation claim that a project supports Linux and a successful CI run on a particular distribution/architecture are related but distinct assertions.

## Temporal model
Retain meaningful observations such as ownership, default branch, archive status, description, release metadata, issue state, and compatibility claims. Distinguish event time, observation time, and validity time where available.

## Semantic direction
Consider a foundational vocabulary for entity, class/type, individual, property, relation, quality, capability, function, process, state, event, role, assertion, and evidence; domain vocabularies for software, hardware, platforms, packages, networks, science, and organizations; mappings to existing vocabularies; graph representation; and validation constraints.

Evaluate RDF, RDFS, OWL, SHACL, SPARQL, JSON-LD, and property graph models. No triple store or graph database is selected.

## Project manifest
A manifest is a generated, revisable view of project knowledge, not the sole source of truth. Candidate content includes purpose, domains, capabilities, languages, platforms, architectures, integrations, dependencies, build systems, lifecycle, and limitations. Each claim retains evidence and a status such as documented, source-observed, tested, user-reported, inferred, planned, deprecated, contradicted, unknown, or not investigated. Define statuses before stabilizing a schema.

Lexical, vector, relational, and graph indexes are derived projections. Canonical records and source evidence remain durable.
