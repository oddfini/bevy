#!/usr/bin/env python3
"""Build and verify the fork's agent/UI command loop without an editor GUI."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time

# tools/* is a Rust workspace glob; local bytecode folders break Cargo metadata.
sys.dont_write_bytecode = True
from brp_client import Client, RpcError
from maintenance import source_hashes


ROOT = Path(__file__).resolve().parents[1]
FEATURES = "ui,bevy_remote_client,bevy_feathers"
URL = "http://127.0.0.1:15702/"
CLIENT = Client(URL, timeout=5)


def rpc(method, params=None, expected_error=None):
    try:
        result = CLIENT.call(method, params)
    except RpcError as error:
        if expected_error is not None and error.code == expected_error:
            return error.error
        raise RuntimeError(f"RPC failed: {error}") from error
    if expected_error is not None:
        raise RuntimeError(f"Expected RPC error {expected_error}, received a result")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for this run's evidence")
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    if args.output:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    else:
        output = Path(tempfile.mkdtemp(prefix="bevy-agent-loop-"))
    target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target"))
    target = (target if target.is_absolute() else ROOT / target).resolve()
    examples = target / "debug" / "examples"
    suffix = ".exe" if os.name == "nt" else ""
    server = None
    report = {"schema": 2, "ok": False, "buildVerified": False, "checks": {},
              "verifiedDate": datetime.now(timezone.utc).date().isoformat(),
              "platform": platform.platform()}
    try:
        report["sourceSha256"] = source_hashes(ROOT)
        if not args.skip_build:
            flags = ["--locked", "--no-default-features", "--features", FEATURES, "-j", "1"]
            if args.offline:
                flags.append("--offline")
            targets = ["--example", "agent_control_app", "--example", "agent_control_test"]
            rust_files = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "examples/agent").rglob("*.rs"))
            commands = {
                "format": ["rustfmt", "--check", "--edition", "2024", *rust_files],
                "exampleTests": [args.cargo, "test", *flags, "--example", "agent_control_app"],
                "clippy": [args.cargo, "clippy", *flags, *targets, "--", "-D", "warnings"],
                "build": [args.cargo, "build", *flags, *targets],
            }
            for name, command in commands.items():
                print(json.dumps({"check": name, "log": str(output / (name + ".log"))}), flush=True)
                with (output / (name + ".log")).open("w") as log:
                    subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                report["checks"][name] = {"command": command, "exitCode": 0}
            report["buildVerified"] = True
        report["cargoVersion"] = subprocess.check_output([args.cargo, "--version"], text=True).strip()
        report["rustcVersion"] = subprocess.check_output([os.environ.get("RUSTC", "rustc"), "--version"], text=True).strip()
        report["binarySha256"] = {
            name: hashlib.sha256((examples / (name + suffix)).read_bytes()).hexdigest()
            for name in ("agent_control_app", "agent_control_test")
        }
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", 15702)) == 0:
                raise RuntimeError("BRP port 15702 is occupied; no existing process was changed")
        with (output / "app.log").open("w") as app_log:
            server = subprocess.Popen([str(examples / ("agent_control_app" + suffix))],
                                      cwd=ROOT, stdout=app_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + min(args.timeout, 60)
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f"App exited before startup: {server.returncode}")
                try:
                    initial = rpc("agent.state")
                    break
                except (OSError, ValueError, RuntimeError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("App did not expose agent.state before timeout")
                    time.sleep(0.1)
            if initial["count"] != 0 or initial["revision"] != 0:
                raise RuntimeError("The demo did not start from its declared initial state")
            updated = rpc("agent.act", {"action": "increment", "expectedRevision": 0})
            if updated["count"] != 1 or updated["revision"] != 1:
                raise RuntimeError("The accepted action did not advance state exactly once")
            rejected = []
            for params in ({"action": "increment", "expectedRevision": 0},
                           {"action": "unknown", "expectedRevision": 1},
                           {"action": "increment", "expectedRevision": 1, "extra": True}):
                rejected.append(rpc("agent.act", params, expected_error=-32602))
                if rpc("agent.state") != updated:
                    raise RuntimeError("A rejected action changed state")
            with (output / "client.log").open("w") as client_log:
                subprocess.run([str(examples / ("agent_control_test" + suffix))], cwd=output,
                               stdout=client_log, stderr=subprocess.STDOUT,
                               timeout=args.timeout, check=True)
            server.wait(timeout=10)
            if server.returncode != 0:
                raise RuntimeError(f"App exited with {server.returncode}")
        ui_report = json.loads((output / "agent-report.json").read_text())
        if not ui_report["ok"] or ui_report["beforeClick"] != updated:
            raise RuntimeError("UI verification did not start from the accepted command state")
        if ui_report["afterClick"]["count"] != 2 or ui_report["afterClick"]["revision"] != 2:
            raise RuntimeError("The real UI click did not advance state exactly once")
        image = output / "screenshot.png"
        if image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("The captured screenshot is not a PNG")
        if source_hashes(ROOT) != report["sourceSha256"]:
            raise RuntimeError("Sources changed during verification; run again with stable inputs")
        report["screenshotSha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
        report.update(ok=True, initial=initial, afterCommand=updated,
                      rejectedActions=rejected, ui=ui_report)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"ok": report["ok"], "evidence": str(output), "error": report.get("error")}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
