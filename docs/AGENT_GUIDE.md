# Guidance for coding agents and contributors

## Before changing code
1. Read the root README and relevant docs.
2. Identify scoped feature and acceptance criteria.
3. Inspect existing code, tests, conventions, and history.
4. Check whether another utility already implements reusable behavior.
5. Distinguish agreed requirements from exploratory roadmap items.
6. Preserve prior decisions unless explicitly revising them.

## Architectural constraints
- Keep provider-specific behavior inside adapters.
- Use canonical records in storage, selection, rendering, and search.
- Preserve provider-native IDs and raw payloads where practical.
- Record provenance, retrieval time, and collection completeness.
- Distinguish observed facts, source claims, derived assertions, and judgments.
- Missing information is not a negative assertion.
- Keep AI/ML and graph capabilities optional until scoped.
- Prefer small working abstractions over speculative frameworks.
- Add databases/services/dependencies only for concrete needs with documented tradeoffs.

## Implementation quality
Add focused tests for behavior and failure cases. Keep normal tests deterministic/offline; live API checks opt-in. Handle pagination, rate limits, retries, timeouts, and partial failures. Treat remote content and filenames as untrusted. Bound downloads/parsing; never execute downloaded artifacts. Never log secrets or commit credentials, generated datasets, caches, databases, or downloaded binaries. Update docs with behavior changes.

## Validation and reporting
Run relevant tests and syntax checks, inspect outputs, and run git diff --check. Review the full diff for unintended files, generated data, secrets, and scope creep.

Report files changed, behavior added, checks actually run and results, checks not run and why, limitations, and deviations. Never claim checks passed unless executed.

## GitHub workflow
Use a focused branch and target main unless instructed otherwise. Prefer draft PR while under review. Never merge without explicit authorization. Do not force-push or rewrite shared history without approval.

Roadmap/concepts are planning material, not authorization to implement everything in a narrowly scoped PR. Record consequential decisions in ADRs.
