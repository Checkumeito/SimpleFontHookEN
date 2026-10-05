# CatSystem2 Adapter

## Responsibilities

This directory adapts the file font path in classic CatSystem2. The engine first loads TTF,
OTF, or TTC bytes from `font/` in the game root directory, then uses FreeType to generate
glyphs. Replacing only GDI `HFONT` therefore cannot cover the actual text on screen.

This adapter is separate from `CatSystemUnity` in the Unity directory. That adapter handles
Mono/IL2CPP and TextMeshPro objects; this directory only handles classic CatSystem2 Win32
file fonts and font resource registration.

## Detection

The adapter requires the main module to meet all of the following contract conditions:

- A `CatScene` or `cs2confx` engine marker is present.
- Both `kcFontImage_Win` and `kcFontImage_FT` font backend markers are present.

Generic GDI imports, the `font` directory, a single font filename, and the `.int` suffix do
not independently determine identity. Detection results are cached per process;
high-frequency file paths only read the cached results.

## File Entry Points

- `font/*.ttf`
- `font/*.otf`
- `font/*.ttc`
- `font/*.otc`

When the physical directory exists, its original enumeration remains unchanged. Each
read-only font file open, `AddFontResourceA/W` registration, and corresponding
`RemoveFontResourceA/W` removal is redirected to the real file for the currently selected font.

When the physical directory is missing, empty, or lacks the target font entry, the adapter
uses the following fallback:

1. Publish virtual directory attributes for the missing `font` root directory.
2. Publish one `SimpleFontHook.*` font entry after the real `FindFirstFile` or
   `FindFirstFileEx` fails.
3. The search handle comes from the actual font file, so the corresponding `FindNextFile`
   and `FindClose` retain their original Win32 semantics.
4. Opening the virtual path still redirects to the real font source through the unified file
   dispatcher.

Game directories are not created, deleted, or written to.

## Font Sources

Font sources are resolved in this order and cached by `ConfigVersion`:

1. The system or current-user font file corresponding to `SourceFontNameW`.
2. The font file corresponding to `ForcedFontNameW`.
3. `FontFileName` or a local SFNT file in the DLL root directory.

The adapter follows the general `EnableFontHook` and `EnableFaceNameReplace` switches and
defines no engine-private configuration. If either switch is disabled, the font source is
unavailable, or identity detection fails, all APIs retain their original behavior.

## Runtime Constraints

- Only redirect read-only opens; do not take over writes, creation, or deletion.
- Configuration notifications invalidate the font source cache. File opens after a version
  notification use the current snapshot.
- FreeType faces already created by CatSystem2 are not forcibly destroyed on unknown threads.
  Scenarios that need to reread font files rely on the engine's own reload or the next process
  startup.
- Virtual enumeration only intervenes after the original search fails. Other resources and
  ordering in the physical `font` directory remain unaffected.

## Diagnostics

With `EnableDebugLog=1`, inspect `[DEBUG][CatSystem2]`:

- `engine-probe`: identity and font backend contract.
- `font-source-ready`: the real file resolved from the currently selected font.
- `font-open-redirect`: redirection of physical or virtual font file opens.
- `font-search-fallback`: virtual enumeration for a missing directory or entry.
- `font-register-redirect`, `font-unregister-redirect`: redirection of font registration and removal.

Both Win32 and x64 Release must remain buildable; classic CatSystem2 samples generally use
the Win32 build.

## Evidence and Reproduction

1. Record matches for `CatScene`/`cs2confx` and `kcFontImage_Win`/`kcFontImage_FT` separately in
   the main module's readable image. Retain all four items in identity and capability groups.
2. Establish baselines with existing, empty, and missing `font/` directories. Call attribute
   queries, `FindFirstFile*`, `FindNextFile`, read-only opens, and font registration APIs
   separately.
3. Retain the source path, `ConfigVersion`, and SFNT extension from `font-source-ready`.
   Check that the virtual entry opens the same source through the unified file dispatcher.
4. Perform negative verification for writes, creation, deletion, paths outside the root
   directory, and non-font files.

| Scenario | Expected log/result |
| --- | --- |
| Both marker groups match and the directory contains fonts | `engine-probe` passes; read-only opens are redirected |
| Both marker groups match but the directory is missing | `font-search-fallback` publishes one virtual font entry |
| Only `CatScene` or only FreeType markers | Identity/capabilities are incomplete; file APIs pass through |
| Write or creation request | Call the real file APIs; do not generate game directories |
| Configuration notification | Resolve the current font source; existing FreeType faces are managed by the engine lifecycle |

The evidence directory contains sample hashes, directory trees, a single
`[DEBUG][CatSystem2]` log capture, configuration snapshots, and A/W API return values. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for the record format.

## Verification

Cover Win32/x64 builds, positive marker combinations, similar non-target modules, all three
physical directory states, TTF/OTF/TTC/OTC, registration and removal, disabled configuration,
missing font sources, non-ASCII paths, and read-only/write semantics.
