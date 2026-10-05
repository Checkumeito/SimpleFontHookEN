# Softpal Adapter

## Responsibilities

This directory handles Softpal's default bitmap-font option and the font type in `Pal.dll`. The
adapter maps the engine's default option to the system-font branch, allowing generic GDI font
hooks to provide the currently selected font.

## Coverage of the Generic Path

Before entering GDI font creation, Softpal selects bitmap or system fonts through the Pal font
type and `DEFAULT_FONT.DAT`. The default type `4` directs text to the engine's bitmap resources;
generic GDI hooks see only calls on the bypass path. Font switching therefore first needs the
engine to select the system-font type, after which the generic model replaces the actual font
object.

The adapter normalizes the type at the Pal export boundary and controls read-only visibility of
the default bitmap-font resource through the file dispatcher. Both paths only select the
branch; font metrics, character sets, and font data remain the responsibility of generic modules.

## Identity and Capabilities

Softpal identity is confirmed by three runtime exports: `PalFontBegin`, `PalFontSetType`, and
`PalFontGetType`. A complete export-name contract in the main module can confirm identity
early; after `Pal.dll` loads, its real export table completes the final binding. When the dynamic
module has not yet loaded, the export-retry path is retained.

The PAC extension, `Pal.dll` filename, and `DEFAULT_FONT.DAT` participate only in candidate
location and feature routing; none is an independent identity condition.

## File Entry Points

- `softpal_default_font.cppinc`: Engine detection, Pal font-type handling, default-font-file classification, and policy interfaces.
- `SoftpalInstallPalFontHooks`: Installs `PalFontBegin` and `PalFontSetType` Detours.
- `engine_file_dispatch.cppinc`: Handles `DEFAULT_FONT.DAT` file visibility.
- Generic font-creation and font-data hooks: Query Softpal's natural-width and data-replacement policies.

## Implementation

1. Main-module markers or the real export table of a loaded `Pal.dll` confirm the complete font contract.
2. `SoftpalInstallPalFontHooks` attaches `PalFontBegin` and `PalFontSetType` once the exports are available.
3. Read the current type at font-session start or a type change, normalizing the default value `4` to the system-font value `1`.
4. The unified file dispatcher exposes read-only existence of the game-root `DEFAULT_FONT.DAT` according to configuration.
5. Once the system-font branch enters GDI, generic hooks use the natural replacement width and font data according to Softpal's policies.
6. If the dynamic module has not yet loaded, retain a retryable state; the module-loading path retries export binding.

## Features

- Resolves the `PalFontBegin`, `PalFontSetType`, and `PalFontGetType` exports.
- Maps Softpal's default font type `4` to the system-font type `1`.
- Normalizes the current font type at font-session start and when the type changes.
- Provides bitmap-font switch behavior for read-only requests to `DEFAULT_FONT.DAT` in the game root.
- Uses the replacement font's natural width and font-data query results in the generic GDI path.

## Rationale for the Design Constraints

- The Pal font type is an engine export contract; the adapter handles this interface without parsing the proprietary DAT bitmap format.
- Only value `4` is mapped; other user selections and engine font types retain their original semantics.
- Identity requires the complete export set; the `Pal.dll` filename, PAC extension, and DAT filename only locate candidates.
- Export binding retries as modules load, avoiding a permanent negative result while the DLL is not yet in the process.
- Pal call exceptions are contained at the adapter boundary; return values continue to follow the engine-function contract.

## Configuration

- `EnableSoftpalHook`
- `SoftpalDisableDefaultFontDat`
- `SoftpalForceDefaultOptionToSystemFont`
- Generic font-name, metric, and character-set settings

## Runtime Constraints

- Commit the Detours transaction only after all Pal exports have been resolved.
- Pal calls use structured exception protection and preserve engine-function return-value semantics.
- `DEFAULT_FONT.DAT` classification is limited to the game root.
- Font-type mapping handles only value `4`; other options pass through directly.
- Debug logs use a fixed sampling limit.

## Evidence and Reproduction

1. Inspect exports in the main module and loaded `Pal.dll`. Separately record the presence of
   `PalFontBegin`, `PalFontSetType`, and `PalFontGetType`, and the module owning each address.
2. Call `SoftpalInstallPalFontHooks` before and after `Pal.dll` loads. Record retry state,
   transaction results, and bound exports.
3. Start sessions, set types, and query types for font types `4`, `1`, and other values. Save
   input parameters, engine return values, and final types.
4. Separately record dispatch results for read-only requests, attributes, writes, and paths
   outside the root involving `DEFAULT_FONT.DAT`.

| Scenario | Expected Result |
| --- | --- |
| All three Pal exports present | Identity and type capability are established; export hooks can be installed |
| `Pal.dll` not yet loaded | Retains retry state without caching a negative result |
| Type `4` | Maps to system-font type `1` according to configuration |
| Other types | Preserves call-parameter and return-value semantics |
| Only PAC/DAT/DLL filenames present | Identity is not established |

The evidence directory contains export snapshots, dynamic-loading timing, type-call records,
`DEFAULT_FONT.DAT` requests, and diagnostic logs. For the generic template, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover loading Pal before and after startup, default and other font types, `DEFAULT_FONT.DAT`,
natural width, font-data queries, feature switches, missing exports, shared PAC extensions, and
non-Softpal programs with a DLL of the same name.
