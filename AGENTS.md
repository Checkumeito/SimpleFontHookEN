# Automation Agent Rules

This file applies to automation agents making code or documentation changes in
this repository.

## Getting Started

1. Read `README.md`, `CONTRIBUTING.md`, `docs/architecture.md`, and the target module's README first.
2. Check the workspace state and preserve existing changes unrelated to the current task.
3. Locate the actual call chain, configuration defaults, and target architecture before choosing where to make changes.
4. The main task reads small files at known locations directly. Cross-directory searches may be delegated to exploration subtasks, but the implementer must personally read the code they ultimately modify.

## Subagents

Subagents are exploration tools. By default, they only search, read, and independently
verify. They do not choose the final approach, modify code, or perform final verification.

- Prefer concurrent delegation for huge files, cross-directory searches, multiple independent questions, and large amounts of log analysis.
- The main task personally reads small files at known locations, code about to be modified, and foundational architecture documents in full.
- Delegated tasks must specify the scope, concrete question, and expected output. Important conclusions must include files, line numbers, and symbol names.
- The main task spot-checks key sources identified by subagents rather than rereading all delegated material.
- Dispatch multiple independent exploration tasks in the same round. Wait for their results before continuing analysis or changes that depend on those results.
- Use the default subagent role with independent context. Do not reuse exploration subagents for subsequent modifications.
- If a subagent makes no progress for a long time or its tools are unavailable, use its partial results and let the main task take over.

Subagents should reduce context clutter in the main task and improve parallelism.
Do not split small tasks so finely that delegation costs more than direct handling.

## Local File Tools

- Prefer FastCtx `glob`, `grep`, and `read` for finding files, searching content, and reading.
- Prefer FastCtx `replace` for mechanical bulk replacements. Run a dry run first and limit the maximum replacement count.
- Use `apply_patch` for semantic changes, new files, and small edits.
- Prefer FastCtx shell for terminal commands. Use background tasks for long builds and tests, and continue reading their results.
- Exclude `Release/`, `x64/Release/`, and other generated directories from searches to avoid treating binary strings as source code.

## Project Invariants

- Do not couple font replacement to code page conversion.
- Do not create an engine-specific module for a single sample without value as a general interface.
- Do not use general GDI imports, window classes, or a single filename as the sole evidence for engine identification.
- Do not identify engines by file extensions or general archive names. Extensions only route resources for an already confirmed engine.
- Keep engine identity, version capabilities, and resource request classification as three separate decision stages.
- Do not bypass `engine_file_dispatch.cppinc` by duplicating file redirection logic.
- Do not compile `.cppinc` files separately. Aggregate `.cpp` files include them, and they retain internal linkage.
- Do not perform repeated disk scans, archive parsing, or unbounded logging in high-frequency hooks.
- Do not wait for worker threads in shutdown paths under the loader lock.
- Do not edit generated files in `Release/`, `x64/Release/`, or project intermediate directories.

## Change Requirements

- Follow the project's existing naming, state management, caching, and `org*` API patterns.
- New features preserve existing behavior by default. Add a disableable configuration option when needed.
- Configuration changes cover declarations, defaults, saving, loading, UI, and runtime refresh together.
- Engine adaptation changes check both positive identification and false positives in non-target applications.
- Font table changes perform complete bounds checking and maintain checksums.
- Comments explain reasons, invariants, or unusual layouts rather than restating code.

## Verification Requirements

- Build Win32 and x64 Release after C++ changes.
- Check the DLL export table when modifying proxy exports, project files, or linker options.
- Run verification appropriate to the change's risk. Do not repeatedly start the target application to verify the same fact.
- When a build fails, fix the first real compiler error. Do not remove features to work around it.
- The final report identifies changed files, behavior changes, build results, and verification not performed.

## Documentation Requirements

- Write new documentation in English using UTF-8.
- Preserve the original spelling of code identifiers, paths, APIs, configuration keys, and product names.
- README files describe current responsibilities, features, interfaces, configuration, and constraints. Put troubleshooting procedures in `docs/diagnostics.md`.
- Maintain a separate README in each `hooks/internal/engines/<engine>/` directory and update the engine index at the same time.
- Describe the current state in documentation. Keep code change history in commits or ADRs.
