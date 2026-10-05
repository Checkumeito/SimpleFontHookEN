# Engine Adapters

## Responsibilities

`engines/` contains engine compatibility logic beyond the general GDI, GDI+, and DirectWrite
hooks. Each adapter handles target environment detection, engine resources or caches,
configuration version refreshes, and diagnostics. Font replacement, character sets, code pages,
and text substitution remain the responsibility of their respective general modules.

## Coverage of the General Paths

General hooks only cover calls that pass through Windows font APIs. Game engines may also read
prerendered glyphs, package fonts in archives, retain internal caches, or render directly through
FreeType, Python, Mono, IL2CPP, or Chromium. In these cases, replacing `HFONT` only affects
auxiliary paths; engine resources still determine the actual text on screen.

Adapters convert the current font configuration into resources or objects that the engine can
consume and maintain their cache lifecycles when the configuration version changes. They do
not take over the general font model or automatically change text encoding when an engine is
identified.

## Compilation Structure

Engine implementations participate in aggregate translation units as `.cppinc` fragments:

- `hooks/font_hooks.cpp` includes font, file, and runtime adapters.
- `hooks/hook_policy.cpp` includes adapters that only return hook policies.
- `.cppinc` fragments share saved `org*` APIs, Detours targets, and process state with internal linkage.
- Each engine directory's `README.md` is the entry point for that adapter's responsibilities,
  detection conditions, and configuration.

## File API Boundary

- `engine_file_dispatch.cppinc` maintains file hiding, redirection, virtual attributes, and engine priority.
- `engine_file_hooks.cppinc` adapts the Win32 ANSI and Unicode file APIs.
- Engine directories provide path classification, resource content, and state update functions.
- The dispatcher uses saved `org*` targets when calling the real file APIs.

File opens, attribute queries, and directory searches share the same classification rules.
The A/W entry points only convert parameters and publish results.

The unified dispatcher's processing order has semantic significance: it first checks whether a
file needs to be hidden, then processes cache files, real font file redirection, Web/ASAR
overrides, and Artemis virtual resources in sequence. Each handler claims a request only when
it matches completely; unhandled requests return to the saved `org*` API. Thread-level
recursion guards and `EngineCommon::IsInternalFileQuery` ensure that adapters' own probes and
font reads see the real file system.

## Identity, Capabilities, and Routing

Adapters operate in three stages:

1. Identity confirmation uses engine module markers, runtime exports, framework directory
   structures, or the combined evidence of successfully parsing an archive format and finding
   engine resources inside it.
2. Capability confirmation checks whether the current version provides the target API, method,
   cache layout, or configuration field.
3. Resource routing selects the appropriate handler from the actual request path only after
   identity and capabilities have been confirmed.

File extensions, generic archive names, generic GDI imports, and any single filename only
narrow the search. Shared suffixes such as `.arc`, `.dat`, `.pfs`, `.med`, and `.tft` do not
establish engine identity by themselves. Static identity results are cached per process;
dynamic module exports are queried again after the module loads. High-frequency hooks only
read cached state and perform bounded path classification.

The evidence requirements for these three stages are:

- Identity answers which engine the current process belongs to and requires stable,
  discriminating evidence.
- Capabilities answer whether this version can use a particular adaptation path; different
  versions of the same engine may use different entry points.
- Routing answers whether the current request belongs to that capability and only handles
  specific resources after identity has been confirmed.

Treating an extension as identity sends programs that share `.arc`, `.dat`, `.med`, or `.tft`
to the wrong handler. Folding capabilities into identity causes a version that lacks an
optional interface to lose other available adaptation capabilities.

## General Workflow

1. Installation or the first low-frequency query collects identity information and caches
   static results in process state.
2. The adapter checks configuration switches and version capabilities, then locates the
   required exports, methods, archive resources, or cache layouts.
3. When a general hook encounters a specific file, font query, or runtime call, it only
   performs bounded classification and reads the prepared results.
4. The adapter returns a virtual file, font data, or a runtime object; unmatched paths retain
   the original API semantics.
5. When `ConfigVersion` changes, the adapter invalidates old caches and prepares or applies
   the current version's resources on the appropriate thread.

## Configuration Versions

`Config::ConfigVersion` identifies a complete runtime font configuration. Font bytes,
resource content, metrics, object handles, and cache refreshes record the corresponding
version. `FontHooks::NotifyConfigChanged` dispatches version notifications to engine adapters
that support live switching.

The configuration version forms part of the identity of font bytes, virtual paths, resource
objects, and refresh records. As a result, changes to weight, metrics, character set capabilities,
or `cmap` configuration create a new resource snapshot even when the font family name stays
the same.

## Engine Index

| Engine | Primary responsibilities | Documentation |
| --- | --- | --- |
| Common foundation | Identity policies, path boundaries, module queries, font sources, and virtual files | [common/README.md](common/README.md) |
| Artemis | Table files, PFS, font resources, and runtime caches | [artemis/README.md](artemis/README.md) |
| Artemis Legacy | IET/text scripts, RFT, and versioned font resources | [artemis_legacy/README.md](artemis_legacy/README.md) |
| BGI | LINE font scripts after x86/x64 DSC decoding; Win32 GDI raster metrics, IAT, and glyph caches | [bgi/README.md](bgi/README.md) |
| classic CatSystem2 | FreeType file fonts, the `font` directory, and font resource registration | [catsystem2/README.md](catsystem2/README.md) |
| DxLib | `_FONTSET.MED` cache consistency | [dxlib/README.md](dxlib/README.md) |
| EntisGLS | Bitmap font registration, internal font objects, and glyph rasterization | [entis/README.md](entis/README.md) |
| Escu:de | `configure.cfg` font configuration view | [escude/README.md](escude/README.md) |
| KiriKiri / TVP | Prerendered font runtime dispatch that preserves TJS members | [krkr/README.md](krkr/README.md) |
| Majiro | FCD disk caches and runtime glyph caches | [majiro/README.md](majiro/README.md) |
| Mirai | FreeType font data sources and font file redirection | [mirai/README.md](mirai/README.md) |
| Ren'Py | Python font mappings, virtual file callbacks, and cache refreshes | [renpy/README.md](renpy/README.md) |
| Softpal | Pal default font types and bitmap font entry points | [softpal/README.md](softpal/README.md) |
| TinkerBell | Wide-character font creation and DC tracking policies | [tinkerbell/README.md](tinkerbell/README.md) |
| TyranoScript | ASAR overrides, Web fonts, and Electron bridging | [tyrano/README.md](tyrano/README.md) |
| Unity | Mono/IL2CPP, TMP font resources, and thread scheduling | [unity/README.md](unity/README.md) |
| YU-RIS | YPF bitmap font identification, CP932/GBK/Big5/YDG resource profiles, and atlas replacement after decoding | [yuris/README.md](yuris/README.md) |

## Evidence Index

| Adapter | Identity evidence | Capability/resource entry points | Negative sample |
| --- | --- | --- | --- |
| Artemis | PFS `pf2/pf6/pf8` + `list_windows*.tbl` resource family | Table fields, PFS fonts, and caches | PFS without table resources |
| Artemis Legacy | PFS + `.iet` in `system/_base` | IET, RFT, and virtual SFNT | Artemis table resources only |
| BGI | Buriko module markers or BURIKO magic bytes | x86/x64 DSC decoders and BP LINE semantic layouts; Win32 GDI imports and caches | DSC strings or GDI imports only |
| classic CatSystem2 | `CatScene/cs2confx` + `kcFontImage_Win/FT` | `font/*.ttf/.otf/.ttc/.otc` | Only one marker group |
| DxLib | DxLib module markers + font contract | `_FONTSET.MED`, `GetFontData` | MED suffix only |
| EntisGLS | `SGLFont::m_pFontStock` + bitmap loader class evidence | BMF, RTTI/vtable, and reference fonts | Either evidence group missing |
| Escu:de | `Company=ESCUDE` + nonempty `Product` | Profile `[Font] Face/Font` | Company or product missing |
| KiriKiri/TVP | ANSI/Unicode `mapPrerenderedFont` | `.tft` hiding and live GDI path | Only one method marker |
| Majiro | `MajiroObj/MajiroArcV/MajiroSavV` | `savedata/fc_*.fcd`, runtime tables | `.fcd` suffix only |
| Mirai | FreeType contract + font configuration markers | Fixed `GetFontData` source, Windows Fonts | FreeType only |
| Ren'Py | `renpy/`, `__init__.py`, and core subsystems | Python callbacks and virtual font names | Script directory only |
| Softpal | `PalFontBegin/SetType/GetType` export set | Type `4 -> 1`, `DEFAULT_FONT.DAT` | Incomplete exports |
| TinkerBell | `Software\\TinkerBell\\` or a combination of Cyberworks markers | `HookPolicy` creation/selection policies | Similar DAT/DLL files |
| TyranoScript | Unpacked `resources/app/tyrano` or ASAR + Tyrano resources | Web fonts, ASAR, and Electron bridging | Electron without Tyrano resources |
| Unity | `UnityPlayer` + Mono or `GameAssembly`/IL2CPP | Mono/IL2CPP TMP and UI.Text | Runtime exports missing |
| YU-RIS | `ysbin\\yscfg.ybn` + `yu-ris1` | YPF profiles, WebP/PNG/YDG | Incomplete profile or non-font image |

Each row lists only the minimum combination of identity and capabilities. Complete fields,
commands, and expected logs appear in the corresponding README's "Evidence and Reproduction"
section and in [Feature Evidence and Reproduction Workflow](../../../../docs/reproduction.md).

## Documentation Standards

Each engine README maintains the following: responsibilities, detection conditions, file
entry points, features, configuration, runtime constraints, evidence sources, reproduction
steps, and a verification matrix.
Code identifiers, paths, configuration keys, and runtime names retain their source spelling.
Documentation describes the current implementation and stable interfaces; troubleshooting
procedures are recorded in the [diagnostics documentation](../../../../docs/diagnostics.md).

## Extension Checklist

Before extending an adapter directory, answer these questions:

1. Which observable or controllable call is missing from the general font path?
2. Which evidence confirms engine identity, and which only confirms version capabilities?
3. How do resource requests enter the adapter through the unified file dispatcher or runtime
   scheduling entry point?
4. How is original behavior preserved when configuration is disabled, identity does not
   match, capabilities are missing, or preparation fails?
5. Which work belongs to expensive preparation, and which state can be read with bounded
   operations on high-frequency paths?
6. How are the current version's resources created, published, invalidated, and released?

## Unified Reproduction Records

Each adapter retains at least one positive sample, one similar non-target sample, one sample
with missing capabilities, and one boundary input. Record the following fields: sample
SHA-256, architecture, configuration snapshot, identity markers, capability entry points,
original request, normalized routing, `ConfigVersion`, log `decision`/`fallback`, and expected
artifacts. Grade file, export, runtime interface, and resource parsing evidence using the
`O/I/U` levels in [Feature Evidence and Reproduction Workflow](../../../../docs/reproduction.md).

| Result type | Identity | Capabilities | Routing | Expected behavior |
| --- | --- | --- | --- | --- |
| Positive | Pass | Pass | Match | Use adapter resources or objects |
| Non-target | Fail | Not evaluated | Pass through | Preserve `org*` API semantics |
| Missing capabilities | Pass | Fail | Record fallback | Do not perform specialized resource processing |
| Boundary | Pass | Pass | Empty/long/unknown request | Handle with bounded operations and preserve error codes |
