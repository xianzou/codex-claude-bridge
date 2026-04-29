import importlib.util
import unittest
from pathlib import Path


def load_bridge_module():
    bridge_path = Path(__file__).resolve().parents[1] / "scripts" / "claude_code_bridge.py"
    spec = importlib.util.spec_from_file_location("claude_code_bridge", bridge_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load claude_code_bridge module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load_bridge_module()


class ExtractExactTests(unittest.TestCase):
    def test_extract_exact_returns_marker_on_standalone_line(self):
        text = "intro\nTASK_DONE\nextra details"
        self.assertEqual(bridge._extract_exact_marker(text, "TASK_DONE"), "TASK_DONE")

    def test_extract_exact_returns_none_when_marker_not_standalone(self):
        text = "The final answer is TASK_DONE in a sentence."
        self.assertIsNone(bridge._extract_exact_marker(text, "TASK_DONE"))


class ReadonlyToolsTests(unittest.TestCase):
    def test_readonly_default_tools_do_not_include_write(self):
        self.assertEqual(bridge.DEFAULT_READONLY_TOOLS, "Read,Glob,Grep,LS")


class ClaudeCommandTests(unittest.TestCase):
    def test_stream_json_always_enables_verbose(self):
        cmd = bridge._build_claude_cmd(
            claude_bin="claude",
            prompt="hello",
            output_format="stream-json",
            model="claude-opus-4-6",
            permission_mode="plan",
            tools=None,
            allowed_tools=None,
            session_id="",
            continue_session=False,
            claude_settings={},
            max_turns=None,
            verbose=False,
        )
        self.assertIn("--verbose", cmd)


class WindowsLaunchBehaviorTests(unittest.TestCase):
    def test_windows_popen_kwargs_hide_console(self):
        kwargs = bridge._get_windows_popen_kwargs()
        self.assertIn("creationflags", kwargs)
        self.assertTrue(kwargs["creationflags"])


if __name__ == "__main__":
    unittest.main()
