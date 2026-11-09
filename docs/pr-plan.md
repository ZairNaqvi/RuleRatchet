# RuleRatchet: PR plan

One concern per PR, each on its own branch from `main`, none stacked. Each
lists what it changes, how it is verified, and what "done" means. Sizes are
for one person. The initial commit (CLI, two hooks, five tests, CI) is the
baseline; the plan takes it to a v1.0 someone else could install and trust.

| # | Branch | Concern | Hours |
|---|---|---|---|
| 1 | `fix-second-host-transcript` | Capture reads the second host's transcript format | 2 |
| 2 | `feat-install` | `ruleratchet install <host>` registers the stop hook | 2 |
| 3 | `feat-report-flags` | `--since`, `--min-days`, `--out` on report | 1 |
| 4 | `feat-draft` | `ruleratchet draft <n>` prints a paste-ready block | 1 |
| 5 | `feat-health` | `ruleratchet health <log>`: did the rules hold | 2 |
| 6 | `test-fixtures` | Recorded, redacted stop events from both hosts as fixtures | 1 |
| 7 | `chore-release` | Version, changelog, tagged release, install from tag | 1 |
| 8 | `docs-public` | Stranger read-through, public flip, branch protection | 1 |

## PR 1: capture reads the second host's transcript

Today `hooks/capture.sh` falls back to the transcript only in the first host's
shape (`type: assistant`, `message.content[].text`). The second host's rollout
file is `{type, payload, timestamp}` lines with `event_msg` payloads of type
`agent_message` carrying `message` or `text`. Add that branch to the fallback.
Verify: a fixture rollout with one `[LEARN]` line produces one log entry.
Done when the CI smoke test covers both shapes.

## PR 2: install

`ruleratchet install <host> [<repo>]` writes the stop hook entry into the
host's project hook file (`.claude/settings.local.json` or
`.codex/hooks.json`), merging with `jq` and never adding a duplicate command.
`uninstall` removes it. Verify: run twice on a scratch repo; second run changes
nothing. Done when the README's manual JSON snippet is replaced by one command.

## PR 3: report flags

`--since YYYY-MM-DD` hides candidates not seen since, `--min-days N` raises the
threshold, `--out <file>` writes the markdown instead of printing. Verify: unit
tests on the fixture log. Done when a weekly run can be one cron line.

## PR 4: draft

`ruleratchet draft <log> <n>` prints a paste-ready block for candidate n: for a
mechanical entry, a shell check in the form `grep ... || echo "... Fix: ..."`;
for a judgement entry, one prescriptive sentence with a placeholder for the
command or path. Nothing is written anywhere. Verify: unit test per kind. Done
when adopting a candidate is copy, paste, commit.

## PR 5: health

`ruleratchet health <log>` prints: entries, candidates, promoted, held (no
recurrence since promotion), broken (recurred), and days from first sighting
to promotion. Verify: unit test on a fixture with one held and one broken
promotion. Done when "did the rules hold" is one command, which is the claim
the tool exists for.

## PR 6: recorded fixtures

`tests/fixtures/` holds one real stop event per host, redacted, and one
transcript tail per host. The capture test runs against them instead of a
hand-written JSON string. Verify: the existing CI smoke test moves to the
fixtures. Done when a format change in either host fails a test here first.

## PR 7: release

Bump to 0.2.0, add `CHANGELOG.md`, tag, and confirm `pipx install
git+https://github.com/ZairNaqvi/RuleRatchet@v0.2.0` works on a clean machine
(a CI job does the install). Done when the harness README can pin a tag.

## PR 8: public

Stranger read-through for employer and provider names, private links, and
machine paths; flip visibility; apply branch protection (require a PR and the
two CI jobs, enforced for the owner). Done when the install URL in the harness
README works for anyone.

## Not planned

- A model call anywhere. The drafts are templates; wording stays with the human.
- A daemon, a database, or a vector index. The log is a text file.
- Applying a rule automatically. The ratchet turns only when a person clicks it.
