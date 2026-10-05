# Common Foundation for Engine Adaptation

## Responsibilities

This directory provides engine adapters with path normalization, module memory marker
queries, runtime export validation, archive magic checks, system font location, SFNT
validation, GDI font export, and temporary read-only handles. Common interfaces only collect
identity and capability evidence or implement font/file operations that have no engine
affiliation. They contain no specific game names or resource file lists.

## Boundaries of Common Capabilities

Engine detection and file virtualization run on global API hooks. Small differences in path
boundaries, memory readability, or read-only open semantics can cause false matches or
recursion. The common foundation implements these rules as engine-neutral primitives so
each adapter only combines evidence and defines its own resource contract.

## Identity Evidence

`EngineIdentityPolicy::Confirm` accepts three kinds of strong evidence: a module or proprietary
format identity marker, a verified runtime/resource contract, and the combination of
successfully parsing an archive format and finding engine resources inside it. File
extensions and root-directory filenames only narrow the search and do not independently
determine identity.

`ConfirmFrameworkContract` requires both the framework runtime directory and the identity
manifest to match. Ren'Py and TyranoScript use this combination; a single directory, filename,
or suffix only keeps a candidate eligible.

`Evidence` represents independent identity markers, verified contracts, container formats,
engine resources within containers, and framework manifests separately. `Confirm` only
accepts strong evidence or the combination of successful container parsing and engine
resources found inside it. Once identity is confirmed, `ConfirmCapability` determines
whether the target interface is available.

## Path Interfaces

`EngineCommon` provides the game root directory, full paths, case and separator normalization,
root-directory boundaries, extension comparison, and UTF-8 log conversion. Every engine uses
the same boundary rules; the file dispatcher remains responsible for publishing the final
A/W API results.

## Module Interfaces

Module markers are queried directly in mapped, readable memory regions to avoid reading the
entire executable. Runtime interfaces are confirmed through the export tables of loaded
modules. A dynamic module that has not loaded remains in a retryable state.

## Font and File Interfaces

System font name resolution shares a registry cache. Root-directory font searches accept
explicitly configured files and standard SFNT extensions. `engine_font_export.cppinc` exports
the currently configured font through real GDI entry points and consistently checks size
limits, object selection results, and SFNT headers. Virtual resources are delivered to the
engine through temporary read-only handles with delete-on-close semantics.
Common file queries carry a thread-level bypass marker, so file hooks forward them directly
to the real APIs and prevent identity probing and font source resolution from reentering
engine dispatch.

## File Responsibilities

| File | Responsibilities |
| --- | --- |
| `engine_identity_policy.h` | Identity, framework contract, and capability confirmation rules, plus compile-time counterexamples |
| `engine_common.h/.cpp` | Paths, modules, exports, font files, SFNT, and internal query guards |
| `engine_font_export.cppinc` | Export and validate deliverable font bytes from the current GDI configuration |

## How It Works

1. `InternalFileQueryScope` sets a thread-level bypass marker for an adapter's own file reads.
2. Paths are first converted to full paths and normalized for case and separators, then
   checked against the game root boundary and extension.
3. Module marker queries inspect committed, readable image memory region by region; runtime
   capabilities inspect the real export table.
4. Font sources are located through the system registry cache and game-root candidates, then
   their SFNT/TTC headers are validated after reading.
5. In-memory resources are delivered through temporary file handles with delete-on-close
   semantics to engines that only accept Win32 file APIs.

This workflow separates evidence collection from changes to request results. The common
layer only returns facts or general resources; each engine decides whether to enable an
adaptation path after configuration, identity, and capabilities all match.

## Runtime Constraints

- Adapters cache module and archive checks; high-frequency file and font paths only read
  cached results.
- Archive suffixes, resource suffixes, generic GDI imports, and any single filename do not
  establish engine identity.
- Common code does not install hooks or change font, code page, or text substitution state.

## Evidence and Reproduction

To reproduce common decisions, use `Evidence`, `Confirm`, `ConfirmFrameworkContract`, and
`ConfirmCapability` in `engine_identity_policy.h` as the decision entry points, and the path
and module functions in `engine_common.h/.cpp` as input boundaries. Record the input evidence
set, normalized path, returned Boolean value, and called symbol each time.

| Input combination | Expected decision |
| --- | --- |
| A single file suffix, archive name, or GDI import | Identity is not confirmed |
| Independent engine marker | Identity is confirmed; capabilities are evaluated separately |
| Parseable container header containing registered engine resources | Combined container evidence is confirmed |
| Parseable container header without engine resources | Identity is not confirmed |
| Framework directory and identity manifest both match | Framework contract is confirmed |
| `InternalFileQueryScope` is active | File requests call the real API |

Font source reproduction uses five fixed input categories: system fonts, game-directory
fonts, TTC, multi-face TTC, and damaged SFNT. Record the source path, font face, size limit,
header validation, and temporary handle access rights. See
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md) for the
common record format.

## Verification

Cover paths inside and outside the root directory, relative paths, case and separators,
unreadable module pages, missing exports, system and local fonts, damaged SFNT, read-only
and write opens, and recursion guards for internal query bypasses.
