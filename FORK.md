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

## Same-frame touch backport

The fork backports [upstream PR #26077](https://github.com/bevyengine/bevy/pull/26077)
by @mirsella, commit `6ef56e780ff11e802359b495067db8546a5f03fe`.
The cherry-pick preserves the original author and commit reference.
`crates/bevy_picking/src/events.rs` is byte-identical to that source; no adaptation
was needed. The recorded upstream engine base remains unchanged.

A touch can start and end in one update. Its release now uses the current hover
hits when the same pointer and button had an unmatched press in that update.
Other releases retain previous-frame targeting. Four regression cases cover
same-frame and split-frame touch with fresh and stale hover maps. The existing
button cleanup and activation tests also remain required.

Focused engine checks cover `bevy_picking` and `bevy_ui_widgets`. Native agent-loop
and game/device evidence remain separate requirements before changing a game pin.

## Upstream compatibility policy

Preserve Bevy's internal names, module layout, and public APIs. Prefer separate
tools, downstream examples, and plugins for new development capabilities. The
current engine-internal differences are the button cleanup fix and the same-frame
touch backport, with their regression tests.

Our examples live under `examples/agent/`; both original remote example files are
preserved byte-for-byte from the engine base. Cargo only adds their downstream
example targets. Keep core patches isolated from tooling and documentation commits.

Evaluate an upstream revision on a task branch, run affected regression tests and
the agent loop, then pin the verified revision. Check Teratorn's compatibility before
changing its engine dependency. Mark a downstream fix as superseded after verifying
an equivalent upstream implementation. Preserve the fixed behavior and published
history rather than undoing the old fix commit.

## Game integration

Teratorn currently pins the verified fork revision
`728db979c0ba0ef125ffa5c804e4cb70e476279b`. This backport does not change that
application pin. A later game update needs an exact tested engine revision and
regression evidence against the existing C# reference.

## Agent command loop

The downstream examples share a counter transition between `agent.act` and real UI
input. `agent.state` exposes revisions and legal actions. Rejected commands must
preserve state. `tools/agent-loop.py` builds and exercises the examples and writes
structured results, process logs, and a native screenshot.

The toolkit README describes the downstream workflow. The original Bevy README is
preserved in `UPSTREAM_README.md`. A new product name has not been selected; engine
package identifiers are kept unchanged to limit update and dependency churn.

## Contribution workflow

The exact base and active patch file hashes are tracked in
`docs/maintenance/policy.json`. See `docs/maintenance/README.md` for selective
upstream intake, adaptation records, replacement tests, promotion, and rollback.
Use PRs with the `downstream-ready` check for downstream development. Runtime
verification receipts are tied to their source inputs and screenshot contents.

AI-assisted implementation, tests, and prose are allowed for this fork. Contributors
remain responsible for review and verification. See `AGENTS.md` for the working
instructions. Upstream Bevy has its own contribution and AI policies, which apply
when submitting work there.
