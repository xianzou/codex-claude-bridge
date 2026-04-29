---
name: codex-claude-bridge
description: "Delegate code implementation/review/debugging/alternatives to Claude Code via a JSON bridge script. Multi-turn via SESSION_ID."
metadata:
  short-description: Bridge Codex and Claude Code
---

# Codex Claude Bridge

Use this skill for second opinions, code review, test design, or code implementations/alternatives. The bridge runs `claude` (Claude Code) non-interactively ("print" mode) and returns JSON.

The script is located at `~/.codex/skills/codex-claude-bridge/scripts/claude_code_bridge.py`.

## Timing

Claude Code often needs **1–2+ minutes** per task.
- Prefer running the bridge directly (no `&`); increase `--timeout-s` as needed (default: 1800s).
- Do **NOT** redirect stdout to a file (e.g. `> /tmp/out.json`).
- By default, the bridge streams Claude's assistant text to `stderr`, and prints only the final JSON envelope to `stdout`.
- On Windows, the bridge tries to hide the spawned `claude` console window by default.

## Context

- Do **NOT** read the script unless you are modifying it; 
- Before running the script, ALWAYS use `python <script_loc> --help` to get the usage instructions.

## Usage

- Default delegation mode: treat Claude Code as a **weak planner, strong executor** unless the task is explicitly codebase exploration or architecture research.
- The supervising agent must understand the task and define the boundaries before delegating. Do not offload initial task framing to Claude by default.
- Give Claude a narrow execution package:
  - the concrete goal
  - the expected behavior
  - the files it may change
  - the files or areas it must not change
  - constraints and non-goals
  - the exact verification or acceptance criteria
- Do not ask Claude to freely explore or fully understand the codebase for routine implementation tasks. Only request broad codebase understanding when that exploration is itself the task.
- Prefer explicit instructions such as: what to modify, what to reuse, what not to refactor, and what not to add.
- Put codex-claude-bridge terminal commands in the background terminal.
- Always review Claude Code's responses, diffs, and verification claims; Claude does not self-accept work.
- When Claude asks clarifying questions in a multi-turn session, answer with current constraints and keep the worker within the original task boundary.

### Delegation template

Use a prompt structure close to this for execution tasks:

1. Objective: one concrete outcome.
2. Allowed edits: exact files or directories Claude may modify.
3. Forbidden edits: shared contracts, config, routes, dependencies, unrelated files, or any area you want frozen.
4. Implementation instructions: what pattern to follow, what existing code to reuse, and what behavior to preserve.
5. Non-goals: explicitly list enhancements or refactors Claude must not add.
6. Acceptance: exact runtime behavior, tests, or checks required for supervisor review.
7. Response format: changed files, summary of changes, blockers, and verification run.

## Operational rules

- Give one Claude worker one clear objective. Do not mix multiple sub-tasks into a single worker prompt.
- Separate human-readable results from machine-readable completion signals.
  - For automation or orchestration, prefer `--extract-exact "TASK_DONE"`-style markers.
  - For human review, keep natural-language output and review it directly.
- Never treat bridge-level `success: true` as task acceptance.
  - It only means the bridge call completed successfully.
  - Final acceptance still belongs to the supervising agent, which should inspect diffs, run tests, and review the result.

## Supervisor loop

Use this skill as part of a supervisor-worker loop:

1. `Codex` defines one focused task for one Claude worker.
2. `Codex` runs the bridge and captures `success`, `SESSION_ID`, and `agent_messages`.
3. `Codex` reviews the result independently by inspecting diffs and running verification.
4. If the result is not acceptable, `Codex` must continue the same conversation with `--SESSION_ID` and give Claude a precise fix request.
5. Repeat until `Codex` accepts the result or Claude returns a blocked state.

Recommended machine-readable markers:

- `TASK_DONE`: ready for supervisor verification.
- `TASK_NEEDS_REVIEW`: requires supervisor review before acceptance.
- `TASK_BLOCKED`: cannot continue without more input or an external dependency.

These markers are orchestration signals, not proof of correctness.

## Default

- **full access** (`--full-access`): use only in trusted repos/directories.
- **extended thinking ON** (can disable via `--no-extended-thinking`).
- **step mode AUTO** (can disable via `--step-mode off`).

## Output format

The bridge prints JSON to `stdout`:

```json
{"success": true, "SESSION_ID": "abc123", "agent_messages": "…Claude output…"}
```

For automation-oriented prompts that should return a single exact marker, prefer `--extract-exact`:

```bash
python <script_loc> \
  --no-full-access \
  --cd "/path/to/repo" \
  --extract-exact "OK_MARKER" \
  --PROMPT "Implement only the scoped task below and reply with exactly OK_MARKER when finished."
```

When the marker is found as a standalone line in Claude output, the bridge returns only that marker in `agent_messages`. If not found, the bridge returns `success: false` to avoid silent misclassification.

## Recommended delegation patterns

- **Guided coding**: "Implement the code for [feature] following these specific steps/constraints."
- **Second opinion**: "Propose an alternative approach and tradeoffs."
- **Code review**: "Find bugs, race conditions, security issues; propose fixes."
- **Test design**: "Write a test plan + edge cases; include example test code."
- **Diff review**: "Review this patch; point out regressions and missing cases."
