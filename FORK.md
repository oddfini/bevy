# Teratorn development fork

This is an experimental fork maintained in `yongjip/bevy`. It is separate from
the official [Bevy project](https://github.com/bevyengine/bevy).

The goal is an AI-assisted game development and maintenance toolkit, using Bevy as
its runtime and Teratorn as its first real game. Keep a small downstream patch set
so upstream updates remain reviewable. Development tools and engine changes belong
here; game rules and private game assets do not.

## Branches and license

- `main`: upstream-derived reference branch. Update it separately from experiments.
- `codex/teratorn-ai`: initial downstream experiment.
- Initial engine base: `3a796854abd94144c6e08c4112e5bd9229392b37`.

The original MIT OR Apache-2.0 licensing and third-party terms remain in place.
See `LICENSE-MIT`, `LICENSE-APACHE`, the original README, and individual crates.

## Initial patch

When a button is disabled during a pointer press, release, drag end, or cancellation
can leave `Pressed` attached. The cleanup handlers now remove `Pressed` regardless
of whether the button is disabled. Activation guards stay in place.

Six regression tests cover the three cleanup events, enabled-button cleanup,
disabled click activation, and disabled activate-on-press behavior.

On 2026-10-25, the patched `bevy_ui_widgets` crate passed 132 unit tests and four
documentation tests on macOS. Formatting passed. Clippy passed for all targets of
this crate with warnings treated as errors. This is a focused engine check, not a
whole-workspace or mobile-runtime validation.

## Game integration

The existing Teratorn Bevy game prototype still uses released Bevy 0.20.0. Creating
this fork does not switch that application's engine dependency. Pin any future
integration to an exact tested revision and compare its game results with the
existing C# reference.

## Agent command loop

The remote examples share a counter transition between `agent.act` and real UI
input. `agent.state` exposes revisions and legal actions. Rejected commands must
preserve state. `tools/agent-loop.py` builds and exercises the examples and writes
structured results, process logs, and a native screenshot.

The toolkit README describes the downstream workflow. The original Bevy README is
preserved in `UPSTREAM_README.md`. A new product name has not been selected; engine
package identifiers are kept unchanged to limit update and dependency churn.

## Contribution workflow

AI-assisted implementation, tests, and prose are allowed for this fork. Contributors
remain responsible for review and verification. See `AGENTS.md` for the working
instructions. Upstream Bevy has its own contribution and AI policies, which apply
when submitting work there.
