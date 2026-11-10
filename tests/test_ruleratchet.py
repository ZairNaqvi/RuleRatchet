import datetime, io, json, os, pathlib, sys, tempfile, unittest
from contextlib import redirect_stdout

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ruleratchet as rr

LOG = """2026-11-01\tLEARN\tsrc/test.sh must run from the repo root
2026-11-03\tBLOCK\tverify: test command failed: bash src/test.sh
2026-11-03\tLEARN\tsrc/test.sh must be run from the repo root
2026-11-04\tFRICTION\talways ask before deleting a branch
2026-11-05\tFRICTION\tif a branch is to be deleted, ask first
2026-11-05\tBLOCK\tverify: test command failed: bash src/test.sh
2026-11-05\tLEARN\tnpx first run takes twenty seconds
"""


class Test(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.log = pathlib.Path(self.dir.name) / "x.log"
        self.log.write_text(LOG)

    def tearDown(self):
        self.dir.cleanup()

    def report(self, *flags):
        out = io.StringIO()
        with redirect_stdout(out):
            self.status = rr.cmd_report(self.log, flags)
        return out.getvalue()

    def test_since_hides_older_candidates_and_keeps_their_numbers(self):
        out = self.report("--since", "2026-11-04")
        self.assertNotIn("1. **", out)
        self.assertIn("2. **verify", out)
        self.assertIn("3. **if a branch", out)

    def test_min_days_and_out(self):
        self.assertIn("No candidate matches the filters.", self.report("--min-days", "3"))
        target = pathlib.Path(self.dir.name) / "weekly.md"
        self.assertIn("3 candidate(s)", self.report("--out", str(target)))
        self.assertIn("1. **src/test.sh", target.read_text())

    def test_bad_report_flags_are_refused(self):
        for flags in (("--since", "last week"), ("--min-days", "few"), ("--nope", "1"), ("--out",)):
            self.report(*flags)
            self.assertEqual(self.status, 2)

    def test_rewordings_cluster_and_singletons_do_not(self):
        cands = rr.candidates(rr.read_log(self.log))
        texts = [c[1][-1][2] for c in cands]
        self.assertEqual(len(cands), 3)
        self.assertIn("if a branch is to be deleted, ask first", texts)
        self.assertNotIn("npx first run takes twenty seconds", texts)

    def test_classification_and_drafts(self):
        out = self.report()
        self.assertIn("mechanical: check", out)
        self.assertIn("grep for 'src/test.sh'", out)
        self.assertIn("judgement: rule", out)
        self.assertIn("conditional phrasing", out)

    def draft(self, n):
        out = io.StringIO()
        with redirect_stdout(out):
            self.status = rr.cmd_draft(self.log, n)
        return out.getvalue()

    def test_draft_for_a_mechanical_entry_is_a_shell_check(self):
        out = self.draft(1)
        self.assertIn("if grep -rnE -- 'src/test.sh' <path>; then", out)
        self.assertIn("Fix: <what to do instead>", out)
        self.assertIn("seen 2 time(s) on 2 day(s)", out)

    def test_draft_for_a_judgement_entry_is_one_rule_line(self):
        out = self.draft(3)
        self.assertTrue(out.startswith("- If a branch is to be deleted, ask first. Applies to: `<command or path>`."))
        self.assertIn("conditional phrasing", out)

    def test_draft_keeps_paths_as_typed_and_escapes_the_echo(self):
        self.assertIn("# src/test.sh must be run from the repo root (", self.draft(1))
        self.assertEqual(rr.sentence("always ask first."), "Always ask first")
        self.assertEqual(rr.sentence("git push needs a branch"), "git push needs a branch")
        block = rr.paste_block('bash x.sh prints "$HOME" and `id`', [("2026-11-01", "LEARN", "")], ["2026-11-01"])
        self.assertIn('echo "bash x.sh prints \\"\\$HOME\\" and \\`id\\`. Fix:', block)

    def test_draft_refuses_a_number_the_report_does_not_list(self):
        self.assertEqual(self.draft(9), "")
        self.assertEqual(self.status, 1)

    def test_ids_survive_a_reorder_that_moves_the_numbers(self):
        first_key = rr.candidates(rr.read_log(self.log))[0][0]
        first_id = rr.cid(first_key)
        self.assertIn(f"1. **src/test.sh must be run from the repo root** `{first_id}`", self.report())
        with self.log.open("a") as f:      # the block lesson gains a third day and now sorts first
            f.write("2026-11-06\tBLOCK\tverify: test command failed: bash src/test.sh\n")
        self.assertNotEqual(rr.candidates(rr.read_log(self.log))[0][0], first_key)   # position 1 is another lesson now
        self.assertEqual(rr.cmd_mark(self.log, [first_id]), 0)
        self.assertEqual(self.log.with_suffix(".promoted").read_text().split("\t")[1].strip(), first_key)

    def test_mark_and_draft_refuse_an_unknown_id(self):
        self.assertEqual(rr.cmd_mark(self.log, ["rzzzzzz"]), 1)
        self.assertEqual(self.log.with_suffix(".promoted").read_text(), "")
        self.assertEqual(rr.cmd_mark(self.log, []), 1)
        self.assertEqual(self.draft("rzzzzzz"), "")
        self.assertEqual(self.status, 1)

    def test_draft_by_id_and_main_passes_ids_through(self):
        first_id = rr.cid(rr.candidates(rr.read_log(self.log))[0][0])
        self.assertIn("grep -rnE -- 'src/test.sh'", self.draft(first_id))
        self.assertEqual(rr.main(["mark", str(self.log), first_id]), 0)
        self.assertEqual(rr.main(["draft", str(self.log), first_id]), 0)

    def test_recurrence_after_promotion(self):
        key = rr.norm("src/test.sh must run from the repo root")
        self.log.with_suffix(".promoted").write_text(f"2026-11-02\t{key}\n")
        self.assertIn("recurred 1 time(s) since", self.report())

    def health(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.status = rr.cmd_health(self.log)
        return out.getvalue()

    def promote(self, text_part, date):
        key = next(k for k, members in rr.cluster(rr.read_log(self.log)) if text_part in members[-1][2])
        with self.log.with_suffix(".promoted").open("a") as f:
            f.write(f"{date}\t{key}\n")

    def test_health_with_no_promotions(self):
        out = self.health()
        self.assertIn("entries: 7 over 4 day(s)", out)
        self.assertIn("promoted: 0 (held 0, broken 0)", out)
        self.assertIn("candidates not yet promoted: 3", out)
        self.assertEqual(self.status, 0)

    def test_health_separates_held_from_broken_and_exits_1(self):
        self.promote("src/test.sh must", "2026-11-02")      # seen again on 11-03: broken
        self.promote("branch", "2026-11-05")                # nothing after 11-05: held
        out = self.health()
        self.assertIn("promoted: 2 (held 1, broken 1)", out)
        self.assertIn("recurred 1 time(s), last 2026-11-03", out)
        self.assertIn("if a branch is to be deleted, ask first: promoted 2026-11-05, quiet for", out)
        self.assertIn("days from first sighting to promotion: median 1", out)
        self.assertIn("candidates not yet promoted: 1", out)
        self.assertEqual(self.status, 1)

    def test_health_survives_a_stale_or_malformed_promotion(self):
        self.log.with_suffix(".promoted").write_text("2026-11-02\tgone from the log\nsoon\t" + rr.norm("npx first run takes twenty seconds") + "\n")
        out = self.health()
        self.assertIn("promotions with no matching log entry or a bad date: 2", out)
        self.assertIn("promoted: 0 (held 0, broken 0)", out)
        self.assertNotIn("None", out)
        self.assertEqual(self.status, 0)

    def test_dates_are_utc_whatever_the_local_zone(self):
        import time
        saved, seen = os.environ.get("TZ"), set()
        try:
            for zone in ("Etc/GMT+12", "Pacific/Kiritimati"):   # 26 hours apart: their local dates never agree
                os.environ["TZ"] = zone
                time.tzset()
                seen.add(rr.utc_today())
                log = pathlib.Path(self.dir.name) / "zone.log"
                rr.cmd_log(log, "LEARN", "one entry, whatever the zone")
        finally:
            if saved is None:
                del os.environ["TZ"]
            else:
                os.environ["TZ"] = saved
            time.tzset()
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(log.read_text().splitlines()), 1)      # same UTC day in both zones, so one line

    def test_mark_records_today(self):
        rr.cmd_mark(self.log, [2])
        line = self.log.with_suffix(".promoted").read_text().strip()
        self.assertTrue(line.startswith(rr.utc_today()))

    def test_log_dedupes_per_day(self):
        log = pathlib.Path(self.dir.name) / "y.log"
        rr.cmd_log(log, "LEARN", "same thing")
        rr.cmd_log(log, "LEARN", "same   thing")
        self.assertEqual(len(log.read_text().splitlines()), 1)

    def test_credential_shaped_text_never_reaches_the_log(self):
        cases = {
            "push failed with ghp_abcdefghijklmnopqrstuvwxyz0123 in the remote": "push failed with [redacted] in the remote",
            "db url postgres://app:hunter2@db.internal/main refused": "db url postgres://[redacted]@db.internal/main refused",
            "set API_KEY=abc123 before bash run.sh": "set API_KEY=[redacted] before bash run.sh",
            "header was Authorization: Bearer abcdef.ghijkl-mnop": "header was Authorization: [redacted]",
            "password: hunter2 is in .env": "password: [redacted] is in .env",
            "the token bucket allows 5 calls a minute": "the token bucket allows 5 calls a minute",
            "src/test.sh must run from the repo root": "src/test.sh must run from the repo root",
        }
        for text, want in cases.items():
            self.assertEqual(rr.mask(text), want)
        log = pathlib.Path(self.dir.name) / "m.log"
        rr.cmd_log(log, "LEARN", "export TOKEN=" + "x" * 300)
        self.assertTrue(log.read_text().rstrip().endswith("LEARN\texport TOKEN=[redacted]"))

    def test_version(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(rr.main(["--version"]), 0)
        self.assertEqual(out.getvalue().strip(), f"ruleratchet {rr.__version__}")
        self.assertIn(f"## {rr.__version__}\n", (pathlib.Path(rr.__file__).parent / "CHANGELOG.md").read_text())


FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


class TestHooks(unittest.TestCase):
    """capture and install; run from the checkout, which is a git repository."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.home = os.environ.get("RULERATCHET_HOME")
        os.environ["RULERATCHET_HOME"] = self.dir.name
        self.stdin = sys.stdin

    def tearDown(self):
        sys.stdin = self.stdin
        if self.home is None:
            del os.environ["RULERATCHET_HOME"]
        else:
            os.environ["RULERATCHET_HOME"] = self.home
        self.dir.cleanup()

    def capture(self, event):
        sys.stdin = io.StringIO(event if isinstance(event, str) else json.dumps(event))
        return rr.cmd_capture()

    def log_text(self):
        return rr.default_log().read_text() if rr.default_log().exists() else ""

    def test_capture_from_the_event(self):
        self.capture({"last_assistant_message": "Done.\n[LEARN] tests run from the root.\n  [FRICTION] slow first run.\nBye."})
        self.assertIn("LEARN\ttests run from the root.", self.log_text())
        self.assertIn("FRICTION\tslow first run.", self.log_text())
        self.assertEqual(len(self.log_text().splitlines()), 2)

    def test_capture_from_a_recorded_stop_event(self):
        event = json.loads((FIXTURES / "claude-stop-event.json").read_text())
        self.capture(event)
        self.assertEqual(self.log_text().split("\t", 1)[1], "LEARN\tthe recorded fixture line\n")

    def test_capture_from_a_recorded_transcript(self):
        # The recording has a thinking-only assistant record before the reply and
        # five other record types after it; the fallback must find the reply anyway.
        event = json.loads((FIXTURES / "claude-stop-event.json").read_text())
        del event["last_assistant_message"]
        event["transcript_path"] = str(FIXTURES / "claude-transcript.jsonl")
        self.capture(event)
        self.assertEqual(self.log_text().split("\t", 1)[1], "LEARN\tthe recorded fixture line\n")

    def test_capture_from_the_second_hosts_documented_shape(self):
        self.capture({"transcript_path": str(FIXTURES / "codex-rollout.synthetic.jsonl")})
        self.assertIn("LEARN\tthe second host writes rollout lines.", self.log_text())

    def test_capture_survives_a_bad_payload(self):
        self.assertEqual(self.capture("not json"), 0)
        self.assertEqual(self.capture("[1, 2]"), 0)
        self.assertEqual(self.capture({"transcript_path": "/nonexistent"}), 0)
        self.assertEqual(self.log_text(), "")

    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            self.status = rr.main(list(argv))
        return out.getvalue()

    def test_the_log_argument_defaults_to_this_repository(self):
        log = rr.default_log()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(LOG)
        self.assertIn("1. **src/test.sh", self.run_main("report"))
        self.assertIn("No candidate matches", self.run_main("report", "--min-days", "3"))
        self.assertIn("promoted: 0", self.run_main("health"))
        self.assertIn("grep -rnE", self.run_main("draft", "1"))
        self.run_main("mark", "2")
        self.assertTrue(log.with_suffix(".promoted").read_text().strip())
        other = pathlib.Path(self.dir.name) / "other.log"
        other.write_text("")
        self.assertIn("Nothing to promote", self.run_main("report", str(other)))

    def test_outside_a_repository_the_log_must_be_named(self):
        here = os.getcwd()
        os.chdir(self.dir.name)
        try:
            self.assertEqual(rr.main(["report"]), 2)
            self.assertEqual(rr.main(["health"]), 2)
        finally:
            os.chdir(here)

    def test_install_is_idempotent_and_keeps_other_settings(self):
        repo = pathlib.Path(self.dir.name) / "repo"
        (repo / ".claude").mkdir(parents=True)
        settings = repo / ".claude" / "settings.local.json"
        settings.write_text(json.dumps({"permissions": {"allow": ["x"]}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bash other.sh"}]}]}}))
        self.assertEqual(rr.cmd_install("claude", repo), 0)
        self.assertEqual(rr.cmd_install("claude", repo), 0)
        data = json.loads(settings.read_text())
        self.assertEqual(data["permissions"], {"allow": ["x"]})
        self.assertEqual(len(data["hooks"]["Stop"]), 2)
        self.assertTrue(data["hooks"]["Stop"][1]["hooks"][0]["command"].endswith(" capture"))
        self.assertEqual(rr.cmd_install("claude", repo, remove=True), 0)
        self.assertEqual(json.loads(settings.read_text())["hooks"]["Stop"], [{"hooks": [{"type": "command", "command": "bash other.sh"}]}])

    def test_install_creates_the_second_host_file_and_uninstall_empties_it(self):
        repo = pathlib.Path(self.dir.name) / "repo2"
        repo.mkdir()
        self.assertEqual(rr.cmd_install("codex", repo), 0)
        self.assertIn("Stop", json.loads((repo / ".codex" / "hooks.json").read_text())["hooks"])
        self.assertEqual(rr.cmd_install("codex", repo, remove=True), 0)
        self.assertEqual(json.loads((repo / ".codex" / "hooks.json").read_text()), {})

    def test_install_refuses_a_file_it_cannot_parse(self):
        repo = pathlib.Path(self.dir.name) / "repo3"
        (repo / ".codex").mkdir(parents=True)
        (repo / ".codex" / "hooks.json").write_text("{ broken")
        self.assertEqual(rr.cmd_install("codex", repo), 1)
        self.assertEqual((repo / ".codex" / "hooks.json").read_text(), "{ broken")
        self.assertEqual(rr.cmd_install("nope", repo), 2)


if __name__ == "__main__":
    unittest.main()
