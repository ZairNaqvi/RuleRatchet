# RuleRatchet

Run `scripts/setup.sh` once after cloning.

RuleRatchet turns repeated agent friction into rules, and checks that they held.
A ratchet only moves forward: once a lesson becomes a rule it should never have
to be learned again, and the tool tells you when it was.

## How it works

1. **Capture.** A stop hook records lines the agent marked `[LEARN]` or
   `[FRICTION]` in its reply. Any hook that blocks an action records a `BLOCK`
   entry. One log per repository, outside the repository, one line per entry:
   `date<TAB>kind<TAB>text`, kept once per day each.
2. **Report.** `ruleratchet report <log>` clusters rewordings of the same
   lesson and lists what was seen on two or more days or three or more times.
   An entry naming a path, flag, command, or exit code drafts a check; anything
   else drafts a prescriptive rule, flagged when it is conditional or names no
   command or path, since such rules are followed less.
3. **Promote.** `ruleratchet draft <log> <n>` prints a block to paste: a shell
   check for a mechanical entry, one rule line for a judgement entry, with
   placeholders for what only you know. You adopt it by hand, in your agent
   instructions file or as a lint rule, and record it: `ruleratchet mark <log> <n>`.
4. **Measure.** A promoted entry that recurs after its promotion date is
   reported as such. That is the finding: the rule did not stop it, so a check
   should replace it.

No model call anywhere; nothing leaves the machine.

## Install

```
pipx install git+https://github.com/ZairNaqvi/RuleRatchet
```

or run `python3 ruleratchet.py` from a checkout. Python 3.11 or later.

## Hooks

`hooks/capture.sh` is a stop hook and `hooks/block.sh` is a helper other hooks
call when they refuse something. Both agent CLIs use the same hook block shape;
register the stop hook in the host's hook settings file for the project:

```json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "bash /path/to/RuleRatchet/hooks/capture.sh", "timeout": 30 } ] } ] } }
```

The log lives under `~/.ruleratchet/` keyed by repository path; set
`RULERATCHET_HOME` to move it.

## Evidence behind the drafts

The drafting rules follow two measured findings on agent instruction files:
conditional phrasing ("if X then Y") is followed less than a plain instruction
(arXiv 2611.04367), and a rule that names a concrete command or path raises
compliance (arXiv 2610.04832).
