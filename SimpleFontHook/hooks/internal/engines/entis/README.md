# EntisGLS Adapter

## Responsibilities

This directory handles EntisGLS bitmap font registration, `SGLWindowsFont` glyph rasterization,
and `SGLReferenceFont` font proxies. The adapter connects internal engine font objects to the
general HFONT replacement path and supports font refreshes driven by configuration versions.

## Coverage of the General Paths

EntisGLS can create internal objects from BMF bitmap fonts and manage HDC, HFONT, styles, and
glyph rasters itself through `SGLWindowsFont` and `SGLReferenceFont`. General font creation
hooks can affect individual Win32 calls but cannot organize the bitmap font branch, reference
objects, and internal lifecycles into consistent state.

The adapter routes BMF registration to the Windows font implementation, creates proxy objects
for reference fonts, and limits replacement HFONT selection to a single engine raster call.
This covers internal engine objects while preserving the original objects' styles and
destruction timing.

## Detection Conditions

The main module must provide both font stock evidence and bitmap loader evidence:

- Export the symbol corresponding to `SGLFont::m_pFontStock`.
- Export `SGLBitmapFontLoader::m_RuntimeClass`, or contain the corresponding runtime class
  name in the image.

Complete runtime object adaptation targets the Win32 MSVC layout; other architectures retain
the unified call entry points.

## File Structure

- `entis_font.cppinc`: aggregation entry point.
- `entis_state.cppinc`: PE image views, detection, memory range checks, and logging.
- `entis_bitmap_font.cppinc`: location and entry handling of bitmap font registration functions.
- `entis_runtime.cppinc`: RTTI/vtable parsing, Windows font proxies, glyph raster hooks, and
  configuration notifications.

## Implementation Principles

1. Module detection validates both the font stock symbol and bitmap loader class evidence.
2. The bitmap registration module locates the BMF registration entry point and sends matching
   requests to the `SGLWindowsFont` path.
3. RTTI and vtable parsers locate `SetStyle`, destruction, and glyph raster methods and
   validate all function addresses.
4. On first use, `SGLReferenceFont` obtains a corresponding Windows font proxy. The proxy
   synchronizes styles and is keyed by the original object.
5. The glyph raster entry point saves HDC state, selects the current replacement HFONT,
   calls the engine method, then restores the original state.
6. Configuration notifications publish the version; the rendering thread observes and
   applies the current font state at controlled entry points.

## Features

- Locate the bitmap font registration entry point and route BMF requests to the
  `SGLWindowsFont` font path.
- Resolve destruction, `SetStyle`, and glyph raster methods for `SGLWindowsFont` and
  `SGLReferenceFont` through RTTI.
- Create corresponding Windows font proxies for reference font objects and synchronize
  styles and lifecycles.
- Select the current replacement HFONT within the scope of a glyph raster call and restore
  HDC state when the call completes.
- Use `ConfigVersion` to record the font configuration observed by the rendering thread.

## Rationale for Design Constraints

- Routing the BMF branch to Windows fonts during registration has a smaller data surface
  than parsing and rebuilding a proprietary bitmap format.
- Proxy objects are managed by the original reference font address, giving style
  synchronization and destructor cleanup an explicit owner.
- HDC changes exist only during a single raster call, preventing the engine's other drawing
  objects from inheriting temporary font state.
- RTTI, vtables, and object memory are validated layer by layer; missing capabilities preserve
  the engine's native font path.
- The complete object layout targets the Win32 MSVC ABI. Architecture checks occur at the
  capability stage rather than the engine identity stage.

## Configuration

- `EnableEntisHook`
- `EntisDisableBitmapFonts`
- `EntisRefreshFontOnSwitch`
- General font name, character set, and metrics configuration

## Runtime Constraints

- PE sections, RTTI, vtables, function addresses, and object memory all undergo range and
  protection attribute validation.
- Reference font proxies are managed by the original object address and released on the
  corresponding destruction path.
- HDC font replacement is limited to the scope of a single raster call.
- Detours attachment uses the unified installation transaction; runtime preparation precedes
  transaction commit.
- A mutex protects the shared proxy table, and its locked scope only covers container access.

## Evidence and Reproduction

1. Inspect main module exports and record symbol or class-name evidence for
   `SGLFont::m_pFontStock` and `SGLBitmapFontLoader::m_RuntimeClass`.
2. Retain address ranges, section protection attributes, and signature check results for RTTI,
   vtables, `SetStyle`, destruction, and glyph raster entry points layer by layer. Addresses
   serve only as evidence for that sample and are not reused across builds.
3. Use BMF, Windows font, and reference font objects to observe registration, proxy creation,
   style synchronization, HDC before and after raster calls, and destructor cleanup.
4. When switching configuration, record the proxy table, object addresses, `ConfigVersion`,
   and threads. Confirm the original path when layout validation fails.

| Scenario | Expected result |
| --- | --- |
| Both export/class evidence groups pass | Install bitmap registration and runtime object capabilities |
| Either evidence group is missing | Do not parse vtables or write object memory |
| Single raster call | Temporarily select the replacement HFONT; restore HDC before returning |
| Reference object destruction | Release proxy by the original object address |
| Non-Entis module | General GDI path; Entis state is empty |

The evidence directory contains PE exports, RTTI/vtable summaries, object lifecycle logs,
Win32/x64 results, and non-target samples. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for field standards.

## Verification

Cover bitmap fonts, Windows fonts, reference fonts, the RTTI export path, the signature scan
path, feature switches, live font switching, object destruction, Win32 Release, and non-Entis
programs.
