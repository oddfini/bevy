# Oddfini's independent Bevy fork

An independently maintained Rust engine fork for AI-assisted game development.
Bevy supplies the starting runtime; Oddfini chooses the roadmap and accepts
verified engine and tooling changes under its own contribution policy.
We prioritize commands, structured state, repeatable runs, and evidence.

This is an early prototype. The product name is not yet selected. The GitHub
repository and internal Rust package names currently remain unchanged.

## First working slice

The remote example is a small counter with one shared transition for an agent
command and a real UI click. It tests the development workflow. This example does
not establish a completed engine, Teratorn migration, or mobile qualification.

- `agent.state` returns the current revision, counter, and legal actions.
- `agent.act` checks the action and expected revision before changing state.
- Unknown, malformed, stale, and over-limit actions leave state unchanged.
- The client finds the real button, injects pointer input, verifies the resulting
  domain state, and captures the rendered window.
- A command-line runner saves JSON results, a screenshot, and process logs.

The example reuses the existing Bevy Remote Protocol. It adds no editor GUI or
separate MCP server. Developer automation is local to this example; it is not a
production multiplayer API.

## Inspect a running local app

The standard-library client in `tools/brp_client.py` can call existing Bevy Remote
Protocol methods and an app's registered methods. Start the counter example, then:

```sh
python3 -B tools/brp_client.py agent.state
python3 -B tools/brp_client.py agent.act --params '{"action":"increment","expectedRevision":0}'
```

Use `--url http://127.0.0.1:PORT/` for another local app. This development client
accepts literal loopback HTTP addresses. It disables proxies and redirects,
checks response IDs and JSON-RPC structure, bounds response size, and never retries
a request automatically. After an action timeout, read the state before deciding
whether another action is needed. An action can complete before its reply arrives.

Keep game actions, private state projections, and game-specific replay comparisons
in the game project. They can use this client without changing Bevy internals.
Run Python with `-B` when importing these modules directly. A local `__pycache__`
directory under `tools/` conflicts with the upstream Rust workspace glob. The
counter entrypoint disables local bytecode before importing its helpers.

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
python3 -B tools/agent-loop.py --output /tmp/agent-loop-first-run
```

The output directory must be new. The runner builds two examples, starts the app,
executes accepted and rejected actions, runs the pointer/capture client, and stops
the app. It exits nonzero on a failed check and writes `summary.json`.

Startup polling rejects `agent.state` replies that return at or after its deadline
and starts no further request once the budget is exhausted. Socket waits and retry
sleeps use the remaining startup budget; the shared client timeout is restored
after polling. Socket timeouts apply per I/O wait: slowly streamed response bodies
still have no absolute total HTTP wall-clock cancellation.

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

Reuse working engine subsystems and add tools or plugins where they fit. Internal
designs and public APIs may evolve for demonstrated requirements, with regression,
consumer-impact, and recovery evidence. Current machine guards and original source
attribution remain enforced. Our examples live under `examples/agent/`.
Select upstream updates on task branches before changing a verified engine revision;
see [the engine policy](FORK.md#engine-evolution-policy) and
[independent roadmap](docs/independent-engine-roadmap.md).

## Origin and license

Based on [Bevy](https://github.com/bevyengine/bevy). This independent fork is
maintained in `oddfini/bevy`; it is not an official Bevy distribution.

The engine source retains its MIT OR Apache-2.0 licensing, original copyright
notices, and applicable third-party terms. See [LICENSE-MIT](LICENSE-MIT),
[LICENSE-APACHE](LICENSE-APACHE), and [CREDITS.md](CREDITS.md). The original upstream
README is preserved in [UPSTREAM_README.md](UPSTREAM_README.md).

For fork scope and contribution rules, read [FORK.md](FORK.md), [AGENTS.md](AGENTS.md),
and [CONTRIBUTING.md](CONTRIBUTING.md). For automated checks and selective upstream
updates, read [the maintenance procedure](docs/maintenance/README.md).
The upstream project's contribution policies
apply when submitting work upstream.
