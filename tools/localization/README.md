# English Localization Verification

These tools check English prose and the compatibility boundaries of the English
fork. Actual installed font names, Unicode font paths, engine resource markers,
glyph probes, and immutable character pairs remain in their original form.
`compatibility_literals.json` records the exact exceptions and why each is needed.

From the repository root:

```powershell
python tools/localization/check_english.py
python tools/localization/check_compatibility.py
git -c core.whitespace=cr-at-eol -c core.safecrlf=false diff --check
```

The English audit checks tracked and non-ignored text files, strict UTF-8,
literal characters, C/C++ Unicode escapes, Markdown links, and heading anchors.
The compatibility check compares configuration, functional character tables,
probes, resource names, bundled third-party files, UI enum values, existing format
placeholders, and geometry constants against `e26b5ef378dce617d074822456e734b17c509385`.
Pass another baseline commit as its first argument when deliberately updating
this verification contract. Negative audit probes check that untranslated prose,
invalid encoding, and broken heading links are rejected.

## Native Windows Checks

`layout_smoke.cpp` includes production picker geometry and measures real GDI
fonts. It checks minimum, default, and enlarged windows at zoom 0.7, 1.0, and 1.8,
all mapping and redirect button rows, edge clicks, and metric text bounds.

`smoke_host.cpp` loads the actual DLL in a disposable game-like process. Its GDI
and conversion probes report hooked font results, mapping code points, and code
page redirection. `run_smoke.py` drives the picker and checks persisted
configuration while saving screenshots. It requires Python with Pillow and an
interactive Windows desktop. It never uses configuration beside the delivered
DLLs. Preserve each run in a fresh artifact directory.

```powershell
./tools/localization/build_smoke.ps1 -Artifacts artifacts/english-localization/example-run
python tools/localization/run_smoke.py --artifacts artifacts/english-localization/example-run
```

The build script accepts `-CompilerRoot`, `-SdkRoot`, and `-SdkVersion` for other
installed toolchains. Both x86 and x64 fixtures are built. The runtime checks
cover first startup, saved hidden startup, font search/application, charset
scrolling, spoofing, all mapping modes, all redirect presets, metric extremes,
reference controls, guide wrapping/scrolling, window visibility, and shutdown.
Screenshots still require visual review; successful automation alone does not
establish that every caption is readable.

## Exports, Packing, and Symbols

Keep untouched packed baseline DLLs as `baseline/win32.dll` and `baseline/x64.dll`
under the artifact directory. Preserve localized DLLs immediately after linking,
before packing, as `symbols/win32/winmm.dll` and `symbols/x64/winmm.dll`, together
with their PDB files. MSBuild accepts `/p:PostBuildEventUseInBuild=false` to defer
packing; then run the existing `pack_release.bat all` after saving these copies.

```powershell
python tools/localization/check_binaries.py --artifacts artifacts/english-localization
```

This compares all 180 export names, ordinals, and forwarding targets per
architecture, tests packed DLLs with the bundled UPX, and matches the retained
linked DLL's CodeView GUID/age with the delivered PDB. The existing UPX packing
workflow clears debug directories, so use the retained uncompressed DLL/PDB pair
for symbol-based debugging. Standard release DLLs remain packed.

These fixtures cover the generic native host and picker. Engine-specific game
resources and real in-game rendering require their own fixtures.
