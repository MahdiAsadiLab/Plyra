"""Tests for the validation statistics (no Stockfish needed)."""

import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (sets up sys.path)

from validate import (
    MIN_RELIABLE_GAMES, Row, ValidationError, build_rows, compare, format_report, load_manifest, pearson,
)


class CompareTests(unittest.TestCase):
    def rows(self, pairs, system="chesscom"):
        return [Row(f"g{i}.pgn", "White", system, mine, ref) for i, (mine, ref) in enumerate(pairs)]

    def test_known_statistics(self):
        stats = compare(self.rows([(90, 80), (70, 75), (60, 60)]))
        self.assertEqual(stats["n"], 3)
        self.assertAlmostEqual(stats["mean_difference"], (10 - 5 + 0) / 3)
        self.assertAlmostEqual(stats["mean_absolute_error"], 5.0)
        self.assertEqual(stats["max_absolute_error"], 10)
        self.assertGreater(stats["correlation"], 0.8)

    def test_few_games_trigger_a_warning(self):
        self.assertIn("too few", compare(self.rows([(90, 80)] * 5))["warning"])
        many = compare(self.rows([(80 + i % 7, 79 + i % 5) for i in range(MIN_RELIABLE_GAMES)]))
        self.assertIsNone(many["warning"])

    def test_no_reference_values(self):
        stats = compare([])
        self.assertEqual(stats["n"], 0)
        self.assertIsNone(stats["mean_difference"])

    def test_correlation_needs_variation(self):
        self.assertIsNone(pearson([(1, 1), (1, 2), (1, 3)]))
        self.assertIsNone(pearson([(1, 1)]))

    def test_rows_skip_missing_values(self):
        refs = {("chesscom", "White"): 88.0, ("chesscom", "Black"): None, ("lichess", "White"): None, ("lichess", "Black"): 70.0}
        rows = build_rows("a.pgn", {"White": 90.0, "Black": 65.0}, refs)
        self.assertEqual([(r.color, r.reference) for r in rows], [("White", "chesscom"), ("Black", "lichess")])

    def test_report_text(self):
        text = format_report(self.rows([(90, 80), (70, 75), (60, 60)]))
        self.assertIn("Summary against chesscom", text)
        self.assertIn("WARNING", text)


class ManifestTests(unittest.TestCase):
    def write(self, folder, text):
        path = Path(folder) / "manifest.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_values_and_blank_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "pgn,white_chesscom,black_chesscom,white_lichess,black_lichess\n"
                                   "# comment line\ngames/a.pgn,91.5,,88,\n")
            entries = load_manifest(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["refs"][("chesscom", "White")], 91.5)
        self.assertIsNone(entries[0]["refs"][("chesscom", "Black")])
        self.assertEqual(entries[0]["refs"][("lichess", "White")], 88.0)

    def test_rejects_bad_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("abc", "150", "-3"):
                path = self.write(tmp, f"pgn,white_chesscom,black_chesscom,white_lichess,black_lichess\na.pgn,{bad},,,\n")
                with self.assertRaises(ValidationError):
                    load_manifest(path)

    def test_missing_file_and_missing_column(self):
        with self.assertRaises(ValidationError):
            load_manifest(Path("no_such_manifest.csv"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValidationError):
                load_manifest(self.write(tmp, "game,score\na,1\n"))


if __name__ == "__main__":
    unittest.main()
