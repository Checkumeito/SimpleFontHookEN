# KiriKiri / TVP Adapter

## Responsibilities

Preserve the native registration of `Font.mapPrerenderedFont` and `Font.unmapPrerenderedFont`.
After confirming TVP native-method capabilities, redirect prerendered mapping calls to the
unmapping method on the same font instance, allowing subsequent real-time rasterization to
enter the generic font hooks. Do not modify game scripts, EXE files, TJS member names, or TFT files.

## Entry Points and Dependencies

- `krkr_paths.cppinc`: Identity cache, TVP plugin ABI binding, and native-method dispatch.
- `KrkrPatchMapPrerenderedFontName`: Retains the existing installation entry-point name and performs only read-only identity checks.
- `KrkrMaybeWrapGetProcAddress`: Wraps the `V2Link` entry point through `newGetProcAddress`.
- `KrkrShouldHidePrerenderedFontW`: Compatibility entry point for the unified file dispatcher; always passes through.
- Reuses existing Detours, `orgGetProcAddress`, configuration, and the generic GDI font model; introduces no TJS SDK library.

## Identity, Capabilities, and Flow

1. Use the ANSI or Unicode `mapPrerenderedFont` marker in the main module for a cached identity
   check; paths, `.tft`, and the XP3 extension are not identity evidence.
2. `V2Link` receives the TVP exporter on the engine's script thread. Store at most 16 distinct
   plugin entry points, each with its own thunk. Preserve the original parameters, HRESULT, and
   nested plugin calls; do not call TJS from `GetProcAddress`.
3. Query the global object and Variant operations through the official export signatures, and
   obtain `Font`'s map/unmap members. `TJS_IGNOREPROP` prevents property-getter side effects;
   Variant construction, cleanup, type queries, and object queries are all performed by the
   engine. The x86 exporter-query entry point uses a stack-neutral boundary to identify `cdecl`
   (pops 0 bytes) or `stdcall` (pops 16 bytes), then uses the corresponding virtual-interface
   convention for reference counting, property retrieval, and native dispatch. Generated TVP
   export helpers and `V2Link` still use `stdcall`; they do not switch with the virtual-interface
   convention. x64 uses the platform's unified calling convention. Do not continue binding if
   the stack-cleanup amount is unknown.
4. The exporter-query function, required functions, and native-dispatch entry point must belong
   to the main module, avoiding references to unloadable plugin code. Verify `FuncCall` using a
   temporary native method created by the engine; do not treat script functions or custom
   dispatchers as native methods.
5. Install Detours only after every capability is confirmed. Within the shared `FuncCall`,
   filter precisely by the map-method object pointer. When the switch is enabled and parameters
   are valid, call the native unmap method with the original font instance, no arguments, and
   the original result pointer. Other methods, nondefault-member calls, missing instances,
   insufficient arguments, and a disabled switch all call the original dispatcher.
6. Do not hide TFT files; loose and archived fonts do not need separate redirection. Missing
   interfaces, a class that is not yet ready, mismatched dispatch, or Detours failure all
   preserve the engine's original behavior. Later plugin links may retry, up to 32 attempts.

## Invariants and Lifecycle

- Do not rename `mapPrerenderedFont`, rely on scripts having `try/catch`, or match or rewrite the `unmap` substring.
- After successful installation, hold engine references to the map/unmap objects for the process lifetime; failure paths release temporary references.
- Do not scan modules, read or write disk, or allocate resources on the font hot path; other native methods incur only one additional pointer check.
- The plugin-slot lock protects only slot allocation; do not call plugins or the engine while holding it.
- Do not call TJS, wait for threads, or uninstall runtime hooks from `DLL_PROCESS_DETACH`.
- Keep fonts, code pages, and text mapping independent; do not add sample-specific identification or modify game files.

## Configuration

- `EnableKrkrHook=1`: Enables identity checks and runtime bridging.
- `KrkrDisablePrerenderedFonts=1`: The installed dispatcher reads this switch on each map call;
  disabled calls the original map, enabled calls unmap. Existing configuration declarations,
  defaults, and persistence remain unchanged.
- Generic font settings continue to control the font name and metrics for real-time rendering.

The switch affects only subsequent mapping calls; it does not automatically replay earlier
`mappfont` calls or enumerate every font instance. Fonts already mapped by the game must be
unmapped through later mapping calls; switching from enabled to disabled does not automatically
restore an old TFT mapping.

Prerendered replacement is not guaranteed when there is no plugin link, plugin linking occurs
after font mapping, the TJS runtime is outside the main module, `Font` is reconstructed at
runtime, or the font path bypasses the native map method. These cases pass through to preserve
startup. Rasterizers that do not pass through the generic GDI hooks are also outside this
adapter's font-replacement guarantee.

## Evidence and Reproduction

Official ABI references:
[TJS Dispatch Interface](https://github.com/krkrz/krkrz/blob/master/tjs2/tjsInterface.h),
[TVP Export Bridge](https://github.com/krkrz/krkrz/blob/master/base/win32/FuncStubs.cpp),
[Native-Method Dispatch](https://github.com/krkrz/krkrz/blob/master/tjs2/tjsNative.cpp),
[Font map/unmap](https://github.com/krkrz/krkrz/blob/master/visual/LayerIntf.cpp).

These sources establish the interface contract; they do not establish runtime verification for
any particular game version. Record version-specific cases and observations in the
[Diagnostics Documentation](../../../../../docs/diagnostics.md).

## Extension and Verification

| Scenario | Expected Behavior |
| --- | --- |
| Valid map call, switch enabled | The original member still exists; the original instance executes unmap; the native dispatcher cleans up the result |
| Switch disabled or a non-map call | The original dispatcher receives the original parameters |
| Missing capability, nontarget program, or export lookup by ordinal | No installation, renaming, or file hiding |
| Multiple plugins, repeated lookups, full slots, or nested links | Original V2Link calls remain correctly associated; full slots pass through |
| Loose TFT file or resource inside XP3 | Win32 file visibility remains unchanged |
| Insufficient arguments or a null instance | Preserves engine validation and error codes |
| x86 cdecl / stdcall virtual interface | The stack is balanced after querying; reference counting, PropGet, and FuncCall use the same convention |

Before extending support to another runtime, independently verify exports, calling conventions,
object lifetime, and initialization timing. For C++ changes, check Win32/x64 Release builds;
offline interface fixtures verify only the dispatch contract and cannot replace in-game font
rendering verification.
