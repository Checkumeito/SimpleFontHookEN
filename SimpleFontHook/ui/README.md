# Font Picker Module

## Module Role

`ui/` provides an in-process font picker. It enumerates fonts, edits font and metric
configuration, saves `FontHook.ini`, and publishes each user action as a complete
runtime configuration version. The UI does not directly modify engine caches or
managed objects; `FontHooks::NotifyConfigChanged` dispatches those actions to the
corresponding modules.

This boundary keeps the window thread responsible only for UI and configuration
state. Adapters can use their own scheduling when an engine requires Python, Mono,
IL2CPP, or the game window thread.

## Public Interfaces

| Interface | Responsibility |
| --- | --- |
| `FontPicker::Init` | Create the picker window and run the message loop |
| `FontPicker::Toggle` | Toggle window visibility |
| `FontPicker::IsVisible` | Query current visibility |
| `FontPicker::Shutdown` | Publish a message-loop exit request across threads |

## Aggregate Structure

`font_picker.cpp` is the UI aggregate translation unit and includes these fragments
in a fixed order:

| Fragment | Responsibility |
| --- | --- |
| `internal/font_picker_state_layout.cppinc` | Aggregate window state, layout geometry, metric-editing state, and show/hide animation |
| `internal/font_picker_apply_config.cppinc` | Validate configuration, save the file, increment the version, and notify game windows and hooks |
| `internal/font_picker_font_list.cppinc` | Font enumeration, search, source resolution, local fonts, and font-table cloning |
| `internal/font_picker_paint.cppinc` | Aggregate title, font settings, ordinary-user guide, preview, and scrollbar drawing |
| `internal/font_picker_input.cppinc` | Aggregate keyboard, mouse, selection, scrolling, and numeric editing |
| `internal/font_picker_lifecycle.cppinc` | Window creation, configuration restoration, message loop, and shutdown |

Fragments compile as part of `font_picker.cpp`, retaining internal linkage for window
handles, drawing caches, selection state, and font lists. File boundaries still allow
state, input, drawing, and configuration application to be maintained separately.

## Application Flow

1. `Init` restores configuration, creates a hidden or visible picker window, and enumerates system and local fonts.
2. Search and list selection update only UI state. Confirming application resolves the real font source and prepares any required font-table clones.
3. Configuration application validates ranges, refreshes generic-hook state, and saves a UTF-8 INI.
4. After incrementing `Config::ConfigVersion`, the UI issues configuration notification and publishes bounded redraw messages to game windows.
5. Engine adapters consume that version within their own threading models; the UI draws previews from the same configuration snapshot.

The title bar offers `Fonts` and `Guide` pages. `Fonts` provides search, selection,
configuration, and preview. `Guide` hides the native search box and provides four
sections: `Start`, `Features`, `Keys`, and `Help`. Start
organizes file preparation, text encoding, font application, and screen checks.
Features explains each visible control, when it applies, and how to interpret its
result. Keys covers the window, font list, and guide reading. Help
distinguishes font coverage, character mapping, code pages, and layout issues by
their visible symptoms. The guide is for ordinary users and does not include engine
detection, resource formats, or adapter compatibility details. `Tab` switches
between the pages; `Insert` is the preferred show/hide key. The footer shows the
key actually registered in the current process.

English controls use compact labels: `W` means width, `H` height, `Gap` character
spacing, `Asc` ascent, `Desc` descent, `Line` line spacing, and `Wgt` font weight.
The guide defines these full terms and explains their effects. Reference controls
use `Set Ref`, `Match Ref`, and `Reset`. Text mapping and code-page controls use
short `Map` and `CP` labels, with their full meanings explained in the guide.
Preview text is English. Labels, values, and guide text must fit their available
space throughout the supported UI zoom range.

## Design Constraints

- Drawing code only reads state, input code only forms action intent, and configuration writes are centralized in `apply_config`.
- The font list preserves the user's selected source font name. Font-table clones use separate internal names so clone names do not interfere with source resolution or file-based font paths in Ren'Py, Unity, and similar engines.
- Double-buffered drawing resources are reused by window size and released together when the window is destroyed.
- The minimum client area is `480×640` logical pixels; the default client area is `480×720`. The UI zoom range remains `0.7–1.8`. The minimum size provides two font-list rows at scale 1.0 and one scrollable row at scale 1.8, alongside three columns of metric controls and the preview.
- Picker captions and numeric values use measured text fitting inside fixed rectangles. Spoof and Map/CP drawing and hit testing share labels, fitted fonts, and row geometry. Preview samples scale together to fit their panel; this changes presentation only, leaving game font configuration intact.
- The picker retains standard top-level window semantics so DWM can compute taskbar transitions. `DWMNCRP_DISABLED`, `WM_NCCALCSIZE`, and `WM_NCPAINT` isolate the system non-client area; the client draws all title, border, and button elements. Close and hide are driven by a window timer and change only layered alpha and position. Minimize and restore use native top-level window state. `WM_CLOSE` still enters the message-loop exit path directly.
- When `SPI_GETCLIENTAREAANIMATION` is disabled, close/hide paths change visibility immediately to respect the system animation preference.
- The picker exposes only cross-engine configuration. Engine-specific diagnostic override keys such as `YurisAtlasCodepage` are managed through `FontHook.ini`, preventing UI-level coupling with text mapping, character-set spoofing, or code-page redirection.
- The guide page does not write configuration. Page switches end active metric input and isolate list, wheel, double-click, and keyboard-application actions belonging to the hidden page.
- Guide text wraps to the available width, keeping English identifiers intact where possible. Multiline text uses explicit line spacing that follows UI zoom. Switching sections returns to the top; the mouse wheel, scrollbar dragging, and track paging share one scroll range.
- Configuration notifications run outside locks; the UI thread does not wait for engine worker threads to finish font application.
- Each control needs layout, drawing, hit testing, and configuration save/restore paths defined together.

## Validation

Cover first startup, restoration of existing configuration, Fonts/Guide page switches,
font search and keyboard selection, local fonts, metric editing, character-set and
text-mapping switches, window visibility and show/hide animation, repeated font
application, non-ASCII paths, and normal shutdown.

## Evidence and Reproduction

Entry symbols are `FontPicker::Init`, `Toggle`, `IsVisible`, and `Shutdown`;
configuration application is centralized in
`internal/font_picker_apply_config.cppinc`. To reproduce UI behavior, save the initial
`FontHook.ini`, a font-list snapshot, `ConfigVersion` before and after application,
and `FontHook.trace.log`. Window messages are evidence of configuration notification
and redraw only, not engine identity.

| Scenario | Observation | Expected result |
| --- | --- | --- |
| Startup restoration | `Init` reads a valid `FontNameW` | The list and metrics display the configuration snapshot |
| Apply font | `apply_config` completes bounds validation and saving | The version increments; notifications are published outside locks |
| Open the user guide | Click the `Guide` tab or press `Tab` | The search box is hidden and font configuration keeps its values |
| Return to font settings | Click the `Fonts` tab or press `Tab` | The search box returns and list input is enabled again |
| Non-ASCII path | The font-file path contains UTF-8 characters | Configuration, list, and clone sources remain consistent |
| Close through the custom title control | Timer frames update alpha and position | The window hides after the animation finishes |
| Minimize through the custom title control | `WM_SYSCOMMAND/SC_MINIMIZE` | DWM moves the window into the grouped taskbar icon |
| Shut down the window | `Shutdown` publishes an exit message | The UI thread exits without waiting for engine worker threads |

See [Feature Evidence and Reproduction](../../docs/reproduction.md) for full input
pinning and result interpretation.
