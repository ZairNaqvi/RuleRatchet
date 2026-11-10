# Changelog

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
