# YU-RIS Adapter

## Responsibilities

The YU-RIS adapter handles the path by which the engine reads prerendered font pages from YPF
archives. When identity, archive structure, font-page layout, and decoder entry points all match,
the adapter rasterizes `Config::SourceFontNameW` into the corresponding 32-bit atlas and writes
it into YU-RIS's WebP, PNG, or YDG decode buffers.

Resource identification, atlas generation, and decode replacement belong to the font-resource
path; script encoding, code-page conversion, text mapping, and ordinary image handling belong
to other modules. The adapter handles only registered font pages and sends other resources to
the default decoder.

## Entry Points and Dependencies

| File | Purpose |
| --- | --- |
| `yuris_font.cppinc` | Aggregates this directory's implementation in order; not compiled separately |
| `yuris_state.cppinc` | Runtime state, resource types, configuration snapshots, catalog index, and bounded caches |
| `yuris_profiles.cppinc` | Code-page candidates, byte layouts, atlas dimensions, pixel order, and style sets |
| `yuris_catalog.cppinc` | YPF v500 directory decoding, resource-catalog construction, and capability confirmation |
| `yuris_renderer.cppinc` | Generates font-page pixels using GDI `GGO_GRAY8_BITMAP` |
| `yuris_runtime.cppinc` | WebP/PNG/YDG entry points, chunk aggregation, configuration notifications, window refresh, and lifecycle |

`hooks/font_hooks.cpp` includes this directory's fragments in the aggregate translation unit.
The adapter depends on `EngineCommon` module and path queries, `Config` font settings, GDI font
APIs, and `HookWorkerThreadState` worker threads. File hiding, virtual attributes, and resource
redirection are handled uniformly by `engine_file_dispatch.cppinc`; this adapter does not
duplicate that dispatcher's logic.

## Identity, Capabilities, and Routing

The adapter handles three decision stages separately:

1. **Identity confirmation**: Confirm the YU-RIS runtime when the main module contains both
   `ysbin\\yscfg.ybn` and `yu-ris1`.
2. **Capability confirmation**: The worker thread enumerates `pac/*.ypf`, parses YPF `0x1F4`
   directories, and checks complete paths, page numbers, styles, image dimensions, and decoder
   modules against registered resource profiles.
3. **Resource routing**: After identity and capability are established, locate font pages using
   compressed sizes, FNV-1a fingerprints, or YDG chunk fingerprints; unmatched requests call
   the default decoder.

Filenames, the `.ypf` extension, and archive hint names affect only candidate ordering or
resource classification. Directory fields are decoded by trying the archive's preferred value,
the process ACP/OEM, UTF-8, and installed Windows code pages. The directory-encoding conclusion
does not participate in double-byte code-page selection for font pages.

Capability confirmation also includes decoder entry points:

- WebP: `YSWBP.DLL` ordinal 3.
- PNG: `YSPNG.DLL` ordinals 1 and 2.
- Relirium/YDG: The QOI decode core in the x86 main module that uniquely matches the registered function signature.

Single-image profiles are classified by compressed size and the complete FNV-1a fingerprint.
YDG profiles are classified by the complete chunk sequence: four chunks must match the same
font page at the same output-atlas base address. Chunk arrival order and duplicate chunks do
not change the classification result.

## Processing Flow

1. `IsIdentityConfirmed` caches the main-module identity result.
2. `Start` creates the `yuris-catalog` worker thread, which scans candidate YPFs and builds the
   catalog index and compatible page tables.
3. `InstallInOpenDetourTransaction` registers and attaches Relirium's QOI core in x86 targets;
   `MaybeWrapGetProcAddress` returns WebP/PNG wrapper entry points by module name and ordinal.
4. WebP and PNG entry points call the default decoder first, then use the catalog index to
   identify font pages. The YDG entry point collects four chunks and writes atlas pixels back
   only after a unique match is complete.
5. `RenderCatalogEntry` uses GDI glyph rasterization, checks `Config::ConfigVersion`, and stores
   results in a fixed-capacity atlas cache.
6. `NotifyConfigChanged` clears pending chunks and the atlas cache, posts `WM_FONTCHANGE` to
   windows in the current process, and requests repainting. If the snapshot version differs
   during rendering, discard the result and use the default decoder.
7. `Stop` stops the catalog thread and clears pending YDG atlases and the atlas cache.

## Resource Profiles

The code pages in the table are preferred values for structural automatic mode. At startup,
the adapter enumerates installed Windows code pages and keeps only candidates that can produce
the complete page counts, slot counts, and reserved positions for the byte layout.
`YurisAtlasCodepage` selects a page table only from these candidates and does not change the
archive layout.

| Profile Name | Directory Contract | Page Slots | Canvas and Grid | Preferred Code Page |
| --- | --- | --- | --- | ---: |
| `cp932-s38` | `源ノ角ゴシック[_style]/fnt_s38_nN.webp`, 45 pages × 8 styles, with files directly in the style directory | CP932 double-byte pages, 188 slots per page; invalid slots use `U+FF65` | 1024x640, origin `(5,11)`, 19×10 cells of 48 px, glyph box 38 px | 932 |
| `gbk-s38` | 127 pages × regular/bold; `fnt_s38_nN.webp` is in a `38/` subdirectory | Pages 1–126 use GBK lead bytes `0x81–0xFE`, 192 slots per page; page 127 is ASCII `0x20–0x7E` | 816x624, origin `(5,11)`, 16×12 cells of 48 px, glyph box 38 px | 936 |
| `big5-c20` | `font_c20/fnt_s20_nN.png`, 89 regular-style pages | Lead bytes `0xA1–0xF9`; trail bytes `0x40–0x7E`, `0xA1–0xFE`; slots 64/65 remain empty | 720x400, origin `(6,9)`, 16×10 cells of 30 px, glyph box 20 px | 950 |
| `big5-c10` | `font_c10/fnt_s10_nN.png`, 38 regular-style pages | Same double-byte slot layout as `big5-c20` | 720x400, origin `(8,10)`, 16×10 cells of 26 px, glyph box 10 px | 950 |
| `big5-c10-89+ascii` | `font_c10/fnt_s10_nN.png`, 90 pages | Pages 1–89 are Big5; page 90 is ASCII | 720x400, origin `(8,10)`, 16×10 cells of 26 px, glyph box 10 px | 950 |
| `big5-c20-89+ascii` | `font_c20/fnt_s20_nN.png`, 90 pages | Pages 1–89 are Big5; page 90 is ASCII | 720x400, origin `(6,9)`, 16×10 cells of 30 px, glyph box 20 px | 950 |
| `big5-c30-89+ascii` | `font_c30/fnt_s30_nN.png`, 90 pages | Pages 1–89 are Big5; page 90 is ASCII | 720x440, origin `(6,11)`, 16×10 cells of 40 px, glyph box 30 px | 950 |
| `big5-c40-89+ascii` | `font_c40/fnt_s40_nN.png`, 90 pages | Pages 1–89 are Big5; page 90 is ASCII | 820x520, origin `(7,13)`, 16×10 cells of 50 px, glyph box 40 px | 950 |
| `relirium-s38` | `源ノ角ゴシック[_style]/38/fnt_s38_nN.ydg`, 46 pages × 8 styles | CP932 double-byte pages including the `0xF0` user-defined lead-byte page, 188 slots per page | 1024x640, origin `(5,11)`, 19×10 cells of 48 px, glyph box 38 px | 932 |
| `relirium-s31-bold` | `源ノ角ゴシック_太/31/fnt_s31_nN.ydg`, 46 pages | Same as `relirium-s38` | 800x440, origin `(5,10)`, 19×10 cells of 41 px, glyph box 31 px | 932 |
| `relirium-s31-bold-shadow-outline` | `源ノ角ゴシック_太影袋/31/fnt_s31_nN.ydg`, pages 1, 2, 3, 46 | Same as `relirium-s38` | 800x440, origin `(5,10)`, 19×10 cells of 41 px, glyph box 31 px | 932 |

### Big5 Resource Tree

PNG profiles accept the following registered directories:

- Direct layouts at `cgsys_c\\font_c20` and `cgsys_c\\font_c10`;
- Nested layouts at `cgsys_c\\font\\font_c20` and `cgsys_c\\font\\font_c10`;
- `font_c10`, `font_c20`, `font_c30`, and `font_c40` in the mixed four-size layout.

The standard four-size profile reads only strictly named files from `fnt_sNN_n1.png` through
`fnt_sNN_n90.png`. Variants with `_`, `__`, or `_old` suffixes, single-character image
directories, button images, and empty unpacked directories are not font pages. When an
identical compressed payload cannot uniquely identify a font size or page number, the current
request retains the default decoded result.

### Glyph Styles and Pixel Rules

`FontToPicPreset` centrally defines the synthetic styles for CP932/GBK:

| Directory Marker | Pixel Behavior |
| --- | --- |
| `太` | Overlays 2 px to the right to form a bold mask |
| `影` | Uses a black shadow at `(2, 1)` |
| `袋` | Uses a 1 px black outline |

GBK slots for `0x7F`, `0xFF`, and failed decoding remain transparent, with stable slot indices.
Big5 PNG uses white fill and a 1 px `RGBA(75,75,75,224)` outline. Relirium/YDG uses the registered
38/31 YDG presets, including quotes aligned to the left edge, bottom-aligned ellipses, optical
centering of dots, and punctuation offsets.

Punctuation placement is handled independently for each atlas layout:

- `cp932-s38` and `gbk-s38` preserve `GLYPHMETRICS::gmptGlyphOrigin`, font bearings, and the
  baseline; `gbk-s38` uses a `(5,4)` GDI drawing offset and a 3 px transparent top area.
- Big5 uses the full-width bearing convention of the PNG atlas: backticks and periods align
  to the bottom left, commas through question/exclamation marks are horizontally centered,
  paired quotes and book-title brackets use their own anchors, and ellipses and dots are
  optically centered on the glyph-box midline.
- Relirium/YDG offsets `，、。．；：！？` 2 px left and 1 px down; quotes and angle
  degree/minute/second symbols align to the left, `…⋯` align to the bottom, and `‥・·•･‧` use
  YDG optical centering.

Glyphs, outlines, and shadows remain within their own slots. For missing code points, first
select a similar punctuation alternative, then choose a system fallback font according to the
atlas code page. Font `.notdef` glyphs are not written to the atlas.

## Atlas Generation and Font Sources

The rendering path obtains grayscale glyph data through `GGO_GRAY8_BITMAP`, then writes it in
the profile's pixel order:

- WebP: Writes to the BGRA buffer defined by `YSWBP` ordinal 3;
- PNG: Writes to the RGBA row buffer defined by `YSPNG` ordinal 2;
- YDG: Writes to decoded YDG RGBA chunks.

The runtime does not generate temporary images, call Python, or repack YPFs. The atlas cache
holds at most 12 entries with a fixed capacity. Cache keys include the catalog entry, character
page-table code page, and `Config::ConfigVersion`.

Atlases select a GDI face using `Config::SourceFontNameW`. System fonts, TTF/OTF/TTC files
registered through `AddFontResourceExW(..., FR_PRIVATE, ...)`, and specific TTC faces selected
by family/full name share the same entry point. Configuration stores the TTC face name rather
than the collection filename.

## Configuration Snapshots and Lifecycle

`Config::ConfigVersion` identifies a complete font-configuration snapshot. The font name,
font-size scale, weight, page-table code page, and generated pixels all carry this version:

1. The font picker publishes a configuration notification; the adapter clears pending YDG
   chunks and the atlas cache.
2. Decode requests generate resources using the specified `SourceFontNameW`, height scale,
   weight, and page-table code page.
3. The adapter posts `WM_FONTCHANGE` to windows in the current process and requests repainting.
4. Recheck the version before committing a render result; discard results with mismatched versions.
5. Textures that YU-RIS has already uploaded to video memory follow the engine's resource-holding
   lifetime; requests build atlases from the current snapshot.

When `EnableFontHook=0`, WebP, PNG, and YDG entry points retain default decoding behavior. They
also retain default decoding behavior if identity, capability, fingerprint, or layout checks fail.

## Configuration

The adapter uses generic font-picker settings and reads the page-table diagnostic override key
through `FontHook.ini`:

| Configuration Key | Purpose |
| --- | --- |
| `EnableFontHook` | Master switch; when disabled, retains default YSWBP/YSPNG/YDG decode results |
| `FontNameW` | Target face, corresponding to `Config::SourceFontNameW` at runtime |
| `EnableFontHeightScale` / `FontHeightScale1000` | Atlas font-size scale; results are limited to 8 px through the current cell height |
| `EnableFontWeight` / `FontWeight` | Base weight; the `太` style still adds synthetic bolding |
| `FontFileName` | Optional private TTF/OTF/TTC file, registered by the generic font loader |
| `YurisAtlasCodepage` | `0` uses the structural automatic result; a nonzero value selects an installed code page compatible with the slot layout |

The font picker presents only cross-engine configuration; `YurisAtlasCodepage` is managed
directly in the INI file. This boundary avoids UI-level coupling between page-table overrides
and text mapping, character-set spoofing, or code-page redirection.

`ForcedCharset=128` affects only generic font requests, without changing YPF page-slot mapping.
`YurisAtlasCodepage` changes only the Unicode characters corresponding to byte slots; it does
not change page counts, slot counts, grids, or archive entries. For example, when SPIN!2 uses
GBK, the 45-page × 188-slot layout cannot accommodate GBK's 126 lead-byte pages and 192 slots.
The code-page override `936` is classified as layout-incompatible; the current request retains
the default decoded result and records `atlas-codepage override incompatible`.

Big5 characters enter Unicode mapping only when generic text mapping is explicitly enabled;
font selection is always determined by `Config::SourceFontNameW`. Directory encoding prefers
CP950, while font slots use the standard Big5 character table. CP950-only `A3E1` and `F9D6–F9FE`
remain empty slots; the 11 positions with differing symbols use standard Big5 code points.

## Invariants and Runtime Constraints

- Identity confirmation uses main-module markers; generic GDI imports, extensions, or a single filename cannot establish YU-RIS identity alone.
- Only candidates that completely match the YPF version, directory paths, consecutive page numbers, style set, image dimensions, and decoder entry points can establish a capability catalog.
- Font replacement writes only confirmed font pages; it does not change script encoding, code-page redirection, or ordinary images.
- Decoder entry points read only the cached catalog and bounded state; they do not scan disk, parse archives, or produce unbounded diagnostic output.
- The worker thread prepares the catalog; the initial wait is limited to 5 seconds, after which requests fall back to the default decoder.
- Font creation, glyph extraction, and cache access use saved `org*` APIs to avoid recursion into generic font hooks.
- Atlas-cache capacity is fixed at 12; the version, catalog entry, and page-table code page together establish cache identity.
- Shutdown stops the started catalog thread and releases events, pending chunks, and caches; the loader-lock path in `DLL_PROCESS_DETACH` only publishes a shutdown signal.

## Offline Generation Tools

Offline scripts use explicit presets with the same names as the runtime and do not accept
arbitrary encoding guesses:

```powershell
python font_to_pic.py --profile cp932-spin2 --font FONT_FILE --font-index TTC_FACE
python font_to_pic.py --profile gbk-goodbye-world-index --font FONT_FILE --font-index TTC_FACE --output-root CGSYSF_ROOT
```

`FONT_FILE` supports TTF, OTF, TTC, and OTC; `TTC_FACE` is indexed from 0. The GBK preset creates a
`38/` subdirectory under regular/bold directories, while the CP932 preset preserves output
directly in style directories. The scripts and their rule files are only for offline resource
preparation and do not participate in DLL compilation or runtime decoding.

## Extension Steps

1. Define an explicit `AtlasEncodingProfile`, `AtlasProfile`, or `ArchiveProfile` in
   `yuris_profiles.cppinc`, specifying contracts for page counts, slots, directory paths, image
   dimensions, and decoder entry points together.
2. Register complete directory validation, fingerprints, or chunk-matching conditions in
   `yuris_catalog.cppinc`; keep identity, capabilities, and resource routing as three separate stages.
3. Implement pixel order, punctuation placement, and missing-glyph fallback rules tied to the
   layout in `yuris_renderer.cppinc`; do not directly reuse another profile's coordinate
   algorithm for this atlas.
4. In `yuris_runtime.cppinc`, attach only confirmed modules, ordinals, or function signatures,
   and let failure paths return default decode results. File redirection still goes through
   `engine_file_dispatch.cppinc`.
5. Prepare verification records for positive samples, nontarget programs, feature disablement,
   incomplete layouts, ambiguous fingerprints, and snapshot switching.

## Evidence and Reproduction

### Static Identity and Directory

1. Fix SHA-256 hashes for the main module and `pac/*.ypf`; record architecture, directory paths,
   and configuration snapshots.
2. Confirm the combined `ysbin\\yscfg.ybn` and `yu-ris1` markers in the readable main-module image;
   use samples with only one marker as nontarget controls.
3. Read the `0x1F4` directory from candidate YPFs, saving the version, index length, entry paths,
   page numbers, styles, and image dimensions. For directory encoding, record decoding results
   in order for the archive's preferred value, ACP/OEM, UTF-8, and explicit Windows code pages.
4. Check the following profile identifiers against complete resource profiles: `cp932-s38`,
   `gbk-s38`, `big5-c20`/`big5-c10`, `big5-c10-89+ascii`, `big5-c20-89+ascii`,
   `big5-c30-89+ascii`, `big5-c40-89+ascii`, `relirium-s38`, `relirium-s31-bold`, and
   `relirium-s31-bold-shadow-outline`.

### Runtime Reproduction

1. Record binding results for `YSWBP.DLL` ordinal 3, `YSPNG.DLL` ordinal 1/2, and the x86 QOI core.
2. Start the catalog worker thread. Save one-time logs and elapsed times for `identity confirmed`,
   `atlas encoding incompatible`, `atlas encoding resolved`, `atlas encoding candidate`,
   `archive matched`, `bitmap-font capability confirmed`, or `capability unavailable`.
3. Send one matching page and one nonfont resource each to WebP, PNG, and YDG. Record `wrapped`,
   `rendered`, chunk aggregation, version numbers, and default-decoder fallback.
4. Set `YurisAtlasCodepage` to automatic, compatible, and incompatible values. Save `layout`,
   slot counts, actual code pages, and `atlas-codepage override incompatible` results.
5. Generate the same font face using an explicit `font_to_pic.py` profile. Record the input-font
   hash, TTC face, output-atlas dimensions, pixel format, and directory tree; compare offline
   output with runtime atlases slot by slot.

| Scenario | Identity | Capability/Routing | Expected Result |
| --- | --- | --- | --- |
| Combined markers + complete YPF profile + decoder entry points | Passes | Passes | Only registered font pages are replaced |
| Combined markers missing | Fails | Not evaluated | WebP/PNG/YDG use default decoding |
| Complete YPF directory, but no matching profile | Passes | Fails | Records the reason and falls back |
| Code-page override incompatible with slots | Passes | Routing rejected | Preserves default decoding without changing the resource layout |
| Nonfont image or incomplete YDG chunks | Passes | No match | No atlas writeback |
| `EnableFontHook=0` | Does not enter replacement | No routing | Preserves default YPF results |
| Configuration-version switch | Passes | Current snapshot | Discards renders with mismatched versions; cache keys include the version |

The evidence directory contains YPF-index summaries, profile tables, decoder entry points,
per-slot atlas hashes, `[Yuris]` logs, configuration snapshots, and nontarget samples. For generic
record fields, see [Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

- Positive-sample diagnostics include `identity confirmed`, resource sources, scan duration,
  automatic code page, compatible-code-page count, resource count, and page count. WebP, PNG,
  and Relirium each record their corresponding wrapper entry points and atlas replacement.
- Non-YU-RIS programs, programs without registered font pages, nonfont WebP/PNG resources, and
  incomplete YDG chunks produce no replacement.
- When `EnableFontHook=0`, the display uses default decoded results from YPF sources.
- For system-face, TTC-face, or page-table-code-page verification, diagnostics include the
  corresponding `ConfigVersion`, actual face, and actual code page.

YPF directory fields and the filename-length exchange table reference GARbro's
[ArcYPF.cs](https://github.com/morkt/GARbro/blob/master/ArcFormats/YuRis/ArcYPF.cs).
