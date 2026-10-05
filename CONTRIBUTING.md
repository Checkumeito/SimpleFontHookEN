# Contribution and Coding Rules

This document defines the project rules for feature development, compatibility
adaptation, structural changes, and documentation maintenance.

## Before Making Changes

1. Read the root `README.md`, `docs/architecture.md`, and the target module's README.
2. Identify whether the change belongs to general hooks, font data, UI, configuration, or an engine adapter.
3. Reuse existing interfaces and state first. Do not duplicate the same checks across multiple hooks.
4. Preserve the default behavior of existing user configurations. Extended behavior must be disableable or automatically detected through verifiable conditions.

## Modules and File Placement

- `dllmain.cpp` handles only the installation entry point and shutdown signal. It contains no business logic.
- Place general Detours handlers in `hooks/internal/font_hooks_*.cppinc`.
- Place the font replacement model in `hooks/internal/model/` and font query adapters in `hooks/internal/queries/`.
- Place engine-specific detection, caches, and resource conversion in `hooks/internal/engines/<engine>/`.
- Place raw SFNT font table modifications only in `font/`.
- Place UI drawing, input, and configuration application in `ui/internal/paint`, `input`, and `font_picker_apply_config.cppinc`, respectively.

Do not create a module for a forwarding function with only one call site. A module
should encapsulate substantial implementation complexity behind a small interface
and improve the locality of changes.

## Hook Rules

1. Save the original function pointer before installing Detours.
2. Prefer `org*` pointers when calling real APIs from hooks.
3. Explicitly handle the picker thread and internal font probes so that probing does not trigger font replacement again.
4. Save state before high-risk calls. Restore HDC, font, and thread state on every success and failure path.
5. Do not wait for threads or perform operations that may acquire the loader lock in the `DllMain` shutdown path.
6. Add hooks to the corresponding `Attach*Hooks` group. Do not accumulate unrelated logic in the installation function.

## Font and Encoding Rules

- Font names, HFONTs, font tables, and text byte streams have separate responsibilities and must not be processed together.
- Changing fonts must not automatically force CP932, CP936, or any other code page.
- Charset replacement changes only explicit charset interfaces. Code page redirection changes only conversion interfaces. Character mapping changes only character data after mapping is enabled.
- ANSI text first uses the charset detected during the application's original font creation. `TextSubstitutionCodepage` is only a fallback when detection is unavailable.
- Single-glyph ANSI parameters must account for both the character value's byte order and the target code page. Invalid sequences must not silently become another character.
- After modifying `cmap`, `name`, `OS/2`, `hhea`, or `head`, recalculate the affected table checksums and `checkSumAdjustment`.

## Engine Adapter Rules

1. Check configuration and low-cost path markers before scanning modules or parsing resources.
2. Cache detection results for the process lifetime.
3. General GDI, file, or window characteristics are supporting evidence only and cannot identify a specific engine on their own.
4. File extensions and general archive names only route candidates. Confirm identity through modules, exports, framework layouts, or engine resources in parsed containers.
5. If the engine does not match, do not modify import tables, file attributes, caches, or text data.
6. Route all file virtualization through `engine_file_dispatch.cppinc`. A/W hooks share the same priority logic.
7. Live switching must tag cache versions with `Config::ConfigVersion` and provide a failure fallback.
8. Maintain a separate README for each engine directory and register it in `hooks/internal/engines/README.md`.

## Performance and DLL Size

- Avoid heap allocation, disk access, module traversal, archive parsing, and unbounded logging in high-frequency hooks.
- Compute immutable probe results, paths, and resolved exports only once.
- Locks cover shared state only. Do not call engines, Python, Mono, or IL2CPP while holding a lock.
- Prefer existing Win32 APIs and the standard library. Do not add unnecessary runtime dependencies.
- Release builds retain function-level linking, string pooling, COMDAT folding, no RTTI, and size-oriented optimization.
- Record Win32/x64 DLL size changes when introducing large tables, template instantiations, or third-party libraries.

## Configuration Rules

- Declare configuration options in `framework.h` and provide defaults, saving, and loading in `utils.cpp`.
- Use `0/1` for Boolean options. Validate numeric ranges after loading.
- UI-editable options must update saved state, UI state, and the `NotifyConfigChanged` path together.
- Disabling an option should restore the behavior without this DLL installed.
- Provide compatible aliases or explicit compatibility parsing when renaming configuration keys.

## Threads and Lifecycle

- Worker threads must respond to `Utils::IsShuttingDown()` or their own stop event.
- The normal shutdown path stops threads and closes handles. `DLL_PROCESS_DETACH` only publishes the shutdown signal.
- Apply fonts across threads through window messages, events, or runtime-provided scheduling interfaces.
- Do not retain unpinned Mono/IL2CPP managed objects across GC cycles. Use runtime handles for long-term ownership.

## Logging Rules

- Debug logging is disabled by default.
- Sampling counters must limit high-frequency logs.
- Logs include at least a module tag, decision result, and key version numbers. Do not output large blocks of font or resource data.
- Compatibility decisions should record why behavior is enabled or skipped, rather than only the final failure.

## Documentation Rules

- Write documentation in English using UTF-8. Do not translate code identifiers, APIs, filenames, configuration keys, or engine names.
- README files describe current responsibilities, features, interfaces, configuration, invariants, lifecycle, and extension steps.
- Engine README files consistently include responsibilities, detection conditions, file entry points, features, configuration, runtime constraints, evidence, reproduction, and verification.
- Label key README conclusions as observed, inferred, or unconfirmed, and cite their files, symbols, commands, or log fields.
- Each engine README provides reproduction steps and expected results for positive, non-target, missing-capability, and boundary inputs.
- Describe the current state with wording such as "handles," "provides," "processes," and "supports." Keep code change history in commits or ADRs.
- Do not put temporary debugging steps, experimental parameters for one game, or one-off logs in README files.
- Keep each fact in a single authoritative location. Reference it elsewhere through relative links.
- Update documentation in the same change when modifying module interfaces, detection conditions, configuration, or thread lifecycle.
- Use this module README structure: Responsibilities, Entry Points and Dependencies, Workflow, Invariants, Configuration, Evidence and Reproduction, Extension Steps, Verification.

## Verification Checklist

- Documentation changes: Check relative links, heading hierarchy, UTF-8 encoding, and code identifiers.
- Documentation changes: Scan for subjective evaluations, temporal narratives, and unsupported conclusions.
- General C++ changes: Build Win32 and x64 Release.
- Proxy or linker changes: Compare export names and ordinals and confirm the target remains `winmm.dll`.
- Font table changes: Cover TTF, OTF, TTC, malformed input, and checksums.
- Engine changes: Cover at least positive detection, negative detection, disabled features, and live switching.
- Performance changes: Confirm high-frequency paths have no additional repeated scans, unbounded allocation, or unbounded logging.
