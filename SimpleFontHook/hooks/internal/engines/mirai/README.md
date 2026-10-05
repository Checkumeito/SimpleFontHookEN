# Mirai Adapter

## Responsibilities

This directory handles Mirai's font path that passes raw SFNT data from Windows HFONTs to
FreeType/D3D. The adapter provides stable font-data sources, Windows font-file redirection, and
font-table configuration so the engine reads data consistent with the current replacement font.

## Coverage of the Generic Path

Mirai passes fonts to FreeType/D3D through `GetFontData` or by directly opening files under
Windows Fonts. These interfaces typically query table sizes and content in multiple calls and
assume the same font source remains stable for the face's lifetime. If generic `HFONT`
replacement recreates objects between consecutive queries, the table directory, offsets, and
actual bytes may come from different resources; direct file reads bypass GDI objects entirely.

The adapter binds a stable replacement-data source to the HDC, original HFONT, and source
`LOGFONT`, and redirects read-only system-font-file requests to the font selected by the same
configuration, giving object queries and file reads consistent SFNT data.

## Identity and Capabilities

Mirai identity requires the main module to contain both the FreeType runtime contract and a
`DEVICE_FONT_NAME`, `getFontFile`, or `FontFile =` font-configuration marker. Both pieces of
evidence are queried directly from the readable memory of the mapped module; the result is
cached in the process.

Font-file extensions participate in Windows Fonts and local font-source classification only
after identity is established.

## File Entry Points

- `mirai_font_data.cppinc`: Detection, stable HFONT sources, `GetFontData` handling, font-file location, and file redirection.
- `../common/engine_common.cpp`: Shared system-font registry cache and font location in the game root.
- Generic `GetFontData` hook: Calls `MiraiTryGetPinnedFontData` first.
- `engine_file_dispatch.cppinc`: Handles font-file opens and attribute queries.

## Implementation

1. The FreeType contract and Mirai font-configuration markers together confirm identity and
   target capability.
2. `GetFontData` queries look up a stable source in fixed slots using the HDC, original HFONT,
   and source `LOGFONT`.
3. If no source exists, create a replacement HFONT, apply the required font-table configuration,
   and save it in a bounded container.
4. Read both complete-SFNT and single-table queries from that source, keeping the directory and
   bytes consistent across calls.
5. File routing accepts only read-only SFNT/TTC requests under Windows Fonts and locates a
   system or game-local source font.
6. Configuration notifications clear paths and source versions, so queries after a version
   notification establish bindings for the current `ConfigVersion`.

## Features

- Establishes stable replacement-font-data sources using the HDC, original HFONT, and source LOGFONT.
- Applies code-page-capability and vertical-metric settings when reading complete SFNT data or individual font tables.
- Redirects TTF, OTF, and TTC reads under Windows Fonts to the current font-source file.
- Caches system or game-local font paths by `ConfigVersion` and font name.
- Records the current configuration version, font name, and stable-source count.

## Rationale for the Design Constraints

- Pinned data sources serve the multi-read contract of a FreeType face rather than replacing a single API return value.
- The container is limited to 64 entries, preventing unbounded object and GDI-handle growth from high-frequency font queries.
- File redirection is limited to Windows Fonts and read-only semantics; the game's own writes and nonfont files retain their original paths.
- Identical target and source paths pass through directly, avoiding redirection recursion on the same path.
- Font capabilities and vertical metrics are handled at the SFNT layer; code-page selection for text bytes remains the responsibility of the generic encoding module.

## Configuration

- `EnableMiraiHook`
- `MiraiReplaceFontDataQueries`
- `MiraiRedirectFontFiles`
- `MiraiPinFontDataSource`
- Generic font-name, character-set-capability, and vertical-metric settings

## Runtime Constraints

- Stable font sources bind only valid HDC, HFONT, and LOGFONT combinations; the container limit is 64 entries.
- Each stable source retains the same replacement HFONT for its lifetime, meeting the data-consistency requirements of a FreeType face.
- File redirection handles only read-only TTF, OTF, and TTC requests under Windows Fonts.
- Identical target and source paths use the real file directly.
- The font-picker thread uses the generic font-query path.

## Evidence and Reproduction

1. Fix the main-module hash, and separately record the FreeType contract and at least one of the
   `DEVICE_FONT_NAME`, `getFontFile`, or `FontFile =` configuration markers.
2. Sequentially query the complete SFNT length, content, and individual tables for the same
   HDC/HFONT/LOGFONT. Save each return length, table tag, byte hash, and pinned-source slot.
3. For read-only TTF/OTF/TTC opens under Windows Fonts, record the requested path, source path,
   and target-file hash. For writes, files outside the root, and identical source/target paths,
   record the pass-through results.
4. Create 64 or more candidate sources in succession and confirm the container limit and reuse
   of existing sources; record the new version bindings after a configuration switch.

| Scenario | Expected Result |
| --- | --- |
| FreeType + a Mirai font-configuration marker | Identity and font-data capability are established |
| Only FreeType or a generic DAT extension | Identity is not established |
| Length/content/single-table queries for the same object | Uses the same pinned source and configuration version |
| Read-only SFNT under Windows Fonts | Redirects to the current font source |
| Source container reaches 64 entries | No unbounded HFONT/object growth |

Evidence includes `[TRACE][Mirai]` logs, query sequences, path mappings, font hashes, and nontarget
module results. For the record template, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover complete SFNT data, single-table queries, system-font files, user fonts, game-local fonts,
stable-source reuse, configuration notifications, feature switches, missing FreeType or
font-configuration markers, and non-Mirai programs sharing the DAT extension.
