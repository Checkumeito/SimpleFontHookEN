# Build and Release

## Environment

- Visual Studio 2022
- MSVC v143 C++ toolset
- Windows 10 SDK
- `detours.h`, `detours.lib`, and `detours_x64.lib` in the repository root

The solution contains four configurations combining Debug/Release with Win32/x64.
The final DLL name is fixed as `winmm.dll`.

## Build Commands

Build and compress both Win32 and x64 Release in one run:

```bat
build_release.bat
```

To build only one architecture, use:

```bat
build_x32.bat
build_x64.bat
```

The Post-Build Event for both Release configurations automatically compresses and
validates `winmm.dll` in the standard output directory after a successful build.
Building through Visual Studio, MSBuild, or repository scripts therefore behaves
consistently. Scripts default to incremental `Build`, preserving IPDB/IOBJ generated
by Release LTCG. To clear all intermediate artifacts, explicitly use a full rebuild:

```bat
build_release.bat rebuild
build_x32.bat rebuild
build_x64.bat rebuild
```

You can also run the following in a Visual Studio Developer Command Prompt:

```bat
msbuild SimpleFontHook.sln /t:Build /p:Configuration=Release /p:Platform=Win32 /v:minimal
msbuild SimpleFontHook.sln /t:Build /p:Configuration=Release /p:Platform=x64 /v:minimal
```

`Rebuild` deletes IPDB/IOBJ first, so a full rebuild may print
`Previous IPDB not found, fall back to full compilation.`. This is the expected linking
process after cleanup. Use the default `Build` for everyday builds so the linker can
reuse the previous LTCG state.

### Visual Studio 2026 MSBuild with the Installed v143 Compiler

If Visual Studio 2026 reports `MSB8020` because its v143 MSBuild definitions are
missing, while MSVC `14.44.35207` is installed, the following command-line overrides
use the available v145 build definitions with that installed compiler. They do not
retarget the checked-in project. This combination is verified for the local English
build; the ordinary commands above remain the Visual Studio 2022 workflow.

```bat
msbuild SimpleFontHook.sln /t:Build /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v145 /p:VCToolsVersion=14.44.35207 /v:minimal
msbuild SimpleFontHook.sln /t:Build /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v145 /p:VCToolsVersion=14.44.35207 /v:minimal
```

## Artifacts

| Architecture | DLL | Debug symbols |
| --- | --- | --- |
| Win32 | `Release/winmm.dll` | `Release/winmm.pdb` |
| x64 | `x64/Release/winmm.dll` | `x64/Release/winmm.pdb` |

Deployment requires only the DLL matching the architecture. PDBs locate crash
addresses; they do not replace the source and configuration records for the
corresponding build.

## Reproducible Build Records

Keep the following fields in a separate directory for each deliverable build:

| Field | Example/source |
| --- | --- |
| Source identity | Workspace path, commit ID, or archive SHA-256 |
| Toolchain | Visual Studio version, MSVC version, Windows SDK version |
| Configuration | `Release` + `Win32` or `Release` + `x64` |
| Command | The script or `msbuild` command actually executed |
| Artifact hashes | DLL and PDB SHA-256 |
| Export snapshot | `dumpbin /nologo /exports` output |
| Configuration snapshot | The `FontHook.ini` used with the DLL |

PowerShell record example:

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
Get-FileHash -Algorithm SHA256 -LiteralPath @(
  'Release\winmm.dll', 'x64\Release\winmm.dll',
  'Release\winmm.pdb', 'x64\Release\winmm.pdb'
) |
  Tee-Object artifacts\build-sha256.txt
```

Record the build script's `Build` or `Rebuild` choice, export tables, and file sizes
separately. Do not mix artifacts from different architectures or configurations in
one evidence directory.

## Release Optimization

The project's Release configurations retain these size optimizations:

- Whole-program optimization and function-level linking.
- `/Os` for size, `/Gw` for global-data optimization, and string pooling.
- RTTI disabled.
- C++ exception unwinding disabled in Release with `_HAS_EXCEPTIONS=0`; Debug keeps the toolchain defaults.
- `/OPT:REF` removes unreferenced symbols.
- `/OPT:ICF` folds identical COMDATs.
- Incremental LTCG reuses IPDB/IOBJ in ordinary `Build`; full `Rebuild` explicitly clears intermediate state.

DLL exports, Win32 hooks, and engine callbacks must not propagate C++ exceptions.
Release code reports failures through return values, bounds checks, and existing SEH
paths. New code must not depend on `throw`/`catch` or exception unwinding for cleanup.
Diagnostic code that tests C++ exception behavior belongs in Debug and must not change
the normal successful Release path.

When adding third-party libraries, large static mappings, template instantiations,
or debug strings, record Win32 and x64 DLL size changes separately. Do not remove
required error handling, bounds checks, or proxy exports to reduce DLL size.

## Proxy Export Checks

`winmm.dll` also serves as a system DLL proxy. Before release, inspect its exports
with `dumpbin`:

```bat
dumpbin /nologo /exports Release\winmm.dll
dumpbin /nologo /exports x64\Release\winmm.dll
```

Compare export names, ordinals, and forwarding targets before and after the change.
Ordinary font-feature changes should not alter the proxy export table.

## Automatic Release Compression

The Release Post-Build Event automatically compresses the final DLL with the pinned
UPX version at `tools/upx/upx.exe`; no additional installation or path argument is
required. To skip compilation and manually compress an existing DLL, run:

```bat
pack_release.bat Win32
pack_release.bat x64
pack_release.bat all
```

To temporarily override the bundled version, supply a custom `upx.exe` path as the
second argument, or provide it through the `UPX_PATH` environment variable or `PATH`.
The script compresses a temporary copy with `--best --lzma` and runs the `upx -t`
integrity check before writing:

| Architecture | Compressed standard DLL |
| --- | --- |
| Win32 | `Release/winmm.dll` |
| x64 | `x64/Release/winmm.dll` |

The script works on a temporary copy first and overwrites the standard DLL only after
the UPX integrity check passes. Repeating the command detects and validates an
already compressed DLL without recompressing it. Compression reduces disk and
distribution size only; it does not reduce the decompressed memory image or remove
any engine adapter. To debug with a Release PDB, first run
`tools\upx\upx.exe -d winmm.dll`, or rebuild with `SIMPLEFONTHOOK_SKIP_PACK=1`.
Some security products or enterprise policies refuse to load packed DLLs. Use a build
that skips compression in such environments; do not change or bypass system security
policies.

If signing is needed, sign the final release copy after compression. Compressing a
signed file invalidates its original signature.

## Release Checklist

1. Both Win32 and x64 Release builds succeed.
2. Build logs contain no compilation or linking errors.
3. Proxy export names and ordinals remain compatible.
4. Record both DLLs' file sizes and SHA-256.
5. Default configuration disables detailed debug logs and high-frequency sampling.
6. The README, configuration documentation, and architecture documentation corresponding to code changes are synchronized.
7. Back up existing `winmm.dll` and `FontHook.ini` in the target directory before deployment.
8. Place only the DLL matching the target process architecture in the target directory.
9. For engine samples requiring reproduction, save sample hashes, configuration, logs, and positive/negative validation results using [Feature Evidence and Reproduction](reproduction.md).

## Rollback

Exit the target program before restoring the original `winmm.dll` and `FontHook.ini`.
Do not overwrite a DLL already loaded by the process, or mix DLLs, PDBs, and
configuration snapshots from different builds.
