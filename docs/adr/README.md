# Architecture Decision Records

ADRs record design decisions that constrain multiple modules over the long term
and may need reevaluation by maintainers. They explain where constraints come
from, the basis for the current approach, and the verification evidence it needs.
Source code and module README files maintain local implementation details,
temporary compatibility parameters, and behavior within a single module.

## ADR Scope

Architectural tradeoffs often cannot be recovered from the final code alone.
For example, aggregate translation units keep state local in exchange for
encapsulation boundaries, while file virtualization accepts centralized coupling
in exchange for unified priorities. ADRs preserve the context and cost of a
tradeoff so reviews can determine whether its constraints still apply and tie
that judgment to reproducible evidence.

## When to Record a Decision

- Changing the aggregate translation unit strategy for hooks.
- Introducing a new runtime dependency or proxy loading method.
- Changing the separation of responsibilities among font replacement, charsets, code pages, and character mapping.
- Establishing a new cross-engine file virtualization or cache refresh mechanism.
- Accepting an approach with known costs that compatibility constraints prevent eliminating.

## Naming

Use a four-digit sequence number and a short English identifier for filenames:

```text
0001-single-hook-translation-unit.md
0002-separate-font-and-codepage.md
```

Use these statuses: `Proposed`, `Accepted`, `Superseded`, `Deprecated`. Do not
directly rewrite the conclusion of an accepted ADR. Create a new ADR for a new
decision and link the superseding relationship in both documents.

## Content Boundaries

- "Context" contains only the facts and constraints on which the decision depends.
- "Decision" specifies module boundaries, interfaces, and required invariants.
- "Consequences" records benefits, costs, failure modes, and maintenance responsibilities together.
- "Alternatives" explains how rejected approaches conflict with the current constraints.
- "Verification" specifies builds, tests, or runtime checks that can falsify the decision's assumptions.
- "Evidence" lists files, symbols, commands, sample hashes, and expected log fields.

## Template

```markdown
# ADR-NNNN: Title

- Status: Proposed
- Date: YYYY-MM-DD
- Supersedes: None
- Superseded by: None

## Context

Conflicts, constraints, and known facts that need to be addressed.

## Decision

The chosen approach, its interfaces, and its invariants.

## Consequences

Benefits, costs, risks, and maintenance requirements.

## Alternatives

Approaches considered but not adopted, and the reasons.

## Verification

Build, test, or runtime evidence needed to establish that the decision holds.

## Evidence

Files, symbols, commands, sample hashes, configuration snapshots, and expected log fields.
```
