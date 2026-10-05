# Artemis Adapter

## Responsibilities

This directory handles Artemis font table configuration, font file virtualization, PFS
resource reads, and runtime font cache refreshes. The adapter converts the font names,
metrics, and spacing configured in the font picker into table files and font resources that
Artemis can read directly, and updates the corresponding runtime objects when
`ConfigVersion` changes.

## Coverage of the General Paths

Artemis window fonts are initially specified by `list_windows*.tbl`. Font files may come
from PFS and, after loading, remain cached in FreeType objects, font atlases, and internal
hash tables. GDI font creation only covers auxiliary paths; it cannot synchronize already
parsed table fields, archive resources, and runtime caches to the same font configuration.

This adapter converts configuration into Artemis's own inputs: table files reference the
current version's font resources, the file dispatcher delivers the corresponding SFNT bytes,
and configuration notifications refresh verified runtime caches. Together, these three parts
ensure that the engine uses the same `ConfigVersion` from resource discovery through glyph
rasterization.

## Identity and Resources

The Artemis table layout is confirmed by the results of parsing PFS headers and indexes.
The parser recognizes `pf2`, `pf6`, and `pf8`, validating index lengths, entry counts,
length-prefixed paths, and 20-byte resource metadata. The presence of the
`system/table/list_windows*.tbl` resource family in the index establishes table-layout
identity.

PFS filenames and the `.pfs` suffix only locate candidate archives. Table and IET layouts
classify their respective resources separately. When a release package contains both kinds
of resources, the file dispatcher calls the appropriate handler for the actual request.
After identity is confirmed, the loose table file corresponding to the actual request can
serve as a resource override source.

## File Structure

- `artemis_paths.cppinc`: path normalization, engine detection, font sources, and resource classification.
- `artemis_detection_contract.cppinc`: PFS layout evidence and resource read interfaces across fragments.
- `artemis_pfs.cppinc`: PFS header, index, hash, and resource content parsing.
- `artemis_table_patch.cppinc`: updates to font, character spacing, line spacing, and font size fields in `list_windows*.tbl`.
- `artemis_file_hooks.cppinc`: read-only virtual file handles and attribute results for tables and font resources.
- `artemis_cache.cppinc`: discovery and refresh of FreeType font objects, font atlases, and internal hash caches.
- `../common/engine_font_export.cppinc`: shared GDI font export and SFNT data validation.

## Implementation Principles

1. The PFS parser validates headers, indexes, and resource boundaries, and confirms the table
   layout through the `list_windows*.tbl` resource family.
2. The font source resolver locates explicit files, system fonts, or game-local fonts;
   TTC sources select the target face by font name.
3. Font bytes receive the name, character set capabilities, vertical metrics, and `cmap`
   configuration and are bound to a versioned virtual path.
4. The table handler modifies font references, font size, ruby text size, character spacing,
   and line spacing so the engine actively requests that virtual resource.
5. The unified file dispatcher returns read-only handles and consistent attribute results for
   tables and fonts; other access goes to the real APIs.
6. Configuration notifications prepare the current version's resources and refresh cache
   objects that pass type, address, and layout validation.

## Features

### Font Resources

Font source resolution covers current-user fonts, system fonts, and game-directory fonts.
The adapter generates a stable virtual font path for each configuration version and supplies
font content through system font file redirection or in-memory SFNT data. Font family names,
weight, character set capabilities, and vertical metrics use the general font configuration.

### Table Files

`list_windows.tbl`, `list_windows_ja.tbl`, and related variants can be read from loose files
or PFS archives. Table content supports the following fields:

- Font files and numbered font assignments.
- `kerning` character spacing.
- Line spacing and vertical metrics converted in thousandths of an em.
- `size` body text font size.
- `rubysize` ruby text font size.

### Live Switching

Font files, table content, and cache state are all identified by `Config::ConfigVersion`.
Configuration notifications prepare the current version's font resources, refresh known
FreeType objects, mark font atlases, and clear internal cache layouts that can be verified.

## Rationale for Design Constraints

- PFS is only a validated resource source. The adapter generates in-memory views for requests
  to avoid rewriting archives and indexes.
- Virtual font paths include the configuration version so engines that cache by path can
  distinguish font snapshots with different content.
- A table request is only represented as a loose file when valid plaintext content can be
  returned, allowing the engine to retain its native PFS fallback.
- Runtime refreshes only access verifiable objects. File and table adaptation can still work
  independently when layout evidence is insufficient.
- Table and IET layouts are confirmed and routed separately because their resource contracts
  and runtime cache structures differ.

## Configuration

- `EnableArtemisHook`
- `ArtemisPatchTables`
- `ArtemisRedirectFontFiles`
- `ArtemisClearFontCacheOnSwitch`
- `ArtemisFontPath`
- `ArtemisFontSize`
- `ArtemisRubySize`
- General font name, weight, character spacing, line spacing, vertical metrics, and character set configuration

## Runtime Constraints

- File virtualization goes through `engine_file_dispatch.cppinc`.
- PFS counts, index sizes, resource offsets, and resource lengths all undergo bounded validation.
- Runtime objects participate in refreshes only when their types, address ranges, memory
  protections, and layout characteristics match completely.
- Font object scans and font source preparation use caches or configuration notification
  paths; PFS layouts and resource entry points are cached per process.
- File write requests are handled by the real file APIs; virtual resources serve read-only
  loading paths.

## Evidence and Reproduction

1. Fix the PFS and main module SHA-256 values and record candidate container paths; suffixes
   are only used for enumeration.
2. Use the parsing entry points in `artemis_pfs.cppinc` to read `pf2`, `pf6`, or `pf8` headers.
   Retain boundary check results for index length, entry count, path lengths, and 20-byte metadata.
3. Confirm the `system/table/list_windows*.tbl` resource family in the parsed index and record
   the actual container path and entries.
4. Read the same table from PFS and a loose file separately. Record font fields, font size,
   ruby text size, character spacing, line spacing, and the generated versioned font path.
5. Open the virtual font and validate its SFNT/TTC header. After switching configuration,
   compare `ConfigVersion`, table content, and cache refresh records.

| Scenario | Identity/capability evidence | Expected result |
| --- | --- | --- |
| Valid PFS + table resource family | Header, index, and target entries all pass | Table and font requests enter Artemis routing |
| Same suffix without table resource family | PFS container only | Identity is not confirmed |
| Readable table, unknown runtime layout | File capability passes; cache capability is missing | File adaptation takes effect; runtime memory stays unchanged |
| Damaged index or out-of-bounds resource | Boundary validation fails | Container provides no resources; fallback reason is recorded |

Reproduction artifacts include a PFS index summary, table content before and after processing,
font byte hashes, a single `[DEBUG][Artemis]` log capture, and non-target sample results. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for field formats.

## Verification

Cover loose table files, PFS table resources, system fonts, game-local fonts, table field
combinations, font atlas refreshes, feature switches, repeated live switching, damaged PFS,
and non-Artemis programs.
