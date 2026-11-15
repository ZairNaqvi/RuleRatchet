# Design

Why RuleRatchet works the way it does. One decision per section: what was chosen, why, and what it costs.

## Why a text log

The log is one line per entry: `date<TAB>kind<TAB>text`.

Anything can write it and anyone can read it. A shell hook, another tool, or you with an editor. There is no schema to migrate and nothing to back up but a file.

**Cost.** No query language. The whole file is read on every command, which is fine for the few entries a day this produces.

## Why no model call

Capture is a pattern match. Grouping is word overlap. Drafts are templates.

A model call would make the report cost money, need a key, and differ from run to run. The agent already decided what was worth marking; the tool only counts.

**Cost.** Two lessons worded very differently are not grouped. The draft cannot reword a clumsy rule; it flags it and leaves the rewording to you.

## Why two days

A candidate is an entry seen on two or more days, or three or more times.

One sighting is an event. Two on different days is a pattern, because each entry is kept once per day, so two days means two separate sessions hit the same thing.

**Cost.** A lesson that matters the first time waits for a second sighting. Mark it by hand with `ruleratchet log` if you cannot wait.

## Why grouping is crude on purpose

Text is lowercased, common words are dropped, endings like `-ing` and `-ed` are cut, and two entries group when their remaining words overlap by 0.6 or more.

That is enough to join "must run from the repo root" with "must be run from the repo root", and simple enough to predict.

**Cost.** The threshold is one number, picked on a handful of examples. It may group too much or too little on a real month of entries.

## Why ids, not numbers

Each candidate has an id such as `r7947d8`, a hash of the first entry in its group.

A number is a position in a sorted list, and the list re-sorts as the log grows. The stop hook writes on every turn, so an entry can arrive between `report` and `mark`, and `mark 1` would then promote a different lesson. The id does not move.

**Cost.** Ids are longer to type. Numbers still work, resolved at the moment the command runs.

## Why every date is UTC

Entries, promotions, reports, and health all use the UTC date.

The log is open to other writers. A writer that stamps UTC and a promotion that stamps local time disagree in the evening: an entry written before a promotion can carry a later date and read as a recurrence.

**Cost.** Near midnight the date in the log may not be the date on your wall.

## Why mask at the write

Credential-shaped text is replaced with `[redacted]` in the one function that writes the log.

A lesson is written by the agent, shown in a report, and pasted by a person into a rules file or a pull request. Masking at the single write point covers every path into the log.

**Cost.** Known shapes only. A secret in a shape it does not know still gets through.

## Why you apply the rule

`draft` prints a block. Nothing writes to your instructions file or your lint scripts.

Only you know what a violation looks like and where it can occur. A tool that edited those files would be guessing in the place where a wrong guess costs the most.

**Cost.** One paste per rule.

## Why health exits 1

`ruleratchet health` exits 1 when a promoted rule broke, and 0 otherwise.

That makes "did the rules hold" a thing a scheduler can alert on, not a report someone has to remember to read.

**Cost.** A broken rule fails a script that does not expect it. Use `ruleratchet health || true` where that matters.

## Why the hook is a subcommand

The stop hook is `ruleratchet capture`, not a shell script in this repository.

A package install ships only the Python module. A hook registered by `install` has to be a command that still exists afterwards.

**Cost.** The hook starts a Python process on every stop. It reads at most the last 200 KB of the transcript, and only when the event carries no reply.

## Limits

- Capture for Codex is tested against the documented transcript shape, not a recording.
- Whether an agent follows the marking instructions in a live session has not been measured.
- Grouping is order-dependent: the first entry of a group names it.
- A log written before the UTC change keeps its local dates.
