# Feature Evidence and Reproduction

This document defines feature descriptions, evidence records, and reproduction steps
for SimpleFontHook adapters. "Observation" means facts obtained directly from runtime
execution or static inspection. "Inference" means an interface contract derived from
multiple observations. "Unconfirmed" means the current sample lacks enough evidence
to support the conclusion.

## Goals and Boundaries

Reproduction targets a repeatably verifiable input-to-output contract, rather than a
copy of one sample's files. Each adapter must answer these questions:

| Question | Record |
| --- | --- |
| How is identity confirmed? | PE imports/exports, strings, directory structure, runtime modules, and call evidence |
| How is capability confirmed? | Target APIs, resource formats, encoding, glyph sources, and failure conditions |
| How are requests routed? | Original paths, normalized paths, virtual paths, resource categories, and handling branches |
| How are results verified? | Positive samples, non-target samples, boundary samples, log fields, and build architectures |

Adapters do not combine font replacement, code-page conversion, and engine detection
into one decision. Identity, version capability, and resource-request classification
are recorded as separate stages.

## Evidence Levels

Assign each conclusion an evidence level and retain its source location:

| Level | Meaning | Permitted wording |
| --- | --- | --- |
| `O` Observation | Directly verifiable from commands, logs, or test output | "The log field `decision=pass` indicates..." |
| `I` Inference | A stable contract derived from two or more observations | "This supports the inference that resource classification occurs before font replacement" |
| `U` Unconfirmed | Samples, symbols, or repeatable output are missing | "The upper version limit for this path is unconfirmed" |

Sources must include at least a file path, symbol name, or command. Runtime evidence
must also include the sample hash, architecture, and configuration snapshot.

## Reproduction Steps

### 1. Pin the Sample

Keep the program and resources to analyze in an isolated directory. Record paths,
architecture, file sizes, modification times, and SHA-256:

```powershell
$Sample = 'samples\TARGET'
New-Item -ItemType Directory -Force 'artifacts' | Out-Null
Get-ChildItem -LiteralPath $Sample -Recurse -File |
  ForEach-Object { Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256 } |
  Export-Csv -NoTypeInformation -Encoding UTF8 'artifacts\TARGET.sha256.csv'
```

Record the runtime environment: Windows version, process architecture (Win32 or x64),
build configuration, font-file path, `FontNameW`, `ConfigVersion`, and adapter switches.
Copy the configuration snapshot directly to the evidence directory so the record does
not depend on the current user's configuration.

### 2. Establish a Baseline

Start the sample with the adapter disabled or the target unmatched. Record original
font queries, resource-open results, and rendering screenshots. The baseline must
include English text, Chinese text, fullwidth punctuation, and a character with a
missing glyph. For each record, include time, thread, module, API, parameter summary,
return value, and duration. Represent text by length and hash to prevent unbounded logs.

### 3. Collect Static Evidence

Run the following checks on the PE file and save output to text files:

```powershell
dumpbin /headers 'samples\TARGET\TARGET.exe' > 'artifacts\TARGET.headers.txt'
dumpbin /imports 'samples\TARGET\TARGET.exe' > 'artifacts\TARGET.imports.txt'
dumpbin /exports 'samples\TARGET\TARGET.exe' > 'artifacts\TARGET.exports.txt'
```

Extract evidence separately from imports, exports, strings, RTTI, directory structure,
and archive directories. Generic `GDI` imports, window class names, file extensions,
and archive names are only clues and cannot independently confirm engine identity.
Retain the match offset for each string and the container, path, and parsing method
for each archive entry.

### 4. Confirm Identity, Capability, and Routing

Create decision records in the following order:

1. Identity: call `EngineIdentityPolicy::Confirm` or the adapter's corresponding confirmation function, and list all matched and missing markers.
2. Capability: confirm that the version, resource format, encoding, and glyph source satisfy the adapter contract; record a `fallback` reason when capability is insufficient.
3. Routing: normalize the request into a resource category, then use the common redirection entry point in `engine_file_dispatch.cppinc`. Document the correspondence between original, normalized, and virtual paths.

Provide one positive sample and one non-target sample for every stage. The non-target
sample should share at least one similar feature to verify a combination of conditions
rather than a single marker.

### 5. Extract the Minimal Contract

Condense observations into a minimal implementable input/output table:

| Input | Preconditions | Output | Failure behavior |
| --- | --- | --- | --- |
| Module/file/export | Identity confirmation passes | Resource classification or API wrapper | Pass through the original call |
| Encoding declaration | The code page is valid in the configuration snapshot | Glyph directory or conversion result | Record the reason and fall back |
| Font resource | The file exists and its format can be parsed | Font handle, byte stream, or atlas | Return the original resource or an empty result |

Implement only conditions supported by evidence. Keep unconfirmed version branches
marked `U`; do not fill them in through guesswork.

### 6. Implement at the Correct Boundary

Choose the implementation location from the call chain:

- Put engine identity and capability decisions in the corresponding `*_detection*` or `EngineIdentityPolicy` module.
- Route file redirection through `engine_file_dispatch.cppinc`; do not duplicate dispatch logic.
- Put font-table, code-page, and atlas processing in `font/` or the adapter's resource-generation module.
- High-frequency hooks perform only cache lookup and lightweight parameter checks; archive parsing, disk scans, and atlas generation belong in initialization or background stages.

Propagate configuration changes through `NotifyConfigChanged` and let each adapter
read the configuration snapshot at its own lifecycle boundary.

### 7. Validation Matrix

Each adapter README must include at least this matrix:

| Scenario | Identity | Capability | Routing | Expected result |
| --- | --- | --- | --- | --- |
| Positive sample | Pass | Pass | Matches the target category | Uses adapter resources |
| Non-target sample | Fail | Not evaluated | No routing | Original call result |
| Missing capability | Pass | Fail | Record the reason | Explicit fallback |
| Boundary input | Pass | Pass | Empty path, long path, unknown encoding | Bounded handling without crashing |
| Configuration switch | Pass | From the snapshot | Repeat the same request | Traceable `ConfigVersion` |

Run positive, non-target, and boundary scenarios separately for Win32 and x64. Place
export tables, logs, and screenshots in the same evidence directory and name them
by sample hash.

## Log Record Format

Reproduction records normalize actual logs to the following fields. The fixed prefix
of `FontHook.trace.log` contains time, PID, and TID. Message bodies use module tags
and adapter-specific fixed text; only some messages directly contain the following
`key=value` fragments:

```text
time=2026-01-01T00:00:00.000Z module=Yuris phase=identity
decision=pass evidence=ysbin/yscfg.ybn+yu-ris1 config_version=7
source=TARGET.exe request=font/abc.ttf route=virtual/abc.ttf
result=handled fallback=none duration_us=142
```

Normalized fields are `time`, `module`, `phase`, `decision`, `evidence`, `config_version`,
`source`, `request`, `route`, `result`, `fallback`, and `duration_us`. Represent paths
and text parameters by length, hash, or a truncated summary. High-frequency paths do
not log full resource content.

## Reproduction Record Template

Copy the following template into an adapter README or diagnostic record:

```text
Sample ID: TARGET
Sample SHA-256: SHA256
Architecture: Win32 | x64
Build configuration: CONFIGURATION
Configuration snapshot: PATH_TO_CONFIG

Observation O-01:
  Source: FILE:LINE / SYMBOL / COMMAND
  Input: INPUT
  Output: OUTPUT

Inference I-01:
  Basis: O-01, O-02
  Contract: CONTRACT

Unconfirmed U-01:
  Gap: MISSING_EVIDENCE

Positive command: COMMAND
Non-target command: COMMAND
Boundary command: COMMAND
Expected log: module=MODULE phase=PHASE decision=DECISION
Expected artifacts: ARTIFACT_PATHS
```

## Documentation Wording Rules

- Use verifiable verbs such as "the function returns", "the log records", "the file contains", and "the configuration reads".
- Separate facts, inferences, and unconfirmed items into columns; avoid unmeasurable judgments such as "reliable", "complete", or "simple".
- Feature documentation describes current interfaces and constraints. Put code history, the evolution of rationale, and commit context in commit records or ADRs.
- Example commands must specify input locations, output locations, and interpretation criteria. Mark omitted criteria as unconfirmed.
- Every conclusion must be traceable to its evidence through files, symbols, commands, or log fields.
