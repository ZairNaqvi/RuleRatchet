# Log format

For anything that wants to write to the log, or read it, without going through the tool.

## The log

One entry per line, three fields, tab-separated:

```text
2026-11-05	LEARN	src/test.sh must be run from the repo root
```

| Field | Rule |
|---|---|
| Date | `YYYY-MM-DD`, in UTC. |
| Kind | A word in capitals. The tool writes `LEARN`, `FRICTION`, and `BLOCK`. Any other word is accepted and counted. |
| Text | One line, at most 200 characters, no tabs. Name the command or path the lesson is about. |

Two more rules keep the counts honest.

- **Once per day.** Do not write the same line twice on one date. The tool counts days, and a day should mean a separate sitting.
- **Append only.** The first entry of a group names the group, and promotions refer to that name. Reordering the file can orphan a promotion.

## Kinds

| Kind | Written by | Means |
|---|---|---|
| `LEARN` | `ruleratchet capture` | The agent was corrected, or a command worked only in a different form. |
| `FRICTION` | `ruleratchet capture` | A hook, a permission, or a missing tool got in the way. |
| `BLOCK` | `ruleratchet block` | A guard hook refused an action. |

## Where it lives

```text
~/.ruleratchet/<key>.log
```

`<key>` is the first 16 hex characters of the SHA-256 of the repository's top-level path. One log per repository, outside the repository, so it is never committed. `RULERATCHET_HOME` moves the directory. `ruleratchet path` prints the file.

## Promotions

Beside the log, with the same name and the suffix `.promoted`:

```text
2026-11-08	ask delet branch
```

| Field | Rule |
|---|---|
| Date | The UTC date the lesson was promoted. |
| Key | The normalized text of the first entry in the group. `ruleratchet norm <text>` prints it. |

A lesson is broken when its group has an entry dated after its promotion.

## Writing from your own tool

The simplest way is to call the tool, which applies the date, the once-per-day rule, and the mask:

```sh
ruleratchet log "$(ruleratchet path)" LEARN "run src/test.sh from the repo root"
```

Writing the line yourself also works, as long as it follows the rules above.
