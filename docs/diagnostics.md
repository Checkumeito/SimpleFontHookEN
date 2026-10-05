# Diagnostics and Troubleshooting

## KRKR: Missing mapPrerenderedFont Member at Startup

The screenshot's `first.ks:14` / `mappfont` /
`Member 'mapPrerenderedFont' does not exist` agrees with the supplied script directly
executing `[mappfont storage=MPLUS1C12.tft]` on line 14. Code inspection found that the old
adapter renamed `mapPrerenderedFont` in the main image to an internal name during
installation. A script calling that member directly therefore cannot be assumed to enter
an exception fallback; the substring scan also matches `unmapPrerenderedFont`.
Hiding TFT files may instead turn the issue into a font-resource loading exception.

The current adapter preserves the member name and file visibility. When a plugin's
`V2Link` supplies the official exporter, it binds the native Font methods and redirects
valid map calls to unmap on the same instance. If required interfaces are missing, it
passes calls through; error dialogs are not used to switch font-rendering paths. See the
[KRKR module documentation](../SimpleFontHook/hooks/internal/engines/krkr/README.md)
for boundaries and switch semantics.

The initial change passed only an offline interface fixture. That fixture originally
simulated only `stdcall` virtual interfaces and did not cover the target game's actual
`cdecl` use. The subsequent runtime evidence and correction are described below.

## KRKR: TVP Virtual-Interface Calling Convention Causes Startup Fail-Fast

When `hfeti_risa_crack.exe` was run, the old DLL exited with `0xC0000409`, and Windows
Application Error recorded `WINMM.dll+0x5f305`. Parameter 2 of the second-chance exception
captured by the debugger indicated a security-cookie check failure. The PDB stack located
it in `KrkrBindFontMethods`, rather than a script dialog.

The target EXE's `QueryFunctionsByNarrowString` (RVA `0x44700`) uses four explicit stack
arguments and returns with a plain `ret`; the caller also cleans the stack at reference-counting
call sites. However, TVP's exported Variant construction helpers return with `ret 4`.
The virtual interfaces and exported helpers therefore cannot share one calling-convention
declaration. The current x86 bridge saves and restores ESP during the first query and
selects a `cdecl` / `stdcall` virtual-interface entry point according to the observed
stack cleanup. All TVP exported helpers retain `stdcall`. Security-cookie checking remains
enabled.

Runtime validation backed up the game's original `winmm.dll` before deploying the Win32
fix built in a separate output directory. The new process logged
`native-font-dispatch install=1 status=0 interface=cdecl`, remained responsive, and its
window displayed a room background and Japanese dialogue instead of stopping at the
startup crash. The game EXE and scripts were not rewritten, and the proxy did not alter
the font configuration. This conclusion is limited to that startup and the observed
dialogue screen; it does not establish full workflow validation. The original DLL,
calling-convention disassembly, debug dumps, and execution records are in
`artifacts/krkr-compat/runtime/`. The four delivery roles from the same transaction and
the offline regression records remain in `artifacts/krkr-compat/`.

## Log File

Runtime logs are written to `FontHook.trace.log` in the target program directory. Each
process session recreates the file on its first write. Log lines include time, PID, TID,
and a module tag.

Basic installation, configuration, and engine-detection logs may appear regardless of
the debug switch. Detailed API sampling, exception records, and hang monitoring are
controlled by `EnableDebugLog`.

## Temporary Debug Configuration for Reproduction

```ini
[FontHook]
EnableDebugLog=1
DebugSlowMs=50
DebugTraceSampleLimit=128
DebugPickerThreadLogLimit=32
```

Enable this only while reproducing the issue. After diagnosis, restore:

```ini
EnableDebugLog=0
DebugTraceSampleLimit=0
DebugPickerThreadLogLimit=0
```

## Structured Fields

Every actual log entry has a fixed prefix containing local time, PID, and TID; its message
body includes a module tag. Some adapter messages use `key=value` fragments after the
tag, while others use fixed text. The table below lists normalized fields for organizing
evidence; it does not mean every `FontHook.trace.log` entry contains all these fields:

| Field | Source | Interpretation |
| --- | --- | --- |
| `module` | Adapter or generic-hook tag in the message body | Identify the processing boundary |
| `phase` | Fixed messages mapped to phases such as `identity`, `capability`, `route`, or `render` | Distinguish decision stages |
| `decision` | Message results normalized to `pass`, `skip`, `fallback`, or `error` | Identify the branch outcome |
| `evidence` | Summary of markers, exports, resource layout, or runtime interfaces | Trace the identity/capability basis |
| `configVersion` | `Config::ConfigVersion` | Associate a configuration snapshot with caches |
| `request` / `route` | Original request and normalized/virtual path | Check dispatch results |
| `fallback` | Fallback reason or `none` | Distinguish missing capability from missing resources |
| `duration_us` | Call timer, or converted from an original field such as `scan-ms` | Locate time spent in high-frequency paths |

Logs, configuration, and sample hashes in the same reproduction record must use the
same process architecture. Mark missing fields as "unconfirmed"; do not infer a branch
solely from the final screen.

## Log Tags

| Tag | Meaning |
| --- | --- |
| `[TRACE]` | Installation, configuration versions, and API sampling |
| `[DEBUG][TextSub]` | Text-mapping input and output |
| `[DEBUG][BGI]` | BGI identity, DSC/LINE font scripts, GDI caches, and metric adaptation |
| `[DEBUG][CatSystem2]` | classic CatSystem2 font sources, file redirection, and fallback for missing directory enumeration |
| `[DEBUG][UnityMono]` | Unity Mono runtime binding and object application |
| `[DEBUG][CatSystemUnity]` | Unity IL2CPP/TMP runtime adaptation |
| `[RenPy]` | Font-source resolution, Python virtual-file callbacks, and cache refresh |
| `[Tyrano]` | ASAR detection, Web font redirection, and bridging |
| `[Yuris]` | YPF directory-encoding detection, compatible page tables, atlas replacement, and override fallback |
| `[DIAG][crash]` | Limited sampling of first-chance exceptions |
| `[DIAG][hang-watchdog]` | Long-running stages and unresponsive-window detection |

## Diagnostic Workflow

1. Check basic loading with all optional compatibility features disabled.
2. Enable only face-name replacement to distinguish font issues from encoding, metric, or engine-cache issues.
3. Enable character-set spoofing, code-page redirection, and text mapping separately; do not change several variables at once.
4. Inspect engine-detection results during process startup to check for false positives.
5. Compare API samples before and after the first incorrect output instead of analyzing only the final screenshot.
6. Record the target program architecture, DLL SHA-256, configuration file, and shortest reproduction steps.

### Evidence Reproduction Steps

1. Copy the sample into an isolated directory and use `Get-FileHash -Algorithm SHA256` to save all input hashes.
2. Start once with the target adapter disabled and save baseline logs and screenshots.
3. Change one configuration group at a time and record `ConfigVersion`, adapter logs, and result hashes.
4. Validate the identity, capability, and routing stages with positive, similar but non-target, missing-capability, and boundary samples.
5. Add commands, configuration, logs, and artifact paths to the record template in [Feature Evidence and Reproduction](reproduction.md).

## Common Issues

### Text Becomes Incorrect Chinese Characters After Changing Fonts

First check whether code-page redirection or text mapping was enabled incorrectly. Font
replacement itself should not change the text byte stream. Inspect the character set
detected from the original font request and the actual decoded Unicode in
`[DEBUG][TextSub]`.

### Font Switching Has No Visible Effect

Check whether `ConfigVersion` changed, whether the target engine uses internal caches,
and whether its adapter logged cache clearing or resource regeneration. Do not immediately
attribute the issue to failed face-name replacement.

### Abnormal Line Breaks in Backlog Text After Traditional/Simplified Mapping

Programs that draw only through ANSI GDI may use `GetTextExtentExPointA` results to
advance through the original DBCS byte buffer. The text-mapping path can temporarily
measure through wide-character APIs, but must convert `lpnFit` and `lpnDx` back to source
byte boundaries. Otherwise, a returned UTF-16 character count may make the caller resume
layout halfway through a Chinese character or too early. While checking decoded output
in `[DEBUG][TextSub]`, also confirm that the metric hook preserves ANSI byte counts;
correct Simplified Chinese on screen alone is insufficient.

### TyranoScript Reports file not found for a Scene or Plugin After Font Switching

First confirm the actual layout of `resources/app.asar` and `resources/app`. An Electron
process already started from `app.asar` must continue to see the same archive after font
hot switching. Otherwise, later `./data/scenario/...` and
`./data/scenario/../others/plugin/...` requests fall into a missing or incomplete loose
root. Enable `EnableDebugLog` and check `[DEBUG][Tyrano]` messages for `asar-visible`,
`asar-index-ready`, and `asar-overlay-open`; also confirm that normalized entries remain
within the application root.

### Startup Stalls

Inspect slow calls and watchdog stages in the logs. Focus on repeated file scans,
PE/ASAR parsing, font-source or resource generation, runtime type lookup, and unbounded
logging in high-frequency hooks.

### Only One Engine Has Problems

First confirm the engine-detection evidence, then temporarily disable that engine's
master switch for comparison. Generic GDI imports are not sufficient evidence of a
specific engine's identity.

### BGI LINE UI Still Uses a Fixed Font

First inspect `phase=line-font-capability` in the startup log. `decision=attached` means
the current x86/x64 DSC decoder profile is unique and attached. For `decision=skip`, use
`evidence` to distinguish missing DSC, an unknown decoder layout, and nonunique matches;
the adapter preserves the original script.

After entering the LINE UI, `phase=line-font-apply decision=patched` must also appear.
Its `evidence` should be the verified `bp-modern-font-record-0c00` or
`bp-legacy-font-record-0bd4`; `size` and `offset` identify the current in-memory output.
Capability without apply means the decoder hook is available, but the current BP has no
unique match for a known LINE semantic layout. Do not substitute a fixed RVA or search
only for font names.

This path processes the in-memory buffer decoded from `sysprg.arc` directly. A target
directory without an extracted `scrdrv._bp` is normal. Placing a loose file with that
name does not enable the feature and cannot establish successful routing.

### Incompatible YU-RIS Page-Table Layout

First inspect `layout`, `auto-codepage`, and the number of compatible code pages in
`atlas encoding resolved`, then check `YurisAtlasCodepage`. A message of
`atlas-codepage override incompatible` means the specified code page cannot fit the
current fixed page count and slots. For example, a CP932 45×188 atlas cannot contain a
GBK 127×192 page table. Provide a font-resource layout matching the target code page
rather than changing `ForcedCharset`, transcoding, or text-mapping options.
Do not determine the page table from a single `push 932` or a `MultiByteToWideChar`
import in the EXE. The existing CP932, GBK, and Big5 samples retain the same CRT
conversion code, so that evidence cannot distinguish actual font slots.

### Offset Punctuation or Stray Pixels in YU-RIS

Distinguish the resource's "slot stride", "actual glyph box", and "text drawing origin".
WebP `gbk-s38` uses an 816x624 canvas, 16x12 slots, a 48 px stride, and 38x38 glyph boxes.
The first runtime GDI slot's drawing origin combines the slot start `(5,11)` and drawing
offset `(5,4)` into `(10,15)` to preserve approximately 6 px of transparency at the slot
top in the reference Pillow atlas. Do not force the black box to the center or reuse
Relirium's left/bottom alignment coordinates. Relirium and Big5 cannot share the same
offsets either: only Relirium/YDG uses the common bottom-left offset and bottom-aligned
ellipsis. Big5's `、。`, fullwidth question and exclamation marks, paired brackets,
small-form symbols, and centered ellipsis are positioned by their PNG atlas bearing
categories. Every configuration clips per slot and uses a related symbol or code-page
fallback font for missing glyphs to avoid spillover into neighboring slots and `.notdef`
fragments.

## What to Include with Logs

Issue reports should include the target program architecture, reproduction steps,
`FontHook.ini`, the corresponding build hash, one complete session's
`FontHook.trace.log`, and the error screen. Remove unrelated duplicate logs and avoid
mixing records from different configuration versions.

## Evidence Interpretation

| Result | Permitted conclusion |
| --- | --- |
| Identity log `decision=pass`, capability log `decision=pass` | Engine-specific resource routing can be inspected |
| Identity passes, capability is `fallback` | The adapter retains the generic path and records the fallback reason |
| Identity is `skip` | Do not inspect engine-specific resources or modify imports, caches, or text |
| Only a visible change in the final screenshot | The result is visible, but its branch source is unconfirmed |
