import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "claude_code_bridge.py"
FAKE_CLAUDE_BIN = ROOT / "tests" / "fake-claude.cmd"
FAKE_REPO = ROOT / "tests" / "fake_repo"
STATE_DIR = ROOT / "tests" / "runtime_state"


class BridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        safe_name = self.id().replace(".", "_")
        self.state_dir = STATE_DIR / safe_name
        shutil.rmtree(self.state_dir, ignore_errors=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def run_bridge(self, scenario: str, *extra_args: str, reset_state: bool = True):
        if reset_state:
            self.reset_state_files()

        env = os.environ.copy()
        env["FAKE_CLAUDE_SCENARIO"] = scenario
        env["FAKE_CLAUDE_STATE_DIR"] = str(self.state_dir)

        cmd = [
            sys.executable,
            str(BRIDGE),
            "--claude-bin",
            str(FAKE_CLAUDE_BIN),
            "--cd",
            str(FAKE_REPO),
            "--PROMPT",
            "Fully understand the repo first, then continue.",
            *extra_args,
        ]
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )

    def reset_state_files(self):
        for path in self.state_dir.glob("*.count"):
            path.unlink()

    def tearDown(self):
        shutil.rmtree(self.state_dir, ignore_errors=True)

    def parse_stdout_json(self, completed: subprocess.CompletedProcess[str]):
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        return json.loads(completed.stdout)

    def test_success_flow_returns_session_and_result(self):
        completed = self.run_bridge("success")
        payload = self.parse_stdout_json(completed)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["SESSION_ID"], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(payload["agent_messages"], "All checks complete.")
        self.assertIn("session_id=11111111-1111-1111-1111-111111111111", completed.stderr)
        self.assertIn("Working through the request.", completed.stderr)

    def test_extract_exact_returns_only_marker(self):
        completed = self.run_bridge("extract_success", "--extract-exact", "TASK_DONE")
        payload = self.parse_stdout_json(completed)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["agent_messages"], "TASK_DONE")

    def test_extract_exact_fails_when_marker_missing(self):
        completed = self.run_bridge("extract_missing", "--extract-exact", "TASK_DONE")
        payload = self.parse_stdout_json(completed)

        self.assertFalse(payload["success"])
        self.assertEqual(payload["SESSION_ID"], "11111111-1111-1111-1111-111111111111")
        self.assertIn('Exact marker not found as a standalone line: "TASK_DONE"', payload["error"])

    def test_needs_review_marker_is_distinct_from_done(self):
        completed = self.run_bridge("needs_review_marker", "--extract-exact", "TASK_NEEDS_REVIEW")
        payload = self.parse_stdout_json(completed)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["agent_messages"], "TASK_NEEDS_REVIEW")
        self.assertNotEqual(payload["agent_messages"], "TASK_DONE")
        self.assertIn("Please inspect the diff and tests.", completed.stderr)

    def test_step_mode_resumes_after_error_max_turns(self):
        completed = self.run_bridge("max_turns_then_success", "--step-mode", "on", "--extract-exact", "TASK_DONE")
        payload = self.parse_stdout_json(completed)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["agent_messages"], "TASK_DONE")
        self.assertIn("Starting step one.", completed.stderr)
        self.assertIn("Resumed and completed.", completed.stderr)

    def test_same_session_can_continue_after_failed_acceptance(self):
        first = self.run_bridge("manual_rework_session")
        first_payload = self.parse_stdout_json(first)

        self.assertTrue(first_payload["success"])
        self.assertEqual(first_payload["SESSION_ID"], "11111111-1111-1111-1111-111111111111")
        self.assertIn("Initial implementation delivered.", first_payload["agent_messages"])

        second = self.run_bridge(
            "manual_rework_session",
            "--SESSION_ID",
            first_payload["SESSION_ID"],
            "--extract-exact",
            "TASK_DONE",
            reset_state=False,
        )
        second_payload = self.parse_stdout_json(second)

        self.assertTrue(second_payload["success"])
        self.assertEqual(second_payload["SESSION_ID"], first_payload["SESSION_ID"])
        self.assertEqual(second_payload["agent_messages"], "TASK_DONE")
        self.assertIn("Patched the requested issues.", second.stderr)

    def test_step_mode_auto_falls_back_after_thinking_schema_400(self):
        completed = self.run_bridge("thinking_400_then_success", "--extract-exact", "TASK_DONE")
        payload = self.parse_stdout_json(completed)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["agent_messages"], "TASK_DONE")
        self.assertIn("session_id=11111111-1111-1111-1111-111111111111", completed.stderr)
        self.assertIn("Recovered with step mode.", completed.stderr)


if __name__ == "__main__":
    unittest.main()
