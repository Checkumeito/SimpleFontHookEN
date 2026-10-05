# Unity Adapter

## Responsibilities

Unity's TextMeshPro and `UI.Text` do not pass through GDI font creation. This directory creates
replacement-font resources through Mono or IL2CPP runtime interfaces and applies them to
managed objects on the Unity window thread.

## Runtime Adaptation Coverage

Unity text components hold managed `Font` objects, TMP font assets, materials, and atlases,
rather than Win32 `HFONT`s. Font assets are also constrained by GC, Unity object lifetimes, TMP
version differences, and main-thread requirements. File redirection or GDI hooks do not change
the objects held by existing components or automatically ensure that atlases, materials, and
character tables belong to the same font version.

The adapter confirms capabilities through Mono or IL2CPP metadata, constructs font resources
that Unity recognizes at runtime, and schedules their application on the Unity window thread.
All managed objects retained across calls are pinned by runtime handles.

## Two Runtime Paths

| Path | Aggregation Entry Point | Positive Detection |
| --- | --- | --- |
| Mono | `unity_mono.cppinc` | `UnityPlayer.dll` is present, `GameAssembly.dll` is absent, and a supported Mono runtime DLL is present |
| IL2CPP | `unity_tmp.cppinc` | Both `UnityPlayer.dll` and `GameAssembly.dll` are present, followed by resolution of required IL2CPP exports and TMP types |

The UnityPlayer and Mono/IL2CPP runtime combination establishes framework identity; final
capability still requires successful resolution of runtime exports, assemblies, types, and
methods. Resource extensions and game-data filenames do not participate in identity decisions.
Detection results are cached for the process lifetime.

## File Structure

### Mono

- `unity_mono_state.cppinc`: Mono APIs, managed handles, version state, and worker-thread state.
- `unity_mono_runtime.cppinc`: Runtime-export, assembly, type, and method binding.
- `unity_mono_source.cppinc`: Source-font reading and Unity `Font` creation.
- `unity_mono_legacy*.cppinc`: Construction of static TMP glyphs, atlases, and font assets.
- `unity_mono_modern.cppinc`: Dynamic TMP font-asset path.
- `unity_mono_apply.cppinc`: Application to TMP and `UI.Text` objects.
- `unity_mono_jit.cppinc`: Narrow JIT/runtime-call hooks.
- `unity_mono_window.cppinc`: Window-message dispatch, retries, and shutdown.

### IL2CPP

- `unity_il2cpp_state.cppinc`: IL2CPP APIs, bindings, managed roots, and version state.
- `unity_il2cpp_runtime.cppinc`: Export resolution and type/method binding.
- `unity_il2cpp_font_asset.cppinc`: Construction of Unity `Font` objects, TMP font assets, and materials.
- `unity_il2cpp_apply.cppinc`: Enumerates and applies resources to live TMP text objects.
- `unity_il2cpp_window.cppinc`: Unity-thread message dispatch, application thread, and shutdown.

## Resource Construction

### Mono

1. Bind Mono exports, the domain, assemblies, types, fields, and methods, adapting to runtime
   differences through candidate signatures.
2. Create a Unity `Font` from a system or local font file, and pin the source object with a GC handle.
3. Modern TMP uses dynamic font assets and runtime character population. The character set
   grows monotonically within the session, reducing UV invalidation from repeated atlas repacking.
4. The static TMP path builds static glyph tables, Alpha8 atlases, materials, and kerning data,
   then calls its defined refresh entry point.
5. Narrow JIT/runtime hooks provide the current resource before assignment to text objects;
   regular object scanning serves as a capability fallback.

### IL2CPP

1. `UnityPlayer.dll` and `GameAssembly.dll` confirm the runtime combination; IL2CPP exports and
   class queries confirm capability.
2. Use runtime APIs to create a Unity `Font`, TMP font assets, and base materials, and pin the
   managed roots.
3. Enumerate live TMP objects on the Unity thread and apply font assets, materials, and required
   fallback lists.
4. Method entry points depend only on the verified stable prefix of `MethodInfo`; access other
   object layouts through runtime APIs.

## Application Flow

1. Detect the target runtime and install the required message or runtime hooks.
2. Resolve Mono/IL2CPP APIs and TMP/Unity types.
3. Create replacement-font resources from `Config::ConfigVersion` and the current font.
4. Pin managed objects that must be retained across calls using GC handles.
5. Post application requests to the Unity window thread.
6. Apply current resources to live objects and add the replacement font to required TMP fallback lists.
7. After a configuration-version change, create and reapply resources for the current version.
   Resources superseded by the current version are released according to the runtime lifecycle.

## Rationale for the Design Constraints

- Mono and IL2CPP use separate state machines because their exports, metadata, calling ABIs, and object-access methods differ.
- Font-resource creation is separate from object application; if preparation fails, live components retain their original fonts.
- Unity-thread messages perform object changes; worker threads only wait, retry, and post requests, avoiding engine API calls across threads.
- GC handles provide stable roots for objects across messages and frames; native pointers are used only within a single runtime call.
- Do not enter the managed runtime while holding a native mutex, preventing lock-order inversion from callback reentry.
- The configuration version follows the source font, atlas, material, and application record; stale resources do not overwrite the current selection.

## Configuration

The adapter requires all of the following:

- `EnableCatSystemUnityHook=1`
- `EnableFontHook=1`
- `EnableFaceNameReplace=1`
- A nonempty `ForcedFontNameW` or `ForcedFontNameA`

## Thread and GC Invariants

- Worker threads only wait, retry, and post requests; they do not directly perform object changes that require Unity's main thread.
- Before calling the managed runtime, ensure that the current thread is attached to the corresponding domain.
- Objects retained across GC cycles must be pinned by Mono/IL2CPP GC handles.
- Do not call Mono, IL2CPP, or managed methods while holding a native mutex.
- Publish the stop signal first on shutdown; do not wait for threads inside `DLL_PROCESS_DETACH`.
- Delay application while the runtime or font resources are not ready; do not overwrite the original font with a null resource.

## Extension

Extend Unity-version compatibility through candidate method signatures or controlled fallbacks;
resolve types and methods using runtime metadata.

## Evidence and Reproduction

1. Fix the hashes of UnityPlayer, GameAssembly, Mono/IL2CPP runtime DLLs, and target assemblies.
   Record process architecture and the `UnityPlayer.dll`/`GameAssembly.dll` combination.
2. Separately save resolution results for Mono exports, IL2CPP exports, assemblies, types,
   fields, and method signatures. Mark a capability fallback if any required entry point is
   missing; do not confirm identity from file extensions.
3. Build a minimal scene containing `UI.Text`, static TMP, dynamic TMP, and live objects. Record
   created font assets, materials, atlases, fallback lists, Unity window-thread IDs, and GC handles.
4. For configuration switching, perform preparation, posting, main-thread application, and
   another object enumeration. Compare `ConfigVersion` and resource hashes; worker threads must
   not call managed objects directly.
5. Run Mono, IL2CPP, no-TMP, missing-runtime-export, missing-font-source, and non-Unity samples separately.

| Scenario | Expected Result |
| --- | --- |
| Mono combination + complete APIs/assemblies/types | Mono resource creation and application on the Unity thread |
| IL2CPP combination + complete exports/types | IL2CPP resource creation and application to TMP objects |
| UnityPlayer present, but runtime capabilities missing | Preserves the generic path without changing managed objects |
| Worker-thread preparation incomplete | Delays posting; does not overwrite objects with null resources |
| Configuration switch | Applies current-version resources; GC handles and thread boundaries are traceable |
| Non-Unity process | No Unity runtime adaptation is installed |

The evidence directory contains `[DEBUG][UnityMono]` and `[DEBUG][CatSystemUnity]` logs,
runtime-export summaries, resource hashes, thread/handle records, and nontarget samples. For the
generic template, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover Mono, IL2CPP, no TMP installed, missing runtime exports, feature disablement, font
switching, and process shutdown.
