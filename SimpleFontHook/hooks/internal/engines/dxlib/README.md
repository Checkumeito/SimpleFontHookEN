# DxLib Adapter

## Responsibilities

This directory maintains consistency between the DxLib `_FONTSET.MED` glyph cache and the
current replacement font, and provides engine identity decisions for DxLib font data queries.
The cache model uses the game's native `_FONTSET.MED` file in the root directory.

## Coverage of the General Paths

`_FONTSET.MED` stores a glyph cache generated from a particular font. When the cache exists,
DxLib can read glyph data directly, leaving font creation and `GetFontData` paths in the
current process no opportunity to generate the corresponding content. If the cached font
name differs from the current configuration, the configuration interface and display may use
different font sources.

The adapter does not parse or rewrite MED content. It maintains consistency state for which
font the native cache corresponds to. When a rebuild is needed, it only makes reads and
enumeration appear as though the cache is missing; DxLib still writes its own format.

## Identity and Resources

DxLib identity requires the main module to provide both DxLib library markers and DxLib font
contract markers. The font contract covers `CreateFontToHandle`, `DrawStringToHandle`, and
the `_FONTSET` runtime path. Detection directly queries mapped module memory and caches results.

`_FONTSET.MED` only indicates that the current request belongs to the DxLib glyph cache
feature. The MED suffix, whether the cache has already been generated, and other MED files
in the same directory do not determine engine identity.

## File Entry Points

- `dxlib_font_cache.cppinc`: path classification, engine detection, cache file access, and
  configuration notifications.
- `engine_file_dispatch.cppinc`: calls this module's open, attribute, and directory search handlers.
- General `GetFontData` hook: uses DxLib identity through `DxLibShouldReplaceFontDataQueries`.

## Implementation Principles

1. Main module markers confirm both DxLib identity and the font-related runtime contract.
2. Path classification only accepts `_FONTSET.MED` in the game root directory and its search
   patterns.
3. Read requests enter the real file APIs when `DxLibCachedFontNameW` matches the current
   `ForcedFontNameW` and configuration allows caching.
4. When fonts do not match or caching is explicitly disabled, opens, attributes, and directory
   searches return consistent missing-file semantics.
5. When DxLib creates a cache for writing, the adapter preserves the native handle and records
   the current font name after a successful open.
6. Font data queries enter the general SFNT replacement and font table processing paths
   according to independent configuration.

## Features

- Compare `DxLibCachedFontNameW` with the current `ForcedFontNameW`.
- Make read-only queries for `_FONTSET.MED` report a missing file when the font changes and
  cache updates are enabled.
- Keep write requests pointed at the native `_FONTSET.MED`, and save the cached font name
  after successfully opening a write handle.
- Supply replacement font SFNT data and font table configuration during font data queries.
- Use bounded sampling to record cache hits, rebuild requests, and configuration versions.

## Rationale for Design Constraints

- Letting the engine rebuild preserves the MED format and write timing; the adapter does not
  implement a MED serializer.
- Read, write, attribute, and search semantics are handled separately to prevent hiding the
  cache from also blocking creation of a new file.
- The cached font name is persisted in configuration so process startup can determine whether
  disk content matches.
- The MED suffix only routes resources for confirmed DxLib instances; identity still comes
  from the runtime contract in the module.
- `GetFontData` replacement and disk cache control use independent switches, allowing them to
  be combined according to actual capabilities.

## Configuration

- `EnableDxLibHook`
- `DxLibDisableFontCache`
- `DxLibReplaceFontDataQueries`
- `DxLibClearRuntimeFontCacheOnSwitch`
- `DxLibCachedFontNameW`: records the font name corresponding to `_FONTSET.MED`

## Runtime Constraints

- Only classify `_FONTSET.MED` in the game root directory and its corresponding search patterns.
- Read paths, write paths, and directory searches are handled separately; writes retain the
  native DxLib format.
- Module marker queries are limited to mapped, readable memory regions of the main module;
  detection results are cached within the process.
- The font picker thread bypasses cache virtualization.
- Font names maintain cache consistency; the general encoding module handles text encoding.

## Evidence and Reproduction

1. Record matches for DxLib markers and the `CreateFontToHandle`, `DrawStringToHandle`, and
   `_FONTSET` contract in the main module image.
2. For `_FONTSET.MED` in the root directory, retain existence, attributes, and return values
   for read-only opens, write opens, and directory searches.
3. Record `DxLibCachedFontNameW`, `ForcedFontNameW`, `DxLibDisableFontCache`, and `ConfigVersion`.
   Run matching-name, mismatched-name, and disabled-cache scenarios separately.
4. Through `DxLibShouldReplaceFontDataQueries`, record whether full SFNT/single-table queries
   enter the general font data path.
5. DxLib itself writes the MED file; evidence only checks the hash after writing and read
   visibility.

| Scenario | Expected result |
| --- | --- |
| Identity contract passes; cached name matches | Read requests call the real file APIs |
| Identity contract passes; cached name differs | Read/attribute/search requests return consistent missing-file semantics; writes retain the original path |
| `_FONTSET.MED` suffix only | Identity is not confirmed; all requests pass through |
| `DxLibReplaceFontDataQueries=0` | MED routing still follows configuration; SFNT queries are not replaced |

Evidence includes path hashes, field snapshots, `[DEBUG][DxLib]` samples, write results, and
non-DxLib control samples. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for the common
record template.

## Verification

Cover existing caches, missing caches, matching font names, changed font names, read-only
opens, rebuilds through writing, feature switches, configuration saving, shared MED suffixes,
and non-DxLib programs without module markers.
