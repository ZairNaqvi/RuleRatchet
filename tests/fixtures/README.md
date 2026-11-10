# Fixtures

| File | Source |
|---|---|
| `claude-stop-event.json` | Recorded. The stdin of a stop hook in a live headless session, host version 2.1.306, on 2026-11-10. |
| `claude-transcript.jsonl` | Recorded. The transcript that event pointed at, all 36 records in order. |
| `codex-rollout.synthetic.jsonl` | Synthetic. Written by hand from the second host's documented rollout shape; replace it with a recording when one can be made. |

## Redaction

The recordings are reduced by allowlist, not by search and replace.

- Stop event: every key is kept as recorded. The two ids are zeroed and the
  three paths are replaced with `<redacted>/...`.
- Transcript: each record keeps its `type`. `user` and `assistant` records also
  keep `message.role` and `message.content`, with text blocks keeping their text
  and every other block keeping only its `type`. Everything else is dropped.

## Recording again

In a scratch repository, register a stop hook that saves its stdin, run one
headless prompt that replies with a marked line, then reduce the saved event
and the transcript it names as above.

```json
{ "hooks": { "Stop": [ { "hooks": [ { "type": "command", "command": "cat > /tmp/stop-event.json" } ] } ] } }
```

A format change in the host shows up here as a failing capture test after a
fresh recording, before it shows up as a silently empty log.
