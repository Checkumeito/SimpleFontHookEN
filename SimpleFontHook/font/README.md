# Font Table Modification Module

`font/` parses and modifies SFNT data in TTF, OTF, and TTC files. This module does
not install hooks, read game text, or decide code pages.

## Module Role

Some engines read font files or the SFNT bytes returned by `GetFontData` directly;
face-name replacement and `HFONT` replacement cannot affect that path. This module
expresses character-set capabilities, vertical metrics, font-family names, and
`cmap` aliases as structured font-table modifications so GDI, FreeType, HarfBuzz,
Unity, and Chromium see the same font capabilities.

Centralizing byte-level modifications here lets hooks and engine adapters decide
only when, to which font, and with which configuration a modification should apply,
instead of each implementing offsets, byte order, and checksums.

## Public Interfaces

Interfaces are defined in the `FontPatcher` namespace in `font_patcher.h`.

| Interface | Responsibility |
| --- | --- |
| `IsFontFile` | Validate the basic header of a standalone SFNT |
| `IsFontCollection` | Determine whether the input is a TTC |
| `NormalizeGdiFontData` | Normalize TTC-relative offsets in font data exported by GDI |
| `FindFontCollectionFaceIndex` | Find a face index in a TTC by font name |
| `ExtractFontFromCollectionByName` | Rebuild a standalone font from a TTC by font name |
| `PatchOS2CodePageRange*` | Modify `OS/2` code-page capability bits |
| `PatchVerticalMetrics` | Modify `hhea` and `OS/2` vertical metrics |
| `PatchNameTableFamily` | Rebuild the `name` table and set a unique font-family name |
| `PatchCmapAliases` | Rebuild Unicode `cmap` character-to-glyph aliases |

## Data Conventions

- SFNT integers use big-endian byte order and are accessed through the module's `ReadU16BE`, `ReadU32BE`, `WriteU16BE`, and `WriteU32BE` helpers.
- Check every offset and length before dereferencing, including protection against addition and multiplication overflow.
- Raw-pointer overloads can only modify existing tables in place. Use `std::vector<BYTE>` when the font must grow or be rebuilt.
- Each face in a TTC may have its own table directory; do not assume the first face represents the entire collection.
- Font data obtained from GDI may retain offsets relative to the original TTC. Call `NormalizeGdiFontData` before using it.

## Implementation Principles

Font modification follows parsing, face selection, target-table rebuilding, directory
correction, and checksum recalculation:

1. Identify standalone SFNT or TTC data and validate the table directory for each candidate face.
2. Score font names from TTC `name` table records; select the target face and rebuild it as a standalone SFNT.
3. Fixed-length fields can be written in place; variable-length tables such as `name` and `cmap` are rebuilt in temporary buffers.
4. When table sizes change, rearrange aligned table data and synchronize directory offsets and lengths.
5. Update the target table checksum and `head.checkSumAdjustment` before committing the result.

Temporary buffers preserve the original input on failure. Full rebuilding gives every
consumer a consistent table directory instead of relying on a rendering library's
tolerance for damaged offsets or checksums.

## Checksums

After modifying or rebuilding a font table:

1. Update the table checksum in its directory entry.
2. Temporarily set `head.checkSumAdjustment` to zero.
3. Recalculate the whole-font checksum and write `checkSumAdjustment`.
4. Process each modified TTC face's table directory separately.

Do not change table contents without updating checksums. Some GDI paths may tolerate
invalid fonts, but FreeType, HarfBuzz, Unity, or Chromium may refuse to load them.

## Modification Workflow

Implement font-table patches in this order:

1. Validate the SFNT/TTC header and the presence of the target table.
2. Determine whether the operation can be completed in place; rebuild data and correct directory offsets when growth is required.
3. Perform bounded checks on all lengths, counts, offsets, and alignment.
4. Return successful modification status only when content actually changes.
5. Update table checksums and `checkSumAdjustment`.
6. Create validation samples for standalone fonts, TTCs, multiple faces, missing target tables, and malformed input.

## Invariants

- This module does not call font hooks or depend on engine-adaptation state.
- `cmap` aliases change only Unicode-to-glyph mapping, not input text encoding.
- `OS/2` code-page capability bits affect font capability declarations only; they do not mean the text byte stream uses that code page.
- Input data must remain usable after failure. Operations requiring rebuilding should complete in temporary buffers first.

## Evidence and Reproduction

Implementation entry points are `font/font_patcher.h` and the corresponding
`font_patcher.cpp`. To reproduce a font-table behavior, record SHA-256 for the same
TTF, OTF, or TTC input and call `IsFontFile`, `IsFontCollection`, the target patch
function, and a checksum check separately. For every output, save the font header,
table directory, modified tables, and final hash. For failing input, save the return
value and original-byte hash.

| Input | Observed evidence | Expected output |
| --- | --- | --- |
| Standalone SFNT | `sfntVersion` and table-directory bounds checks pass | The target table is modified according to its contract; directory and checksums are consistent |
| Multi-face TTC | `ttcf` header, face count, target `name` records | The specified face is selected and rebuilt as standalone SFNT |
| Missing target table | The directory lacks the target tag | Returns unchanged; the input hash remains the same |
| Out-of-bounds or malformed length | Bounds checks fail | Returns failure without writing output |

A reproduction record must contain at least the input path and hash, face-selection
criteria, table directories before and after modification, `head.checkSumAdjustment`,
return status, and parser version. This record corresponds to the `O/I/U` labels in
[Feature Evidence and Reproduction](../../docs/reproduction.md).
