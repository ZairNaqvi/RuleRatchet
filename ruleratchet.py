#!/usr/bin/env python3
"""ruleratchet: turn repeated agent friction into rules, and check that they held.

Usage:
  ruleratchet report <log>                 what has recurred, with a drafted rule or check each
  ruleratchet mark <log> <n> [<n> ...]     record candidate n as promoted today
  ruleratchet log <log> <kind> <text>      append one dated entry (once per day per entry)
  ruleratchet norm <text>                  print the normalized key for <text>

The log is a text file, one entry per line: date<TAB>kind<TAB>text. Any
producer can write it; the hooks in hooks/ write it from both supported agent
CLIs. Promotions are recorded beside the log in <log>.promoted.

`ruleratchet draft <log> <n>` prints a block for candidate n, ready to paste
into a lint script or the agent instructions file. It writes nothing.

A candidate is an entry whose normalized text, or a near-duplicate, was seen on
two or more distinct days or three or more times. An entry naming a path, flag,
command, or exit code is mechanical and drafts a check; anything else drafts a
prescriptive rule. A promoted entry that recurs after its promotion date is
reported as such: the rule did not stop it, so a check should replace it.
Nothing here calls a model and nothing leaves the machine.
"""
import collections, datetime, pathlib, re, sys

STOP = set("a an and are as at be by for from in into is it its of on or that the this to use when with you your not do does if then always never first before after must should".split())
COMMANDS = {"bash", "git", "gh", "npm", "npx", "node", "python3", "python", "make", "cargo", "go", "pnpm", "yarn", "deno", "docker", "curl"}
THRESHOLD = 0.6


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
    if not 1 <= n <= len(cands):
        print(f"ruleratchet: no candidate {n} (the report lists {len(cands)})", file=sys.stderr)
        return 1
    _, members, days = cands[n - 1]
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


def read_promoted(path):
    promoted = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            d, _, key = line.partition("\t")
            if key:
                promoted[key] = d
    return promoted


def cmd_report(log):
    today = datetime.date.today().isoformat()
    cands = candidates(read_log(log))
    promoted = read_promoted(log.with_suffix(".promoted"))
    print(f"# ruleratchet report, {today}, from {log}\n")
    if not cands:
        print("No entry has recurred yet. Nothing to promote.")
        return 0
    for i, (key, members, days) in enumerate(cands, 1):
        text = members[-1][2]
        kind = classify(text)
        kinds = collections.Counter(r[1] for r in members)
        print(f"{i}. **{text}**")
        print(f"   - seen {len(members)} time(s) on {len(days)} day(s): {', '.join(days)}; kinds: {dict(kinds)}")
        print(f"   - {kind}: {draft(kind, text)}")
        if key in promoted:
            recur = [r for r in members if r[0] > promoted[key]]
            verdict = f"recurred {len(recur)} time(s) since, so the rule did not stop it; replace it with a check" if recur else "no recurrence since"
            print(f"   - promoted on {promoted[key]}; {verdict}")
        print()
    print(f"Accept one with: ruleratchet mark {log} <n>   (records the date; later reports show recurrence)")
    return 0


def cmd_mark(log, numbers):
    cands = candidates(read_log(log))
    today = datetime.date.today().isoformat()
    path = log.with_suffix(".promoted")
    with path.open("a", encoding="utf-8") as f:
        for n in numbers:
            if 1 <= n <= len(cands):
                f.write(f"{today}\t{cands[n - 1][0]}\n")
                print(f"ruleratchet: marked {n} as promoted on {today}")
            else:
                print(f"ruleratchet: no candidate {n}", file=sys.stderr)
    return 0


def cmd_log(log, kind, text):
    text = " ".join(text.split())[:200]
    if not text:
        return 0
    entry = f"{datetime.date.today().isoformat()}\t{kind}\t{text}"
    log.parent.mkdir(parents=True, exist_ok=True)
    existing = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    if entry not in existing:   # once per day; repeats on later days are what report counts
        with log.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "norm" and rest:
        print(norm(" ".join(rest)))
        return 0
    if cmd in ("report", "mark", "log") and rest:
        log = pathlib.Path(rest[0]).expanduser()
        if cmd == "report":
            return cmd_report(log)
        if cmd == "mark":
            return cmd_mark(log, [int(a) for a in rest[1:] if a.isdigit()])
        if cmd == "log" and len(rest) >= 3:
            return cmd_log(log, rest[1], " ".join(rest[2:]))
    if cmd == "draft" and len(rest) == 2 and rest[1].isdigit():
        return cmd_draft(pathlib.Path(rest[0]).expanduser(), int(rest[1]))
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
