"""Plain data containers shared by analyzer, classifier and reports.

This file does not import python-chess, so everything built on it (the
classifier, the report writers and their tests) can be tested without
Stockfish or python-chess.

The single definitions of MoveResult, GameInfo and ChessLensError live HERE.
Every other module imports them from this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from scoring import (
    ACCURACY_MODEL,
    EXPECTED_POINTS_MODEL,
    Eval,
    game_accuracies,
)

# Every classification label ChessLens can produce, in display order.
LABELS = [
    "Brilliant",
    "Great",
    "Best",
    "Excellent",
    "Good",
    "Book",
    "Inaccuracy",
    "Mistake",
    "Miss",
    "Blunder",
    "Unclassified",
]

# Labels that count as "errors" in filters and summaries.
ERROR_LABELS = ("Inaccuracy", "Mistake", "Miss", "Blunder")


class ChessLensError(Exception):
    """A problem we can explain to the user in plain language."""


@dataclass
class DeepCheck:
    """Result of the deeper engine check used to verify a possible Brilliant move.

    Evaluations are from the point of view of the player who moved.
    """

    best_eval: Eval
    played_eval: Eval
    sacrifice_points: float  # material given up (in pawns) along the played line
    depth: int


@dataclass
class MoveResult:
    """Everything we know about one half-move (one player's move).

    Perspective rule: every Eval and every win_* / ep_* number is from the point
    of view of the player who made the move. Fields ending in "_text" are the
    only White-perspective values, because they are meant for people to read.
    """

    # --- identity -------------------------------------------------------
    ply: int                        # 1 = White's first move, 2 = Black's first move, ...
    move_number: int                # chess move number (1, 1, 2, 2, ...)
    color: str                      # "White" or "Black"
    move_label: str                 # "Move 1" for White, "Move 1..." for Black
    played_san: str                 # e.g. "Nf3"
    played_uci: str                 # e.g. "g1f3"
    fen_before: str = ""            # position BEFORE the move
    fen_after: str = ""             # position AFTER the move

    # --- engine facts ----------------------------------------------------
    depth: int = 0                  # search depth used for the evaluations
    best_san: Optional[str] = None
    best_uci: Optional[str] = None
    matched: Optional[bool] = None  # played move == engine's first choice
    best_eval: Optional[Eval] = None            # evaluation of the position BEFORE the move
    candidate_evals: list[Eval] = field(default_factory=list)  # top candidates, best first
    played_rank: Optional[int] = None           # index in the candidate list, None if not a candidate
    played_candidate_eval: Optional[Eval] = None  # eval of the played move in the SAME search as best_eval
    after_eval: Optional[Eval] = None           # evaluation of the position AFTER the move
    after_terminal: Optional[str] = None        # "checkmate", "stalemate" or "draw" if the game ended
    best_score_text: Optional[str] = None       # White's perspective
    played_score_text: Optional[str] = None     # White's perspective (position after the move)
    candidates: list[str] = field(default_factory=list)  # e.g. ["Nf3 (+0.30)"]
    best_line: list[str] = field(default_factory=list)   # engine's best continuation (SAN)
    played_line: list[str] = field(default_factory=list)  # played move + engine's reply line (SAN)
    legal_moves: int = 0
    is_recapture: bool = False
    sacrifice_points: float = 0.0   # material the mover gives up along the played line

    # --- accuracy model (scoring.py) --------------------------------------
    win_before: Optional[float] = None  # Win% (0-100) before the move
    win_after: Optional[float] = None   # Win% (0-100) after the move
    accuracy: Optional[float] = None    # move accuracy 0-100, None = could not be scored
    loss_cp: Optional[int] = None       # centipawn loss; None when a forced mate is involved
    context: Optional[str] = None       # description of the position
    note: Optional[str] = None          # why the move could not be scored

    # --- classification (classifier.py) -----------------------------------
    ep_before: Optional[float] = None   # expected points (0-1) before the move
    ep_after: Optional[float] = None    # expected points after the move (next position's search)
    ep_played: Optional[float] = None   # expected points used for the loss (see classifier.py)
    ep_loss: Optional[float] = None     # ep_before - ep_played, never negative
    band_before: Optional[str] = None   # "winning", "drawish" or "losing"
    band_after: Optional[str] = None
    label: str = "Unclassified"
    annotations: list[str] = field(default_factory=list)
    classification_note: Optional[str] = None
    explanation: list[str] = field(default_factory=list)  # data-based reasons
    confidence: str = "normal"          # "low" when the evaluations disagree
    brilliant_candidate: bool = False   # waiting for the deeper verification


@dataclass
class GameInfo:
    """Game metadata and analysis settings, used in the reports."""

    headers: dict[str, str] = field(default_factory=dict)
    depth: int = 0
    multipv: int = 0
    verify_depth: int = 0
    engine_name: Optional[str] = None
    book_file: Optional[str] = None
    ending: str = ""
    warnings: list[str] = field(default_factory=list)
    generated_at: str = ""
    accuracy_model: str = ACCURACY_MODEL
    ep_model: str = EXPECTED_POINTS_MODEL
    thresholds: dict[str, float] = field(default_factory=dict)
    positions_analyzed: int = 0     # engine searches performed
    cache_hits: int = 0             # positions reused instead of re-analyzed

    def header(self, key: str, default: str = "") -> str:
        """Return a PGN header, treating '?' and empty values as missing."""
        value = (self.headers.get(key) or "").strip()
        if value in ("", "?", "????.??.??"):
            return default
        return value


# --------------------------------------------------------------------------
# Perspective helpers
# --------------------------------------------------------------------------

def flip(ev: Optional[Eval]) -> Optional[Eval]:
    """The same position seen by the other player."""
    if ev is None:
        return None
    if ev.mate is not None:
        return Eval(mate=-ev.mate)
    return Eval(cp=-ev.cp)


def to_white_view(ev: Optional[Eval], color: str) -> Optional[Eval]:
    """Convert a mover-perspective Eval to White's perspective."""
    return ev if color == "White" else flip(ev)


def eval_for_pgn(ev: Optional[Eval], color: str) -> Optional[str]:
    """Text for a PGN [%eval ...] command (White's perspective), e.g. '0.52' or '#3'."""
    white = to_white_view(ev, color)
    if white is None:
        return None
    if white.mate is not None:
        return f"#{white.mate}"
    return f"{white.cp / 100:.2f}"


def white_win_percent_after(r: MoveResult) -> Optional[float]:
    """Win% after the move, from White's point of view (used by the graph)."""
    if r.win_after is None:
        return None
    return r.win_after if r.color == "White" else 100.0 - r.win_after


def white_win_percent_before(r: MoveResult) -> Optional[float]:
    if r.win_before is None:
        return None
    return r.win_before if r.color == "White" else 100.0 - r.win_before


# --------------------------------------------------------------------------
# Game summary
# --------------------------------------------------------------------------

def win_percent_sequence(results: list[MoveResult]) -> list[Optional[float]]:
    """Win% (White's point of view) of positions 0..N rebuilt from the move results."""
    if not results:
        return []
    sequence: list[Optional[float]] = [white_win_percent_before(results[0])]
    for r in results:
        sequence.append(white_win_percent_after(r))
    return sequence


def _mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def summarize(results: list[MoveResult]) -> dict[str, Any]:
    """Counts, accuracy and classification counts for a whole game."""
    matched = sum(1 for r in results if r.matched is True)
    not_matched = sum(1 for r in results if r.matched is False)
    no_recommendation = sum(1 for r in results if r.matched is None)
    comparable = matched + not_matched
    rate = (matched / comparable * 100) if comparable else 0.0

    white_moves = [r.accuracy for r in results if r.color == "White" and r.accuracy is not None]
    black_moves = [r.accuracy for r in results if r.color == "Black" and r.accuracy is not None]
    unscored = [f"{r.move_label} ({r.color}): {r.note}" for r in results if r.accuracy is None]

    # Game accuracy: Lichess-style volatility-weighted + harmonic mean (see scoring.py).
    start_color = results[0].color if results else "White"
    game = game_accuracies(win_percent_sequence(results), start_color)
    both = [a for a in (game["White"], game["Black"]) if a is not None]

    label_counts = {
        "White": {label: 0 for label in LABELS},
        "Black": {label: 0 for label in LABELS},
        "Total": {label: 0 for label in LABELS},
    }
    for r in results:
        label_counts[r.color][r.label] += 1
        label_counts["Total"][r.label] += 1

    return {
        "accuracy_model": ACCURACY_MODEL,
        "total": len(results),
        "matched": matched,
        "not_matched": not_matched,
        "no_recommendation": no_recommendation,
        "match_rate": rate,
        "white_accuracy": game["White"],          # game accuracy (volatility-weighted + harmonic)
        "black_accuracy": game["Black"],
        "overall_accuracy": _mean(both),          # average of the two game accuracies
        "white_mean_move_accuracy": _mean(white_moves),   # plain arithmetic mean, for comparison
        "black_mean_move_accuracy": _mean(black_moves),
        "scored": len(white_moves) + len(black_moves),
        "unscored": unscored,
        "label_counts": label_counts,
    }
