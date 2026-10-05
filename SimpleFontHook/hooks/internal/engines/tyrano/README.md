# TyranoScript Adapter

## Responsibilities

TyranoScript 5 usually runs in Electron/Chromium, where bundled `@font-face` fonts bypass the
game process's GDI font-creation path. This adapter replaces Web fonts through file
virtualization, ASAR overlays, and a JavaScript bridge.

## Adaptation Target

Chromium reads Web fonts from an unpacked directory or ASAR and maintains its own font cache in
the renderer process. Generic GDI and DirectWrite creation hooks are not the authoritative entry
points for this resource chain. The adapter must handle font-file contents, the `app.asar` or
`resources/app` storage root selected at Electron startup, and cache synchronization between the
main and renderer processes. Runtime configuration changes do not change the selected storage
root.

## Detection Conditions

Two layouts are supported:

- Unpacked directory: `resources/app/tyrano` exists, and `resources/app/package.json` contains
  a TyranoScript marker.
- ASAR: `resources/app.asar` can be parsed, and a positive TyranoScript marker is found in
  `package.json` or the `tyrano/` resource area.

The Electron runtime, `app.asar` filename, and `data/scenario` directory can be reused by other
applications and are not independent identity evidence.

Detection results are cached for the process lifetime. If ASAR header, JSON-length, or
index-boundary validation fails, `app.asar` visibility remains unchanged.

## File Structure

- `tyrano_web_fonts.cppinc`: Aggregation entry point, Web-font redirection, and configuration refresh.
- `tyrano_state.cppinc`: Detection, font-byte, ASAR-index, and logging state.
- `tyrano_detection.cppinc`: Unpacked/ASAR detection and `app.asar` visibility decisions.
- `tyrano_asar_parser.cppinc`: Bounded parsing of ASAR headers and file indexes.
- `tyrano_asar_overlay.cppinc`: Archive content and virtual attributes for unpacked paths.
- `tyrano_bridge.cppinc`: Injects the font-synchronization bridge into Electron's main and renderer processes.
- `../common/engine_font_export.cppinc`: Shared GDI font export and SFNT-data validation.

## Implementation

1. Confirm unpacked layouts through `package.json` and the `tyrano/` framework structure;
   confirm archived layouts through bounded ASAR parsing and Tyrano resources inside the archive.
2. The font exporter generates SFNT data for the current version. The Web-font handler returns
   read-only virtual handles for `.ttf`, `.otf`, and `.ttc` requests directly under `data/others`
   or in its subdirectories.
3. When a replacement font is available, compressed Web-font requests appear as missing files,
   allowing CSS font sources to continue to an SFNT fallback.
4. The ASAR index maps required archive entries to the `resources/app` view, overlaying only
   text, scripts, and missing or size-mismatched resources. Path normalization collapses `.`
   and `..` and rejects requests that escape the application root.
5. In-memory views of `main.js` and `tyrano/tyrano.js` append bridge code with a unique marker
   to synchronize font state between Electron's main and renderer processes. The CSS font-family
   list includes localized names, English names, and typographic-family candidates with numeric
   weight suffixes removed.
6. Configuration notifications clear the font-byte and injection-result caches and publish the
   current `ConfigVersion` to the bridge.

## Font Redirection

- `.ttf`, `.otf`, and `.ttc` requests directly under `resources/app/data/others` or in its
  subdirectories return SFNT data for the currently selected font. This covers both the
  generator's common `data/others/<face>.ttf` layout and manually organized
  `data/others/font/<face>.ttf` layouts.
- `.woff` and `.woff2` are hidden after replacement data is ready, allowing Chromium to fall
  back to replaceable SFNT font sources.
- Font bytes are cached by `ConfigVersion` and font name, and cleared after configuration changes.

## ASAR Overlay

Electron can load unpacked resources from `resources/app`; the ASAR index provides authoritative
content for text and scripts of the same name. Processes that started from `app.asar` continue
using the archive root; the adapter does not hide the archive during font switching. `main.js`
and `tyrano/tyrano.js` can have a bridge script with a unique marker appended, and repeated reads
share the same injection result. The persistent `app.asar.sfh` also validates bridge-slot
contents; after the DLL updates its bridge implementation, old caches rebuild automatically
even if the original archive timestamp has not changed.

## Rationale for the Design Constraints

- ASAR participates through a read-only index and overlay view, without modifying the original archive or depending on Electron's internal modules.
- `app.asar` visibility remains stable during process execution, preventing later `./data` and `./tyrano` relative requests from switching to nonexistent or incomplete loose directories.
- Large audio and video resources retain their real-file or archive paths; the overlay focuses on text, scripts, and necessary missing resources.
- Compressed fonts are hidden only once the SFNT replacement is ready, preventing all CSS font sources from becoming unavailable.
- The JavaScript bridge handles runtime synchronization; native file redirection remains an independently available resource path.
- Injection markers make repeated opens of the same script idempotent. Bridge content participates in ASAR cache identity, while the configuration version controls font-state updates.

## Configuration

- `EnableTyranoHook`
- `TyranoRedirectWebFonts`
- Generic `EnableFontHook`, `EnableFaceNameReplace`, and `ForcedFontNameW`

## Invariants

- Hide or redirect files only after complete positive Tyrano detection and successful replacement-font preparation.
- All file-open and attribute results pass through the engine file dispatcher; A/W entry points share classification logic.
- After collapsing `.` and `..`, archive paths must remain within the `resources/app` root.
- ASAR header sizes, JSON sizes, offsets, and file lengths must have limits and overflow checks.
- Handle only read-only opens; writes, creates, and truncations go to the real file APIs.
- The JavaScript bridge is an enhancement path; if it fails, native Web-font redirection can still work independently.
- Configuration changes only clear caches and notify the bridge; file hooks do not repeatedly export fonts.

## Evidence and Reproduction

1. Fix the SHA-256 hashes of `resources/app`, `resources/app.asar`, `package.json`, `tyrano/`,
   and the font directory; record unpacked and ASAR samples separately.
2. For unpacked layouts, check `resources/app/tyrano`, `package.json` markers, and font paths.
   For ASAR, save boundary-check results for header size, JSON size, index entries, offsets,
   and lengths.
3. Sequentially perform read-only opens, attribute queries, and Web-font fallback for `.ttf`,
   `.otf`, `.ttc`, `.woff`, and `.woff2` files directly under `data/others` and in
   `data/others/font`. Record SFNT byte hashes and `ConfigVersion`.
4. In `main.js` and `tyrano/tyrano.js`, record bridge markers, injection positions, repeated-read
   results, and main/renderer message order. If index validation fails, check that `app.asar`
   remains the real file.
5. Run negative samples covering writes, creates, truncations, non-Tyrano Electron applications,
   and damaged archives.

| Scenario | Expected Result |
| --- | --- |
| Unpacked framework + Tyrano marker | File-font and bridge paths are available |
| Complete ASAR index + Tyrano resources | Archive and unpacked views are routed according to the request |
| ASAR boundary/JSON/resource validation fails | `app.asar` visibility remains unchanged; calls the real API |
| SFNT preparation complete | Both `data/others` font layouts redirect according to configuration; compressed fonts are handled as fallback sources |
| Localized GDI name includes a weight suffix such as `75W` | CSS tries the original name, English name, and typographic-family candidates in sequence |
| DLL bridge implementation updated, original ASAR unchanged | `app.asar.sfh` rebuilds automatically because its bridge slot no longer matches |
| Write request or configuration disabled | File writes pass through; caches and the bridge preserve engine state |

The evidence directory contains ASAR-index summaries, font hashes, bridge logs, main/renderer
thread identifiers, and nontarget samples. For the record template, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover at least unpacked layouts, ASAR-only layouts, damaged ASARs, missing positive markers,
`.woff` fallback, SFNT redirection, bridge deduplication, feature disablement, font switching,
and non-Tyrano Electron programs.
