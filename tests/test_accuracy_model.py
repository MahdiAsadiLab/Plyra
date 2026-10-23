"""Tests for the Lichess-inspired accuracy model (scoring.py).

Expected numbers are recomputed here from the documented constants with plain
math, so the tests do not just repeat the implementation's code path.
"""

import math
import unittest

import helpers  # noqa: F401  (sets up sys.path)

from scoring import (
    ACCURACY_MODEL, Eval, game_accuracies, harmonic_mean, lichess_move_accuracy,
    volatility_weights, weighted_mean, win_percent, window_size,
)


def reference_accuracy(drop):
    """The documented Lichess formula written out by hand."""
    return min(100.0, max(0.0, 103.1668100711649 * math.exp(-0.04354415386753951 * drop) - 3.166924740191411 + 1))


def win(cp):
    return 100 / (1 + math.exp(-0.00368208 * cp))


class MoveAccuracyTests(unittest.TestCase):
    def test_model_name(self):
        self.assertEqual(ACCURACY_MODEL, "lichess-inspired-v1")

    def test_win_percent_matches_both_published_forms(self):
        for cp in (-1000, -300, -50, 0, 25, 100, 400, 1500):
            alt = 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
            self.assertAlmostEqual(win_percent(Eval(cp=cp)), alt, places=9)
        self.assertAlmostEqual(win_percent(Eval(cp=100)), 59.10, places=2)

    def test_no_drop_or_gain_is_100(self):
        self.assertEqual(lichess_move_accuracy(50, 50), 100.0)
        self.assertEqual(lichess_move_accuracy(50, 65), 100.0)   # the player improved their position

    def test_formula_values(self):
        for drop in (1, 5, 10, 25, 40, 80):
            self.assertAlmostEqual(lichess_move_accuracy(80, 80 - drop), reference_accuracy(drop), places=9)
        self.assertAlmostEqual(lichess_move_accuracy(60, 50), 64.58, places=2)
        self.assertAlmostEqual(lichess_move_accuracy(50, 10), 15.91, places=2)

    def test_tiny_drops_are_forgiven_by_the_uncertainty_bonus(self):
        self.assertEqual(lichess_move_accuracy(50, 49.9), 100.0)

    def test_accuracy_decreases_as_the_drop_grows_and_stays_in_range(self):
        values = [lichess_move_accuracy(100, 100 - d) for d in range(0, 101, 5)]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertTrue(all(0.0 <= v <= 100.0 for v in values))

    def test_evaluation_changes_from_the_specification(self):
        # Same player's point of view, centipawns before -> after the move.
        gain_a = lichess_move_accuracy(win(50), win(90))      # +0.5 -> +0.9
        gain_b = lichess_move_accuracy(win(210), win(320))    # +2.1 -> +3.2
        small = lichess_move_accuracy(win(20), win(-30))      # +0.2 -> -0.3
        big = lichess_move_accuracy(win(500), win(300))       # +5.0 -> +3.0
        self.assertEqual((gain_a, gain_b), (100.0, 100.0))
        self.assertAlmostEqual(small, reference_accuracy(win(20) - win(-30)), places=9)
        self.assertAlmostEqual(big, reference_accuracy(win(500) - win(300)), places=9)
        self.assertLess(big, small)      # losing 2.0 pawns costs more than losing 0.5 pawns ...
        equal_loss = lichess_move_accuracy(win(0), win(-200))
        self.assertGreater(big, equal_loss)   # ... but less than losing the same 2.0 pawns from an equal position

    def test_same_pawn_loss_costs_more_in_an_equal_position(self):
        equal = lichess_move_accuracy(win(0), win(-200))
        winning = lichess_move_accuracy(win(800), win(600))
        losing = lichess_move_accuracy(win(-600), win(-800))
        self.assertLess(equal, winning)
        self.assertLess(equal, losing)

    def test_mates_are_separate_from_centipawns(self):
        self.assertEqual(win_percent(Eval(mate=2)), 100.0)
        self.assertEqual(win_percent(Eval(mate=-2)), 0.0)
        self.assertEqual(lichess_move_accuracy(100.0, 0.0), reference_accuracy(100.0))   # mate thrown away
        self.assertEqual(lichess_move_accuracy(0.0, 0.0), 100.0)                          # already mated: no drop

    def test_extreme_decisive_positions_do_not_break_anything(self):
        for cp in (-30000, 30000):
            value = win_percent(Eval(cp=cp))
            self.assertTrue(0.0 <= value <= 100.0)
        self.assertEqual(lichess_move_accuracy(win(2500), win(2000)), 100.0)   # still totally winning


class WeightTests(unittest.TestCase):
    def test_window_size(self):
        self.assertEqual([window_size(n) for n in (1, 19, 20, 49, 80, 400)], [2, 2, 2, 4, 8, 8])

    def test_one_weight_per_move(self):
        for n in (1, 2, 3, 9, 20, 55, 120):
            self.assertEqual(len(volatility_weights([50.0] * (n + 1))), n)

    def test_calm_game_has_the_minimum_weight(self):
        self.assertEqual(set(volatility_weights([50.0] * 11)), {0.5})

    def test_big_swings_are_capped_at_12(self):
        weights = volatility_weights([50, 50, 50, 10])
        self.assertEqual(weights, [0.5, 0.5, 12.0])

    def test_means(self):
        self.assertAlmostEqual(weighted_mean([(100, 1), (50, 3)]), 62.5)
        self.assertAlmostEqual(harmonic_mean([100, 50]), 66.6666666667)
        self.assertEqual(harmonic_mean([100, 0]), 0.0)
        self.assertIsNone(harmonic_mean([]))
        self.assertIsNone(weighted_mean([]))


class GameAccuracyTests(unittest.TestCase):
    def test_flat_game_is_100_for_both(self):
        self.assertEqual(game_accuracies([50, 50, 50, 50]), {"White": 100.0, "Black": 100.0})

    def test_white_blunder_hand_calculation(self):
        # Win% of White: 50, 50, 50, 10. White moves are pairs (50,50) and (50,10).
        # accuracies 100 (weight 0.5) and 15.909 (weight 12).
        weighted = (100 * 0.5 + 15.909 * 12) / 12.5
        harmonic = 2 / (1 / 100 + 1 / 15.909)
        expected = (weighted + harmonic) / 2          # about 23.36
        result = game_accuracies([50, 50, 50, 10])
        self.assertAlmostEqual(result["White"], expected, delta=0.02)
        self.assertEqual(result["Black"], 100.0)

    def test_same_blunder_by_black_gives_the_same_accuracy(self):
        white = game_accuracies([50, 50, 50, 10])["White"]
        black = game_accuracies([50, 50, 50, 50, 90])["Black"]    # White's Win% rises = Black blundered
        self.assertAlmostEqual(white, black, places=9)

    def test_game_accuracy_is_not_the_plain_mean(self):
        sequence = [50, 50, 50, 10]
        plain = (100 + lichess_move_accuracy(50, 10)) / 2
        self.assertLess(game_accuracies(sequence)["White"], plain)    # blunders weigh more

    def test_deterministic(self):
        sequence = [50, 53, 49, 60, 30, 28, 70, 90, 95, 99, 100]
        self.assertEqual(game_accuracies(sequence), game_accuracies(list(sequence)))

    def test_game_starting_with_black_to_move(self):
        result = game_accuracies([50, 50, 10], start_color="Black")   # Black moves first, then White drops 40
        self.assertEqual(result["Black"], 100.0)
        self.assertLess(result["White"], 100.0)

    def test_missing_evaluations_are_skipped_not_treated_as_zero(self):
        result = game_accuracies([50, None, 50, 50, 50])
        self.assertEqual(result["White"], 100.0)
        result = game_accuracies([None, None, None])
        self.assertEqual(result, {"White": None, "Black": None})
        self.assertEqual(game_accuracies([]), {"White": None, "Black": None})

    def test_long_game(self):
        sequence = [50 + 10 * math.sin(i / 3) for i in range(201)]
        result = game_accuracies(sequence)
        self.assertTrue(all(0 <= v <= 100 for v in result.values()))


if __name__ == "__main__":
    unittest.main()
