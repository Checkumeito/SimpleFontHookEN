# Hooks Module

## Responsibilities

`hooks/` handles Detours installation, the font-replacement model, font API queries,
text drawing, and engine adaptation. Its public entry points are
`FontHooks::Install(HMODULE)`, configuration notification, and normal shutdown.

The generic hooks keep the same replacement font consistent across creation,
selection, drawing, measurement, identity queries, and raw font-data queries.
Changing only `CreateFont*` would expose contradictory font names, character sets,
or dimensions through query interfaces. These APIs therefore share one model and
cache system.

## Aggregate Structure

`font_hooks.cpp` includes `internal/**/*.cppinc` in a fixed order to form one hook
translation unit. This keeps original API pointers, Detours targets, font caches,
and engine state under internal linkage.

| Path | Responsibility |
| --- | --- |
| `font_hooks.h` | Public interface of the hook subsystem |
| `font_hooks.cpp` | Implementation aggregation and include order |
| `hook_policy.*` | Hook enablement, compatibility policy, and debug sampling |
| `internal/font_hooks_*.cppinc` | Installation, runtime, drawing, code pages, and text mapping |
| `internal/model/` | Font-replacement caches, logical font views, metrics, and glyph indices |
| `internal/queries/` | Font identity, enumeration, metric, and font-data queries |
| `internal/engines/` | Engine detection, resources, caches, and runtime bridges |

## Hook Categories

- `AttachFontCreationHooks`: `CreateFont*` and `CreateFontIndirect*`.
- `AttachRuntimeLibraryHooks`: GDI+, DirectWrite, and deferred module loading.
- `AttachTextDrawingHooks`: `TextOut`, `ExtTextOut`, and `DrawText`.
- `AttachDcFontSelectionHooks`: HDC and HFONT selection state.
- `AttachGlyphOutlineHooks`: Glyph bitmaps, outlines, and indices.
- `AttachTextLayoutMetricHooks`: Widths, extents, ABC metrics, and character spacing.
- `AttachFontIdentityQueryHooks`: `GetObject`, `GetTextMetrics`, and `GetTextFace`.
- `AttachFontEnumerationHooks`: Font-family and extended LOGFONT enumeration.
- `AttachGlyphMetricSupplementHooks`: Kerning and glyph-positioning information.
- `AttachFontDataQueryHooks`: SFNT tables, character ranges, languages, and outline metrics.
- `AttachDirectWriteHooks`: `DWriteCreateFactory` and factory vtables.

## Call Flow

1. `FontHooks::Install` loads configuration and prepares static detection that must finish before the Detours transaction.
2. `AttachHooksByCategory` attaches font, encoding, Profile, file, and runtime APIs by responsibility.
3. Font-creation hooks save the source `LOGFONT`, construct the target `LOGFONT` and replacement `HFONT`, and write a cache entry tagged with `ConfigVersion`.
4. Drawing and query hooks locate the same cached view using the HDC, original font, and replacement font, returning actual drawing results and application-facing logical properties respectively.
5. Engine file dispatch, managed runtimes, and deferred module paths cover resources invisible to generic font APIs.
6. Configuration notification clears or versions caches and dispatches application actions to the required threads.

## Font-Replacement Model

`internal/model/` organizes source LOGFONT, replacement LOGFONT, HFONT, configuration
version, and the external query view in one cache. The model supports font names,
character sets, dimensions, weight, vertical metrics, character spacing, line spacing,
and glyph-index aliases. Encoding conversion and text mapping use independent state;
text code pages are not inferred from the replacement font.

## Engine Adaptation

Engine adapters handle internal font resources, prerendered caches, archive content,
or managed runtime objects. See [internal/engines/README.md](internal/engines/README.md)
for the full engine list, detection rules, and directory documentation.

File-based adaptation consistently uses `engine_file_dispatch.cppinc`. Runtime
adaptation uses window messages, worker threads, Python pending calls, Mono/IL2CPP
thread attachment, or engine-function hooks.

## Rationale for Design Constraints

- Aggregated `.cppinc` files keep original API pointers, recursion guards, and cache state under internal linkage while file boundaries separate implementation responsibilities.
- `org*` pointers represent real system entry points. Hooks call APIs through them to prevent internal probing from causing recursion.
- Logical font views separate the replacement object actually used by the engine from the properties the application should see in queries, so compatibility with one query does not damage the real rendering object.
- `ConfigVersion` participates in cache identity, allowing distinct results for configurations with the same font name but different metrics, character-set capabilities, or font data.
- Expensive detection occurs during installation, preparation, or worker-thread stages; per-frame paths perform only cache lookups and bounded conversions.

## Lifecycle

1. `FontHooks::Install` loads configuration and prepares static adaptation state.
2. The Detours transaction attaches public APIs and engine functions by hook category.
3. Deferred-module, runtime, and font-picker threads start after the transaction commits.
4. Configuration application increments `ConfigVersion` and notifies caches and engines.
5. Normal shutdown stops worker threads and closes handles; process detach only publishes a shutdown signal.

## Extension Rules

1. Place added APIs in the `Attach*Hooks` category matching their responsibility.
2. Keep original function pointers and hook handlers in the same aggregate translation unit.
3. Centralize compatibility decisions in `hook_policy.*`.
4. Use cached state, bounded lookups, and sampled logs in high-frequency paths.
5. Publish engine-specific file behavior through the common file dispatcher.
6. Give each new engine directory an independent README and register it in the engine index.

## Validation

Generic-hook validation covers font creation, HDC selection, drawing, queries, cache
hits, disabled configuration, and the picker thread. Engine-adaptation validation
covers positive detection, negative detection, configuration-version refresh, and
target architecture. C++ changes require both Win32 and x64 Release builds.

## Evidence and Reproduction

Static entry points are `font_hooks.cpp`, `font_hooks.h`, `hook_policy.*`, and the
`Attach*Hooks` functions. Runtime entry points are `FontHooks::Install`, configuration
notification, and shutdown. To reproduce a generic font path, pin the process
architecture and `FontHook.ini`. First record creation/query/drawing results without
the adaptation installed; then enable hooks by category and compare `ConfigVersion`,
cache hits, and `org*` fallback logs.

| Scenario | Check entry point | Expected result |
| --- | --- | --- |
| Font creation | `AttachFontCreationHooks` | Saves the source `LOGFONT` and returns a replacement `HFONT` in a versioned cache |
| Queries/metrics | `AttachFontIdentityQueryHooks`, `AttachTextLayoutMetricHooks` | The query view and drawing object use the same configuration version |
| Internal probing | `EngineCommon::IsInternalFileQuery` | Adapter probes read through real APIs without entering virtual paths |
| Configuration disabled | `FontHooks::NotifyConfigChanged` | Caches become invalid; a cache miss calls `org*` |
| Non-target process | Identity-policy cache | No engine-specific logic is installed |

Record logs, configuration snapshots, sample hashes, and commands using
[Feature Evidence and Reproduction](../../docs/reproduction.md). Retain only bounded
sampling for high-frequency APIs.
