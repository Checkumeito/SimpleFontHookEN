# Majiro Adapter

## Responsibilities

This directory handles Majiro's disk glyph cache and runtime glyph cache. The adapter keeps
`savedata/fc_*.fcd` and `savedata/fca_*.fcd` consistent with the current font version and provides
targeted compatibility for Majiro's ANSI text and character-set branches.

## Coverage of the Generic Path

Majiro maintains both on-disk FCD files and in-process glyph tables. A disk-cache hit can bypass
the current font-generation path; the runtime tables can continue referencing old widths,
offsets, and bitmap data after a font switch. Handling only one of the two cache levels leaves
font objects inconsistent with the glyphs on screen.

The adapter makes read-only FCD requests appear as cache misses, allowing the engine to write
them back in its original format. For the in-process cache, it first identifies the complete
layout, then clears counts and dirty state according to the configuration version. ANSI
compatibility decisions have an independent engine-specific entry point; the code page is not
inferred from the replacement font.

## Identity and Resources

Majiro identity is confirmed by the `MajiroObj`, `MajiroArcV`, or `MajiroSavV` format markers in
the main module. The markers are queried directly from the readable memory of the mapped
module, and the result is cached in the process.

The `.arc` and `.fcd` extensions are used only for candidate-file routing. After identity is
established, the adapter verifies the `savedata` directory level, `fc_`/`fca_` naming, and
three-digit width and height fields.

## File Entry Points

- `majiro_font_cache.cppinc`: Engine detection, FCD path classification, runtime-layout scanning, and configuration notifications.
- `engine_file_dispatch.cppinc`: Calls the disk cache's open, attribute, and search handlers.
- Generic font-data and text-conversion hooks: Query Majiro's targeted compatibility decisions.

## Implementation

1. Confirm Majiro identity using the main-module format markers and cache the result.
2. Path classification validates the `savedata` directory level, `fc_`/`fca_` prefixes,
   three-digit width and height fields, and `.fcd` extension.
3. Matching read-only opens, attribute requests, and wildcard searches return missing-file
   semantics; writes are performed by the real API.
4. Bounded code and memory scans locate the width table, offset table, data count, and dirty
   flag, and save a layout description.
5. Configuration notifications are deduplicated by `ConfigVersion`. Clear only layouts whose
   address ranges, writable protection, and field relationships all validate.
6. After identity is established, the generic text and font-query hooks read the CP932 decoding
   and `DEFAULT_CHARSET` preservation policies.

## Features

- Identifies FCD font caches under the `savedata` root that follow Majiro's naming format.
- Returns missing-file results for read-only cache requests so the engine generates glyph data using the current GDI font.
- Allows the engine to write new FCD caches in the original format.
- Scans and validates runtime glyph-width tables, offset tables, data-area counts, and dirty flags.
- Clears validated runtime tables when the configuration version changes, marking cache content for regeneration.
- Uses CP932 decoding rules on Majiro's text path and preserves the source character set for `DEFAULT_CHARSET` font requests.

## Rationale for the Design Constraints

- FCD writes are left entirely to the engine, avoiding dependence on undocumented cache-serialization details.
- Filename structure participates in resource routing but not identity confirmation, reducing false positives from shared `.arc` and `.fcd` extensions.
- Runtime refresh requires complete field relationships and writable ranges; a partial signature match is insufficient to write memory.
- CP932 and character-set policies are provided to the generic encoding module only under confirmed Majiro identity; the font switch itself does not change encoding.
- Disk and runtime caches are invalidated separately, allowing versions missing one capability to use the other compatibility path.

## Configuration

- `EnableMajiroHook`
- `MajiroDisableFontCache`
- Generic font, character-set, code-page-redirection, and text-mapping settings

## Runtime Constraints

- FCD filenames, directory levels, and three-digit width and height fields must match completely.
- Runtime-cache addresses must be within the main module and cover writable memory.
- Cache-layout scanning runs once per process; refreshes are deduplicated by `ConfigVersion`.
- Majiro performs its own file writes; file virtualization affects only cache reads and queries.
- CP932 and character-set compatibility are enabled only after positive Majiro detection.

## Evidence and Reproduction

1. Fix the main-module hash and record the `MajiroObj`, `MajiroArcV`, and `MajiroSavV` markers and
   process architecture.
2. Collect `savedata/fc_*.fcd` and `savedata/fca_*.fcd`. Independently verify directory levels,
   prefixes, three-digit width and height fields, and extensions; use invalid names as nontarget
   files.
3. Record API results for reads, attributes, wildcard searches, and writes. Confirm that
   read-only cache requests return missing-file results while writes call the real API.
4. Save address ranges, protection attributes, and field relationships for the runtime width
   table, offset table, data count, and dirty flag. When switching configuration, record the
   cleared layouts and `ConfigVersion`.
5. For CP932, `DEFAULT_CHARSET`, and text mapping, separately save source bytes, decoded results,
   and the mapping switch state.

| Scenario | Expected Result |
| --- | --- |
| Complete Majiro markers + a valid FCD name | Disk-cache reads return missing-file results, allowing the engine to write the cache back |
| Shared `.arc`/`.fcd` extensions without markers | Identity is not established; files pass through |
| Incomplete field relationships in a runtime layout | No memory writes; preserves the runtime cache |
| Configuration switch + a complete layout | Clears only validated fields and records the version association |
| `DEFAULT_CHARSET` or CP932 branch | Preserves the source character set and follows generic encoding rules |

Evidence includes filename lists, layout summaries, read/write results, `[DEBUG][Majiro]` logs,
and nontarget samples. For the record format, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover `fc_`/`fca_` caches, wildcard searches, cache writes, runtime-layout matches and misses,
font switching, the `DEFAULT_CHARSET` branch, text mapping, feature switches, shared ARC
extensions, and programs without Majiro markers.
