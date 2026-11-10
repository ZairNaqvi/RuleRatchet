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

    def test_recurrence_after_promotion(self):
        key = rr.norm("src/test.sh must run from the repo root")
        self.log.with_suffix(".promoted").write_text(f"2026-11-02\t{key}\n")
        self.assertIn("recurred 1 time(s) since", self.report())

    def test_mark_records_today(self):
        rr.cmd_mark(self.log, [2])
        line = self.log.with_suffix(".promoted").read_text().strip()
        self.assertTrue(line.startswith(datetime.date.today().isoformat()))

    def test_log_dedupes_per_day(self):
        log = pathlib.Path(self.dir.name) / "y.log"
        rr.cmd_log(log, "LEARN", "same thing")
        rr.cmd_log(log, "LEARN", "same   thing")
        self.assertEqual(len(log.read_text().splitlines()), 1)


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

    def test_capture_falls_back_to_either_transcript_shape(self):
        self.capture({"transcript_path": str(FIXTURES / "transcript.jsonl")})
        self.capture({"transcript_path": str(FIXTURES / "rollout.jsonl")})
        self.assertIn("FRICTION\tthe first host writes transcript lines.", self.log_text())
        self.assertIn("LEARN\tthe second host writes rollout lines.", self.log_text())

    def test_capture_survives_a_bad_payload(self):
        self.assertEqual(self.capture("not json"), 0)
        self.assertEqual(self.capture("[1, 2]"), 0)
        self.assertEqual(self.capture({"transcript_path": "/nonexistent"}), 0)
        self.assertEqual(self.log_text(), "")

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
