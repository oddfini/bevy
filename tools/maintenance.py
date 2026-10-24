#!/usr/bin/env python3
"""Check fork compatibility, bind runtime evidence, and inspect upstream candidates."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
POLICY = "docs/maintenance/policy.json"
UPSTREAM = "https://github.com/bevyengine/bevy"
PROTECTED = (
    "LICENSE-MIT", "LICENSE-APACHE", "CREDITS.md",
    "examples/remote/app_under_test.rs", "examples/remote/integration_test.rs",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def revision(root, value):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", value)), "Use a full 40-character commit SHA")
    git(root, "cat-file", "-e", value + "^{commit}")
    return value


def digest(path):
    require(path.is_file() and not path.is_symlink(), f"Expected a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy_at(root):
    policy = json.loads((root / POLICY).read_text())
    require(policy["schema"] == 1 and policy["upstream"] == UPSTREAM, "Invalid maintenance policy")
    revision(root, policy["base"])
    return policy


def engine_changes(root, base):
    tracked = git(root, "diff", "--name-only", "-z", base, "--", "crates", "src")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "crates", "src")
    return set((tracked + untracked).decode().strip("\0").split("\0")) - {""}


def package_name(manifest):
    section = re.search(r"(?ms)^\[package\]\s*\n(.*?)(?=^\[|\Z)", manifest)
    require(section is not None, "Expected an upstream [package] section")
    name = re.search(r'^name\s*=\s*"([a-zA-Z0-9_-]+)"\s*$', section[1], re.MULTILINE)
    require(name is not None, "Expected an upstream literal package name")
    return name[1]


def example_suffix(root, examples):
    suffix = "\n# Downstream examples. Keep upstream examples and engine identifiers unchanged.\n"
    for index, example in enumerate(examples):
        path = PurePosixPath(example["path"])
        require(example["name"].startswith("agent_") and path.parts[:2] == ("examples", "agent") and ".." not in path.parts, "Keep downstream examples under examples/agent/")
        digest(root / path)
        suffix += ("\n" if index else "") + "[[example]]\n"
        for key in ("name", "path", "required-features"):
            suffix += f"{key} = {json.dumps(example[key])}\n"
    return suffix


def check_compatibility(root):
    policy = policy_at(root)
    base = policy["base"]
    git(root, "merge-base", "--is-ancestor", base, "HEAD")
    expected = {}
    packages = set()
    for patch in policy["patches"]:
        require(patch["reason"].strip() and patch["regression"].strip(), "Patch needs a reason and regression test")
        revision(root, patch["source"])
        require(patch["origin"] in ("downstream", "upstream"), "Invalid patch origin")
        require(patch["status"] in ("active", "superseded"), "Invalid patch status")
        if patch["status"] == "superseded":
            require(not patch["files"], "Superseded patches must have no remaining file overrides")
            continue
        require(patch["files"], "Active patch must list its file hashes")
        for name, sha in patch["files"].items():
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and path.parts[0] in ("crates", "src"), "Invalid engine patch path")
            require(name not in expected, f"Combine overlapping patches in one record: {name}")
            require(sha is None or bool(re.fullmatch(r"[0-9a-f]{64}", sha)), "Invalid file hash")
            expected[name] = sha
            if path.parts[0] == "crates":
                packages.add(path.parts[1])
            else:
                packages.add("bevy")
            if not patch.get("adaptation") and sha is not None:
                source = git(root, "show", f"{patch['source']}:{name}")
                require(hashlib.sha256(source).hexdigest() == sha, f"Document the adaptation from the source commit: {name}")
    require(engine_changes(root, base) == set(expected), "Engine changes differ from recorded patches")
    for name, sha in expected.items():
        actual = digest(root / name) if (root / name).exists() else None
        require(actual == sha, f"Engine patch changed without a matching record: {name}")
    require(packages <= set(policy["testPackages"]) and policy["testPackages"], "testPackages must cover every active engine patch")
    for package in policy["testPackages"]:
        require(bool(re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_-]*", package)), "Invalid Cargo package name")
        manifest = "Cargo.toml" if package == "bevy" else f"crates/{package}/Cargo.toml"
        current = (root / manifest).read_text()
        original = git(root, "show", f"{base}:{manifest}").decode()
        require(package_name(current) == package_name(original) == package, "Preserve upstream package names")
    for name in PROTECTED:
        require((root / name).read_bytes() == git(root, "show", f"{base}:{name}"), f"Upstream file changed: {name}")
    example_changes = git(root, "diff", "--name-only", base, "--", "examples").decode().splitlines()
    require(all(name.startswith("examples/agent/") for name in example_changes), "Preserve original upstream examples")
    require((root / "UPSTREAM_README.md").read_bytes() == git(root, "show", f"{base}:README.md"), "Refresh the preserved upstream README from the recorded base")
    original = git(root, "show", f"{base}:Cargo.toml").decode()
    current = (root / "Cargo.toml").read_text()
    require(current == original + example_suffix(root, policy["examples"]), "Only append recorded example targets to the unchanged upstream Cargo manifest")
    workflows = git(root, "diff", "--name-only", base, "--", ".github/workflows").decode().splitlines()
    require(set(workflows) <= {".github/workflows/downstream.yml"}, "Preserve original upstream workflow files")
    return policy


def test_packages(root, policy, since=None):
    packages = set(policy["testPackages"])
    if since:
        for name in engine_changes(root, revision(root, since)):
            path = PurePosixPath(name)
            if path.parts[0] == "src":
                packages.add("bevy")
            else:
                manifest = root / "crates" / path.parts[1] / "Cargo.toml"
                require(manifest.is_file(), f"Removed or restructured crate needs an explicit replacement test plan: {name}")
                packages.add(package_name(manifest.read_text()))
    return sorted(packages)


def source_hashes(root):
    policy = policy_at(root)
    names = {POLICY, "Cargo.toml", "Cargo.lock", "tools/agent-loop.py", "tools/maintenance.py"}
    names.update(str(path.relative_to(root)) for path in (root / "examples/agent").rglob("*") if path.is_file())
    for patch in policy["patches"]:
        names.update(name for name, sha in patch["files"].items() if sha is not None)
    return {name: digest(root / name) for name in sorted(names)}


def check_evidence(root, report, image):
    require(report["schema"] == 2 and report["ok"] is True, "Runtime run did not pass")
    require(report["buildVerified"] is True, "Run the driver with its Cargo build enabled")
    require(set(report["checks"]) == {"format", "exampleTests", "clippy", "build"} and all(check["exitCode"] == 0 and check["command"] for check in report["checks"].values()), "Required local checks did not pass")
    require(report["sourceSha256"] == source_hashes(root), "Runtime evidence is stale; rerun the driver for the current sources")
    require(report["screenshotSha256"] == digest(image), "Screenshot does not match the runtime receipt")
    require(report["platform"] and report["verifiedDate"] and report["cargoVersion"] and report["rustcVersion"], "Runtime environment is missing")
    binaries = report["binarySha256"]
    require(set(binaries) == {"agent_control_app", "agent_control_test"} and all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in binaries.values()), "Runtime binary hashes are missing")
    def state(count):
        return {"schema": 1, "count": count, "revision": count, "limit": 10, "legalActions": ["increment"]}
    require(report["initial"] == state(0) and report["afterCommand"] == state(1), "Command transition was not verified")
    require(len(report["rejectedActions"]) == 3 and all(error["code"] == -32602 for error in report["rejectedActions"]), "Rejected-action checks are missing")
    ui = report["ui"]
    require(ui["ok"] is True and ui["beforeClick"] == state(1) and ui["afterClick"] == state(2), "Pointer transition was not verified")
    header = image.read_bytes()[:24]
    require(header[:8] == b"\x89PNG\r\n\x1a\n" and len(header) == 24, "Screenshot is not a PNG")
    require(struct.unpack(">II", header[16:24]) == (ui["screenshot"]["width"], ui["screenshot"]["height"]), "Screenshot dimensions differ from the receipt")


def upstream_plan(root, commit, mode):
    policy = policy_at(root)
    revision(root, commit)
    parents = git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()[1:]
    require(mode == "baseline" or len(parents) == 1, "Inspect merge commits as a baseline update")
    start = policy["base"] if mode == "baseline" else parents[0]
    paths = git(root, "diff", "--name-only", start, commit).decode().splitlines()
    patched = {name for patch in policy["patches"] if patch["status"] == "active" for name in patch["files"]}
    return {"mode": mode, "source": commit, "url": f"{UPSTREAM}/commit/{commit}",
            "subject": git(root, "show", "-s", "--format=%s", commit).decode().strip(),
            "comparisonBase": start, "changedFileCount": len(paths),
            "patchOverlaps": sorted(patched.intersection(paths)),
            "stat": git(root, "diff", "--stat", start, commit).decode(),
            "next": "Apply on a task branch, record adaptations, run affected tests and native verification. This command made no changes."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    engine = sub.add_parser("test-engine")
    engine.add_argument("--since", help="Also test every engine package changed since this exact commit")
    record = sub.add_parser("record")
    record.add_argument("directory", type=Path)
    plan = sub.add_parser("plan")
    plan.add_argument("commit")
    plan.add_argument("--mode", choices=("backport", "baseline"), default="backport")
    changed = sub.add_parser("needs-engine")
    changed.add_argument("base")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            print(json.dumps(upstream_plan(ROOT, args.commit, args.mode), indent=2))
        elif args.command == "needs-engine":
            print("true" if engine_changes(ROOT, revision(ROOT, args.base)) else "false")
        elif args.command == "test-engine":
            policy = check_compatibility(ROOT)
            for package in test_packages(ROOT, policy, args.since):
                for command in (["cargo", "fmt", "-p", package, "--check"],
                                ["cargo", "test", "-p", package, "--locked"],
                                ["cargo", "clippy", "-p", package, "--all-targets", "--locked", "--", "-D", "warnings"]):
                    print(json.dumps({"run": command}), flush=True)
                    subprocess.run(command, cwd=ROOT, check=True)
        else:
            policy = check_compatibility(ROOT)
            directory = args.directory if args.command == "record" else ROOT / "docs/agent-loop"
            report_name = "summary.json" if args.command == "record" else "verification.json"
            report = json.loads((directory / report_name).read_text())
            check_evidence(ROOT, report, directory / "screenshot.png")
            if args.command == "record":
                target = ROOT / "docs/agent-loop"
                target.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(directory / report_name, target / "verification.json")
                shutil.copyfile(directory / "screenshot.png", target / "screenshot.png")
            print(json.dumps({"ok": True, "base": policy["base"], "enginePatches": len(policy["patches"])}))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
