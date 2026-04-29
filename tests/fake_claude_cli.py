import argparse
import json
import os
import sys
from pathlib import Path


SESSION_ID = "11111111-1111-1111-1111-111111111111"


def emit(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def load_call_count(state_dir: Path, scenario: str) -> int:
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / f"{scenario}.count"
    if not state_path.exists():
        state_path.write_text("0", encoding="utf-8")
        return 0
    count = int(state_path.read_text(encoding="utf-8").strip() or "0")
    state_path.write_text(str(count + 1), encoding="utf-8")
    return count + 1


def emit_assistant(text: str) -> None:
    emit(
        {
            "type": "assistant",
            "session_id": SESSION_ID,
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
            },
        }
    )


def emit_result(subtype: str, result: str, *, is_error: bool = False) -> None:
    emit(
        {
            "type": "result",
            "session_id": SESSION_ID,
            "subtype": subtype,
            "is_error": is_error,
            "result": result,
        }
    )


def main() -> int:
    if "--version" in sys.argv:
        print("fake-claude 0.0.1")
        return 0

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-p", "--print-prompt", dest="prompt")
    parser.add_argument("--output-format")
    parser.add_argument("--model")
    parser.add_argument("--permission-mode")
    parser.add_argument("--tools")
    parser.add_argument("--allowedTools")
    parser.add_argument("--settings")
    parser.add_argument("--max-turns")
    parser.add_argument("--resume", default="")
    parser.add_argument("--continue", dest="continue_session", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args, _ = parser.parse_known_args()

    scenario = os.environ.get("FAKE_CLAUDE_SCENARIO", "success")
    state_dir = Path(os.environ["FAKE_CLAUDE_STATE_DIR"])
    call_count = load_call_count(state_dir, scenario)

    if scenario == "success":
        emit_assistant("Working through the request.")
        emit_result("success", "All checks complete.")
        return 0

    if scenario == "extract_success":
        emit_assistant("Review finished.\nTASK_DONE\nYou can verify the diff now.")
        emit_result("success", "Review finished.\nTASK_DONE\nYou can verify the diff now.")
        return 0

    if scenario == "extract_missing":
        emit_assistant("Review finished without the requested marker.")
        emit_result("success", "Review finished without the requested marker.")
        return 0

    if scenario == "needs_review_marker":
        emit_assistant("Implementation updated.\nTASK_NEEDS_REVIEW\nPlease inspect the diff and tests.")
        emit_result("success", "Implementation updated.\nTASK_NEEDS_REVIEW\nPlease inspect the diff and tests.")
        return 0

    if scenario == "max_turns_then_success":
        if call_count == 0:
            emit_assistant("Starting step one.")
            emit_result("error_max_turns", "Need another turn.", is_error=True)
            return 0
        if not args.resume and not args.continue_session:
            emit_result("error", "Expected resume or continue on second call.", is_error=True)
            return 0
        emit_assistant("Resumed and completed.")
        emit_result("success", "TASK_DONE")
        return 0

    if scenario == "manual_rework_session":
        if call_count == 0:
            emit_assistant("Initial implementation delivered.")
            emit_result("success", "Initial implementation delivered. Please review and report issues.")
            return 0
        if args.resume != SESSION_ID:
            emit_result("error", "Expected the prior SESSION_ID on follow-up.", is_error=True)
            return 0
        emit_assistant("Patched the requested issues.\nTASK_DONE")
        emit_result("success", "Patched the requested issues.\nTASK_DONE")
        return 0

    if scenario == "thinking_400_then_success":
        if call_count == 0:
            emit(
                {
                    "type": "result",
                    "session_id": SESSION_ID,
                    "subtype": "error",
                    "is_error": True,
                    "result": (
                        "API Error: 400 Expected `thinking` or `redacted_thinking`, but found `tool_use`"
                    ),
                }
            )
            return 0
        if not args.resume and not args.continue_session:
            emit_result("error", "Expected resume or continue after the 400 fallback.", is_error=True)
            return 0
        emit_assistant("Recovered with step mode.\nTASK_DONE")
        emit_result("success", "Recovered with step mode.\nTASK_DONE")
        return 0

    emit_result("error", f"Unknown scenario: {scenario}", is_error=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
