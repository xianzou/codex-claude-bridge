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

- please always require claude code to fully understand the codebase before responding or making any changes.
- Put codex-claude-bridge terminal commands in the background terminal.
- Always review claude code's responses (or changes it makes) and make sure they are correct, constructive and complete.
- When claude code asks clarifying questions in a multi-turn session, always respond to its questions in that session based on current situation.

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
  --PROMPT "Fully understand the repo first. Reply with exactly OK_MARKER."
```

When the marker is found as a standalone line in Claude output, the bridge returns only that marker in `agent_messages`. If not found, the bridge returns `success: false` to avoid silent misclassification.

## Recommended delegation patterns

- **Guided coding**: "Implement the code for [feature] following these specific steps/constraints."
- **Second opinion**: "Propose an alternative approach and tradeoffs."
- **Code review**: "Find bugs, race conditions, security issues; propose fixes."
- **Test design**: "Write a test plan + edge cases; include example test code."
- **Diff review**: "Review this patch; point out regressions and missing cases."
