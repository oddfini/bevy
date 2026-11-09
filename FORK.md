# Oddfini's independent Bevy fork

This is an independently maintained engine fork in `oddfini/bevy`. It is separate from
the official [Bevy project](https://github.com/bevyengine/bevy).

The owner selected this direction on 2026-10-30: reuse Bevy as the starting point,
then choose our own roadmap, engine designs, and contribution policy. AI may implement
changes and prepare commits and PRs. Actual review and verification govern adoption.
Official upstream acceptance is not required for our development decisions.

Teratorn is the first real game used to validate the engine. Shared development
tools and engine features belong here; game rules, private assets, accounts, and
service credentials stay in their game projects. Grow from working subsystems and
replace modules when a demonstrated limit justifies the work. A complete engine
rewrite is not the current plan. See [the roadmap](docs/independent-engine-roadmap.md).

## Branches and license

- `main`: existing upstream-derived reference branch.
- `codex/teratorn-ai`: current default and verified integration branch, despite its historical name.
- Initial engine base: `3a796854abd94144c6e08c4112e5bd9229392b37`.

This decision does not rename branches, change package identifiers, or update any
game's engine pin. Branch transitions require a separate reviewed change.

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

## Engine evolution policy

The engine roadmap is independent. We may accept a different internal design or
public API when it solves a concrete requirement and passes the relevant checks.
Compatibility remains useful where it reduces maintenance cost; it does not give
upstream a veto over our features. Keep each change reviewable, record its affected
consumers, and provide migration and recovery steps when behavior or APIs change.

Current machine protections still preserve package names, original examples,
upstream provenance, the root Cargo prefix, and inherited workflow files. New
protected-structure changes need an explicit guard and regression update. This
document does not make an unrecorded engine edit pass. The currently recorded
engine differences remain the button cleanup fix and same-frame touch backport.

Our examples live under `examples/agent/`; both original remote example files are
preserved byte-for-byte from the engine base. Cargo only adds their downstream
example targets. Keep core patches isolated from tooling and documentation commits.

Select upstream revisions when they benefit our roadmap. Evaluate each exact revision
on a task branch, run affected regression tests and required native checks, then
promote the verified revision. Check Teratorn's compatibility before
changing its engine dependency. Mark a downstream fix as superseded after verifying
an equivalent upstream implementation. Preserve the fixed behavior and published
history rather than undoing the old fix commit.

## Game integration

The original separate Teratorn prototype used the tested revision
`728db979c0ba0ef125ffa5c804e4cb70e476279b`; this is a historical baseline.
The game's own `clients/bevy/engine.json`, manifest, and lockfile record its current
pin. Its game rules, assets, and C# comparison artifacts remain there.
Engine updates require a new tested game pin and
game regression evidence. Tool-only updates do not require changing the engine pin.
Publishing an engine change does not by itself change an application pin or authorize a release.

## Agent command loop

The downstream examples share a counter transition between `agent.act` and real UI
input. `agent.state` exposes revisions and legal actions. Rejected commands must
preserve state. `tools/agent-loop.py` builds and exercises the examples and writes
structured results, process logs, and a native screenshot.

`tools/brp_client.py` supplies the shared local HTTP client for the counter runner
and real-game scenario tools. It validates the protocol and request ID before
returning a result. Game-specific behavior stays outside the engine repository.

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

## Bevy 0.20.1 fixes on the existing base (2026-11-10)

The owner selected selective fixes, retaining our development base and existing
fork changes. This is not a switch to the stable release tree. Package versions
stay `0.20.0-dev`; do not describe this fork as the unmodified 0.20.1 release.
The release commit is `a0577b5c6a7b208719dd761c5c6a7a539e472a97`.
See [the exact intake record](docs/maintenance/releases/0.20.1.json).

Seven of the release's nine functional fixes already have identical patch IDs
in the retained history. They are not applied or tested as new changes again.
The release packaging/version bump is omitted because this is a selective intake.
Two missing fixes retain their original authors and `cherry-pick -x` provenance:

- `334ea201fa60035915f4b7f21f00091d4600fc8a`: prevent generated BSN struct
  defaults from producing false `clippy::needless_update` diagnostics. Its
  upstream regression produced two diagnostics before the generator fix.
  The allowance is scoped to generated construction; crate-wide Clippy flags
  are not relaxed.
- `1c1a02a9316f7844ac003bdb587c1d447c7dc13a`: draw fog volumes that reach the
  near plane, using a clipped ray interval for perspective and orthographic
  projections. Retain the upstream rotated orthographic negative regression.

The existing disabled-button cleanup and same-frame touch patches remain active.
No dependencies, package names, engine base, game assets or game pins change here.
Policy package checks cover `bevy_pbr`, `bevy_scene`, `bevy_picking` and
`bevy_ui_widgets`. The nested `bevy_scene_macros` package is also checked explicitly:
its manifest is inside `crates/bevy_scene/macros/`, outside the selector's direct
`crates/<package>` layout. The original protection/selection rules stay intact.

Native agent-loop proof covers the shared counter's input, commands and capture.
It does not qualify the fog's rendered image, a physical phone, Teratorn gameplay,
or performance. Game adoption is separate and keeps the old verified pin until
an engine PR has actually met its required checks. Hosted checks are not replaced
with invented local statuses. Existing CI/spending restrictions still apply.

Local validation on macOS with Rust 1.99.1 passed 227 engine unit tests, 42
engine documentation tests and 42 maintenance-tool tests. The upstream examples
retain 23 ignored documentation cases; these were not reported as passes.
The native agent example passed its seven tests, Clippy and locked build, then
verified accepted/rejected commands, an actual UI click, a source-bound screenshot
and clean process exit. These results do not replace the required hosted status.
