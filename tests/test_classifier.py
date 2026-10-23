"""Tests for classifier.py: labels, annotations and special rules.

All evaluations are from the point of view of the player who moved.
Run from the chesslens folder:  python -m unittest discover -s tests -v
"""

import unittest

from helpers import cp, make_result, sample_game  # also sets up sys.path

from classifier import (
    DEFAULT_THRESHOLDS, Thresholds, classify_move, confirm_brilliant, expected_points,
    load_thresholds, ordinary_label, result_band, thresholds_from_dict,
)
from models import ChessLensError, DeepCheck, eval_for_pgn, summarize, to_white_view
from scoring import Eval


class OrdinaryLabelTests(unittest.TestCase):
    def label_for_loss(self, loss_cp):
        return make_result(cp(0), cp(-loss_cp)).label

    def test_played_best_move_is_best(self):
        self.assertEqual(self.label_for_loss(0), "Best")

    def test_labels_follow_expected_points_loss(self):
        # From an equal position (see README table for the expected-points losses).
        expected = {20: "Excellent", 35: "Good", 80: "Inaccuracy", 150: "Mistake", 300: "Blunder"}
        for loss, label in expected.items():
            with self.subTest(loss_cp=loss):
                self.assertEqual(self.label_for_loss(loss), label)

    def test_labels_get_worse_as_loss_grows(self):
        order = ["Best", "Excellent", "Good", "Inaccuracy", "Mistake", "Blunder"]
        indexes = [order.index(self.label_for_loss(x)) for x in (0, 20, 35, 80, 150, 300, 600)]
        self.assertEqual(indexes, sorted(indexes))

    def test_matching_the_top_move_is_not_what_decides_the_label(self):
        # The played move is NOT the engine's first choice but loses almost nothing.
        r = make_result(cp(30), cp(28), candidates=[cp(30), cp(28), cp(25)])
        self.assertFalse(r.matched is True)
        self.assertEqual(r.label, "Best")

    def test_same_centipawn_loss_costs_less_when_already_winning(self):
        winning = make_result(cp(1000), cp(800)).label
        equal = make_result(cp(0), cp(-200)).label
        self.assertEqual(winning, "Good")
        self.assertEqual(equal, "Mistake")

    def test_threshold_function_is_configurable(self):
        strict = Thresholds(best_max_loss=0.0, excellent_max_loss=0.001)
        self.assertEqual(ordinary_label(0.003, strict), "Good")
        self.assertEqual(ordinary_label(0.003, DEFAULT_THRESHOLDS), "Best")

    def test_missing_engine_data_is_unclassified(self):
        r = make_result(cp(0), classify=False)
        r.best_eval = None
        classify_move(r)
        self.assertEqual(r.label, "Unclassified")
        self.assertIsNotNone(r.classification_note)

    def test_move_with_no_evaluation_after_it_and_no_candidate_is_unclassified(self):
        r = make_result(cp(0), cp(-100), candidates=[cp(0)], played_rank=None, classify=False)
        r.after_eval = None
        classify_move(r)
        self.assertEqual(r.label, "Unclassified")


class PerspectiveTests(unittest.TestCase):
    def test_black_and_white_are_classified_the_same_way(self):
        white = make_result(cp(0), cp(-150), color="White")
        black = make_result(cp(0), cp(-150), color="Black")
        self.assertEqual(white.label, black.label)
        self.assertAlmostEqual(white.ep_loss, black.ep_loss)

    def test_to_white_view_flips_only_for_black(self):
        self.assertEqual(to_white_view(Eval(cp=50), "White"), Eval(cp=50))
        self.assertEqual(to_white_view(Eval(cp=50), "Black"), Eval(cp=-50))
        self.assertEqual(to_white_view(Eval(mate=3), "Black"), Eval(mate=-3))

    def test_pgn_eval_text_is_from_whites_point_of_view(self):
        self.assertEqual(eval_for_pgn(Eval(cp=52), "White"), "0.52")
        self.assertEqual(eval_for_pgn(Eval(cp=52), "Black"), "-0.52")
        self.assertEqual(eval_for_pgn(Eval(mate=2), "White"), "#2")
        self.assertEqual(eval_for_pgn(Eval(mate=2), "Black"), "#-2")


class MateTests(unittest.TestCase):
    def test_delivering_mate_is_best_but_not_great(self):
        r = make_result(Eval(mate=1), san="Qh7#", candidates=[Eval(mate=1), cp(300)])
        self.assertEqual(r.label, "Best")
        self.assertEqual(r.accuracy, 100.0)

    def test_missing_a_forced_mate_is_flagged(self):
        r = make_result(Eval(mate=2), cp(300), candidates=[Eval(mate=2), cp(300)])
        self.assertIn("Missed forced mate in 2", r.annotations)
        self.assertIn(r.label, ("Mistake", "Blunder"))

    def test_moving_into_a_forced_mate_is_a_blunder(self):
        r = make_result(cp(0), Eval(mate=-3), candidates=[cp(0), cp(-50), Eval(mate=-3)])
        self.assertIn("Allows forced mate in 3", r.annotations)
        self.assertEqual(r.label, "Blunder")


class ForcedMoveTests(unittest.TestCase):
    def test_forced_defensive_move_is_annotated(self):
        # The only move that avoids mate; both alternatives lose by force.
        r = make_result(cp(0), candidates=[cp(0), Eval(mate=-2), Eval(mate=-3)], san="Kh1")
        self.assertIn("Forced move", r.annotations)
        self.assertEqual(r.label, "Great")  # the only good move, and it keeps the game alive

    def test_a_best_move_is_not_forced_just_because_it_is_first(self):
        r = make_result(cp(30), candidates=[cp(30), cp(28), cp(20)])
        self.assertNotIn("Forced move", r.annotations)

    def test_missing_the_only_move_is_flagged(self):
        r = make_result(cp(0), Eval(mate=-2), candidates=[cp(0), Eval(mate=-2)])
        self.assertIn("Missed the only good move", r.annotations)

    def test_only_legal_move(self):
        r = make_result(cp(-200), legal_moves=1, candidates=[cp(-200)], san="Kh1")
        self.assertIn("Only legal move", r.annotations)


class GreatTests(unittest.TestCase):
    def test_great_when_alternatives_are_much_worse(self):
        r = make_result(cp(100), candidates=[cp(100), cp(-250), cp(-300)], san="Rd1")
        self.assertEqual(r.label, "Great")

    def test_routine_best_move_is_not_great(self):
        r = make_result(cp(30), candidates=[cp(30), cp(10), cp(-5)])
        self.assertEqual(r.label, "Best")

    def test_several_nearly_equal_moves_are_not_great(self):
        r = make_result(cp(30), cp(27), candidates=[cp(30), cp(27), cp(25)])
        self.assertNotEqual(r.label, "Great")
        self.assertEqual(r.label, "Best")

    def test_recapture_is_not_great(self):
        r = make_result(cp(100), candidates=[cp(100), cp(-250), cp(-300)], is_recapture=True)
        self.assertEqual(r.label, "Best")

    def test_great_needs_alternatives(self):
        r = make_result(cp(100), candidates=[cp(100)])
        self.assertEqual(r.label, "Best")
        self.assertIn("multipv", r.classification_note)

    def test_move_that_does_not_keep_the_position_alive_is_not_great(self):
        # Best move is still hopeless (ep ~0.02): not Great.
        r = make_result(cp(-1000), candidates=[cp(-1000), cp(-1500)])
        self.assertNotEqual(r.label, "Great")


class MissTests(unittest.TestCase):
    def opponent_blunder(self):
        return make_result(cp(0), cp(-400), color="Black", move_number=1, ply=2)

    def test_miss_after_an_opponent_mistake(self):
        previous = self.opponent_blunder()
        self.assertEqual(previous.label, "Blunder")
        # We could be at +4.00 but play a move that keeps only +1.00.
        r = make_result(cp(400), cp(100), previous=previous, move_number=2, ply=3)
        self.assertEqual(r.label, "Miss")

    def test_same_move_without_an_opponent_mistake_is_not_a_miss(self):
        calm = make_result(cp(0), cp(-10), color="Black", ply=2)
        r = make_result(cp(200), cp(0), previous=calm, ply=3)
        self.assertEqual(r.label, "Mistake")

    def test_mistake_sized_loss_after_an_opponent_blunder_is_a_miss(self):
        r = make_result(cp(200), cp(0), previous=self.opponent_blunder(), ply=3)
        self.assertEqual(r.label, "Miss")

    def test_throwing_the_position_away_is_a_blunder_not_a_miss(self):
        previous = self.opponent_blunder()
        r = make_result(cp(400), cp(-500), previous=previous, ply=3)
        self.assertEqual(r.label, "Blunder")

    def test_a_miss_needs_a_real_chance(self):
        previous = self.opponent_blunder()
        r = make_result(cp(20), cp(-150), previous=previous, ply=3)  # best was only equal
        self.assertNotEqual(r.label, "Miss")


class BookTests(unittest.TestCase):
    def test_book_move_overrides_ordinary_label(self):
        r = make_result(cp(0), cp(-150), book_move=True)
        self.assertEqual(r.label, "Book")

    def test_without_a_book_nothing_is_called_book(self):
        for flag in (None, False):
            r = make_result(cp(0), cp(0), book_move=flag)
            self.assertNotEqual(r.label, "Book")


class BrilliantTests(unittest.TestCase):
    def sacrifice(self, **overrides):
        args = dict(best=cp(150), candidates=[cp(150), cp(120), cp(50)], san="Qxf7+", sacrifice=9.0)
        args.update(overrides)
        return make_result(**args)

    def deep(self, best=150, played=140, sacrifice=9.0):
        return DeepCheck(best_eval=cp(best), played_eval=cp(played), sacrifice_points=sacrifice, depth=16)

    def test_sound_sacrifice_becomes_brilliant_after_verification(self):
        r = self.sacrifice()
        self.assertTrue(r.brilliant_candidate)
        self.assertNotEqual(r.label, "Brilliant")  # not final yet
        confirm_brilliant(r, self.deep())
        self.assertEqual(r.label, "Brilliant")
        self.assertFalse(r.brilliant_candidate)

    def test_deeper_search_can_reject_the_sacrifice(self):
        r = self.sacrifice()
        confirm_brilliant(r, self.deep(best=150, played=-200))
        self.assertNotEqual(r.label, "Brilliant")
        self.assertIn("did not confirm", r.classification_note)

    def test_deeper_search_that_finds_no_sacrifice_rejects(self):
        r = self.sacrifice()
        confirm_brilliant(r, self.deep(sacrifice=1.0))
        self.assertNotEqual(r.label, "Brilliant")

    def test_forced_mate_queen_sacrifice_is_a_candidate(self):
        # Qb8+! style: mate in 2, the only other good move is only +3.35.
        r = make_result(Eval(mate=2), candidates=[Eval(mate=2), cp(335), cp(324)], san="Qb8+", sacrifice=9.0)
        self.assertTrue(r.brilliant_candidate)
        confirm_brilliant(r, DeepCheck(Eval(mate=2), Eval(mate=2), 9.0, 16))
        self.assertEqual(r.label, "Brilliant")

    def test_best_move_without_a_sacrifice_is_never_brilliant(self):
        r = self.sacrifice(sacrifice=0.0)
        self.assertFalse(r.brilliant_candidate)

    def test_small_material_loss_is_not_a_sacrifice(self):
        self.assertFalse(self.sacrifice(sacrifice=1.0).brilliant_candidate)

    def test_not_brilliant_when_already_completely_winning(self):
        r = self.sacrifice(best=cp(1500), candidates=[cp(1500), cp(1400)])
        self.assertFalse(r.brilliant_candidate)

    def test_not_brilliant_when_the_sacrifice_leaves_a_worse_position(self):
        r = self.sacrifice(best=cp(-400), candidates=[cp(-400), cp(-500)])
        self.assertFalse(r.brilliant_candidate)

    def test_a_worse_than_best_sacrifice_is_not_brilliant(self):
        r = self.sacrifice(played=cp(0), candidates=[cp(150), cp(0)])
        self.assertFalse(r.brilliant_candidate)

    def test_brilliant_needs_alternatives(self):
        r = self.sacrifice(candidates=[cp(150)])
        self.assertFalse(r.brilliant_candidate)


class SummaryTests(unittest.TestCase):
    def test_normal_game_has_both_colors(self):
        info, results = sample_game()
        summary = summarize(results)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["scored"], 4)
        self.assertEqual(sum(summary["label_counts"]["White"].values()), 2)
        self.assertEqual(sum(summary["label_counts"]["Black"].values()), 2)
        self.assertEqual(summary["label_counts"]["Total"]["Blunder"], 1)  # Black's Qh4
        self.assertGreater(summary["white_accuracy"], summary["black_accuracy"])
        self.assertAlmostEqual(
            summary["overall_accuracy"], (summary["white_accuracy"] + summary["black_accuracy"]) / 2)
        self.assertEqual(summary["accuracy_model"], "lichess-inspired-v1")

    def test_unscored_moves_are_listed(self):
        _, results = sample_game()
        results[0].accuracy = None
        results[0].note = "no data"
        summary = summarize(results)
        self.assertEqual(summary["scored"], 3)
        self.assertEqual(len(summary["unscored"]), 1)


class ExpectedPointsTests(unittest.TestCase):
    def test_range_and_mates(self):
        self.assertAlmostEqual(expected_points(cp(0)), 0.5)
        self.assertEqual(expected_points(Eval(mate=3)), 1.0)
        self.assertEqual(expected_points(Eval(mate=-3)), 0.0)


class ResultChangeTests(unittest.TestCase):
    """Classification looks at what happened to the RESULT, not only at centipawns."""

    def test_bands(self):
        self.assertEqual(result_band(0.95), "winning")
        self.assertEqual(result_band(0.5), "drawish")
        self.assertEqual(result_band(0.1), "losing")

    def test_win_turned_into_draw_is_at_least_a_mistake(self):
        # +3.0 -> +0.3: expected points 0.75 -> 0.53 (loss 0.22 is already a Blunder, so use a smaller step)
        r = make_result(cp(260), cp(100))      # 0.72 -> 0.59: loss 0.13, base label Mistake anyway
        self.assertIn("Win turned into a draw", r.annotations)
        self.assertIn(r.label, ("Mistake", "Blunder"))
        # A step of the same size inside the winning band keeps the ordinary label.
        inside = make_result(cp(560), cp(400))
        self.assertEqual(inside.band_before, "winning")
        self.assertEqual(inside.band_after, "winning")
        self.assertIn(inside.label, ("Good", "Inaccuracy"))

    def test_band_edge_crossing_upgrades_a_smaller_loss(self):
        # 0.73 -> 0.65: loss 0.08 is only an Inaccuracy, but the win became a draw.
        r = make_result(cp(275), cp(170))
        self.assertEqual(ordinary_label(r.ep_loss), "Inaccuracy")
        self.assertEqual(r.label, "Mistake")
        self.assertIn("Win turned into a draw", r.annotations)

    def test_tiny_loss_across_a_band_edge_is_not_punished(self):
        r = make_result(cp(240), cp(215))      # 0.71 -> 0.69, loss about 0.02
        self.assertEqual(r.label, "Excellent")
        self.assertNotIn("Win turned into a draw", r.annotations)

    def test_draw_turned_into_loss(self):
        r = make_result(cp(-60), cp(-250))
        self.assertIn("Draw turned into a loss", r.annotations)
        self.assertIn(r.label, ("Mistake", "Blunder"))

    def test_win_turned_into_loss_is_a_blunder(self):
        r = make_result(cp(400), cp(-400))
        self.assertEqual(r.label, "Blunder")
        self.assertIn("Win turned into a loss", r.annotations)

    def test_loss_inside_a_decided_position_is_not_a_blunder(self):
        # The result does not change, so these never become errors, unlike the same loss from an equal position.
        for before, after in ((-900, -1300), (1500, 900)):
            self.assertIn(make_result(cp(before), cp(after)).label, ("Best", "Excellent", "Good"))
        self.assertEqual(make_result(cp(0), cp(-200)).label, "Mistake")

    def test_drawish_positions_with_small_changes(self):
        for before, after in ((10, -5), (-20, -35), (30, 18)):
            self.assertIn(make_result(cp(before), cp(after)).label, ("Best", "Excellent"))


class StabilityAndExplanationTests(unittest.TestCase):
    def test_disagreeing_searches_lower_confidence_and_block_special_labels(self):
        # Great-looking move, but the next position's search says something very different.
        r = make_result(cp(100), candidates=[cp(100), cp(-250), cp(-300)], after=cp(-150))
        self.assertEqual(r.confidence, "low")
        self.assertIn("Unstable evaluation", r.annotations)
        self.assertNotEqual(r.label, "Great")

    def test_agreeing_searches_keep_normal_confidence(self):
        r = make_result(cp(100), candidates=[cp(100), cp(-250), cp(-300)], after=cp(90))
        self.assertEqual(r.confidence, "normal")
        self.assertEqual(r.label, "Great")

    def test_move_outside_the_candidates_cannot_beat_the_last_candidate(self):
        # Not a candidate; the next search is optimistic (+0.60) but the weakest candidate is only +0.10.
        r = make_result(cp(100), played=cp(60), candidates=[cp(100), cp(80), cp(10)], played_rank=None, after=cp(60))
        self.assertLessEqual(r.ep_played, expected_points(cp(10)) + 1e-9)

    def test_checkmate_delivered_counts_as_a_full_point(self):
        r = make_result(Eval(mate=1), san="Qh7#", terminal="checkmate", candidates=[Eval(mate=1), cp(200)])
        self.assertEqual(r.ep_after, 1.0)
        self.assertEqual(r.label, "Best")
        self.assertEqual(r.accuracy, 100.0)

    def test_stalemate_ending_a_winning_game_is_a_blunder(self):
        r = make_result(cp(900), san="Qg6", terminal="stalemate", candidates=[cp(900), cp(700)], played_rank=None)
        self.assertEqual(r.ep_after, 0.5)
        self.assertEqual(r.label, "Blunder")

    def test_explanation_is_built_from_numbers(self):
        r = make_result(cp(0), cp(-150))
        text = " ".join(r.explanation)
        self.assertIn("Expected points", text)
        self.assertIn("Mistake range", text)

    def test_accuracy_and_label_are_independent(self):
        # A move can be an Inaccuracy by expected points and still score a high accuracy.
        r = make_result(cp(275), cp(170))
        self.assertGreater(r.accuracy, 65)
        self.assertEqual(r.label, "Mistake")


class ConfigTests(unittest.TestCase):
    def test_thresholds_can_be_changed(self):
        strict = thresholds_from_dict({"excellent_max_loss": 0.01})
        self.assertEqual(strict.excellent_max_loss, 0.01)
        loose = make_result(cp(0), cp(-20), classify=False)
        classify_move(loose, None, strict)
        self.assertEqual(loose.label, "Good")      # 0.018 is Excellent by default

    def test_unknown_or_bad_settings_are_rejected(self):
        for bad in ({"nonsense": 1}, {"best_max_loss": "high"}, {"best_max_loss": 0.5},
                    {"winning_min_ep": 0.2}, {"ep_slope": -1}):
            with self.subTest(bad=bad):
                with self.assertRaises(ChessLensError):
                    thresholds_from_dict(bad)

    def test_load_from_file(self):
        import json, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps({"great_min_gap": 0.5}), encoding="utf-8")
            self.assertEqual(load_thresholds(str(path)).great_min_gap, 0.5)
            path.write_text("[1,2]", encoding="utf-8")
            with self.assertRaises(ChessLensError):
                load_thresholds(str(path))
        with self.assertRaises(ChessLensError):
            load_thresholds("no_such_file.json")


if __name__ == "__main__":
    unittest.main()
