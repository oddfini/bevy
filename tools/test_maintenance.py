"""Regression checks for the maintenance gate using isolated, tiny Git repositories."""

import base64
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import maintenance as gate

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jpaMAAAAASUVORK5CYII=")


class MaintenanceTests(unittest.TestCase):
    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self, message):
        gate.git(self.root, "add", ".")
        gate.git(self.root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", message)
        return gate.git(self.root, "rev-parse", "HEAD").decode().strip()

    def save_policy(self):
        self.write(gate.POLICY, json.dumps(self.policy))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        gate.git(self.root, "init", "-q")
        for name in (*gate.PROTECTED, "README.md", ".github/workflows/ci.yml"):
            self.write(name, "upstream\n")
        self.write("Cargo.toml", '[package]\nname = "bevy"\nversion = "0.1.0"\n')
        self.write("crates/widget/Cargo.toml", '[package]\nname = "widget"\nversion = "0.1.0"\n')
        self.write("crates/widget/src/lib.rs", "bug\n")
        base = self.commit("upstream")
        self.write("crates/widget/src/lib.rs", "fixed\n")
        source = self.commit("local fix")
        self.policy = {"schema": 1, "upstream": gate.UPSTREAM, "base": base,
                       "testPackages": ["widget"],
                       "examples": [{"name": "agent_demo", "path": "examples/agent/demo.rs", "required-features": []}],
                       "patches": [{"id": "fixture", "origin": "downstream", "source": source,
                                    "status": "active", "reason": "Reproduced bug", "regression": "Bug regression",
                                    "files": {"crates/widget/src/lib.rs": gate.digest(self.root / "crates/widget/src/lib.rs")}}]}
        self.save_policy()
        self.write("UPSTREAM_README.md", "upstream\n")
        with (self.root / "Cargo.toml").open("a") as manifest:
            manifest.write('\n# Downstream examples. Keep upstream examples and engine identifiers unchanged.\n'
                           '[[example]]\nname = "agent_demo"\npath = "examples/agent/demo.rs"\nrequired-features = []\n')
        for name in ("Cargo.lock", "tools/agent-loop.py", "tools/brp_client.py", "tools/maintenance.py", "examples/agent/demo.rs"):
            self.write(name, "fixture\n")
        self.image = self.root / "screenshot.png"
        self.image.write_bytes(PNG)
        def state(count):
            return {"schema": 1, "count": count, "revision": count, "limit": 10, "legalActions": ["increment"]}
        self.report = {"schema": 2, "ok": True, "buildVerified": True,
                       "checks": {name: {"command": ["fixture"], "exitCode": 0}
                                  for name in ("format", "exampleTests", "clippy", "build")},
                       "sourceSha256": gate.source_hashes(self.root), "screenshotSha256": gate.digest(self.image),
                       "platform": "fixture", "verifiedDate": "2026-10-25", "cargoVersion": "fixture", "rustcVersion": "fixture",
                       "binarySha256": {"agent_control_app": "a" * 64, "agent_control_test": "b" * 64},
                       "initial": state(0), "afterCommand": state(1),
                       "rejectedActions": [{"code": -32602}] * 3,
                       "ui": {"ok": True, "beforeClick": state(1), "afterClick": state(2),
                              "screenshot": {"width": 1, "height": 1}}}

    def test_recorded_patch_and_current_evidence_pass(self):
        gate.check_compatibility(self.root)
        gate.check_evidence(self.root, self.report, self.image)

    def test_new_engine_file_requires_a_patch_record(self):
        self.write("crates/widget/src/unrecorded.rs", "change\n")
        with self.assertRaisesRegex(ValueError, "recorded patches"):
            gate.check_compatibility(self.root)

    def test_recorded_engine_file_cannot_silently_change(self):
        self.write("crates/widget/src/lib.rs", "another behavior\n")
        with self.assertRaisesRegex(ValueError, "matching record"):
            gate.check_compatibility(self.root)

    def test_cargo_cannot_append_dependency_overrides(self):
        with (self.root / "Cargo.toml").open("a") as manifest:
            manifest.write('\n[patch.crates-io]\nwidget = { path = "elsewhere" }\n')
        with self.assertRaisesRegex(ValueError, "Cargo manifest"):
            gate.check_compatibility(self.root)

    def test_original_license_and_workflow_are_preserved(self):
        for name in ("LICENSE-MIT", ".github/workflows/ci.yml"):
            with self.subTest(name=name):
                self.write(name, "changed\n")
                with self.assertRaisesRegex(ValueError, "Upstream file changed|workflow files"):
                    gate.check_compatibility(self.root)
                self.write(name, "upstream\n")

    def test_original_remote_example_cannot_change(self):
        self.write("examples/remote/app_under_test.rs", "modified\n")
        with self.assertRaisesRegex(ValueError, "Upstream file changed"):
            gate.check_compatibility(self.root)

    def test_new_module_or_changed_driver_invalidates_evidence(self):
        for name in ("examples/agent/new_model.rs", "tools/agent-loop.py", "tools/brp_client.py"):
            with self.subTest(name=name):
                self.write(name, "new input\n")
                with self.assertRaisesRegex(ValueError, "stale"):
                    gate.check_evidence(self.root, self.report, self.image)
                if "new_model" in name:
                    (self.root / name).unlink()
                else:
                    self.write(name, "fixture\n")

    def test_skip_build_and_incorrect_transitions_cannot_be_recorded(self):
        for key in ("buildVerified", "afterCommand", "rejectedActions", "ui"):
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report[key] = {"buildVerified": False, "afterCommand": {}, "rejectedActions": [],
                               "ui": {**report["ui"], "afterClick": report["initial"]}}[key]
                with self.assertRaises(ValueError):
                    gate.check_evidence(self.root, report, self.image)

    def test_screenshot_content_and_dimensions_are_bound(self):
        self.image.write_bytes(PNG + b"changed")
        with self.assertRaisesRegex(ValueError, "does not match"):
            gate.check_evidence(self.root, self.report, self.image)
        self.image.write_bytes(PNG)
        self.report["ui"]["screenshot"]["width"] = 2
        with self.assertRaisesRegex(ValueError, "dimensions"):
            gate.check_evidence(self.root, self.report, self.image)

    def test_failed_local_check_cannot_be_recorded(self):
        self.report["checks"]["exampleTests"]["exitCode"] = 1
        with self.assertRaisesRegex(ValueError, "local checks"):
            gate.check_evidence(self.root, self.report, self.image)

    def test_adapted_patch_requires_an_explanation(self):
        self.policy["patches"][0]["source"] = self.policy["base"]
        self.save_policy()
        with self.assertRaisesRegex(ValueError, "adaptation"):
            gate.check_compatibility(self.root)
        self.policy["patches"][0]["adaptation"] = "Fixture demonstrates a documented adaptation."
        self.save_policy()
        gate.check_compatibility(self.root)

    def test_plan_reports_overlap_without_changing_files(self):
        before = gate.git(self.root, "status", "--porcelain")
        plan = gate.upstream_plan(self.root, self.policy["patches"][0]["source"], "backport")
        self.assertEqual(plan["patchOverlaps"], ["crates/widget/src/lib.rs"])
        self.assertEqual(before, gate.git(self.root, "status", "--porcelain"))

    def test_baseline_update_adds_tests_for_each_changed_crate(self):
        self.write("crates/another/Cargo.toml", '[package]\nname = "another"\nversion = "0.1.0"\n')
        self.write("crates/another/src/lib.rs", "new upstream behavior\n")
        self.assertEqual(gate.test_packages(self.root, self.policy, self.policy["base"]), ["another", "widget"])

    def test_removed_crate_requires_a_replacement_test_plan(self):
        (self.root / "crates/widget/Cargo.toml").unlink()
        with self.assertRaisesRegex(ValueError, "replacement test plan"):
            gate.test_packages(self.root, self.policy, self.policy["base"])

    def test_short_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "40-character"):
            gate.upstream_plan(self.root, self.policy["base"][:7], "baseline")

    def test_cli_fails_for_missing_runtime_evidence(self):
        with patch.object(gate, "ROOT", self.root), patch.object(sys, "argv", ["maintenance.py", "check"]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(), 1)


if __name__ == "__main__":
    unittest.main()
