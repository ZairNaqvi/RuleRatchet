# Changelog

## 0.3.2

- `status` also finds the marking instructions in `CLAUDE.local.md`, the
  untracked personal file, so a setup that changes no shared file reads as set up.

## 0.3.1

- `status` says whether capture is set up in a repository and whether anything
  is arriving, and prints the command for whatever is missing.
- Documentation for a first-time reader: a rewritten README, `docs/GUIDE.md`,
  `docs/DESIGN.md`, and `docs/LOG-FORMAT.md`.
- Package metadata carries the project URLs.

## 0.3.0

- Candidates have ids. `report` prints one beside each candidate, and `mark`
  and `draft` take it. A report position can shift when a new entry arrives
  between report and mark; an id cannot. `mark` prints the lesson it marked and
  exits 1 for a reference that matches nothing.
- Every date is UTC: entries, promotions, reports, and health. Logs written
  earlier keep the local dates they have.
- Credential-shaped text in an entry is replaced with `[redacted]` before it is
  written.
- `report`, `mark`, `draft`, and `health` use this repository's log when no log
  is named.
- `instructions` prints the block that tells the agent how to mark lessons, and
  `install` points at it.

## 0.2.0

- `install <host>` and `uninstall` register and remove the stop hook in the
  host's project hook file, keeping every other setting.
- The stop hook is the `capture` subcommand; `block` records a guard's refusal
  and `path` prints the repository's log. The shell scripts under `hooks/` are gone.
- `capture` reads the second host's rollout transcript as well as the first's.
- `report` takes `--since`, `--min-days`, and `--out`. Candidate numbers stay
  fixed under any filter.
- `draft <log> <n>` prints a paste-ready shell check or rule line.
- `health <log>` counts the promoted rules that held and the ones that broke,
  and exits 1 when one broke.
- `--version`.
- Capture is tested against a recorded stop event and transcript.

## 0.1.0

- `report`, `mark`, `log`, `norm`; two shell hooks; clustering, classification,
  and recurrence after promotion.
