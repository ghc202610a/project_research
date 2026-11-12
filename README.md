# project_research

A provider-neutral system for collecting, preserving, searching, and researching software-project information across forges, source repositories, package ecosystems, project websites, and external datasets.

GitHub is the initial provider and release tracking is the first practical application. Neither defines the permanent domain model or limits future source integration.

## Project documentation
- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data and knowledge model](docs/DATA_MODEL.md)
- [Provider and source integration](docs/PROVIDERS.md)
- [Roadmap](docs/ROADMAP.md)
- [Concepts to explore](docs/CONCEPTS_TO_EXPLORE.md)
- [PR1 scope](docs/PR1_SCOPE.md)
- [Agent and contributor guide](docs/AGENT_GUIDE.md)
- [Architecture decisions](docs/adr/README.md)

## Principles
1. Prefer interoperable formats, open protocols, and replaceable components.
2. Separate provider-specific adapters from provider-neutral application logic.
3. Preserve source material, provenance, and historical observations.
4. Keep deterministic CLI/API functionality useful without an LLM.
5. Treat AI/ML output as derived, revisable interpretation—not ground truth.
6. Deliver useful capabilities incrementally; do not require the entire envisioned platform first.

Documentation describes intended architecture and planned scope, not proof that a feature exists. Verify implementation and tests.