# Contributing to this fork

For work submitted to `oddfini/bevy`, read [FORK.md](FORK.md) and
[AGENTS.md](AGENTS.md). AI-assisted code, tests, and prose are allowed in this
fork. Keep changes focused and include verification evidence.

## Make a change

1. Read the current code and reproduce the problem. Record the expected result.
2. Create a `codex/` task branch. Keep one behavior change in each PR. Separate
   upstream backports, engine fixes, and development features.
3. Reuse existing APIs when they fit. Independent engine features and API changes
   are welcome with a concrete requirement, affected-consumer analysis, regressions,
   and recovery steps. Keep game rules and private assets in the game repo.
   Record internal changes in `docs/maintenance/policy.json`. Current package-name,
   provenance, and structural guards still apply; change a guard only through its
   own reviewed change with negative regressions.
4. Run the fast checks below. For engine changes, run `test-engine` against the
   PR's exact base commit. For runtime changes, run and record the native driver.
5. Review the diff. Check rejected commands, existing behavior, dependencies,
   error handling, and test failures. Report any platform that was not tested.
6. Open a PR against `oddfini/bevy:codex/teratorn-ai`. Use the fork's PR template.
   Merge after `downstream-ready` passes and review discussions are resolved.

AI may write and maintain code, tests, commit messages, and PR prose in this fork.
The owner does not need to manually rewrite each contribution. State how AI was
used and who implemented and reviewed the change. Do not claim an independent review when the implementing agent reviewed its
own code. A passing receipt records an observed run; it is not a trusted attestation
against a contributor who changes both the code and its evidence.

There is no changed-line quota. Remove unrelated edits and abstractions that have
no current caller. Split a PR when its changes need separate reasons or rollback.
Do not suppress a failing assertion, weaken a guard, or change a snapshot just to
make a check pass. Changes to these checks need a failing-case regression test.

## Test commands

Use Python 3.9 or later and Rust 1.99.1 with rustfmt and Clippy. Keep `Cargo.lock`
tracked. Dependency changes belong in a separate, explained update.

Fast checks:

```sh
python3 -B -m unittest discover -s tools -p 'test_*.py' -v
python3 -B tools/maintenance.py check
rustfmt --check --edition 2024 examples/agent/*.rs
rustc --edition 2024 --test examples/agent/command_model.rs -o /tmp/command-model-tests
/tmp/command-model-tests
git diff --check
```

For an engine change, replace `FULL_BASE_SHA` with the PR's 40-character base SHA:

```sh
python3 -B tools/maintenance.py test-engine --since FULL_BASE_SHA
```

This runs format, unit and documentation tests, and Clippy with warnings treated as
errors. It covers every changed engine package plus the recorded patch packages.
A removed or restructured crate requires an explicit replacement test plan.

For runtime source, manifest, lockfile, driver, or patch-policy changes:

```sh
python3 -B tools/agent-loop.py --output /tmp/agent-loop-new-run
python3 -B tools/maintenance.py record /tmp/agent-loop-new-run
python3 -B tools/maintenance.py check
```

Reserve a shared desktop before the native run. The driver runs formatting, seven
example/model unit tests, Clippy, a locked build, accepted/rejected remote commands,
real pointer input, and screenshot capture. It writes logs and a JSON receipt.
`record` validates the receipt before copying the result and screenshot into docs.
It rejects stale inputs, failed checks, skipped builds, and a mismatched screenshot.

CI repeats the fast checks on Ubuntu 24.04 with Rust 1.99.1. Engine, dependency,
and maintenance pipeline changes also run engine package checks.
Native macOS evidence remains a local run. Rendering, input,
and platform changes need their own relevant runtime checks. This counter example
does not establish Teratorn, mobile, performance, or whole-engine compatibility.

Reuse passing checks while their code, configuration, toolchain, and evidence
inputs remain valid. Respect the task's cost limits and allowed execution targets.
A required hosted status cannot be replaced with an invented local success or a
branch-protection bypass. Report a blocked check and keep the PR unmerged.

## Adopt upstream work

Follow [the upstream intake procedure](docs/maintenance/README.md). Use an exact
commit, record its reason and adaptations, preserve local regression behavior, and
keep the previous verified revision until the candidate passes. Never sync the
upstream default branch directly into the verified downstream branch.

## Contributing upstream

If you'd like to help build Bevy, start by reading this
[introduction](https://bevy.org/learn/contribute/introduction), as well as our [policy regarding AI usage](https://bevy.org/learn/contribute/policies/ai/). Thanks for contributing!
