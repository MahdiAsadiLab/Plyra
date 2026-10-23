"""Tests that need python-chess (skipped if it is not installed).

They use a FAKE engine, so Stockfish is not needed. The fake engine ranks the
legal moves alphabetically and gives them decreasing scores, which lets us
check perspective handling, engine-call reuse and error handling exactly.
"""

import io
import tempfile
import unittest
from pathlib import Path

from helpers import cp  # also sets up sys.path

try:
    import chess
    import chess.engine
    import chess.pgn
    from analyzer import (
        ChessLensError, _material_balance, _sacrifice_points, analyze_game,
        describe_ending, find_stockfish, load_game,
    )
    from scoring import Eval
    HAVE_CHESS = True
except ImportError:
    HAVE_CHESS = False

SCHOLARS_MATE = """[White "Player A"]
[Black "Player B"]
[Result "1-0"]

1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0
"""


if HAVE_CHESS:
    class FakeEngine:
        """Scores the legal moves alphabetically: +0.50, +0.40, +0.30, ... (side to move)."""

        def __init__(self):
            self.calls = []

        def _score(self, board, rank):
            return chess.engine.PovScore(chess.engine.Cp(50 - 10 * rank), board.turn)

        def analyse(self, board, limit, *, multipv=None, root_moves=None, **kwargs):
            self.calls.append({"multipv": multipv, "root_moves": root_moves})
            moves = sorted(board.legal_moves, key=lambda m: m.uci())
            if root_moves is not None:
                move = root_moves[0]
                return {"score": self._score(board, moves.index(move)), "pv": [move]}
            count = multipv or 1
            infos = [{"score": self._score(board, i), "pv": [m], "multipv": i + 1}
                     for i, m in enumerate(moves[:count])]
            return infos if multipv else infos[0]


@unittest.skipUnless(HAVE_CHESS, "python-chess is not installed")
class FakeEngineTests(unittest.TestCase):
    def run_game(self, pgn_text=SCHOLARS_MATE, multipv=3):
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        engine = FakeEngine()
        stats = {}
        results = list(analyze_game(game, engine, depth=5, multipv=multipv, stats=stats))
        return results, engine, stats

    def test_every_half_move_is_analyzed_once_with_correct_colors(self):
        results, _, _ = self.run_game()
        self.assertEqual([r.played_san for r in results], ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"])
        self.assertEqual([r.color for r in results], ["White", "Black"] * 3 + ["White"])
        self.assertEqual([r.move_number for r in results], [1, 1, 2, 2, 3, 3, 4])
        self.assertEqual([r.ply for r in results], list(range(1, 8)))
        self.assertEqual(results[1].move_label, "Move 1...")

    def test_black_and_white_perspective(self):
        results, _, _ = self.run_game()
        for r in results:
            # The engine's top move is +0.50 for the side to move, so +50 for the mover.
            self.assertEqual(r.best_eval, Eval(cp=50))
        self.assertEqual(results[0].best_score_text, "+0.50")   # White to move
        self.assertEqual(results[1].best_score_text, "-0.50")   # Black to move: shown from White's side
        # After a move the OTHER side is to move and is +0.50, so the mover sees -0.50.
        for r in results[:-1]:
            self.assertEqual(r.after_eval, Eval(cp=-50))
        # Win% before 54.6, after 45.4 for the mover: the same for White's and Black's moves.
        self.assertAlmostEqual(results[0].win_after, results[1].win_after)

    def test_each_position_is_searched_once(self):
        results, engine, stats = self.run_game()
        self.assertEqual(len(engine.calls), 7)                                # positions 0..6; the mate is not searched
        self.assertTrue(all(call["root_moves"] is None for call in engine.calls))
        self.assertEqual(stats, {"positions_analyzed": 7, "cache_hits": 0})

    def test_repeated_positions_are_reused(self):
        results, engine, stats = self.run_game("[Result \"*\"]\n\n1. Nf3 Nf6 2. Ng1 Ng8 *\n")
        self.assertEqual(len(results), 4)
        self.assertEqual(stats["positions_analyzed"], 4)    # the 5th position equals the starting position
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(len(engine.calls), 4)

    def test_position_chain_and_fens(self):
        results, _, _ = self.run_game()
        self.assertTrue(results[0].fen_before.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"))
        self.assertTrue(results[0].fen_after.startswith("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b"))
        for before, after in zip(results, results[1:]):
            self.assertEqual(before.fen_after, after.fen_before)            # the board advanced exactly once per move

    def test_scores_labels_and_terminal_move(self):
        results, _, _ = self.run_game()
        for r in results:
            self.assertIsNotNone(r.accuracy)
            self.assertIsNotNone(r.ep_loss)
            self.assertNotEqual(r.label, "Unclassified")
            self.assertTrue(0.0 <= r.accuracy <= 100.0)
        last = results[-1]
        self.assertEqual(last.after_terminal, "checkmate")
        self.assertIsNone(last.after_eval)
        self.assertEqual(last.win_after, 100.0)
        self.assertEqual(last.accuracy, 100.0)
        self.assertEqual(last.played_line, ["Qxf7#"])
        self.assertEqual(len(results[0].played_line), 2)   # played move + the engine's reply

    def test_multipv_one_still_works(self):
        results, _, _ = self.run_game(multipv=1)
        self.assertEqual(len(results), 7)

    def test_helpers_on_real_boards(self):
        board = chess.Board("3qk3/8/8/3p4/8/4N3/8/4K3 w - - 0 1")
        line = [chess.Move.from_uci(u) for u in ("e3d5", "d8d5", "e1f1")]
        self.assertEqual(_material_balance(board, chess.WHITE), 3 - 10)
        self.assertEqual(_sacrifice_points(board, line, chess.WHITE), 2.0)  # +1 pawn, -3 knight
        self.assertEqual(_sacrifice_points(board, line[:1], chess.WHITE), 0.0)  # too short to judge
        quiet = [chess.Move.from_uci("e1f1"), chess.Move.from_uci("d8d7")]
        self.assertEqual(_sacrifice_points(board, quiet, chess.WHITE), 0.0)

    def test_describe_ending(self):
        game = chess.pgn.read_game(io.StringIO(SCHOLARS_MATE))
        self.assertEqual(describe_ending(game), "Checkmate - White won.")

    def test_command_line_stays_backward_compatible(self):
        import sys
        import main
        old = sys.argv
        try:
            sys.argv = ["main.py", "games/g.pgn", "--stockfish", "engines/sf.exe", "--depth", "12"]
            args = main.parse_args()
        finally:
            sys.argv = old
        self.assertEqual((args.pgn, args.stockfish, args.depth), ("games/g.pgn", "engines/sf.exe", 12))
        self.assertEqual(args.format, ["html"])
        self.assertEqual(args.output_dir, "reports")
        self.assertFalse(args.no_report)


@unittest.skipUnless(HAVE_CHESS, "python-chess is not installed")
class InputErrorTests(unittest.TestCase):
    def write(self, folder, name, text):
        path = Path(folder) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_file(self):
        with self.assertRaises(ChessLensError):
            load_game(Path("definitely_not_here.pgn"))

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ChessLensError):
                load_game(self.write(tmp, "empty.pgn", ""))

    def test_garbage_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ChessLensError):
                load_game(self.write(tmp, "bad.pgn", "this is not chess at all"))

    def test_illegal_first_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ChessLensError):
                load_game(self.write(tmp, "bad.pgn", '[Event "x"]\n\n1. Ke4 e5 *\n'))

    def test_valid_game_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = load_game(self.write(tmp, "ok.pgn", SCHOLARS_MATE))
            self.assertEqual(game.headers["White"], "Player A")

    def test_missing_stockfish_path(self):
        with self.assertRaises(ChessLensError):
            find_stockfish("no/such/stockfish.exe")

    def test_stockfish_path_that_is_a_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ChessLensError):
                find_stockfish(tmp)


if __name__ == "__main__":
    unittest.main()
