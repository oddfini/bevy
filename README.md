# AI-assisted game development and maintenance

An experimental Rust toolkit for agents that build, run, inspect, and verify games.
This fork uses Bevy as its runtime. It keeps developer-facing GUI work small and
prioritizes commands, structured state, repeatable runs, and evidence.

This is an early prototype. The product name is not yet selected. The GitHub
repository and internal Rust package names currently remain unchanged.

## First working slice

The remote example is a small counter with one shared transition for an agent
command and a real UI click. It is a test of the development workflow, not a new
game engine or a completed Teratorn migration.

- `agent.state` returns the current revision, counter, and legal actions.
- `agent.act` checks the action and expected revision before changing state.
- Unknown, malformed, stale, and over-limit actions leave state unchanged.
- The client finds the real button, injects pointer input, verifies the resulting
  domain state, and captures the rendered window.
- A command-line runner saves JSON results, a screenshot, and process logs.

The example reuses the existing Bevy Remote Protocol. It adds no editor GUI or
separate MCP server. Developer automation is local to this example; it is not a
production multiplayer API.

Verified on macOS on 2026-10-25: seven focused unit tests, rejected-command checks,
real pointer input, domain-state assertions, screenshot capture, and normal app
exit passed. Missing binaries and a non-finite timeout correctly failed. Evidence:
[JSON result](docs/agent-loop/verification.json) and
[rendered screenshot](docs/agent-loop/screenshot.png).

The local unoptimized example build emitted a large-unwind-section linker warning.
These checks do not establish release performance or mobile behavior.

## Run the verification

Rust, Python 3, a desktop session, and the platform dependencies for Bevy are
required. On shared machines, reserve the desktop through the local QA process
before starting a windowed run.

This fork tracks `Cargo.lock` so agents use the verified dependency resolution.

```sh
python3 tools/agent-loop.py --output /tmp/agent-loop-first-run
```

The output directory must be new. The runner builds two examples, starts the app,
executes accepted and rejected actions, runs the pointer/capture client, and stops
the app. It exits nonzero on a failed check and writes `summary.json`.

Use `--offline` with a populated Cargo cache. The driver runs formatting, focused
tests, Clippy, and a locked build before the native run. `CARGO_TARGET_DIR` selects
the binary directory. `--skip-build` produces diagnostic evidence that the
maintenance gate will reject for publication as a verified result.

Validate and save a successful run, then check the fork:

```sh
python3 -B tools/maintenance.py record /tmp/agent-loop-first-run
python3 -B tools/maintenance.py check
```

Focused domain tests:

```sh
cargo test --example agent_control_app --no-default-features \
  --features ui,bevy_remote_client,bevy_feathers --locked
```

## Direction

Use Teratorn as the first real game to validate the workflow. Keep the game rules,
player-facing UI, accessibility, and platform integration in the game project.
Add development capabilities when a concrete workflow needs them. Data-driven
layout editing and direct Teratorn integration are future work.

Preserve Bevy's internal names, public APIs, module layout, and original examples.
Our examples live under `examples/agent/`. New development features belong in tools
or plugins using public APIs. Keep necessary core bug fixes small and isolated.
Test upstream updates on a task branch before changing a verified engine revision;
see [the compatibility policy](FORK.md#upstream-compatibility-policy).

## Origin and license

Based on [Bevy](https://github.com/bevyengine/bevy), with a small downstream patch
set. This is an independent experiment maintained in `yongjip/bevy`.

The engine source retains its MIT OR Apache-2.0 licensing, original copyright
notices, and applicable third-party terms. See [LICENSE-MIT](LICENSE-MIT),
[LICENSE-APACHE](LICENSE-APACHE), and [CREDITS.md](CREDITS.md). The original upstream
README is preserved in [UPSTREAM_README.md](UPSTREAM_README.md).

For fork scope and contribution rules, read [FORK.md](FORK.md), [AGENTS.md](AGENTS.md),
and [CONTRIBUTING.md](CONTRIBUTING.md). For automated checks and selective upstream
updates, read [the maintenance procedure](docs/maintenance/README.md).
The upstream project's contribution policies
apply when submitting work upstream.
