#!/usr/bin/env bash
# capture.sh: stop hook for either supported agent CLI. Reads the event JSON on
# stdin, finds lines the agent marked [LEARN] or [FRICTION] in its last reply,
# and appends each to this repository's log. No model call.
# Log: $RULERATCHET_HOME/<repo key>.log, default ~/.ruleratchet/, keyed by the
# repository path so the file never lands in the repository.
set -u
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
key=$(printf '%s' "$root" | shasum -a 256 | cut -c1-16)
log="${RULERATCHET_HOME:-$HOME/.ruleratchet}/$key.log"
tool=$(command -v ruleratchet || echo "python3 $(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)/ruleratchet.py")
input=$(cat)
msg=$(printf '%s' "$input" | python3 -c '
import json, sys
d = json.load(sys.stdin)
m = d.get("last_assistant_message")
if not m and d.get("transcript_path"):
    try:
        with open(d["transcript_path"], "rb") as f:      # tail only; a long session is tens of MB
            f.seek(0, 2); f.seek(max(0, f.tell() - 200_000)); tail = f.read().decode("utf-8", "replace")
        for line in reversed(tail.splitlines()):
            try: e = json.loads(line)
            except Exception: continue
            if e.get("type") == "assistant":                       # first host: message.content[] text blocks
                c = e.get("message", {}).get("content", [])
                m = "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                if m: break
            if e.get("type") == "event_msg":                        # second host: rollout payload with the reply text
                pl = e.get("payload") or {}
                if pl.get("type") == "agent_message":
                    m = pl.get("message") or pl.get("text") or ""
                    if m: break
    except OSError: pass
print(m or "")' 2>/dev/null)
[ -n "$msg" ] || exit 0
printf '%s\n' "$msg" | grep -E '^[[:space:]]*\[(LEARN|FRICTION)\]' | sed -E 's/^[[:space:]]*//' | while IFS= read -r line; do
  kind=$(printf '%s' "$line" | sed -E 's/^\[([A-Z]+)\].*/\1/'); text=$(printf '%s' "$line" | sed -E 's/^\[[A-Z]+\][[:space:]]*//')
  $tool log "$log" "$kind" "$text"
done
exit 0
