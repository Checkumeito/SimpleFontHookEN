# BGI Font Compatibility Adapter

## Responsibilities

This directory maintains two independent BGI font compatibility layers:

- LINE script font layer: after BGI decodes DSC resources from an archive, identifies the
  semantics in `scrdrv._bp` that look up a fixed font and copy its `FontRecord`, then changes
  them to copy the font record currently selected by the game.
- Win32 GDI raster layer: patches the target module's IAT, normalizes replacement font
  metrics, and refreshes glyph caches with verified layouts.

The two layers only share the BGI identity result and the `EnableBgiHook` master switch.
LINE capabilities, GDI import capabilities, and cache layouts are confirmed separately.
Missing capabilities on either path do not disable the other available path. The general
encoding module still manages text code pages.

## Support Scope

| Capability | Win32 | x64 |
| --- | --- | --- |
| LINE font script adaptation after DSC decoding | Supports fastcall and legacy ESI/EDI decoders | Supports the Win64 fastcall decoder |
| BGI-specific GDI IAT, metrics, and cache adaptation | Supported | Inactive |
| General GDI font replacement | Supported | Supported |

The LINE layer identifies versions by the engine decoder ABI and BP bytecode layout. It does
not check game names, executable filenames, or fixed RVAs.

## File Structure

- `bgi_compat.cppinc`: namespace and implementation aggregation entry point.
- `bgi_identity.cppinc`: architecture-independent BGI identity confirmation and result caching.
- `bgi_line_font.cppinc`: DSC decoder capability detection, x86/x64 attachment, BP semantic matching, and same-length patching.
- `bgi_compat_state.cppinc`: Win32 imports, cache layouts, instance versions, and metrics state.
- `bgi_import_detection.cppinc`: Win32 PE import table checks and rasterization workflow characteristics.
- `bgi_cache_detection.cppinc`: Win32 cache access layout location within bounded code ranges.
- `bgi_cache_hooks.cppinc`: cache function hooks, version observation, and GDI import patching.
- `bgi_font_metrics.cppinc`: helpers for font probing, width/height ratios, and vertical metrics.
- `bgi_runtime.cppinc`: independent capability installation, metrics normalization, text output scopes, and configuration refresh interfaces.

## Activation Workflow

1. Check `EnableBgiHook`, which is enabled by default.
2. Confirm identity through `Buriko General Interpreter`, `BURIKO ARC` module markers, or a
   BURIKO archive header.
3. The LINE layer checks for `DSC FORMAT 1.00` in the image, then requires a unique match for
   the current architecture's decoder function structure and internal `call` target ranges.
4. The LINE layer attaches the confirmed decoder in the existing Detours transaction.
   x86 fastcall, the legacy x86 register ABI, and x64 fastcall each use their own entry points.
5. The Win32 GDI layer independently parses PE imports and confirms raster capabilities,
   then attaches cache layouts and patches the IAT according to configuration.
6. LINE activity state and Win32 `g_active` are maintained separately; GDI capabilities do
   not stand in for script capabilities.

The `.arc` suffix, generic GDI imports, and a single resource name are not identity evidence.
Archive magic bytes are only read during installation; decoder hooks do not scan the disk.

## LINE Font Script Adaptation

The original LINE initialization logic looks up a font by name, then copies its complete
`FontRecord` into a LINE-specific record. As a result, LINE may retain the font record
hardcoded in the script when only the font in the normal settings interface or GDI objects
are replaced.

The adapter processes the output buffer after the original DSC decoder returns successfully:

1. Validate BP header size, body size, and reserved fields, and limit the maximum script scan length.
2. Match the complete instruction sequence that looks up the font name, stores its index
   in a local slot, copies a `FontRecord` with a 524-byte stride, and initializes LINE styles.
3. Validate that `push_string` references a nonempty, syntactically valid CP932 font name
   within the buffer. The font name's content does not participate in profile selection.
4. Require exactly one semantic match across all known layouts, then use same-length
   instructions to read the current font index for that layout.
5. Preserve script length, subsequent instruction addresses, branch labels, the string
   region, and archive content.

The current layouts cover two generations of verified BGI global `FontRecord` tables:

| BP layout | Font table | Current font index | LINE record |
| --- | --- | --- | --- |
| `bp-modern-font-record-0c00` | `0x80000C00` | `0x80000C0C` | `0x520` |
| `bp-legacy-font-record-0bd4` | `0x80000BD4` | `0x80000BDC` | `0x51C` |

These values are part of complete bytecode layouts and are not used as individual signatures.
Unknown layouts, duplicate matches, invalid string references, and decoding failures all
preserve the original buffer and return value.

### Archive Boundary

Runtime processing operates on BP content that the engine decodes from `sysprg.arc` into
memory. The game directory does not need an unpacked `scrdrv._bp`, and one must not be
required. Loose files, developer analysis directories, and test fixtures do not participate
in detection or attachment.

## Win32 GDI Raster Adaptation

After confirming font creation, selection, raster output, and supporting GDI imports, the
Win32 path connects the target module's IAT to the installed general font hooks. The metrics
module measures ink, total width, and `TEXTMETRIC` for the source and replacement fonts,
normalizes width and height within a bounded candidate range, and caches results by LOGFONT
and `ConfigVersion`.

Glyph caches are refreshed according to the configuration version observed by the rendering
thread only after both layout and instance validation. Probe fonts bypass replacement through
`ScopedInternalFontProbe`, keeping source and target fonts distinguishable.

## Configuration

- `EnableBgiHook`: BGI master switch, enabled by default; controls installation of both the
  LINE and Win32 GDI layers.
- `BgiPatchGdiImports`: controls only Win32 GDI IAT patching.
- `BgiClearGlyphCacheOnSwitch`: controls only version-based refreshes of verified Win32 glyph caches.

LINE adaptation is an automatic capability under `EnableBgiHook`. It adds no per-game
configuration and is not bound to code page options.

## Logging

The LINE layer uses structured `[DEBUG][BGI]` logs:

- `phase=line-font-capability decision=attached evidence=x64-fastcall-dsc`: the decoder
  profile is unique and Detours attachment succeeded.
- `phase=line-font-capability decision=skip ... fallback=original-script`: DSC or decoder
  capabilities are incomplete; preserve the original script.
- `phase=line-font-apply decision=patched evidence=bp-... size=... offset=...`: the decoded
  BP has a unique match and the same-length patch is complete.
- `phase=line-font-apply decision=skip evidence=multiple-layout-matches`: the input is
  ambiguous; preserve the original content.

Success and ambiguity logs both have per-process limits. Decoding other DSC/BP resources
does not produce unbounded miss logs.

## Invariants

- Do not depend on an external or previously unpacked `scrdrv._bp`.
- Do not identify capabilities by game name, path, fixed RVA, a single font name, or a single
  byte offset.
- Identity, DSC decoder capabilities, BP semantic routing, and Win32 GDI capabilities remain
  separate stages.
- Decoder signatures must match uniquely in executable sections; internal relative `call`
  targets must fall within the executable image range.
- BP modifications must pass header, boundary, string reference, complete instruction
  sequence, and uniqueness checks and preserve length.
- Unknown architectures, unknown ABIs, unknown BP layouts, and any boundary failure preserve
  the original function's return value and output.
- This adapter does not decode ANSI text, force CP932, or change the text substitution code page.
- High-frequency decoder hooks do not access disk, parse archive directories, allocate
  unbounded caches, or produce unbounded logs.

## Evidence and Reproduction

1. Record architecture, SHA-256, image sections, and `DSC FORMAT 1.00` for the main module.
   Count matches for each decoder profile separately; only one profile with a unique match
   is expected to be allowed.
2. Validate BP header and body lengths in DSC output. Record semantic layout, match count,
   patch offset, and sizes before and after patching.
3. Use a BP disassembler to confirm that the patched code reads the current font index and
   leaves the address of the next `FontRecord` copy instruction unchanged.
4. Retain both capability and apply logs at runtime. Without an apply log, the display alone
   cannot establish that routing occurred.
5. Verify fallback to original content separately for BGI identity without a known decoder,
   a decoder without a LINE layout, duplicate layouts, and damaged BP.

| Scenario | Identity | LINE capability | BP routing | Expected result |
| --- | --- | --- | --- | --- |
| BGI + unique x86/x64 DSC profile + known LINE layout | Pass | Pass | Unique match | Same-length change to the current font record |
| BGI + unique DSC profile + ordinary BP | Pass | Pass | No match | Original output unchanged |
| BGI + unknown or duplicate DSC profiles | Pass | Fail | Not performed | Original decoder and script |
| BGI + known profile + duplicate/damaged LINE layout | Pass | Pass | Rejected | Original output unchanged, with bounded logging |
| GDI imports or DSC strings only | Fail | Not performed | Not performed | No BGI-specific hooks installed |

See [Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for
common evidence fields and record formats.
