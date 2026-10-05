# Ren'Py Adapter

## Responsibilities

Ren'Py uses its own FreeType/HarfBuzz rendering path. This adapter maintains Ren'Py's
font-replacement mapping on the Python interpreter thread and uses
`renpy.config.file_open_callback` to connect stable virtual font names to the current
source-font file.

## Python Scheduling Boundary

Ren'Py's text layout, font loading, and caches reside in Python and native FreeType/HarfBuzz
extensions; font creation does not pass through GDI or DirectWrite. Replacing on-disk files
directly would not cover script font aliases and would disrupt the game's custom
`file_open_callback` and font mappings.

The adapter expresses replacement relationships through Ren'Py's public configuration objects:
the mapping table directs script fonts to stable virtual names, and the file callback directs
those virtual names to the current source font. Cache refresh also uses Ren'Py's own entry points.

## Detection Conditions

The Ren'Py framework layout requires `renpy/` and `renpy/__init__.py`, plus at least one core
subsystem from `renpy/text`, `renpy/display`, or `renpy/common`. Game-script directory names and
individual font-module files do not participate in identity decisions.

Detection results are cached for the process lifetime.

## File Structure

- `renpy_font.cppinc`: Adapter aggregation entry point.
- `renpy_state.cppinc`: Configuration snapshots, worker thread, Python APIs, and version state.
- `renpy_detection.cppinc`: Root-directory identification and path helpers.
- `renpy_font_source.cppinc`: Source-font location and validation, and TTC font-face index parsing.
- `renpy_python_bridge.cppinc`: Python API binding, virtual-file callback registration, and application-script construction.
- `renpy_runtime.cppinc`: Worker thread, configuration notifications, and shutdown.

## Font-Source Access

The adapter first uses the user's actual `SourceFontNameW` selection to locate a system or
current-user installed font file. If it cannot find one, it checks the game-local font referenced
by `FontFileName`. Ordinary TTF/OTF files need only a 12-byte header read for basic validation;
only TTC/OTC files require reading the collection directory and selecting the correct face index
by font name.

Ren'Py's mapping uses stable virtual names of the form `__simplefonthook__/selected.*`. When the
font-loading callback receives that name, it opens the source-font path in read-only binary
mode. Runtime state consists of the source path, virtual name, TTC face index, and configuration
version.

`SourceFontNameW` is in-process state that preserves the font the user actually selected. When
vertical-metric or code-page patching creates an in-memory font clone, generic GDI hooks can
still use the clone name, while Ren'Py always resolves the original font file.

## Python Application Flow

1. The worker thread resolves the source-font path and TTC face index for the current `ConfigVersion`.
2. Locate Python among loaded modules and resolve `Py_IsInitialized`, `Py_AddPendingCall`, and `PyRun_SimpleString`.
3. Use `Py_AddPendingCall` to post the application callback to the interpreter thread.
4. Wrap `renpy.config.file_open_callback` and chain the game-provided callback.
5. Wrap or restore `renpy.config.font_replacement_map`.
6. Call `renpy.text.font.free_memory()` to clear the font cache.
7. When refresh is enabled, call `restart_interaction` to restart the current interaction.

When mapping is disabled, restore the file callback from before the adapter was entered and
clear the path state attached to `renpy.config`. Absolute paths are passed to Python as UTF-8
hexadecimal data, avoiding Python 2 source-encoding and Windows non-ASCII-path issues.

## Rationale for the Design Constraints

- Stable virtual names separate font identifiers in game scripts from Windows absolute paths; font switching updates only callback state.
- Wrapping the existing `file_open_callback` and chaining the original callback preserves the game's resource-loading contract.
- `Py_AddPendingCall` posts state changes to the interpreter thread; the worker thread performs only file location and byte validation.
- `SourceFontNameW` preserves the real source name so generic GDI font-table clones do not interfere with file location.
- TTC/OTC parsing is limited to the collection directory and target face; ordinary TTF/OTF files use minimal header validation, reducing preparation-stage I/O.
- Checking `ConfigVersion` and the font name before and after application prevents stale preparation results from overwriting a newer user selection.

## Configuration

- `EnableRenPyHook`
- `RenPyRedirectFonts`
- `RenPyRefreshFontOnSwitch`
- Generic `EnableFontHook`, `EnableFaceNameReplace`, and `ForcedFontNameW`

## Thread Invariants

- The worker thread only resolves and validates font sources; it must not execute Python scripts directly.
- Python state changes only on the interpreter thread running the pending callback.
- Configuration snapshots are copied under a mutex; file reads and Python calls run outside the lock.
- Revalidate the requested version and font name before submitting preparation results.
- On shutdown, wake the worker thread and wait for a bounded time on the normal shutdown path.

## Evidence and Reproduction

1. Record the presence and file hashes of `renpy/`, `renpy/__init__.py`, and at least one core
   subsystem; use samples containing only a script directory or font file as nontarget controls.
2. Save the source-font path, SFNT/TTC header, target font face, virtual name, and `ConfigVersion`.
3. Observe binding and posting results for `Py_IsInitialized`, `Py_AddPendingCall`, and
   `PyRun_SimpleString` before Python initialization, after initialization, and during interpreter
   shutdown.
4. Install a game-customized `file_open_callback`. Record callback order before and after
   wrapping, virtual-file return values, and pass-through results for ordinary resources.
5. Enable/disable mapping and switch fonts. Record `font_replacement_map`, `free_memory()`,
   `restart_interaction`, and non-ASCII-path results.

| Scenario | Expected Result |
| --- | --- |
| Complete framework inventory + available Python APIs | Installs the mapping and file callback on the interpreter thread |
| Framework confirmed, but Python not yet initialized | The worker thread waits and retries without executing scripts |
| Custom file callback present | The adapter handles virtual fonts; other requests chain to the original callback |
| TTC/OTC | The virtual name preserves the target face index |
| Mapping disabled | Restores callback and mapping state from before the adapter was entered |

The evidence directory contains the framework inventory, font hashes, Python API bindings,
`[RenPy]` logs, and positive and negative samples. For field conventions, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover positive and negative Ren'Py detection, Python initialization timing, ordinary TTF/OTF
files, different TTC faces, non-ASCII source paths, game-customized `file_open_callback`,
font-mapping enable/disable, font switching, and shutdown.
