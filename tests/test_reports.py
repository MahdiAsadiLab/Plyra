"""Tests for reports.py: HTML, CSV, annotated PGN, JSON and file writing.

No Stockfish needed. A few PGN checks use python-chess if it is installed.
"""

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from helpers import cp, make_result, sample_game  # also sets up sys.path

from models import ChessLensError, GameInfo, summarize
from reports import (
    CSV_COLUMNS, build_annotated_pgn, build_csv, build_html, build_json,
    choose_path, prepare_output_dir, safe_stem, write_reports,
)

try:
    import chess.pgn
    HAVE_CHESS = True
except ImportError:
    HAVE_CHESS = False


class HtmlTests(unittest.TestCase):
    def test_html_contains_the_important_parts(self):
        info, results = sample_game()
        page = build_html(info, results, summarize(results))
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        for text in ("Alice", "Bob", "ChessLens Accuracy", "Blunder", "Best", "e4", "Qh4",
                     "Fake Engine 1", "Depth: 12", "Checkmate - White won."):
            self.assertIn(text, page)
        # Self-contained: nothing is loaded from the network.
        for marker in ("src=", "<link", "@import", "url(http", "<iframe"):
            self.assertNotIn(marker, page)

    def test_every_label_shows_its_name_not_only_a_colour(self):
        info, results = sample_game()
        page = build_html(info, results, summarize(results))
        for r in results:
            self.assertIn(r.label, page)

    def test_special_characters_are_escaped(self):
        info, results = sample_game()
        info.headers["White"] = "<b>Eve</b> & Co"
        results[0].annotations.append("<script>alert(1)</script>")
        page = build_html(info, results, summarize(results))
        self.assertNotIn("<b>Eve</b>", page)
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;b&gt;Eve&lt;/b&gt; &amp; Co", page)

    def test_opening_name_and_eco_are_shown_prominently(self):
        info, results = sample_game()
        info.headers["Opening"] = "Philidor Defense"
        info.headers["ECO"] = "C41"
        page = build_html(info, results, summarize(results))
        self.assertIn('class="opening-badge"', page)
        self.assertIn("Philidor Defense", page)
        self.assertIn('class="opening-eco">C41<', page)

    def test_opening_name_is_escaped(self):
        info, results = sample_game()
        info.headers["Opening"] = "<b>Evil</b> Opening"
        page = build_html(info, results, summarize(results))
        self.assertNotIn("<b>Evil</b>", page)

    def test_game_with_missing_metadata(self):
        _, results = sample_game()
        info = GameInfo(depth=12, multipv=3, verify_depth=16, generated_at="now")
        page = build_html(info, results, summarize(results))
        self.assertIn("Unknown", page)
        self.assertNotIn("Opening:", page)  # unavailable fields are hidden, not invented


class CsvTests(unittest.TestCase):
    def test_round_trip_with_awkward_text(self):
        info, results = sample_game()
        results[0].classification_note = 'Contains, a comma, "quotes" and\na new line'
        rows = list(csv.reader(io.StringIO(build_csv(info, results))))
        self.assertEqual(rows[0], CSV_COLUMNS)
        self.assertEqual(len(rows), len(results) + 1)
        note_column = CSV_COLUMNS.index("note")
        self.assertEqual(rows[1][note_column], 'Contains, a comma, "quotes" and\na new line')
        self.assertEqual(rows[1][CSV_COLUMNS.index("played_san")], "e4")
        self.assertEqual(rows[4][CSV_COLUMNS.index("classification")], "Blunder")

    def test_every_row_has_every_column(self):
        info, results = sample_game()
        for row in csv.reader(io.StringIO(build_csv(info, results))):
            self.assertEqual(len(row), len(CSV_COLUMNS))


class JsonTests(unittest.TestCase):
    def test_valid_json_with_expected_sections(self):
        info, results = sample_game()
        data = json.loads(build_json(info, results, summarize(results)))
        self.assertEqual(data["tool"], "ChessLens")
        self.assertEqual(data["settings"]["depth"], 12)
        self.assertEqual(len(data["moves"]), 4)
        self.assertEqual(data["moves"][3]["label"], "Blunder")
        self.assertEqual(data["moves"][0]["best_eval"], {"cp": 30, "mate": None})
        self.assertIn("label_counts", data["summary"])
        self.assertEqual(data["game"]["headers"]["White"], "Alice")


class PgnTests(unittest.TestCase):
    def test_structure_and_content(self):
        info, results = sample_game()
        text = build_annotated_pgn(info, results)
        self.assertIn('[White "Alice"]', text)
        self.assertIn('[Black "Bob"]', text)
        self.assertIn('[Result "1-0"]', text)
        self.assertIn("1. e4", text)
        self.assertIn("1... d6", text)
        self.assertIn("ChessLens: Blunder", text)
        self.assertIn("[%eval", text)
        self.assertTrue(text.rstrip().endswith("1-0"))

    def test_best_line_is_added_as_a_variation(self):
        info, results = sample_game()
        text = " ".join(build_annotated_pgn(info, results).split())  # ignore line wrapping
        self.assertIn("(1... e5 2. Nf3 Nc6)", text)   # Black's alternative, numbered correctly
        self.assertIn("(2... Nc6 3. Bb5)", text)

    def test_braces_and_parentheses_are_balanced(self):
        info, results = sample_game()
        results[0].annotations.append("odd } text { here )")
        body = build_annotated_pgn(info, results).split("\n\n", 1)[1]
        depth_brace = depth_paren = 0
        in_comment = False
        for ch in body:
            if in_comment:
                if ch == "}":
                    in_comment = False
                elif ch == "{":
                    self.fail("nested brace inside a comment")
                continue
            if ch == "{":
                in_comment = True
            elif ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren -= 1
                self.assertGreaterEqual(depth_paren, 0)
        self.assertFalse(in_comment)
        self.assertEqual(depth_paren, 0)

    def test_missing_metadata_still_gives_the_seven_tag_roster(self):
        _, results = sample_game()
        text = build_annotated_pgn(GameInfo(), results)
        for tag in ("Event", "Site", "Date", "Round", "White", "Black"):
            self.assertIn(f'[{tag} "?"]', text)
        self.assertIn('[Result "*"]', text)
        self.assertTrue(text.rstrip().endswith("*"))

    def test_quotes_in_headers_are_escaped(self):
        info, results = sample_game()
        info.headers["Event"] = 'The "Big" Open'
        self.assertIn('[Event "The \\"Big\\" Open"]', build_annotated_pgn(info, results))

    @unittest.skipUnless(HAVE_CHESS, "python-chess is not installed")
    def test_python_chess_can_read_it_back(self):
        # A real game so every move is legal.
        moves = [("e4", "White", 1), ("e5", "Black", 1), ("Nf3", "White", 2), ("Nc6", "Black", 2)]
        results = [
            make_result(cp(30), san=san, best_san=san, color=color, move_number=number, ply=i + 1,
                        best_line=[san])
            for i, (san, color, number) in enumerate(moves)
        ]
        info = GameInfo(headers={"White": "A", "Black": "B", "Result": "*"})
        game = chess.pgn.read_game(io.StringIO(build_annotated_pgn(info, results)))
        self.assertEqual(game.errors, [])
        board = game.board()
        sans = []
        for move in game.mainline_moves():
            sans.append(board.san(move))
            board.push(move)
        self.assertEqual(sans, ["e4", "e5", "Nf3", "Nc6"])
        self.assertIn("ChessLens", game.next().comment)


class WriteTests(unittest.TestCase):
    def test_all_four_formats_are_written(self):
        info, results = sample_game()
        summary = summarize(results)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "reports"
            prepare_output_dir(out)
            saved, errors = write_reports(info, results, summary, ["html", "csv", "pgn", "json"], out, "my game")
            self.assertEqual(errors, [])
            names = sorted(p.name for p in saved)
            self.assertEqual(names, ["my_game_chesslens.csv", "my_game_chesslens.html",
                                     "my_game_chesslens.json", "my_game_chesslens.pgn"])
            for path in saved:
                self.assertGreater(path.stat().st_size, 100)
            json.loads((out / "my_game_chesslens.json").read_text(encoding="utf-8"))

    def test_existing_files_are_not_overwritten_by_default(self):
        info, results = sample_game()
        summary = summarize(results)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = out / "g_chesslens.html"
            first.write_text("my own file", encoding="utf-8")
            saved, errors = write_reports(info, results, summary, ["html"], out, "g")
            self.assertEqual(first.read_text(encoding="utf-8"), "my own file")
            self.assertEqual(saved[0].name, "g_chesslens_2.html")
            saved, _ = write_reports(info, results, summary, ["html"], out, "g", overwrite=True)
            self.assertEqual(saved[0], first)
            self.assertIn("<!DOCTYPE html>", first.read_text(encoding="utf-8"))

    def test_output_path_that_is_a_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "reports"
            blocker.write_text("not a folder", encoding="utf-8")
            with self.assertRaises(ChessLensError):
                prepare_output_dir(blocker)

    def test_unwritable_target_is_reported_not_raised(self):
        info, results = sample_game()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "g_chesslens.html").mkdir()  # a folder where the file should go
            saved, errors = write_reports(info, results, summarize(results), ["html", "csv"], out, "g", overwrite=True)
            self.assertEqual(len(errors), 1)
            self.assertIn("HTML", errors[0])
            self.assertEqual([p.suffix for p in saved], [".csv"])  # the other format still worked

    def test_file_name_helpers(self):
        self.assertEqual(safe_stem("my game (1)"), "my_game_1")
        self.assertEqual(safe_stem("???"), "game")
        self.assertEqual(choose_path(Path("x"), "g", ".csv", True).name, "g_chesslens.csv")


if __name__ == "__main__":
    unittest.main()
