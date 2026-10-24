# Agent guide for yongjip/bevy

This is an experimental downstream fork of Bevy for Teratorn development.
Read `FORK.md` before changing engine code. Preserve upstream history, licenses,
copyright notices, and third-party credits.

## AI-assisted work in this fork

- AI assistance may be used for code, tests, documentation, issue text, and PR
  text submitted to `yongjip/bevy`. Follow the user's authorization for external
  actions. This permission does not itself authorize publishing or merging.
- Review generated changes. Report what changed, what was tested, and remaining
  limits. Never claim a build, device run, or test that was not observed.
- Keep engine patches small. Keep Teratorn rules, content, credentials, and private
  game assets outside this engine repository.
- Reuse Bevy systems before adding abstractions. Do not turn a game-specific
  adapter into a general framework without a concrete need.

## Verification

For the current button patch, run:

```sh
cargo fmt -p bevy_ui_widgets --check
cargo test -p bevy_ui_widgets --locked
cargo clippy -p bevy_ui_widgets --all-targets --locked -- -D warnings
```

Use matching checks for other changed crates. Changes to rendering, input, or
mobile behavior also need relevant runtime evidence. Headless tests do not prove
phone behavior. Reuse passing checks while their inputs are unchanged.

## Upstream boundary

The upstream Bevy contribution and AI policies still apply to submissions and
communication in `bevyengine/bevy` and its communities. This fork's permission to
use AI-generated prose does not apply there. Obtain the user's instruction before
opening an upstream issue or PR; prepare the evidence first.

Use `codex/` task branches. Push only to the user's fork unless another target
was explicitly authorized. Do not push to or rewrite upstream branches.
