# Escu:de Adapter

## Responsibilities

This directory provides a runtime view of the font options in Escu:de's `configure.cfg`. The
adapter returns the current replacement font through the Win32 Profile APIs, directing the
engine into a font branch that the generic GDI hooks can handle.

## Coverage of the Generic Path

Escu:de reads the `[Font]` options from `configure.cfg` before creating a font. This configuration
value determines which font path the engine selects, so intercepting only GDI font creation
cannot guarantee that the engine enters the system-font branch. Editing the configuration file
in the root or user directory would also change the game's persistent state and would not cover
font switching within the process.

The adapter provides virtual values at the Profile API boundary, limited to the target section,
keys, and product. The engine enters the GDI path through its own configuration-reading flow;
the on-disk configuration and other Profile requests retain their original semantics.

## Detection Conditions

The root configuration, or the `configure.cfg` actually requested by the current Profile API
call, provides the following in its `[General]` section:

- `Company=ESCUDE`
- A nonempty `Product`

The product name identifies the root configuration and the user configuration at
`Documents/ESCUDE/<Product>/configure.cfg`. The user configuration can be the initial source of
identity evidence, so identification also works when the resources are in the user directory.

## File Entry Points

- `escude_config.cppinc`: Engine detection, configuration-path identification, and Profile API return-value handling.
- `newGetPrivateProfileStringA/W`: Provides virtual values for `[Font] Face` and `[Font] Font`.
- Generic Profile API Detours: Passes other sections and keys to the real API.

## Implementation

1. Read `[General]` from a candidate `configure.cfg` and confirm identity using both
   `Company=ESCUDE` and a nonempty `Product`.
2. Derive the allowed root configuration path and
   `Documents/ESCUDE/<Product>/configure.cfg` path from the product name.
3. The Profile hook matches the file, section name, key name, master font switch, and virtual
   configuration switch together.
4. When `[Font] Face` or `[Font] Font` matches, return the corresponding `ForcedFontName` for the
   A/W call.
5. The copy functions reproduce Win32 buffer-truncation, terminator, and return-length semantics;
   unmatched requests call the `org*` APIs.

## Features

- Supports both ANSI and Unicode Profile APIs.
- Identifies the game-root and current product's user-configuration paths.
- Returns `ForcedFontNameA/W` for the `Face` and `Font` keys in the `[Font]` section.
- Preserves Win32 Profile API buffer-length, truncation, and return-value semantics.
- Uses bounded logging to record the product, configuration path, and font value.

## Rationale for the Design Constraints

- Providing a view at the read boundary covers both root and user configurations while keeping
  runtime font selection from affecting the on-disk files.
- The company and product together establish identity; the `configure.cfg` filename only
  locates candidates.
- A/W entry points share the same identity and path state, while string copying follows the
  corresponding Win32 contract for each entry point.
- The font-picker thread reads the real configuration so the UI does not consume the virtual
  values intended for the game.
- Profile integer reads and unrelated sections and keys pass through entirely, limiting the
  adaptation surface to two font strings.

## Configuration

- `EnableEscudeHook`
- `EscudeVirtualFontConfig`
- `EnableFontHook`
- `EnableFaceNameReplace`
- `ForcedFontNameA`, `ForcedFontNameW`

## Runtime Constraints

- Virtual font values are provided only after the company, product, section name, key name, and
  configuration path all match.
- The font-picker thread uses the real configuration-reading path.
- Profile integer reads and unrelated string reads retain system API behavior.
- Confirmed product names and identity are cached for the process lifetime; dynamic
  configuration requests can supplement identity after root-directory probing completes.

## Evidence and Reproduction

1. Fix the root and user-directory copies of `configure.cfg`, and record `[General]`'s `Company`
   and `Product`, file hashes, and actual Profile API paths.
2. Call `newGetPrivateProfileStringA/W` separately to read `[Font] Face` and `[Font] Font`. Save
   the return values and terminators for buffer lengths of `0`, `1`, a normal length, and a
   truncating length.
3. Call the real `org*` APIs for other sections, other keys, integer reads, write requests, and
   nonmatching products, and record the results.
4. Include `ForcedFontNameA/W`, the master switch, the virtual configuration switch, and
   `ConfigVersion` in each log entry.

| Scenario | Expected Result |
| --- | --- |
| `Company=ESCUDE` and a nonempty `Product` | The root/user path becomes an identity candidate |
| Either identity field is missing | Profile requests pass through |
| An A/W font key matches | Returns the replacement font in the corresponding encoding, preserving buffer semantics |
| Other keys or writes | Returns the real Profile result |
| Any switch is disabled | No virtual font value is provided |

The evidence directory contains configuration hashes for both paths, A/W return values,
truncation tests, `[DEBUG][Escude]` logs, and nontarget configurations. For the record template,
see [Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover root and user configurations, ANSI/Unicode calls, the `Face`/`Font` keys, buffer truncation,
feature switches, other sections and keys, and non-Escu:de programs with a configuration file of
the same name.
