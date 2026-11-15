# RuleRatchet

RuleRatchet turns repeated coding-agent friction into rules, and checks that the rules held.

An agent makes the same mistake in session after session because nothing carries the lesson forward.

RuleRatchet records each lesson and each blocked action in a plain text log. It tells you which ones keep coming back and drafts a rule or a check for each. Later it tells you whether the rule stopped the recurrence.

A ratchet only moves forward. Once a lesson becomes a rule it should not have to be learned again, and this tool tells you when it was.

## What it looks like

A weekly look, from inside a repository:

```text
$ ruleratchet report

1. **src/test.sh must be run from the repo root** `r7947d8`
   - seen 2 time(s) on 2 day(s): 2026-11-03, 2026-11-05; kinds: {'LEARN': 2}
   - mechanical: check (a lint rule or a hook): src/test.sh must be run from the repo root. Start from: grep for 'src/test.sh'.

3. **if a branch is to be deleted, ask first** `r005991`
   - seen 2 time(s) on 2 day(s): 2026-11-06, 2026-11-09; kinds: {'FRICTION': 2}
   - judgement: rule (prescriptive, in the agent instructions file): If a branch is to be deleted, ask first (reword as a plain instruction; ...)
```

And later, the question the tool exists for:

```text
$ ruleratchet health

entries: 7 over 5 day(s)
promoted: 2 (held 1, broken 1)
candidates not yet promoted: 1

broken (recurred after promotion; replace the rule with a check):
- if a branch is to be deleted, ask first: promoted 2026-11-08, recurred 1 time(s), last 2026-11-09

held:
- src/test.sh must be run from the repo root: promoted 2026-11-15, quiet for 0 day(s)
```

Both examples are real output, shortened.

## The loop

1. **Capture.** A stop hook records the lines the agent marked `[LEARN]` or `[FRICTION]` in its reply. A guard hook records each action it refused.
2. **Report.** `ruleratchet report` groups rewordings of the same lesson and lists what was seen on two or more days.
3. **Promote.** `ruleratchet draft <id>` prints a block to paste. You adopt it by hand and record it with `ruleratchet mark <id>`.
4. **Measure.** `ruleratchet health` separates the promoted rules that held from the ones that broke.

No model call anywhere. Nothing leaves the machine.

## Contents

| Path | What it holds |
|---|---|
| `ruleratchet.py` | The whole tool: one file, standard library only. |
| `docs/GUIDE.md` | How to use it week to week. Start here after installing. |
| `docs/DESIGN.md` | Why it works the way it does, one decision at a time. |
| `docs/LOG-FORMAT.md` | The log format, for anything else that wants to write to it. |
| `docs/pr-plan.md` | The plan the tool was built from, PR by PR. |
| `tests/` | Unit tests, plus a stop event and transcript recorded from a live session. |
| `CHANGELOG.md` | What changed in each release. |
| `AGENTS.md` | Rules for an agent working in this repository. |
| `scripts/` | The maintainer's git hooks. Contributors do not need them. |

## Install

```
pipx install git+https://github.com/ZairNaqvi/RuleRatchet            # latest
pipx install git+https://github.com/ZairNaqvi/RuleRatchet@v0.3.0     # a pinned release
```

Or run `python3 ruleratchet.py` from a checkout. Python 3.11 or later, no dependencies.

## Quick start

Run these inside the repository you want to watch.

1. Register the stop hook for your agent:

   ```
   ruleratchet install claude          # or: ruleratchet install codex
   ```

2. Tell the agent how to mark lessons. Without this the log stays empty.

   ```
   ruleratchet instructions >> AGENTS.md
   ```

3. Work as usual for a week.

4. Look at what kept happening:

   ```
   ruleratchet report
   ```

At any point, `ruleratchet status` says whether it is set up and whether anything has arrived.

`docs/GUIDE.md` takes it from there.

## Commands

`report`, `draft`, `mark`, and `health` use this repository's log unless you name one.

| Command | What it does |
|---|---|
| `install <host> [<repo>]` | Register the stop hook. Hosts: `claude`, `codex`. |
| `uninstall <host> [<repo>]` | Remove it, leaving every other setting. |
| `instructions` | Print the block that tells the agent how to mark lessons. |
| `report [--since DATE] [--min-days N] [--out FILE]` | List what recurred, with an id and a draft for each. |
| `draft <id>` | Print a shell check or a rule line to paste. Writes nothing. |
| `mark <id> [<id> ...]` | Record a candidate as promoted today. |
| `health` | Count the rules that held and the ones that broke. Exits 1 when one broke. |
| `status` | Say whether capture is set up here and whether anything is arriving. Exits 1 when it cannot be working. |
| `path` | Print this repository's log path. |
| `capture` | The stop hook itself. Reads the event on stdin. |
| `block <text>` | For your own guard hooks: record a refusal. |
| `log <log> <kind> <text>` | Append one entry by hand. |

## Hosts

| | Claude Code | Codex |
|---|---|---|
| File `install` writes | `.claude/settings.local.json` | `.codex/hooks.json` |
| Hook event | `Stop` | `Stop` |
| Reply is read from | the stop event, else the transcript tail | the stop event, else the rollout transcript |
| Capture is tested against | a stop event and transcript recorded from a live session | the documented shape, written by hand |
| First run | nothing extra | trust the project hook once in the hooks menu |

## What it reads and writes

| | |
|---|---|
| Reads | The stop event on stdin. The last 200 KB of the transcript, only when the event carries no reply. Its own log. |
| Writes | `~/.ruleratchet/<key>.log` and `<key>.promoted`, outside the repository. |
| Writes on install | The host's project hook file, and one line in `.git/info/exclude` so that file stays out of commits. |
| Never touches | The network, a model, your instructions file, your lint scripts. |

Credential-shaped text in an entry is replaced with `[redacted]` before it is written. This covers known shapes only; it is a mask, not a secret scanner.

## Deliberately excluded

- **A model call.** The drafts are templates. The wording stays with you.
- **Applying a rule for you.** The ratchet turns only when a person clicks it.
- **A daemon, a database, or an index.** The log is a text file you can read and edit.

## Evidence behind the drafts

The drafting rules follow two measured findings.

- Conditional wording ("if X then Y") was followed less often than prescriptive or explanatory wording, across 86 tasks and four harness and model pairs (arXiv 2611.04367).
- Adding a rule that names a command or path raised the rate of the required action by 0.23 on average across four agents; the study used skill files (arXiv 2610.04832).

So the report flags a conditional rule, and flags a rule that names no command or path.

## Tests

```
python3 -m unittest discover tests
```

CI runs the same suite, pipes a stop event through the installed hook command, and checks that the package version matches the source.

## Contributing

Issues and pull requests are welcome.

- CI checks every commit message in a pull request: a capitalized subject of at most 72 characters, plain ASCII, and no co-author or tool-attribution trailer.
- `scripts/setup.sh` installs the maintainer's local git hooks. One of them rejects any committer but the maintainer, so contributors should not run it.

## License

MIT. See `LICENSE`.
