# ADR 0001: Provider-neutral domain model

- Status: Accepted
- Date: 2026-11-12

## Context
The initial use case is GitHub release tracking, but the intended system may collect project information from GitHub, GitLab, Forgejo/Gitea, SourceHut, Pagure, Launchpad, Git itself, package registries, project websites, and external datasets.

These sources expose overlapping but non-identical concepts. Embedding one provider's API objects directly into the application domain makes interoperability expensive and conflates provider limitations with general project concepts.

## Decision
Use provider adapters to translate source-specific records into a provider-neutral canonical domain model.

Preserve provider instance, native object type and ID, source URL, raw payload where practical, retrieval timestamp, and provider-specific extensions. Keep project identity distinct from repository identity. Declare provider capabilities rather than assuming every provider supports every operation.

Application logic such as release selection, storage, rendering, and search operates on canonical records rather than provider response objects.

## Consequences
Positive: a second provider can be evaluated without redesigning every application layer; limitations can be represented explicitly; native data and identifiers remain available; CLI, REST, and agent interfaces can share domain concepts.

Costs: normalization requires careful mapping; canonical concepts must accommodate differences without false equivalence; the adapter boundary must be validated by implementation rather than over-abstracted.

## Scope
This establishes direction. It does not require multiple providers, a universal forge API, ontology, graph database, or external dataset connectors in the first release-tracker increment.
