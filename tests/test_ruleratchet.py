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
