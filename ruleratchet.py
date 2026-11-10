#!/usr/bin/env python3
"""ruleratchet: turn repeated agent friction into rules, and check that they held.

Usage:
  ruleratchet install <host> [<repo>]      register the stop hook (host: claude | codex)
  ruleratchet uninstall <host> [<repo>]    remove it
  ruleratchet path                         print this repository's log path
  ruleratchet report <log>                 what has recurred, with a drafted rule or check each
  ruleratchet mark <log> <id> [<id> ...]   record a candidate as promoted today, by the id report prints
  ruleratchet health <log>                 did the promoted rules hold; exits 1 when one broke
  ruleratchet log <log> <kind> <text>      append one dated entry (once per day per entry)
  ruleratchet capture                      stop hook: reads the event JSON on stdin
  ruleratchet block <text>                 for a guard hook: record that it refused something
  ruleratchet norm <text>                  print the normalized key for <text>
  ruleratchet --version

The log is a text file, one entry per line: date<TAB>kind<TAB>text. Any
producer can write it; `capture` and `block` write it from both supported agent
CLIs, to ~/.ruleratchet/<key>.log keyed by the repository path (RULERATCHET_HOME
moves it). Dates are UTC. Promotions are recorded beside the log in <log>.promoted.

`ruleratchet draft <log> <id>` prints a block for that candidate, ready to paste
into a lint script or the agent instructions file. It writes nothing.

A candidate is an entry whose normalized text, or a near-duplicate, was seen on
two or more distinct days or three or more times. An entry naming a path, flag,
command, or exit code is mechanical and drafts a check; anything else drafts a
prescriptive rule. A promoted entry that recurs after its promotion date is
reported as such: the rule did not stop it, so a check should replace it.
Nothing here calls a model and nothing leaves the machine.

report takes --since YYYY-MM-DD (only candidates seen on or after that date),
--min-days N (only candidates seen on N or more days), and --out <file> (write
the report instead of printing it). A candidate keeps its number from the full
report under any filter, so `mark` needs no flags.
"""
import collections, datetime, hashlib, json, os, pathlib, re, shlex, shutil, subprocess, sys

__version__ = "0.2.0"

STOP = set("a an and are as at be by for from in into is it its of on or that the this to use when with you your not do does if then always never first before after must should".split())
COMMANDS = {"bash", "git", "gh", "npm", "npx", "node", "python3", "python", "make", "cargo", "go", "pnpm", "yarn", "deno", "docker", "curl"}
THRESHOLD = 0.6


def utc_today():
    """Every date this tool writes or compares is UTC, so a log fed by several producers agrees with itself."""
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def stem(w):
    for suffix in ("ing", "ed", "es", "s"):   # crude, but enough to match "deleting" with "deleted"
        if len(w) > 4 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def norm(text):
    return " ".join(stem(w) for w in re.sub(r"[^a-z0-9/._ -]", " ", text.lower()).split() if w not in STOP)


def jaccard(a, b):
    a, b = set(a.split()), set(b.split())
    return len(a & b) / len(a | b) if a and b else 0.0


def classify(text):
    t = text.lower()
    tokens = t.split()
    mechanical = (
        any("/" in w or w.endswith((".sh", ".py", ".md", ".toml", ".json", ".yml", ".ts", ".mjs")) for w in tokens)
        or any(w.startswith("--") for w in tokens)
        or any(w in COMMANDS for w in tokens)
        or "exit code" in t or re.search(r"\bexit \d", t)
    )
    return "mechanical" if mechanical else "judgement"


def sentence(text):
    """Capitalize the first word unless it is a path, flag, or command, which must stay as typed."""
    body = text.strip().rstrip(".")
    first = body.split()[0] if body else ""
    return body[0].upper() + body[1:] if first.isalpha() and first.lower() not in COMMANDS else body


def draft(kind, text):
    body = sentence(text)
    if kind == "mechanical":
        words = text.split()
        token = (next((w for w in words if "/" in w), None) or next((w for w in words if w.startswith("--")), None)
                 or next((w for w in words if w.lower() in COMMANDS), None))
        hint = f"grep for '{token}'" if token else "name the command or path to check"
        return f"check (a lint rule or a hook): {body}. Start from: {hint}."
    conditional = " (reword as a plain instruction; conditional phrasing is followed less)" if re.match(r"(if|when|whenever|unless)\b", body, re.I) else ""
    needs = " (name the command or path it applies to before adopting; rules without one are followed less)"
    return f"rule (prescriptive, in the agent instructions file): {body}{conditional}{needs}"


def shell_dq(text):
    """Escape text for the inside of a double-quoted shell string."""
    return re.sub(r'([\\"$`])', r"\\\1", text)


def paste_block(text, members, days):
    """A block to paste into a lint script (mechanical) or the instructions file (judgement).
    Angle-bracket placeholders are for the human; only they know what a violation looks like."""
    body = sentence(text)
    seen = f"seen {len(members)} time(s) on {len(days)} day(s): {', '.join(days)}"
    if classify(text) == "mechanical":
        words = text.split()
        token = (next((w for w in words if "/" in w), None) or next((w for w in words if w.startswith("--")), None)
                 or next((w for w in words if w.lower() in COMMANDS), "<pattern>"))
        quoted = "'" + token.strip(".,;:").replace("'", "'\\''") + "'"
        return "\n".join([
            f"# {body} ({seen})",
            "# Narrow the pattern to what a violation looks like, and the path to where it can occur.",
            f"if grep -rnE -- {quoted} <path>; then",
            f'  echo "{shell_dq(body)}. Fix: <what to do instead>"',
            "  exit 1",
            "fi",
        ])
    note = "  <!-- reword as a plain instruction; conditional phrasing is followed less -->" if re.match(r"(if|when|whenever|unless)\b", body, re.I) else ""
    return f"- {body}. Applies to: `<command or path>`.{note}\n  <!-- {seen} -->"


def cmd_draft(log, n):
    cands = candidates(read_log(log))
    i = resolve(cands, n)
    if i is None:
        print(f"ruleratchet: no candidate {n} (the report lists {len(cands)})", file=sys.stderr)
        return 1
    _, members, days = cands[i]
    print(paste_block(members[-1][2], members, days))
    return 0


def read_log(log):
    rows = []
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3 and parts[0]:
                rows.append((parts[0], parts[1], parts[2].strip()))
    return rows


def cluster(rows):
    clusters = []  # [normalized key, [rows]]
    for row in rows:
        n = norm(row[2])
        for c in clusters:
            if n == c[0] or jaccard(n, c[0]) >= THRESHOLD:
                c[1].append(row)
                break
        else:
            clusters.append([n, [row]])
    return clusters


def candidates(rows):
    out = []
    for key, members in cluster(rows):
        days = sorted({r[0] for r in members})
        if len(days) >= 2 or len(members) >= 3:
            out.append((key, members, days))
    out.sort(key=lambda c: (-len(c[2]), -len(c[1])))
    return out


def cid(key):
    """A candidate's id. It stays the same as the log grows; its position in the report does not."""
    return "r" + hashlib.sha256(key.encode()).hexdigest()[:6]


def resolve(cands, ref):
    """Index of the candidate named by an id, or by a report position, or None."""
    ref = str(ref)
    if ref.isdigit():
        return int(ref) - 1 if 1 <= int(ref) <= len(cands) else None
    return next((i for i, c in enumerate(cands) if cid(c[0]) == ref), None)


def read_promoted(path):
    promoted = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            d, _, key = line.partition("\t")
            if key:
                promoted[key] = d
    return promoted


REPORT_USAGE = "usage: ruleratchet report <log> [--since YYYY-MM-DD] [--min-days N] [--out <file>]"


def cmd_report(log, flags=()):
    opts = dict(zip(flags[::2], flags[1::2]))
    since = opts.get("--since", "")
    try:
        if len(flags) % 2 or set(opts) - {"--since", "--min-days", "--out"}:
            raise ValueError
        if since:
            datetime.date.fromisoformat(since)
        min_days = int(opts.get("--min-days", 0))
    except ValueError:
        print(REPORT_USAGE, file=sys.stderr)
        return 2
    today = utc_today()
    cands = candidates(read_log(log))
    promoted = read_promoted(log.with_suffix(".promoted"))
    out = [f"# ruleratchet report, {today}, from {log}", ""]
    shown = 0
    for i, (key, members, days) in enumerate(cands, 1):   # i is the number in the full report, so mark needs no flags
        if len(days) < min_days or days[-1] < since:
            continue
        shown += 1
        text = members[-1][2]
        kind = classify(text)
        kinds = collections.Counter(r[1] for r in members)
        out.append(f"{i}. **{text}** `{cid(key)}`")
        out.append(f"   - seen {len(members)} time(s) on {len(days)} day(s): {', '.join(days)}; kinds: {dict(kinds)}")
        out.append(f"   - {kind}: {draft(kind, text)}")
        if key in promoted:
            recur = [r for r in members if r[0] > promoted[key]]
            verdict = f"recurred {len(recur)} time(s) since, so the rule did not stop it; replace it with a check" if recur else "no recurrence since"
            out.append(f"   - promoted on {promoted[key]}; {verdict}")
        out.append("")
    if shown:
        out.append(f"Accept one by its id: ruleratchet mark {log} <id>   (records the date; later reports show recurrence)")
    else:
        out.append("No candidate matches the filters." if cands else "No entry has recurred yet. Nothing to promote.")
    if "--out" in opts:
        pathlib.Path(opts["--out"]).expanduser().write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"ruleratchet: wrote {opts['--out']} ({shown} candidate(s))")
    else:
        print("\n".join(out))
    return 0


def days_between(a, b):
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except ValueError:      # a hand-edited date; skip it rather than fail the whole report
        return None


def cmd_health(log):
    """Did the promoted rules hold. Exits 1 when one broke, so a scheduler can alert on it."""
    rows = read_log(log)
    promoted = read_promoted(log.with_suffix(".promoted"))
    today = utc_today()
    held, broken, waits = [], [], []
    for key, members in cluster(rows):
        if key not in promoted:
            continue
        since, text = promoted[key], members[-1][2]
        if days_between(since, today) is None:      # a hand-edited date; counted below as not matching
            continue
        wait = days_between(min(r[0] for r in members), since)
        if wait is not None:
            waits.append(wait)
        after = sorted(r[0] for r in members if r[0] > since)
        if after:
            broken.append(f"- {text}: promoted {since}, recurred {len(after)} time(s), last {after[-1]}")
        else:
            held.append(f"- {text}: promoted {since}, quiet for {days_between(since, today)} day(s)")
    waiting = sum(1 for key, _, _ in candidates(rows) if key not in promoted)
    print(f"# ruleratchet health, {today}, from {log}\n")
    print(f"entries: {len(rows)} over {len({r[0] for r in rows})} day(s)")
    print(f"promoted: {len(held) + len(broken)} (held {len(held)}, broken {len(broken)})")
    if len(promoted) > len(held) + len(broken):
        print(f"promotions with no matching log entry or a bad date: {len(promoted) - len(held) - len(broken)}")
    if waits:
        print(f"days from first sighting to promotion: median {sorted(waits)[len(waits) // 2]}")
    print(f"candidates not yet promoted: {waiting}")
    if broken:
        print("\nbroken (recurred after promotion; replace the rule with a check):")
        print("\n".join(broken))
    if held:
        print("\nheld:")
        print("\n".join(held))
    return 1 if broken else 0


def cmd_mark(log, numbers):
    cands = candidates(read_log(log))
    today = utc_today()
    path = log.with_suffix(".promoted")
    with path.open("a", encoding="utf-8") as f:
        for ref in numbers:
            i = resolve(cands, ref)
            if i is None:
                print(f"ruleratchet: no candidate {ref}; take the id from the report", file=sys.stderr)
                continue
            key, members, _ = cands[i]
            f.write(f"{today}\t{key}\n")
            print(f"ruleratchet: marked {cid(key)} as promoted on {today}: {members[-1][2]}")
    if not numbers:
        print("ruleratchet: name at least one candidate id from the report", file=sys.stderr)
    return 1 if not numbers or any(resolve(cands, ref) is None for ref in numbers) else 0


def cmd_log(log, kind, text):
    text = " ".join(text.split())[:200]
    if not text:
        return 0
    entry = f"{utc_today()}\t{kind}\t{text}"
    log.parent.mkdir(parents=True, exist_ok=True)
    existing = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    if entry not in existing:   # once per day; repeats on later days are what report counts
        with log.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    return 0


HOSTS = {"claude": ".claude/settings.local.json", "codex": ".codex/hooks.json"}


def default_log():
    """This repository's log, or None outside a repository."""
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    home = os.environ.get("RULERATCHET_HOME") or pathlib.Path.home() / ".ruleratchet"
    return pathlib.Path(home) / (hashlib.sha256(root.encode()).hexdigest()[:16] + ".log")


def last_message(event):
    """The agent's last reply: from the stop event, else from the tail of the transcript."""
    if event.get("last_assistant_message"):
        return event["last_assistant_message"]
    try:
        with open(event.get("transcript_path") or "", "rb") as f:   # tail only; a long session is tens of MB
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 200_000))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return ""
    for line in reversed(tail.splitlines()):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "assistant":      # first host: message.content[] text blocks
            content = (e.get("message") or {}).get("content") or []
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            if text:
                return text
        if e.get("type") == "event_msg":      # second host: rollout payload with the reply text
            payload = e.get("payload") or {}
            if payload.get("type") == "agent_message" and (payload.get("message") or payload.get("text")):
                return payload.get("message") or payload.get("text")
    return ""


def cmd_capture():
    log = default_log()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0          # a hook never fails the session over a bad payload
    if log is None or not isinstance(event, dict):
        return 0
    for line in last_message(event).splitlines():
        m = re.match(r"\s*\[(LEARN|FRICTION)\]\s*(.+)", line)
        if m:
            cmd_log(log, m.group(1), m.group(2))
    return 0


def hook_command():
    exe = shutil.which("ruleratchet")   # the host runs this through a shell, so quote paths with spaces
    return shlex.join([exe, "capture"] if exe else [sys.executable, str(pathlib.Path(__file__).resolve()), "capture"])


def is_ours(group):
    return any("ruleratchet" in h.get("command", "") and h.get("command", "").endswith(" capture") for h in group.get("hooks", []))


def cmd_install(host, repo, remove=False):
    if host not in HOSTS:
        print(f"ruleratchet: unknown host '{host}' (known: {', '.join(HOSTS)})", file=sys.stderr)
        return 2
    repo = pathlib.Path(repo).expanduser().resolve()
    if not repo.is_dir():
        print(f"ruleratchet: {repo} is not a directory", file=sys.stderr)
        return 2
    path = repo / HOSTS[host]
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() and path.read_text().strip() else {}
    except ValueError as err:   # never overwrite a settings file we cannot parse
        print(f"ruleratchet: {path} is not valid JSON ({err}); fix it by hand, nothing was written", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"ruleratchet: {path} does not hold a JSON object; nothing was written", file=sys.stderr)
        return 1
    stop = data.setdefault("hooks", {}).setdefault("Stop", [])
    had = any(is_ours(g) for g in stop)
    if remove:
        data["hooks"]["Stop"] = [g for g in stop if not is_ours(g)]
        if not data["hooks"]["Stop"]:
            del data["hooks"]["Stop"]
        if not data["hooks"]:
            del data["hooks"]
        verb = "removed the stop hook from" if had else "no stop hook to remove in"
    elif had:
        print(f"ruleratchet: stop hook already registered in {path}")
        return 0
    else:
        stop.append({"hooks": [{"type": "command", "command": hook_command(), "timeout": 30}]})
        verb = "registered the stop hook in"
    if remove and not had:
        print(f"ruleratchet: {verb} {path}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    exclude = repo / ".git" / "info" / "exclude"
    if not remove and exclude.parent.is_dir():   # the hook command is a machine path; keep the file out of commits
        lines = exclude.read_text().splitlines() if exclude.exists() else []
        if HOSTS[host] not in lines:
            exclude.write_text("\n".join(lines + [HOSTS[host]]) + "\n")
    print(f"ruleratchet: {verb} {path}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("--version", "-V"):
        print(f"ruleratchet {__version__}")
        return 0
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "norm" and rest:
        print(norm(" ".join(rest)))
        return 0
    if cmd in ("install", "uninstall") and rest:
        return cmd_install(rest[0], rest[1] if len(rest) > 1 else ".", remove=cmd == "uninstall")
    if cmd == "capture":
        return cmd_capture()
    if cmd == "path":
        log = default_log()
        print(log if log else "ruleratchet: not inside a repository", file=sys.stdout if log else sys.stderr)
        return 0 if log else 1
    if cmd == "block" and rest:
        log = default_log()
        return cmd_log(log, "BLOCK", " ".join(rest)) if log else 0
    if cmd in ("report", "mark", "log") and rest:
        log = pathlib.Path(rest[0]).expanduser()
        if cmd == "report":
            return cmd_report(log, rest[1:])
        if cmd == "mark":
            return cmd_mark(log, rest[1:])
        if cmd == "log" and len(rest) >= 3:
            return cmd_log(log, rest[1], " ".join(rest[2:]))
    if cmd == "draft" and len(rest) == 2:
        return cmd_draft(pathlib.Path(rest[0]).expanduser(), rest[1])
    if cmd == "health" and len(rest) == 1:
        return cmd_health(pathlib.Path(rest[0]).expanduser())
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
