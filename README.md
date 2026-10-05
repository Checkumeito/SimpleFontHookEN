# SimpleFontHookEN

SimpleFontHookEN is an English fork of
[SuQiandYing/SimpleFontHook](https://github.com/SuQiandYing/SimpleFontHook).
SimpleFontHook is a font compatibility and replacement DLL for Windows games. The DLL
loads with the target process as a `winmm.dll` proxy, retaining the system `winmm`
exports while hooking into GDI, GDI+, DirectWrite, and selected engine runtimes.
The project treats font objects, font data, text encoding, and engine resources as
separate layers, choosing the smallest adaptation surface for the actual call path.

## Main Capabilities

- Replace fonts created through ANSI, Unicode, GDI+, and DirectWrite APIs.
- Adjust font height, width, character spacing, line spacing, weight, and vertical metrics.
- Control charset spoofing, code page redirection, Japanese proxy glyph mapping, and Traditional/Simplified Chinese character mapping independently.
- Switch fonts live through the font picker and save `FontHook.ini`.
- Provide a guide for regular users in the font picker, covering font selection, application, display correction, and layout adjustments.
- Generate system font atlases at runtime for confirmed YU-RIS CP932, GBK, and Big5 bitmap font resources, and Relirium YDG bitmap font resources.
- Provide compatibility paths for Unity Mono/IL2CPP, classic CatSystem2, BGI, Artemis and Artemis Legacy, KiriKiri,
  Entis, Softpal, Escude, Mirai, Majiro, DxLib, TinkerBell, TyranoScript, Ren'Py, and YU-RIS.

## How It Works

Applying a font involves the following layers:

1. Windows loads the proxy `winmm.dll` from the application directory. The proxy exports continue forwarding to the system `winmm`.
2. `FontHooks::Install` reads `FontHook.ini` and installs general API hooks and engine entry points with confirmed capabilities in the same Detours transaction.
3. The general font model creates a replacement `HFONT` from the source `LOGFONT`, target font, and configuration version, and provides a consistent view for drawing, measurement, enumeration, and font data queries.
4. Engine adapters handle resources that general APIs cannot see, such as prerendered fonts, disk caches, archive contents, Python mappings, and Mono/IL2CPP managed objects.
5. The font picker saves the configuration and increments `Config::ConfigVersion`. Caches and engine resources accept only data for the matching version, making each switch a complete snapshot.

This layering ensures that font replacement changes only font-related state.
Charset spoofing, code page conversion, and character mapping each have independent
switches and data flows. The replacement font's charset is not used to determine
the source text encoding.

## Feature Evidence and Reproduction

Module documentation describes features through four categories: inputs and
preconditions, execution entry points, outputs and fallbacks, and verification
methods. Engine adapters record identity confirmation, version capabilities, and
resource routing separately. General GDI imports, file extensions, or a single
filename do not establish engine identity. Conclusions can be traced to evidence
through source files, symbols, commands, or runtime logs with named fields.

To reproduce behavior on another sample, first record its SHA-256, architecture,
and `FontHook.ini` snapshot, then establish a baseline with the target adapter
disabled. Collect PE, file structure, and runtime evidence, extract the minimum
input/output contract, and exercise positive, non-target, missing-capability,
and boundary scenarios. See the
[Feature Evidence and Reproduction Workflow](docs/reproduction.md)
for the complete procedure and record templates.

## Quick Start

1. Confirm the target application's architecture. Use the Win32 build for a 32-bit application and the x64 build for a 64-bit application.
2. Back up any existing `winmm.dll` and `FontHook.ini` in the target application directory.
3. Place the matching `winmm.dll` next to the target executable.
4. Start the application, choose the Chinese, Japanese, Traditional Chinese, or Korean charset that matches the game text's actual encoding, then select and apply a font.

The font picker first tries to register the single-key `Insert` shortcut. If it
conflicts, it tries `Pause`, then `Scroll Lock`. The footer and guide show the key
that was successfully registered. The configuration file is saved next to the DLL
using UTF-8 encoding.

## Build

Prerequisites: Visual Studio 2022, the v143 C++ toolset, and the Windows 10 SDK.
The repository root already includes the Detours headers and static libraries
used by Win32 and x64.

```bat
build_x32.bat
build_x64.bat
```

Release outputs:

- Win32: `Release/winmm.dll`
- x64: `x64/Release/winmm.dll`

See [docs/build-and-release.md](docs/build-and-release.md) for the complete build
and release checks.

## Directory Structure

| Path | Responsibility |
| --- | --- |
| `SimpleFontHook/dllmain.cpp` | Process load entry point and shutdown signal |
| `SimpleFontHook/hooks/` | Detours hooks, font replacement model, and engine adapters |
| `SimpleFontHook/font/` | TTF/OTF/TTC parsing and font table modification |
| `SimpleFontHook/ui/` | Font picker, configuration application, and drawing |
| `SimpleFontHook/utils.cpp` | Configuration persistence, custom font loading, and diagnostics |
| `Release/`, `x64/Release/` | Release build outputs |

## Module Boundaries

- `dllmain.cpp` only exposes the installation entry point and shutdown signal. Business logic resides in the hook, font, UI, and configuration modules.
- `hooks/font_hooks.cpp` aggregates `.cppinc` implementations, keeping original API pointers and engine state at internal linkage.
- `font/` handles only SFNT/TTC bytes. It does not read game text or participate in engine identification.
- `ui/` only modifies configuration and publishes version notifications. It does not directly manipulate internal engine objects.
- `engine_file_dispatch.cppinc` is the sole cross-engine dispatch entry point for file hiding, virtual attributes, and redirection.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Feature Evidence and Reproduction Workflow](docs/reproduction.md)
- [Build and Release](docs/build-and-release.md)
- [Diagnostics and Troubleshooting](docs/diagnostics.md)
- [Contribution and Coding Rules](CONTRIBUTING.md)
- [Automation Agent Rules](AGENTS.md)
- [Hook Module Structure](SimpleFontHook/hooks/README.md)
- [Engine Adapter Index](SimpleFontHook/hooks/internal/engines/README.md)
- [UI Module Structure](SimpleFontHook/ui/README.md)

## Core Invariants

- Font replacement handles only font objects and font data. It must not implicitly change text encoding.
- Text encoding is determined from the application's original charset and explicit configuration, never inferred from the replacement font.
- Engine adapters must have verifiable positive detection conditions. General GDI imports alone cannot identify a specific engine.
- Hooks use saved `org*` pointers when calling real Win32 APIs to avoid recursive hook entry.
- High-frequency paths must not repeatedly scan executables, resource archives, or font files.
- Code changes must preserve successful Win32 and x64 Release builds.
