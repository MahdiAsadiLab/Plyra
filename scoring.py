"""ChessLens Accuracy: turn engine evaluations into a 0-100 move score.

This file is pure math. It does NOT import python-chess and never talks to
Stockfish, so it is easy to test. Everything here uses the point of view of
the player who is making the move (the "mover"):

    positive evaluation  = good for the mover
    negative evaluation  = bad for the mover

Converting Stockfish's White-based scores into the mover's point of view is
done in analyzer.py (function pov_eval).

How the score is built (see README for the full explanation):

    1. Convert each evaluation into a WIN PERCENT (0-100) with a logistic curve.
    2. win drop = win percent of the best move - win percent of the played move.
    3. Forgive a tiny drop (engine noise), then turn the rest into an accuracy
       with a smooth decay curve:  100 * exp(-(drop / DECAY_SCALE) ** DECAY_SHAPE)
    4. Candidate moves are used only to describe the position (and to widen the
       noise tolerance when many moves are equally good).

ChessLens Accuracy is a custom, experimental metric. It is NOT Chess.com's
Accuracy and does not try to reproduce it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

# --- Tunable parameters (change these to experiment) ----------------------

# Logistic slope: how quickly centipawns turn into winning chances.
# With 0.00368208, +100 cp is about 59% and +300 cp is about 75%.
# (This constant comes from a fit to real games published by Lichess.)
CP_TO_WIN_SLOPE = 0.00368208

# Decay curve: accuracy = 100 * exp(-(effective_drop / DECAY_SCALE) ** DECAY_SHAPE)
DECAY_SCALE = 20.0   # larger = more forgiving
DECAY_SHAPE = 1.3    # > 1 : tiny drops cost almost nothing, big drops cost a lot

# Win-percent drops smaller than this are treated as engine noise.
BASE_TOLERANCE = 0.5   # about 14 cp near an equal position
FLAT_TOLERANCE = 1.0   # used when several candidate moves are nearly identical

# Thresholds (in win-percent points) for describing a position.
ONLY_MOVE_GAP = 15.0   # best move is this far ahead of the 2nd best
CLEAR_BEST_GAP = 5.0
FLAT_SPREAD = 2.0      # best and last candidate are within this -> "flat"


# --- Data types ----------------------------------------------------------

@dataclass(frozen=True)
class Eval:
    """An evaluation from the mover's point of view.

    Exactly one field is set:
        cp   - centipawns (100 = one pawn), for ordinary positions
        mate - moves until checkmate. Positive: the mover mates the opponent.
               Negative: the mover gets mated.
    """

    cp: Optional[int] = None
    mate: Optional[int] = None

    def __post_init__(self) -> None:
        if (self.cp is None) == (self.mate is None):
            raise ValueError("Eval needs exactly one of cp or mate.")

    @property
    def is_mate(self) -> bool:
        return self.mate is not None


@dataclass(frozen=True)
class MoveScore:
    loss_cp: Optional[int]  # centipawn loss; None when a forced mate is involved
    win_drop: float         # win-percent points lost (never negative)
    accuracy: float         # 0-100
    context: str            # plain-English description of the position


# --- Step 1: evaluation -> win percent -----------------------------------

def win_percent(ev: Eval) -> float:
    """Winning chances (0-100) for the mover.

    Forced mates are handled separately from centipawns: a mate for the mover
    is 100, a mate against the mover is 0.
    """
    if ev.mate is not None:
        return 100.0 if ev.mate > 0 else 0.0
    return 100.0 / (1.0 + math.exp(-CP_TO_WIN_SLOPE * ev.cp))


def loss_in_centipawns(best: Eval, played: Eval) -> Optional[int]:
    """How many centipawns the mover gave up. None if a mate score is involved.

    Positive means the played move was worse than the best move. A small
    negative number (engine noise) is clamped to 0.
    """
    if best.is_mate or played.is_mate:
        return None
    return max(0, best.cp - played.cp)


# --- Step 2: describe the position using the candidate moves -------------

def describe_position(candidates: Sequence[Eval]) -> tuple[str, float]:
    """Return (description, noise tolerance) from the engine's candidate list.

    `candidates` must be sorted best first. This only describes the position
    and slightly widens the noise tolerance; it never decides the score alone.
    """
    wins = [win_percent(ev) for ev in candidates]
    if len(wins) < 2:
        return "Only one candidate available", BASE_TOLERANCE

    gap = wins[0] - wins[1]
    spread = wins[0] - wins[-1]

    if gap >= ONLY_MOVE_GAP:
        return "Critical position: the best move is far ahead of the alternatives", BASE_TOLERANCE
    if gap >= CLEAR_BEST_GAP:
        return "The best move is clearly better than the alternatives", BASE_TOLERANCE
    if spread < FLAT_SPREAD:
        return "Several moves are nearly equal", FLAT_TOLERANCE
    return "Normal position", BASE_TOLERANCE


# --- Step 3: win drop -> accuracy ----------------------------------------

def accuracy_from_win_drop(win_drop: float, tolerance: float = BASE_TOLERANCE) -> float:
    """Convert a win-percent drop into an accuracy between 0 and 100."""
    effective = max(0.0, win_drop - tolerance)
    raw = 100.0 * math.exp(-((effective / DECAY_SCALE) ** DECAY_SHAPE))
    return min(100.0, max(0.0, raw))


# --- Putting it together --------------------------------------------------

def score_move(best: Eval, played: Eval, candidates: Sequence[Eval]) -> MoveScore:
    """Score one played move.

    best       evaluation of the engine's best move (mover's point of view)
    played     evaluation after the move that was actually played
    candidates evaluations of the engine's top candidate moves, best first
    """
    context, tolerance = describe_position(candidates if candidates else [best])
    win_drop = max(0.0, win_percent(best) - win_percent(played))
    accuracy = accuracy_from_win_drop(win_drop, tolerance)
    return MoveScore(
        loss_cp=loss_in_centipawns(best, played),
        win_drop=win_drop,
        accuracy=accuracy,
        context=context,
    )


def mean_accuracy(values: Sequence[float]) -> Optional[float]:
    """Plain arithmetic mean, or None if there is nothing to average."""
    if not values:
        return None
    return sum(values) / len(values)


# ==========================================================================
# ChessLens Accuracy model "lichess-inspired-v1"
# ==========================================================================
#
# This is a re-implementation of the method Lichess documents publicly:
#   https://lichess.org/page/accuracy
#   https://github.com/lichess-org/lila (modules/analyse/src/main/AccuracyPercent.scala,
#   commit 2e653ad1e2b9fad31b4a092394019ef8fafdedb8)
# It is NOT Chess.com's CAPS2 (Chess.com has not published CAPS2's formulas).
#
#   1. Win%      = 100 / (1 + exp(-0.00368208 * cp))          (see win_percent)
#   2. Move accuracy compares Win% before and after the move, from the point
#      of view of the player who moved:
#         if after >= before:  100
#         else:  103.1668100711649 * exp(-0.04354415386753951 * (before - after))
#                - 3.166924740191411 + 1          (the +1 is Lichess's "uncertainty bonus")
#         result is limited to 0..100
#   3. Game accuracy of one player = average of
#         a) the volatility-weighted mean of that player's move accuracies and
#         b) the harmonic mean of that player's move accuracies.
#      Weights come from sliding windows over the Win% of ALL positions of the
#      game (both players): window size = clamp(number_of_moves // 10, 2, 8);
#      weight = population standard deviation of the window, clamped to 0.5..12.
#
# Known differences from Lichess (kept on purpose, all documented in the README):
#   * Lichess uses a constant evaluation for the starting position; ChessLens
#     uses the engine's own evaluation of it.
#   * Mate scores: ChessLens maps mate for a player to 100 Win% and mate against
#     to 0 (see win_percent); Lichess converts them to a capped centipawn value.
#   * Engine, depth and search limits differ, so evaluations differ.

ACCURACY_MODEL = "lichess-inspired-v1"
LEGACY_ACCURACY_MODEL = "chesslens-v0"

LICHESS_ACC_A = 103.1668100711649
LICHESS_ACC_K = 0.04354415386753951
LICHESS_ACC_B = -3.166924740191411
LICHESS_ACC_BONUS = 1.0           # "uncertainty bonus (due to imperfect analysis)"
VOLATILITY_MIN = 0.5
VOLATILITY_MAX = 12.0
WINDOW_MIN = 2
WINDOW_MAX = 8


def lichess_move_accuracy(win_before: float, win_after: float) -> float:
    """Accuracy (0-100) of one move from the mover's Win% before and after it."""
    if win_after >= win_before:
        return 100.0
    drop = win_before - win_after
    raw = LICHESS_ACC_A * math.exp(-LICHESS_ACC_K * drop) + LICHESS_ACC_B + LICHESS_ACC_BONUS
    return min(100.0, max(0.0, raw))


def window_size(num_moves: int) -> int:
    """Sliding-window size used for the volatility weights."""
    return max(WINDOW_MIN, min(WINDOW_MAX, num_moves // 10))


def _population_std(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _sliding(values: Sequence, size: int) -> list[list]:
    """Sliding windows with Scala semantics: a short list gives one window."""
    values = list(values)
    if not values:
        return []
    if len(values) < size:
        return [values]
    return [values[i:i + size] for i in range(len(values) - size + 1)]


def volatility_weights(win_percents: Sequence[Optional[float]]) -> list[float]:
    """One weight per move, from the Win% of the positions 0..N (White's point of view).

    Positions with no evaluation (None) are left out of their window.
    """
    values = list(win_percents)
    num_moves = len(values) - 1
    if num_moves < 1:
        return []
    size = window_size(num_moves)
    leading = [values[:size]] * max(0, min(size, len(values)) - 2)
    windows = leading + _sliding(values, size)
    weights = []
    for window in windows:
        std = _population_std([v for v in window if v is not None])
        weights.append(min(VOLATILITY_MAX, max(VOLATILITY_MIN, std if std is not None else 0.0)))
    return weights


def weighted_mean(pairs: Sequence[tuple[float, float]]) -> Optional[float]:
    total = sum(weight for _, weight in pairs)
    if not pairs or total <= 0:
        return None
    return sum(value * weight for value, weight in pairs) / total


def harmonic_mean(values: Sequence[float]) -> Optional[float]:
    """Harmonic mean; it is 0 if any value is 0 (the limit of the formula)."""
    if not values:
        return None
    if any(v <= 0 for v in values):
        return 0.0
    return len(values) / sum(1.0 / v for v in values)


def game_accuracies(
    win_percents_white: Sequence[Optional[float]],
    start_color: str = "White",
) -> dict[str, Optional[float]]:
    """Game accuracy of White and Black.

    win_percents_white: Win% of positions 0..N from White's point of view
    (position 0 = the position before the first move). Moves whose before/after
    evaluation is missing are skipped.
    """
    wp = list(win_percents_white)
    weights = volatility_weights(wp)
    collected: dict[str, list[tuple[float, float]]] = {"White": [], "Black": []}
    for i, weight in enumerate(weights):  # zip semantics: stops at the shorter list
        if i + 1 >= len(wp):
            break
        previous, following = wp[i], wp[i + 1]
        if previous is None or following is None:
            continue
        white_moves = (i % 2 == 0) == (start_color == "White")
        if white_moves:
            accuracy = lichess_move_accuracy(previous, following)
        else:
            accuracy = lichess_move_accuracy(following, previous)
        collected["White" if white_moves else "Black"].append((accuracy, weight))

    result: dict[str, Optional[float]] = {}
    for color, pairs in collected.items():
        weighted = weighted_mean(pairs)
        harmonic = harmonic_mean([accuracy for accuracy, _ in pairs])
        result[color] = None if weighted is None or harmonic is None else (weighted + harmonic) / 2
    return result


# --------------------------------------------------------------------------
# Expected points
# --------------------------------------------------------------------------
#
# ChessLens treats the Lichess Win% curve (divided by 100) as an "expected
# points" estimate in [0, 1] for the player. It is NOT a calibrated
# P(win) + 0.5 * P(draw): the curve was fitted by Lichess on 2300-rated games.
# The model name is recorded in every report.

EXPECTED_POINTS_MODEL = "lichess-logistic-v1"


def expected_points_from_cp(cp: float, slope: float = CP_TO_WIN_SLOPE) -> float:
    return 1.0 / (1.0 + math.exp(-slope * cp))


def expected_points(ev: Eval, slope: float = CP_TO_WIN_SLOPE) -> float:
    """Expected points (0-1) for the player the Eval belongs to. Mates are 1 or 0."""
    if ev.mate is not None:
        return 1.0 if ev.mate > 0 else 0.0
    return expected_points_from_cp(ev.cp, slope)
