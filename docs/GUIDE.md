# Guide

How to use RuleRatchet week to week. `README.md` covers installing it.

## Start here

Two things must be true before anything shows up.

1. The stop hook is registered: `ruleratchet install claude` or `ruleratchet install codex`, run inside the repository.
2. The agent has been told to mark lessons: `ruleratchet instructions >> AGENTS.md`.

After that the agent ends a reply with lines like these, and the hook saves them:

```text
[LEARN] run src/test.sh from the repo root
[FRICTION] the verify hook blocked the first attempt
```

You do nothing during the week.

## A week with RuleRatchet

1. **Look.** Run `ruleratchet report`. It lists only what was seen on two or more days, so a one-off does not appear.
2. **Pick.** Each candidate has an id such as `r7947d8`. Use the id, not the position; positions move when new entries arrive.
3. **Draft.** Run `ruleratchet draft r7947d8`. It prints a block to paste and writes nothing.
4. **Adopt.** Paste the block into your lint script or your agent instructions file. Fill in the placeholders. Commit it the way you commit anything else.
5. **Record.** Run `ruleratchet mark r7947d8`. It prints the lesson it marked, so you can see it took the right one.
6. **Check later.** Run `ruleratchet health`. A rule that held shows how long it has been quiet. A rule that broke shows when it recurred.

## Typical paths

### The lesson names a command or a path

The report calls it mechanical. The draft is a shell check:

```sh
# src/test.sh must be run from the repo root (seen 2 time(s) on 2 day(s): 2026-11-03, 2026-11-05)
# Narrow the pattern to what a violation looks like, and the path to where it can occur.
if grep -rnE -- 'src/test.sh' <path>; then
  echo "src/test.sh must be run from the repo root. Fix: <what to do instead>"
  exit 1
fi
```

Replace the pattern with what a violation looks like, and `<path>` with where it can occur. Only you know those. Then add the block to a lint script or a hook.

A check is better than a rule when one is possible. A check fails; a rule is advice.

### The lesson is a judgement call

The report calls it judgement. The draft is one line for the instructions file:

```markdown
- If a branch is to be deleted, ask first. Applies to: `<command or path>`.
```

Two flags can appear beside it.

- **Conditional wording.** Reword "if a branch is to be deleted, ask first" as "ask before deleting a branch".
- **No command or path.** Name what the rule applies to, for example `git branch -D`.

Both flags come from measured results; see `README.md`.

### A rule broke

`ruleratchet health` lists it under broken and exits 1.

A broken rule is a lesson that came back after you promoted it. The rule did not stop it. Replace the rule with a check, then mark the lesson again.

### Nothing shows up in the report

Work down this list.

1. `ruleratchet path` prints the log. Is the file there, and does it have lines?
2. No file: the hook is not running. Run `ruleratchet install <host>` again and, on Codex, trust the hook in the hooks menu.
3. A file with only `BLOCK` lines: the agent was never told to mark lessons. Run `ruleratchet instructions >> AGENTS.md`.
4. Lines, but an empty report: nothing has recurred yet. A lesson has to be seen on two days.

### You want it from a scheduler

```
ruleratchet report --since 2026-11-08 --out weekly.md
ruleratchet health || echo "a rule broke"
```

`--since` shows only candidates seen on or after the date, with their full history. `--min-days 3` raises the bar. `health` exits 1 when a rule broke, so a scheduler can alert on it.

### Your own guard hooks

A hook of yours that refuses an action can record the refusal:

```sh
ruleratchet block "deploy-guard: refused a push to main"
```

Refusals count like lessons. A guard that fires on two days becomes a candidate.

## Guardrails

- The tool never edits your instructions file or your lint scripts. `draft` prints; you paste.
- The tool never calls a model and never uses the network.
- `install` refuses a hook file it cannot parse, and writes nothing.
- A hook never fails your session. A bad payload is ignored.

## Keeping it healthy

- **Move the log.** Set `RULERATCHET_HOME`. The default is `~/.ruleratchet/`.
- **Remove the hook.** `ruleratchet uninstall <host>` leaves every other setting in place.
- **Prune by hand.** The log is a text file. Delete a line and it is gone.
- **Keep secrets out.** Known credential shapes are masked at the write. Do not rely on that for shapes it does not know.
