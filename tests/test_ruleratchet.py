import datetime, io, pathlib, sys, tempfile, unittest
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

    def report(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rr.cmd_report(self.log)
        return out.getvalue()

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


if __name__ == "__main__":
    unittest.main()
