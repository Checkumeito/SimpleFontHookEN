# Artemis Legacy Adapter

## Responsibilities

This directory handles the Artemis layout that uses `.iet` scripts, text scripts, and `.rft`
prerendered font resources. The adapter supplies scripts with font paths, font sizes, spacing,
and text substitution, and connects them to the general font configuration through versioned
virtual font resources.

## Boundary with the Artemis Table Layout

This layout describes fonts in `.iet` or text scripts and can supply prerendered results
through `.rft`. Its fields, resource routing, and runtime objects differ from the
`list_windows*.tbl` layout. Combining the two layouts would let a shared suffix or archive
trigger unrelated handlers and place different cache structures in the same refresh logic.

The separate adapter confirms identity through script resources inside PFS, classifies
scripts, prerendered fonts, and virtual SFNT separately, and lets the unified file dispatcher
select the processing path for the actual request.

## Identity and Resources

The IET layout is confirmed by the results of parsing PFS headers and indexes. The parser
validates archive index entry counts, path boundaries, and 20-byte resource metadata.
The presence of `.iet` in the `system` or `_base` runtime resource namespace inside the index
establishes IET-layout identity.

IET and text scripts inside PFS are located and read through the archive index. Files at the
same paths under the game root directory are resource override entry points and do not
participate in engine identity confirmation.
The `.iet`, `.rft`, and font suffixes only classify resources after Artemis identity has been
confirmed. Table and IET files enter their respective handlers; loose files corresponding
to actual requests can serve as resource override sources.

## File Structure

- `artemis_legacy_paths.cppinc`: layout detection, font source location, virtual paths, and resource classification.
- `artemis_legacy_iet_patch.cppinc`: processing of font, rendering, spacing, and text fields in IET/text scripts.
- `artemis_legacy_file_hooks.cppinc`: script reads from loose files or PFS resources, and read-only virtual file handles and attributes for fonts.
- `artemis_legacy_text_substitution.cppinc`: multibyte-to-Unicode text substitution entry points for this layout.
- `artemis_legacy_notify.cppinc`: configuration version notifications, font preparation, and live-switching state records.
- `../common/engine_font_export.cppinc`: shared GDI font export and SFNT data validation.

## Implementation Principles

1. The PFS parser validates the index and looks for the IET contract in the `system` or `_base`
   resource namespace.
2. The path module unifies loose files and archive entries into three request categories:
   scripts, RFT, and fonts.
3. The script handler modifies font paths, font sizes, ruby text sizes, character spacing,
   line spacing, and rendering flags within bounded fields.
4. Text fields are decoded using an explicit ANSI source code page, then passed to the
   general Unicode substitution. This path has a switch independent of font replacement
   configuration.
5. The font exporter generates the current version's SFNT, and the file handler publishes
   script and font content through read-only virtual handles.
6. Configuration notifications prepare font resources in advance and record the versions
   consumed by script processing, opens, and redirection.

## Features

### Script Processing

Script processing covers font file fields, font variables, name text contexts, prerendering
flags, `kerning`, line spacing, `size`, and `rubysize`. Text substitution decodes using the
configured ANSI source code page, then calls the general Unicode substitution table.

### Font Resources

Virtual fonts are located at `_base/font/FontHook.ttf` by default, with a configuration
version suffix in the filename. Font content can come from current-user fonts, system fonts,
game-local fonts, or GDI SFNT data. TTC sources select a face by font name and apply character
set capabilities, vertical metrics, and `cmap` alias configuration.

### Live Switching

Configuration notifications prepare the current version's font and record script open,
script processing, and font redirection versions. Each script or font read request receives
content corresponding to the current `ConfigVersion`.

## Rationale for Design Constraints

- Scripts form a versioned view when read; original resources on disk and in PFS remain read-only.
- Resource classification controls RFT hiding and virtual SFNT delivery separately, so the
  live font path only takes effect when identity and configuration match.
- Text substitution calls the real conversion APIs with a thread-local recursion guard to
  prevent script processing from reentering its own hooks.
- Loose override files only supply resource content and do not confirm identity; identity
  still comes from the parsed PFS contract.
- Each request category records its configuration version, making it possible to determine
  whether script content, font paths, and font bytes come from the same snapshot.

## Configuration

- `EnableArtemisHook`
- `ArtemisPatchTables`
- `ArtemisRedirectFontFiles`
- `ArtemisFontPath`
- `ArtemisFontSize`
- `ArtemisRubySize`
- General font, character set, text substitution, character spacing, line spacing, and vertical metrics configuration

## Runtime Constraints

- Resource paths must be inside the game root directory and match known script or font extensions.
- Script parsing checks field ranges, quotes, numbers, and binary inputs for boundaries.
- Text substitution calls the real `MultiByteToWideChar` through a thread-local recursion guard.
- File virtualization only handles reads and attribute queries; file dispatch priority is
  maintained centrally.
- Each cache entry and diagnostic state is associated with an explicit configuration version.

## Evidence and Reproduction

1. Fix the PFS hash and parse the index, requiring at least one `.iet` entry in the `system`
   or `_base` resource namespace.
2. Retain the IET/text script source bytes and the parsed font, `size`, `rubysize`, `kerning`,
   line spacing, and text fields.
3. Read a loose script and a PFS entry with the same configuration, then compare generated
   content, virtual font paths, and version numbers.
4. Record file dispatch results separately for `.rft`, virtual SFNT, read-only attributes,
   and write requests.
5. Text substitution tests retain source bytes, the explicit ANSI code page, intermediate
   Unicode values, and substitution results.

| Scenario | Expected result |
| --- | --- |
| Valid PFS containing the IET contract | Identity is confirmed; scripts and fonts are classified by request |
| Artemis table resources without IET | This adapter's identity is not confirmed; the table-layout adapter handles them independently |
| Damaged fields, unclosed quotes, or out-of-bounds lengths | Script retains source content or falls back; failed fields are recorded |
| Script/font writes | Call the real file APIs |
| Features disabled | IET, RFT, and font requests retain engine semantics |

The evidence directory contains index summaries, script hashes before and after processing,
font SHA-256, configuration snapshots, and a single diagnostic log capture. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for the record template.

## Verification

Cover loose IET files, IET inside PFS, font variables, name text, RFT paths, TTC fonts, text
substitution, feature switches, repeated live switching, damaged scripts, and the Artemis
table-file layout.
