# Configuration

`FontHook.ini` is located beside `winmm.dll`. The font picker saves configuration as UTF-8
with a BOM. The loader ignores blank lines, comments beginning with `;` or `#`, and section
headings. Configuration is currently saved in the `[FontHook]` section, but parsing uses
the key names.

`FontNameW` is required for a valid configuration. The configuration file is not applied
when this key is missing.

Configuration is implemented in `SimpleFontHook/utils.cpp`: defaults are declared in the
`Config` namespace, `Utils::SaveConfig` writes the `[FontHook]` section, and
`Utils::LoadConfig` parses values and normalizes their bounds. The parser looks up key
names in a compact linear key-value table; section names do not participate in lookup,
and the last value of a duplicate key takes precedence. Boolean values are parsed as
integers: `0` disables an option and any nonzero value enables it. Missing keys use the
source defaults.

## Basic Font Settings

| Configuration key | Default | Description |
| --- | ---: | --- |
| `FontNameW` | `galgame` | Unicode font name; an empty value disables font and face-name replacement |
| `FontNameA` | `galgame` | ANSI font name; converted from `FontNameW` when missing |
| `EnableFontHook` | `0` | Master switch for font hooks |
| `EnableFaceNameReplace` | `0` | Replace font face names |
| `PickerShowOnStartup` | `1` | Show the font picker at startup |
| `EnableCharsetReplace` | `0` | Replace the character set in font requests |
| `ForcedCharset` | `1` | Target character set; `1` is `DEFAULT_CHARSET` |

Common East Asian character-set values: `128` is Shift-JIS, `129` is Korean,
`134` is GB2312, and `136` is Big5.

### In-Process Font File State

`FontFileName` is not an INI key. It starts empty; `LoadCustomFont` consumes a nonempty
value and may write back the actual filename after matching a local font candidate.
CatSystem2, Artemis, Mirai, Ren'Py, and the generic font-file entry points read this field;
`SaveConfig` and `LoadConfig` do not persist it.

## Font Metrics

Each metric has an independent switch. A value is not applied while its switch is `0`.

| Switch | Value key | Default | Description |
| --- | --- | ---: | --- |
| `EnableFontHeightScale` | `FontHeightScale1000` | `1000` | Height multiplier; 1000 means 1.0 |
| `EnableFontWidthScale` | `FontWidthScale1000` | `1000` | Width multiplier; 1000 means 1.0 |
| `EnableFontCharSpacing` | `FontCharSpacing` | `0` | Additional character spacing |
| `EnableFontVerticalMetrics` | `FontAscentPermille` | `880` | Ascent, in thousandths of an em |
| `EnableFontVerticalMetrics` | `FontDescentPermille` | `-120` | Descent, in thousandths of an em |
| `EnableFontLineSpacing` | `FontLineSpacing` | `0` | Additional line spacing |
| `EnableFontWeight` | `FontWeight` | `400` | Font weight |

## Character Sets and Code Pages

| Configuration key | Default | Description |
| --- | ---: | --- |
| `EnableCodepageSpoof` | `0` | Enable character-set capability spoofing |
| `EnableCodepageRuntimeReplace` | `0` (derived) | Runtime replacement state, calculated from the spoofing switch and source/target character sets |
| `SpoofFromCharset` | `134` | Source character set to spoof |
| `SpoofToCharset` | `128` | Target character set exposed to the application |
| `EnableCodepageRedirect` | `0` | Enable code-page conversion redirection |
| `CodepageRedirectFrom` | `932` | Source code page to redirect |
| `CodepageRedirectTo` | `65001` | Code page used for conversion; 65001 is UTF-8 |

When character-set spoofing is enabled and the source and target character sets differ,
runtime character-set replacement becomes active automatically. When they are the same,
only the font capability flags are changed. The UI treats `EnableCodepageRuntimeReplace`
as derived state; configuration determines the mode automatically. Character-set spoofing,
code-page redirection, and font replacement are independent. Font replacement affects only
font objects and font data. The parser accepts the compatibility aliases `Enable`,
`CodePageConvertEnable`, `FromCodePage`, and `ToCodePage`; the keys in the table are the
canonical spellings for the configuration file.

Alias precedence is: the canonical key, `CodePageConvertEnable`, then the value derived
from `Enable` combined with the compatibility keys. Code-page numbers are read with
`atoi`. A negative text-mapping code page falls back to `932`; zero uses the system ACP.
An invalid `YurisAtlasCodepage` is normalized to `0`. An empty `FontNameW` disables both
`EnableFontHook` and `EnableFaceNameReplace`.

## Text Mapping

| Configuration key | Default | Description |
| --- | ---: | --- |
| `EnableTextSubstitution` | `0` | Enable text mapping |
| `TextSubstitutionMode` | `0` | `0`: Japanese proxy ideographs to Simplified Chinese (`JP→SC`); `1`: Traditional to Simplified Chinese (`TC→SC`); `2`: Simplified to Traditional Chinese (`SC→TC`) |
| `TextSubstitutionCodepage` | `932` | ANSI decoding fallback when the original character set cannot be detected |

When the application exposes a definite character set through its original font-creation
request, text mapping prefers that character set's code page. For example,
`GB2312_CHARSET` uses CP936. The replacement font and `ForcedCharset` do not determine
the source text encoding.

## Generic Compatibility Switches

| Configuration key | Default | Description |
| --- | ---: | --- |
| `CompatSkipDrawTextA` | `1` | Skip the `DrawTextA` replacement path not covered by the current compatibility policy |
| `CompatSkipFontDataQueries` | `1` | Skip some font-data query replacements by default |
| `CompatSelectObjectTrackedOnly` | `0` | Handle `SelectObject` only for tracked fonts |
| `CompatHookCreateFontW` | `1` | Hook `CreateFontW` |
| `CompatHookCreateFontIndirectW` | `1` | Hook `CreateFontIndirectW` |
| `CompatHookGetTextFace` | `0` | Replace `GetTextFace` query results |

## Engine Switches

Engine master switches default to enabled, but adaptation should run only after positive
detection matches the engine.

| Engine | Configuration keys and defaults |
| --- | --- |
| [BGI](../SimpleFontHook/hooks/internal/engines/bgi/README.md) | `EnableBgiHook=1`, `BgiPatchGdiImports=1`, `BgiClearGlyphCacheOnSwitch=1` |
| [Artemis](../SimpleFontHook/hooks/internal/engines/artemis/README.md) | `EnableArtemisHook=1`, `ArtemisPatchTables=1`, `ArtemisRedirectFontFiles=1`, `ArtemisClearFontCacheOnSwitch=1` |
| [Artemis Legacy](../SimpleFontHook/hooks/internal/engines/artemis_legacy/README.md) | Shares the Artemis switches, font path, font size, spacing, and text-mapping configuration |
| [KiriKiri](../SimpleFontHook/hooks/internal/engines/krkr/README.md) | `EnableKrkrHook=1`, `KrkrDisablePrerenderedFonts=1` |
| [Entis](../SimpleFontHook/hooks/internal/engines/entis/README.md) | `EnableEntisHook=1`, `EntisDisableBitmapFonts=1`, `EntisRefreshFontOnSwitch=1` |
| [Softpal](../SimpleFontHook/hooks/internal/engines/softpal/README.md) | `EnableSoftpalHook=1`, `SoftpalDisableDefaultFontDat=1`, `SoftpalForceDefaultOptionToSystemFont=1` |
| [Escude](../SimpleFontHook/hooks/internal/engines/escude/README.md) | `EnableEscudeHook=1`, `EscudeVirtualFontConfig=1` |
| [Mirai](../SimpleFontHook/hooks/internal/engines/mirai/README.md) | `EnableMiraiHook=1`, `MiraiReplaceFontDataQueries=1`, `MiraiRedirectFontFiles=1`, `MiraiPinFontDataSource=1` |
| [Majiro](../SimpleFontHook/hooks/internal/engines/majiro/README.md) | `EnableMajiroHook=1`, `MajiroDisableFontCache=1` |
| [DxLib](../SimpleFontHook/hooks/internal/engines/dxlib/README.md) | `EnableDxLibHook=1`, `DxLibDisableFontCache=0`, `DxLibReplaceFontDataQueries=1`, `DxLibClearRuntimeFontCacheOnSwitch=0` |
| [TinkerBell](../SimpleFontHook/hooks/internal/engines/tinkerbell/README.md) | `EnableTinkerBellHook=1` |
| [classic CatSystem2](../SimpleFontHook/hooks/internal/engines/catsystem2/README.md) | Uses `EnableFontHook`, `EnableFaceNameReplace`, `FontNameW`, and the in-process `FontFileName`; no engine-private configuration |
| [Unity](../SimpleFontHook/hooks/internal/engines/unity/README.md) | `EnableCatSystemUnityHook=1` |
| [TyranoScript](../SimpleFontHook/hooks/internal/engines/tyrano/README.md) | `EnableTyranoHook=1`, `TyranoRedirectWebFonts=1` |
| [Ren'Py](../SimpleFontHook/hooks/internal/engines/renpy/README.md) | `EnableRenPyHook=1`, `RenPyRedirectFonts=1`, `RenPyRefreshFontOnSwitch=1` |
| [YU-RIS](../SimpleFontHook/hooks/internal/engines/yuris/README.md) | `YurisAtlasCodepage=0` (INI diagnostic override); uses `EnableFontHook`, `FontNameW`, and generic metric settings |

BGI's `EnableBgiHook` controls both the LINE font-script layer after x86/x64 DSC decoding
and the Win32 GDI raster layer. `BgiPatchGdiImports` and `BgiClearGlyphCacheOnSwitch`
apply only to the Win32 GDI path. LINE script capability is detected automatically by
default; it requires neither a separate setting nor an external `scrdrv._bp`.

Artemis also saves `ArtemisFontPath`, `ArtemisFontSize=0`, and `ArtemisRubySize=-1`.
DxLib's `DxLibCachedFontNameW` is compatibility cache state. Reading it fills the
in-process cache; a missing key clears that cache.
YU-RIS resource configuration is independent of `ForcedCharset`. For example, running
under a different locale may use `FontNameW=MSMSMS` and `ForcedCharset=128`; the character-set
value does not change bitmap-page resource indices. The adapter selects the
`45 pages × 8 styles`, `127 pages × 2 styles`, `89 c20 pages + 38 c10 pages`, or
`4 × (89 Big5 pages + 1 ASCII page)` layout from the complete YPF contract. Archive
directory-name encoding is detected automatically, and page-table code pages are filtered
by slot structure. The adapter enumerates `pac/*.ypf` and confirms capability from internal
paths, the complete font-page set, and image layout. It does not restrict archive filenames
or total entry counts; extracted directories do not participate in runtime identification.
`YurisAtlasCodepage` is managed through `FontHook.ini`; the font picker exposes only
cross-engine font, text-mapping, and code-page redirection configuration. `0` uses the
automatic result; a nonzero value may select an installed Windows code page. Values
incompatible with the current page count and slots preserve the original decoding result.
This key does not reuse character-set spoofing, system ACP, transcoding, or text-mapping state.

## Debug Settings

| Configuration key | Default | Description |
| --- | ---: | --- |
| `EnableDebugLog` | `0` | Enable detailed logs, exception sampling, and hang monitoring |
| `DebugSlowMs` | `50` | Slow-call logging threshold in milliseconds |
| `DebugTraceSampleLimit` | `0` | Trace sample limit for each high-frequency API category; 0 disables sampling |
| `DebugPickerThreadLogLimit` | `0` | Font-picker thread log limit; 0 disables logging |

After troubleshooting, restore `EnableDebugLog=0` and both sample limits to `0` so
high-frequency logging does not affect performance.

## Runtime State

`DetectedCharset`, `ConfigVersion`, `NeedFontReload`, and `SourceFontNameW` exist only
within the process. The loader writes `ForcedFontNameW`, `ForcedFontNameA`, and the switches
into process state. The local font-loading path consumes `FontFileName` and writes it back
when a candidate matches; it is an in-process field. The font picker saves configuration,
increments the version, and notifies runtime caches. File values take effect on the next
`LoadConfig` call. `ConfigVersion` is not read from the INI.

## Configuration Sources and Reproduction

### Minimal Runnable Configuration

The following file provides only the required keys and master switches and can be used to
establish a baseline without engine intervention:

```ini
[FontHook]
FontNameW=galgame
FontNameA=galgame
EnableFontHook=1
EnableFaceNameReplace=1
EnableDebugLog=0
DebugTraceSampleLimit=0
DebugPickerThreadLogLimit=0
```

### Configuration for Testing One Variable

Change only one related group of keys at a time in the baseline file, and record
`ConfigVersion` for each group:

```ini
[FontHook]
FontNameW=TARGET_FONT
FontNameA=TARGET_FONT
EnableFontHook=1
EnableFaceNameReplace=1
EnableCharsetReplace=0
EnableCodepageSpoof=0
EnableCodepageRedirect=0
EnableTextSubstitution=0
EnableDebugLog=1
DebugSlowMs=50
DebugTraceSampleLimit=128
DebugPickerThreadLogLimit=32
```

### Parsing Validation Matrix

| Input | Observation | Interpretation |
| --- | --- | --- |
| Missing `FontNameW` | `LoadConfig` returns failure | The file is not applied |
| `FontNameW=` | The font name is empty and both font switches are `0` | The font-replacement path is disabled |
| Missing `FontNameA` | The ANSI name is converted from `FontNameW` | The ANSI name can be traced |
| `TextSubstitutionMode` outside `0..2` | The value is normalized to `0` | Japanese proxy ideographs to Simplified Chinese mode is used |
| Negative `DebugSlowMs`, sample limits, or font dimensions | Values are normalized to a nonnegative range | Logging and size calculations are bounded |
| Invalid `YurisAtlasCodepage` | The value is normalized to `0` | Automatic code-page selection is used |
| Only `FromCodePage`/`ToCodePage` are present | The redirection switch is derived together with `Enable` | Compatibility key combination |

For each validation item, save `FontHook.ini`, `FontHook.trace.log`, and the in-process
version number. Full sample pinning and evidence fields are described in
[Feature Evidence and Reproduction](reproduction.md).
