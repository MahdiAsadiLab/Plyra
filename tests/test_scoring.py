"""Tests for scoring.py (pure math; no Stockfish or python-chess needed).

Run from the chesslens folder:
    python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scoring import (  # noqa: E402
    Eval,
    accuracy_from_win_drop,
    describe_position,
    loss_in_centipawns,
    mean_accuracy,
    score_move,
    win_percent,
)


def cp(value: int) -> Eval:
    return Eval(cp=value)


class WinPercentTests(unittest.TestCase):
    def test_equal_position_is_fifty_percent(self):
        self.assertAlmostEqual(win_percent(cp(0)), 50.0)

    def test_symmetry(self):
        self.assertAlmostEqual(win_percent(cp(150)) + win_percent(cp(-150)), 100.0)

    def test_mates_are_separate_from_centipawns(self):
        self.assertEqual(win_percent(Eval(mate=3)), 100.0)
        self.assertEqual(win_percent(Eval(mate=-3)), 0.0)

    def test_eval_needs_exactly_one_field(self):
        with self.assertRaises(ValueError):
            Eval()
        with self.assertRaises(ValueError):
            Eval(cp=10, mate=2)


class ScenarioTests(unittest.TestCase):
    # 1. The played move is the engine's best move.
    def test_best_move_scores_100(self):
        s = score_move(cp(35), cp(35), [cp(35), cp(10), cp(-20)])
        self.assertEqual(s.loss_cp, 0)
        self.assertEqual(s.accuracy, 100.0)

    # 2. The played move is almost as good as the best move.
    def test_almost_as_good_scores_high(self):
        s = score_move(cp(35), cp(30), [cp(35), cp(30), cp(-60)])
        self.assertEqual(s.loss_cp, 5)
        self.assertGreater(s.accuracy, 99.0)

    # 3. The played move is significantly worse.
    def test_significantly_worse_scores_low(self):
        s = score_move(cp(0), cp(-200), [cp(0), cp(-60), cp(-200)])
        self.assertEqual(s.loss_cp, 200)
        self.assertLess(s.accuracy, 50.0)

    def test_loss_grows_progressively(self):
        scores = [score_move(cp(0), cp(-d), [cp(0), cp(-d)]).accuracy
                  for d in (0, 25, 50, 100, 200, 300, 500)]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(set(scores)), len(scores))  # strictly decreasing

    # 4. Several candidate moves have nearly equal evaluations.
    def test_flat_position_is_described_and_more_tolerant(self):
        text, tolerance = describe_position([cp(30), cp(25), cp(20)])
        self.assertIn("nearly equal", text)
        _, normal_tolerance = describe_position([cp(30), cp(-10), cp(-40)])
        self.assertGreater(tolerance, normal_tolerance)

    # 5. The best move is clearly better than the alternatives.
    def test_clear_best_move_is_described(self):
        text, _ = describe_position([cp(0), cp(-80), cp(-95)])
        self.assertIn("clearly better", text)
        text, _ = describe_position([cp(200), cp(-100), cp(-150)])
        self.assertIn("Critical", text)

    def test_context_does_not_replace_the_played_moves_loss(self):
        # Same candidate gap, but different played moves: the played move decides.
        cands = [cp(0), cp(-80), cp(-95)]
        best_played = score_move(cp(0), cp(0), cands)
        second_played = score_move(cp(0), cp(-80), cands)
        self.assertEqual(best_played.accuracy, 100.0)
        self.assertLess(second_played.accuracy, 85.0)

    # 7. The engine reports a forced checkmate.
    def test_playing_the_forced_mate_scores_100(self):
        s = score_move(Eval(mate=2), Eval(mate=2), [Eval(mate=2), cp(300)])
        self.assertEqual(s.accuracy, 100.0)
        self.assertIsNone(s.loss_cp)  # no centipawn number for a mate

    def test_missing_a_forced_mate_is_penalized(self):
        s = score_move(Eval(mate=2), cp(300), [Eval(mate=2), cp(300)])
        self.assertLess(s.accuracy, 40.0)
        self.assertGreater(s.accuracy, 0.0)

    # 8. A move leads to a forced mate for the opponent.
    def test_allowing_forced_mate_scores_near_zero(self):
        s = score_move(cp(0), Eval(mate=-3), [cp(0), cp(-50), Eval(mate=-3)])
        self.assertLess(s.accuracy, 5.0)
        self.assertGreaterEqual(s.accuracy, 0.0)

    def test_already_lost_by_force_does_not_crash(self):
        s = score_move(Eval(mate=-4), Eval(mate=-2), [Eval(mate=-4), Eval(mate=-2)])
        self.assertEqual(s.accuracy, 100.0)

    # Positions that are already won / lost.
    def test_big_loss_inside_a_crushing_position_is_forgiven(self):
        crushing = score_move(cp(1000), cp(800), [cp(1000), cp(800)]).accuracy
        equal = score_move(cp(0), cp(-200), [cp(0), cp(-200)]).accuracy
        self.assertGreater(crushing, equal + 30)


class RangeAndHelperTests(unittest.TestCase):
    def test_accuracy_always_between_0_and_100(self):
        for drop in (-50.0, 0.0, 0.3, 5.0, 50.0, 100.0, 1e6):
            value = accuracy_from_win_drop(drop)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 100.0)

    def test_noise_cannot_give_negative_loss(self):
        # Played move looks 10 cp BETTER than "best" (search noise).
        self.assertEqual(loss_in_centipawns(cp(20), cp(30)), 0)
        self.assertEqual(score_move(cp(20), cp(30), [cp(20)]).accuracy, 100.0)

    def test_hand_worked_values(self):
        def acc(loss):
            return score_move(cp(0), cp(-loss), [cp(0), cp(-loss)]).accuracy
        # Starting from an equal position (these values are quoted in the README).
        self.assertAlmostEqual(acc(25), 95.7, places=1)
        self.assertAlmostEqual(acc(50), 88.1, places=1)
        self.assertAlmostEqual(acc(100), 71.6, places=1)
        self.assertAlmostEqual(acc(200), 44.2, places=1)
        self.assertAlmostEqual(acc(300), 27.0, places=1)

    def test_mean_accuracy(self):
        self.assertEqual(mean_accuracy([100.0, 50.0]), 75.0)
        self.assertIsNone(mean_accuracy([]))


if __name__ == "__main__":
    unittest.main()
