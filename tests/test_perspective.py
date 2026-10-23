"""Perspective tests: White and Black must be converted correctly.

These need python-chess (pip install -r requirements.txt) and are skipped if
it is not installed. Run from the chesslens folder:
    python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    import chess
    import chess.engine
    from analyzer import pov_eval
    from scoring import Eval, score_move
    HAVE_CHESS = True
except ImportError:
    HAVE_CHESS = False


@unittest.skipUnless(HAVE_CHESS, "python-chess is not installed")
class PerspectiveTests(unittest.TestCase):
    def test_white_to_move_keeps_sign(self):
        score = chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE)
        self.assertEqual(pov_eval(score, chess.WHITE), Eval(cp=50))

    def test_black_to_move_flips_sign(self):
        # +50 for White means -50 for Black.
        score = chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE)
        self.assertEqual(pov_eval(score, chess.BLACK), Eval(cp=-50))

    def test_engine_score_given_from_blacks_side(self):
        # Stockfish reports from the side to move; same position, same meaning.
        score = chess.engine.PovScore(chess.engine.Cp(30), chess.BLACK)
        self.assertEqual(pov_eval(score, chess.BLACK), Eval(cp=30))
        self.assertEqual(pov_eval(score, chess.WHITE), Eval(cp=-30))

    def test_mate_scores_flip_correctly(self):
        score = chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)
        self.assertEqual(pov_eval(score, chess.WHITE), Eval(mate=2))
        self.assertEqual(pov_eval(score, chess.BLACK), Eval(mate=-2))

    def test_same_mistake_scores_the_same_for_white_and_black(self):
        # White to move: best +0.30, played +0.00 (White's view)
        white_best = pov_eval(chess.engine.PovScore(chess.engine.Cp(30), chess.WHITE), chess.WHITE)
        white_played = pov_eval(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE), chess.WHITE)
        # Black to move: best -0.30, played 0.00 (White's view) = the same mistake for Black
        black_best = pov_eval(chess.engine.PovScore(chess.engine.Cp(-30), chess.WHITE), chess.BLACK)
        black_played = pov_eval(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE), chess.BLACK)
        white_result = score_move(white_best, white_played, [white_best, white_played])
        black_result = score_move(black_best, black_played, [black_best, black_played])
        self.assertEqual(white_result.loss_cp, 30)
        self.assertEqual(black_result.loss_cp, 30)
        self.assertAlmostEqual(white_result.accuracy, black_result.accuracy, places=6)


if __name__ == "__main__":
    unittest.main()
