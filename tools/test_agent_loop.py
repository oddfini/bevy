"""Exercise the real driver flow with a fake clock, RPC client and owned app."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brp_client import RpcError, TransportError

spec = importlib.util.spec_from_file_location("agent_loop_tests", Path(__file__).with_name("agent-loop.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def state(count):
    return {"schema": 1, "count": count, "revision": count, "limit": 10,
            "legalActions": ["increment"]}


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class OwnedApp:
    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout):
        return self.returncode


class ScriptedClient:
    def __init__(self, clock, delays, *, action_failure=False):
        self.clock, self.delays = clock, iter(delays)
        self.timeout = 5
        self.count = 0
        self.calls = []
        self.action_failure = action_failure

    def call(self, method, params=None):
        self.calls.append((method, params, self.timeout))
        if method == "agent.state":
            elapsed, fails = next(self.delays, (0, False))
            self.clock.now += elapsed
            if fails:
                raise TransportError("synthetic startup failure")
            return state(self.count)
        if self.action_failure:
            raise TransportError("synthetic action outcome unknown")
        if params == {"action": "increment", "expectedRevision": 0} and self.count == 0:
            self.count = 1
            return state(1)
        raise RpcError({"code": -32602, "message": "synthetic rejected action"})


class StartupDeadlineTests(unittest.TestCase):
    def run_driver(self, timeout, delays, *, action_failure=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            output, target = root / "evidence", root / "target"
            examples = target / "debug/examples"
            examples.mkdir(parents=True)
            suffix = ".exe" if os.name == "nt" else ""
            for name in ("agent_control_app", "agent_control_test"):
                (examples / (name + suffix)).write_bytes(b"not an executable; synthetic hash input")
            clock, app = Clock(), OwnedApp()
            client = ScriptedClient(clock, delays, action_failure=action_failure)

            def ui(command, **kwargs):
                self.assertEqual([str(examples / ("agent_control_test" + suffix))], command)
                self.assertEqual(output, kwargs["cwd"])
                (output / "agent-report.json").write_text(json.dumps({"ok": True,
                    "beforeClick": state(1), "afterClick": state(2)}))
                (output / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\nsynthetic image")
                app.returncode = 0

            argv = ["agent-loop.py", "--skip-build", "--timeout", str(timeout), "--output", str(output)]
            with patch.object(sys, "argv", argv), patch.dict(os.environ, {"CARGO_TARGET_DIR": str(target)}), \
                 patch.object(driver, "ROOT", root), patch.object(driver, "CLIENT", client), \
                 patch.object(driver.platform, "platform", return_value="synthetic platform"), \
                 patch.object(driver, "source_hashes", return_value={"synthetic": "input"}), \
                 patch.object(driver.time, "monotonic", clock.monotonic), patch.object(driver.time, "sleep", clock.sleep), \
                 patch.object(driver.subprocess, "check_output", return_value="synthetic tool\n"), \
                 patch.object(driver.subprocess, "Popen", return_value=app) as launch, \
                 patch.object(driver.subprocess, "run", side_effect=ui) as pointer, \
                 patch.object(driver.socket, "socket") as socket, \
                 contextlib.redirect_stdout(io.StringIO()):
                socket.return_value.__enter__.return_value.connect_ex.return_value = 1
                result = driver.main()
            return result, json.loads((output / "summary.json").read_text()), client, app, clock, pointer.call_count, launch.call_count

    def test_late_success_fails_before_any_action_and_cleans_up_owned_app(self):
        code, report, client, app, _, pointer_calls, launches = self.run_driver(0.05, [(0.2, False)])
        self.assertEqual(1, code)
        self.assertFalse(report["ok"])
        self.assertIn("before timeout", report["error"])
        self.assertEqual(["agent.state"], [call[0] for call in client.calls])
        self.assertTrue(app.terminated)
        self.assertEqual(0, pointer_calls)
        self.assertEqual(1, launches)

    def test_reply_exactly_at_deadline_is_not_startup_success(self):
        code, _, client, app, _, pointer_calls, _ = self.run_driver(0.05, [(0.05, False)])
        self.assertEqual(1, code)
        self.assertEqual(["agent.state"], [call[0] for call in client.calls])
        self.assertTrue(app.terminated)
        self.assertEqual(0, pointer_calls)

    def test_reply_before_deadline_preserves_normal_flow_and_restores_rpc_timeout(self):
        code, report, client, app, _, pointer_calls, _ = self.run_driver(0.05, [(0.049, False)])
        self.assertEqual(0, code)
        self.assertTrue(report["ok"])
        self.assertFalse(report["buildVerified"], "synthetic skip-build evidence is diagnostic only")
        self.assertEqual(0.05, client.calls[0][2])
        self.assertTrue(all(call[2] == 5 for call in client.calls[1:]))
        self.assertEqual(5, client.timeout)
        self.assertEqual(1, pointer_calls)
        self.assertFalse(app.terminated)
        self.assertEqual(state(1), report["afterCommand"])
        self.assertEqual(3, len(report["rejectedActions"]))

    def test_startup_keeps_existing_five_second_socket_cap(self):
        code, _, client, _, _, _, _ = self.run_driver(90, [(0.1, False)])
        self.assertEqual(0, code)
        self.assertEqual(5, client.calls[0][2])

    def test_startup_keeps_existing_sixty_second_deadline_cap(self):
        code, _, client, app, _, _, _ = self.run_driver(90, [(60, False)])
        self.assertEqual(1, code)
        self.assertEqual(["agent.state"], [call[0] for call in client.calls])
        self.assertTrue(app.terminated)

    def test_failed_read_cannot_start_another_poll_after_budget_is_exhausted(self):
        code, report, client, app, clock, _, _ = self.run_driver(0.05, [(0.02, True)])
        self.assertEqual(1, code)
        self.assertIn("before timeout", report["error"])
        self.assertEqual(["agent.state"], [call[0] for call in client.calls])
        self.assertLessEqual(sum(clock.sleeps), 0.03 + 1e-12)
        self.assertTrue(app.terminated)
        self.assertEqual(5, client.timeout)

    def test_read_retry_with_time_remaining_can_start_normally(self):
        code, _, client, app, _, pointer_calls, _ = self.run_driver(0.5, [(0.02, True), (0.01, False)])
        self.assertEqual(0, code)
        self.assertEqual(["agent.state", "agent.state"], [call[0] for call in client.calls[:2]])
        self.assertAlmostEqual(0.5, client.calls[0][2])
        self.assertAlmostEqual(0.38, client.calls[1][2])
        self.assertEqual(1, pointer_calls)
        self.assertFalse(app.terminated)

    def test_unknown_action_outcome_is_not_retried(self):
        code, report, client, app, _, pointer_calls, _ = self.run_driver(1, [(0, False)], action_failure=True)
        self.assertEqual(1, code)
        self.assertIn("action outcome unknown", report["error"])
        self.assertEqual(["agent.state", "agent.act"], [call[0] for call in client.calls])
        self.assertTrue(app.terminated)
        self.assertEqual(0, pointer_calls)
        self.assertEqual(5, client.timeout)


if __name__ == "__main__":
    unittest.main()
