# RuleRatchet

Run `scripts/setup.sh` once after cloning.

RuleRatchet turns repeated agent friction into rules, and checks that they held.
A ratchet only moves forward: once a lesson becomes a rule it should never have
to be learned again, and the tool tells you when it was.

## How it works

1. **Capture.** The stop hook records lines the agent marked `[LEARN]` or
   `[FRICTION]` in its reply. Any hook that blocks an action records a `BLOCK`
   entry. One log per repository, outside the repository, one line per entry:
   `date<TAB>kind<TAB>text`, kept once per day each. Dates are UTC.
2. **Report.** `ruleratchet report <log>` clusters rewordings of the same
   lesson and lists what was seen on two or more days or three or more times.
   An entry naming a path, flag, command, or exit code drafts a check; anything
   else drafts a prescriptive rule, flagged when it is conditional or names no
   command or path, since such rules are followed less.
3. **Promote.** `ruleratchet draft <log> <id>` prints a block to paste: a shell
   check for a mechanical entry, one rule line for a judgement entry, with
   placeholders for what only you know. You adopt it by hand, in your agent
   instructions file or as a lint rule, and record it: `ruleratchet mark <log> <id>`.
   The id is printed beside each candidate and stays the same as the log grows;
   a report position can shift when a new entry arrives between report and mark.
4. **Measure.** `ruleratchet health <log>` counts the promoted rules that held
   and the ones that broke, and exits 1 when one broke, so a scheduler can
   alert on it. A promoted entry that recurs after its promotion date is
   reported as such. That is the finding: the rule did not stop it, so a check
   should replace it.

No model call anywhere; nothing leaves the machine. Credential-shaped text in
an entry is replaced with `[redacted]` before it is written, because a lesson
ends up pasted into a rules file or a pull request.

## Install

```
pipx install git+https://github.com/ZairNaqvi/RuleRatchet            # latest
pipx install git+https://github.com/ZairNaqvi/RuleRatchet@v0.2.0     # a pinned release
```

or run `python3 ruleratchet.py` from a checkout. Python 3.11 or later.

## Hooks

Register the stop hook in a repository with one command, for either host:

```
ruleratchet install claude          # writes .claude/settings.local.json
ruleratchet install codex           # writes .codex/hooks.json
```

It merges into the existing file, never adds itself twice, refuses a file it
cannot parse, and adds the file to `.git/info/exclude` because the hook command
is a path on this machine. `ruleratchet uninstall <host>` removes it. The
second host asks you to trust a new project hook once, in its hooks menu.

The agent has to be told to mark its lessons, or the log stays empty.
`ruleratchet instructions` prints a short block for the agent instructions file:

```
ruleratchet instructions >> AGENTS.md
```

The hook is `ruleratchet capture`: it reads the stop event on stdin and records
the marked lines of the agent's last reply. A guard hook of your own records a
refusal with `ruleratchet block "<guard>: <reason>"`.

The log lives under `~/.ruleratchet/`, keyed by repository path; `ruleratchet
path` prints it and `RULERATCHET_HOME` moves it. `report`, `mark`, `draft`, and
`health` use it when no log is named. A weekly look, from inside the repository:

```
ruleratchet report
```

## Evidence behind the drafts

The drafting rules follow two measured findings on agent instruction files:
conditional phrasing ("if X then Y") is followed less than a plain instruction
(arXiv 2611.04367), and a rule that names a concrete command or path raises
compliance (arXiv 2610.04832).

## Report flags

```
ruleratchet report <log> --since 2026-11-01 --min-days 3 --out weekly.md
```

`--since` shows only candidates seen on or after the date, with their full
history. `--min-days` shows only candidates seen on that many days. `--out`
writes the report to a file. A candidate keeps its number from the full report
under any filter, so `ruleratchet mark <log> <n>` needs no flags. A weekly
cron line is `ruleratchet report <log> --since <last week> --out <file>`.
