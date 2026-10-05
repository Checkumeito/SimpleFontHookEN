# TinkerBell Adapter

## Responsibilities

This directory provides hook policies for TinkerBell/Cyberworks' GDI calling patterns. The
adapter selects font-creation entry points and the scope of `SelectObject` tracking, preventing
wide-character font creation and untracked DCs from interfering with the engine's rendering
state.

## Policy Adaptation Boundary

TinkerBell's compatibility points are the installation scope of the generic GDI hooks and the
`SelectObject` handling boundary, rather than proprietary font resources. Installing a separate
set of engine hooks for this would duplicate the font model and put the same HFONT through two
sets of state.

This module answers only which generic entry points participate in the current process and
whether untracked objects pass through. Generic hooks still perform actual font creation, object
caching, metrics, and drawing.

## Identity and Capabilities

TinkerBell identity is confirmed by the strong `Software\\TinkerBell\\` or
`Cyberworks "TinkerBell"` markers in the main module, or by the `Cyberworks` and `TinkerBell`
marker pair. Queries are limited to mapped, readable memory regions in the main module, and
the result is cached for the process lifetime.

DAT archive names, `render.dll`, and other generic filenames do not determine engine identity.

## File Entry Points

- `tinkerbell_compat.cppinc`: Module identity scanning and policy queries.
- `hook_policy.cpp`: Includes this module and calls its compatibility policies.
- `HookPolicy::ShouldAttach`: Determines attachment of `CreateFontW` and `CreateFontIndirectW`.
- `HookPolicy::ShouldPassThroughUntrackedSelectObject`: Controls selection of untracked fonts.

## Implementation

1. The first policy query collects strong TinkerBell/Cyberworks markers from the readable image
   ranges of the main module.
2. `IsCompatibilityActive` combines engine identity with `EnableTinkerBellHook`.
3. During installation, `HookPolicy::ShouldAttach` determines whether wide-character
   font-creation entry points enter the Detours transaction.
4. The high-frequency `SelectObject` path reads only the cached policy; untracked HFONTs call
   the real API directly according to configuration.
5. Objects already tracked by the font model continue through replacement, HDC selection-state
   maintenance, and query-view maintenance.

## Features

- Uses the ANSI/generic font-creation compatibility path for matching TinkerBell processes.
- Applies a pass-through policy to `SelectObject` calls not tracked by the font-replacement model.
- Preserves replacement, metrics, and drawing for tracked HFONTs.
- Centrally provides engine identification to generic `hook_policy`, without repeated scans in high-frequency hooks.

## Rationale for the Design Constraints

- The policy module owns no font or HDC state, avoiding a second cache and lifecycle.
- Marker scanning runs only once; per-frame entry points such as `SelectObject` read only a Boolean result.
- Installation-point policies and runtime pass-through policies are expressed separately, allowing different versions' calling patterns to be combined.
- Generic DAT files, DLLs, and directory layouts do not participate in identity decisions; policies apply only to processes with strong module evidence.
- Disabling configuration returns all policies to generic defaults; the module itself has no memory resources to roll back.

## Configuration

- `EnableTinkerBellHook`
- `CompatHookCreateFontW`
- `CompatHookCreateFontIndirectW`
- `CompatSelectObjectTrackedOnly`
- Generic font-name, metric, and character-set settings

## Runtime Constraints

- Strong module markers determine engine identity; generic directories and filenames do not select policies.
- Module scanning accesses only committed, readable image memory.
- Detection runs only once, at the first policy query.
- This module returns only policy decisions; generic hooks create font objects and track DCs.

## Evidence and Reproduction

1. Fix the main-module hash and record the matched combinations of `Software\\TinkerBell\\`,
   `Cyberworks "TinkerBell"`, and the `Cyberworks` + `TinkerBell` marker pair.
2. For each combination, call `HookPolicy::ShouldAttach` and
   `HookPolicy::ShouldPassThroughUntrackedSelectObject`, saving configuration switches and
   return values.
3. Select tracked HFONTs, untracked HFONTs, and nonfont GDI objects separately, and record
   whether `SelectObject` passes through.
4. Use programs containing only DAT files, `render.dll`, or similar directories as nontarget samples.

| Identity | Switch | Object State | Expected Policy |
| --- | --- | --- | --- |
| TinkerBell | Enabled | Wide-character creation entry point | Uses the attachment set defined by the adapter |
| TinkerBell | Enabled | Untracked HFONT | Calls the real `SelectObject` |
| TinkerBell | Enabled | Tracked HFONT | Enters the generic font model |
| TinkerBell | Disabled | Any | Uses the generic default policy |
| Nontarget | Any | Any | Uses the generic default policy |

Evidence includes marker combinations, policy return values, object-tracking state, and bounded
sampled logs. For the record format, see
[Feature Evidence and Reproduction Workflow](../../../../../docs/reproduction.md).

## Verification

Cover strong markers, marker pairs, similar DAT/DLL layouts, missing module markers,
wide-character creation policies, untracked and tracked `SelectObject`, feature switches, and
programs with similar directory layouts.
