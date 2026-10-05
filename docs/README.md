# Project Documentation

`docs/` maintains facts shared across modules: process architecture, configuration
contracts, evidence reproduction, build and release requirements, diagnostics,
and architecture decisions. README files in source directories explain each
module's responsibilities and implementation. This division gives stable rules
one authoritative location while keeping module documentation close to entry
points, state, and runtime constraints.

| Document | Contents |
| --- | --- |
| [architecture.md](architecture.md) | Process entry point, module interfaces, data flow, threads, and cache lifecycle |
| [configuration.md](configuration.md) | `FontHook.ini` options, defaults, and scope |
| [reproduction.md](reproduction.md) | Feature evidence levels, fixed samples, contract extraction, reproduction steps, and verification matrices |
| [build-and-release.md](build-and-release.md) | Win32/x64 builds, DLL size, exports, and release workflow |
| [diagnostics.md](diagnostics.md) | Logs, crashes, stalls, and compatibility troubleshooting |
| [adr/README.md](adr/README.md) | Architecture decision record rules and template |
| [Engine Adapters](../SimpleFontHook/hooks/internal/engines/README.md) | Responsibilities, detection conditions, configuration, and runtime constraints for all engines |

Module documentation resides in the corresponding source directory. The root
`CONTRIBUTING.md` governs rules shared across modules. Module README files describe
current responsibilities, entry points, workflows, configuration, and invariants.

## Reading Path

1. Read [architecture.md](architecture.md) first to understand proxy loading, hook aggregation, configuration versions, and thread lifecycles.
2. Continue to the module README for the task. Start engine-related work at the [Engine Adapter Index](../SimpleFontHook/hooks/internal/engines/README.md).
3. To confirm a feature's evidence or reproduce it on another sample, follow [reproduction.md](reproduction.md) to fix inputs, record evidence, and execute the verification matrix.
4. Also check [configuration.md](configuration.md) for user configuration changes and [build-and-release.md](build-and-release.md) for build outputs.
5. Use [diagnostics.md](diagnostics.md) as the common reference for runtime failures, compatibility decisions, and log semantics.

## Content Boundaries

- README files describe responsibilities, interfaces, workflows, configuration, and constraints verifiable from the current source.
- `architecture.md` documents data flow and lifecycle across modules without copying resource details for individual engines.
- `reproduction.md` defines evidence levels and the general reproduction workflow. Module README files retain concrete symbols, inputs, and expected outputs.
- ADRs record decisions that constrain multiple modules over the long term. Keep local implementation explanations in the relevant module README.
- Put parameters for a single sample and one-off logs in diagnostic records or commit context. Put stable contracts in the relevant module README.
