"""Move classification for ChessLens.

Pure logic: no python-chess, no Stockfish. The analyzer collects engine facts
and stores them in a MoveResult; the functions here turn those facts into a
label such as "Best", "Mistake" or "Brilliant".

Classification is INDEPENDENT of ChessLens Accuracy. Accuracy (scoring.py)
measures how much Win% a move gave up using the Lichess-inspired formula.
Classification asks different questions: how many expected points were lost,
did the result of the game change (win -> draw, draw -> loss), was the move
among the engine's candidates, was an opportunity missed, is the engine
evaluation stable. A move can have a high accuracy and still be "Mistake"
(it turned a win into a draw), or a low accuracy and be "Good".

IMPORTANT: the labels are a ChessLens approximation. They are NOT Chess.com's
Game Review labels, and the thresholds were chosen by us, not copied from anyone.

Quantities (all from the point of view of the player who moved, 0 to 1):

    ep_before  expected points of the position before the move
               (engine's best candidate)
    ep_played  expected points of the played move. If the move was one of the
               engine's candidates, its value from the SAME search as ep_before.
               Otherwise the value of the position after the move, capped at
               the weakest candidate (a move outside the top N cannot be better
               than the N-th candidate).
    ep_after   expected points of the position after the move (next position's
               own search); used to check that the evaluation is stable.
    ep_loss    max(0, ep_before - ep_played)

Ordinary labels come from ep_loss (default thresholds):
    <= 0.005 Best | <= 0.02 Excellent | <= 0.05 Good | <= 0.10 Inaccuracy |
    <= 0.20 Mistake | otherwise Blunder
and are made at least as severe when the result of the game changes:
    winning -> losing: Blunder;  winning -> drawish or drawish -> losing: Mistake
(only when the loss is at least `transition_min_loss`, so tiny moves across a
band edge are not punished).

Special labels (Book, Miss, Great, Brilliant) need extra evidence; see below.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Optional

from models import ChessLensError, DeepCheck, MoveResult
from scoring import CP_TO_WIN_SLOPE, Eval, expected_points as _expected_points

SEVERITY = ["Best", "Excellent", "Good", "Inaccuracy", "Mistake", "Blunder"]


@dataclass(frozen=True)
class Thresholds:
    """All tunable numbers in one place. Expected-points values are 0-1."""

    # Expected-points model (the same logistic curve Lichess uses for Win%).
    ep_slope: float = CP_TO_WIN_SLOPE

    # Ordinary labels: maximum expected-points loss for each label.
    best_max_loss: float = 0.005
    excellent_max_loss: float = 0.02
    good_max_loss: float = 0.05
    inaccuracy_max_loss: float = 0.10
    mistake_max_loss: float = 0.20  # anything worse is a Blunder

    # Result bands: where the game "stands" before/after the move.
    winning_min_ep: float = 0.70
    losing_max_ep: float = 0.30
    transition_min_loss: float = 0.08  # smaller losses never change the label because of a band change

    # Stability: if the same move gets expected points this far apart in two
    # different searches, the evaluation is not trusted for special labels.
    unstable_gap: float = 0.10

    # Forced-move annotation: every alternative is at least this much worse.
    forced_min_gap: float = 0.30

    # Great: (nearly) best move, and every alternative is clearly worse.
    great_max_loss: float = 0.01
    great_min_gap: float = 0.20
    great_min_ep: float = 0.30      # the move must keep the position alive

    # Miss: the opponent just erred, and we gave the chance away.
    miss_opponent_min_loss: float = 0.10
    miss_min_best_ep: float = 0.65  # the chance was real (clearly better position)
    miss_min_loss: float = 0.10     # we lost at least a Mistake-sized amount
    miss_min_played_ep: float = 0.45  # but the position is not lost (else it is a Blunder)

    # Brilliant (checked first cheaply, then verified by a deeper search).
    brilliant_max_loss: float = 0.02
    brilliant_min_sacrifice: float = 3.0   # pawns of material given up (a minor piece)
    brilliant_max_alt_ep: float = 0.85     # without the sacrifice the position is not already won
    brilliant_min_ep_after: float = 0.45   # after the sacrifice the position is not worse


DEFAULT_THRESHOLDS = Thresholds()


def thresholds_to_dict(t: Thresholds) -> dict[str, float]:
    return asdict(t)


def thresholds_from_dict(data: dict[str, Any]) -> Thresholds:
    """Build Thresholds from a dict, rejecting unknown names and bad values."""
    known = {f.name for f in fields(Thresholds)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ChessLensError(
            f"Unknown classification setting(s): {', '.join(unknown)}. "
            f"Valid names: {', '.join(sorted(known))}"
        )
    values = {}
    for name, value in data.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ChessLensError(f"Classification setting {name} must be a number, got {value!r}.")
        values[name] = float(value)
    t = Thresholds(**{**asdict(DEFAULT_THRESHOLDS), **values})
    ordered = [t.best_max_loss, t.excellent_max_loss, t.good_max_loss,
               t.inaccuracy_max_loss, t.mistake_max_loss]
    if ordered != sorted(ordered) or ordered[0] < 0 or ordered[-1] > 1:
        raise ChessLensError("The ordinary loss thresholds must increase: best < excellent < good < "
                             "inaccuracy < mistake, all between 0 and 1.")
    if not 0 <= t.losing_max_ep < t.winning_min_ep <= 1:
        raise ChessLensError("losing_max_ep must be lower than winning_min_ep (both between 0 and 1).")
    if t.ep_slope <= 0:
        raise ChessLensError("ep_slope must be positive.")
    return t


def load_thresholds(path: str) -> Thresholds:
    """Read classification settings from a JSON file (only the values you want to change)."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as error:
        raise ChessLensError(f"Classification config not found: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ChessLensError(f"Could not read the classification config {path}: {error}") from error
    if not isinstance(data, dict):
        raise ChessLensError("The classification config must be a JSON object, e.g. {\"best_max_loss\": 0.01}.")
    return thresholds_from_dict(data)


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------

def expected_points(ev: Eval, t: Thresholds = DEFAULT_THRESHOLDS) -> float:
    """Expected points (0-1) for the player the Eval belongs to."""
    return _expected_points(ev, t.ep_slope)


def ordinary_label(ep_loss: float, t: Thresholds = DEFAULT_THRESHOLDS) -> str:
    """The label that depends only on how much expected points the move lost."""
    if ep_loss <= t.best_max_loss:
        return "Best"
    if ep_loss <= t.excellent_max_loss:
        return "Excellent"
    if ep_loss <= t.good_max_loss:
        return "Good"
    if ep_loss <= t.inaccuracy_max_loss:
        return "Inaccuracy"
    if ep_loss <= t.mistake_max_loss:
        return "Mistake"
    return "Blunder"


def result_band(ep: float, t: Thresholds = DEFAULT_THRESHOLDS) -> str:
    """Where the game stands for the player: winning, drawish or losing."""
    if ep >= t.winning_min_ep:
        return "winning"
    if ep <= t.losing_max_ep:
        return "losing"
    return "drawish"


def _at_least(label: str, minimum: str) -> str:
    """The more severe of two ordinary labels."""
    return label if SEVERITY.index(label) >= SEVERITY.index(minimum) else minimum


def _range_text(label: str, t: Thresholds) -> str:
    bounds = {
        "Best": f"at most {t.best_max_loss:.3f}",
        "Excellent": f"{t.best_max_loss:.3f} to {t.excellent_max_loss:.3f}",
        "Good": f"{t.excellent_max_loss:.3f} to {t.good_max_loss:.3f}",
        "Inaccuracy": f"{t.good_max_loss:.3f} to {t.inaccuracy_max_loss:.3f}",
        "Mistake": f"{t.inaccuracy_max_loss:.3f} to {t.mistake_max_loss:.3f}",
        "Blunder": f"more than {t.mistake_max_loss:.2f}",
    }
    return bounds[label]


def _alternatives(r: MoveResult) -> list[Eval]:
    """Candidate evaluations EXCLUDING the move that was played (best first)."""
    return [ev for index, ev in enumerate(r.candidate_evals) if index != r.played_rank]


def _mate_annotations(best: Eval, played: Optional[Eval]) -> list[str]:
    if played is None:
        return []
    notes = []
    if best.mate is not None and best.mate > 0 and not (played.mate is not None and played.mate > 0):
        notes.append(f"Missed forced mate in {best.mate}")
    if played.mate is not None and played.mate <= 0 and not (best.mate is not None and best.mate <= 0):
        notes.append(f"Allows forced mate in {abs(played.mate)}")
    return notes


def _after_ep(r: MoveResult, t: Thresholds) -> Optional[float]:
    if r.after_terminal == "checkmate":
        return 1.0  # the player who just moved delivered mate
    if r.after_terminal in ("stalemate", "draw"):
        return 0.5
    if r.after_eval is not None:
        return expected_points(r.after_eval, t)
    return None


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def classify_move(
    r: MoveResult,
    previous: Optional[MoveResult] = None,
    t: Thresholds = DEFAULT_THRESHOLDS,
    book_move: Optional[bool] = None,
) -> None:
    """Fill in the classification fields of `r` (it is modified in place).

    previous   the result of the opponent's move just before this one (or None)
    book_move  True if the move was found in the opening book, False if not,
               None if no opening book is being used
    """
    r.annotations = []
    r.explanation = []
    r.classification_note = None
    r.brilliant_candidate = False
    r.confidence = "normal"

    ep_after = _after_ep(r, t)
    candidate_ep = expected_points(r.played_candidate_eval, t) if r.played_candidate_eval is not None else None

    if r.best_eval is None or (candidate_ep is None and ep_after is None):
        r.label = "Unclassified"
        r.classification_note = "Not enough engine evidence to classify this move."
        r.explanation.append("The engine did not return an evaluation for this move or position.")
        return

    # 1. Expected points before/after, from the mover's point of view.
    ep_before = expected_points(r.best_eval, t)
    if candidate_ep is not None:
        ep_played = candidate_ep                     # same search as ep_before: fair comparison
    else:
        ep_played = ep_after                         # type: ignore[assignment]
        if r.candidate_evals:                        # outside the top N: cannot beat the N-th
            ep_played = min(ep_played, expected_points(r.candidate_evals[-1], t))
    r.ep_before, r.ep_after, r.ep_played = ep_before, ep_after, ep_played
    r.ep_loss = max(0.0, ep_before - ep_played)
    r.band_before = result_band(ep_before, t)
    r.band_after = result_band(ep_played, t)

    # 2. Stability: two different searches of the same move should roughly agree.
    if candidate_ep is not None and ep_after is not None and r.after_terminal is None:
        if abs(candidate_ep - ep_after) >= t.unstable_gap:
            r.confidence = "low"
            r.annotations.append("Unstable evaluation")
            r.explanation.append(
                f"The move scored {candidate_ep:.2f} in the search of the position before it but "
                f"{ep_after:.2f} when the next position was searched, so the evaluation is not stable."
            )

    # 3. Ordinary label, made more severe if the result of the game changed.
    base = ordinary_label(r.ep_loss, t)
    label = base
    if r.ep_loss >= t.transition_min_loss:
        if r.band_before == "winning" and r.band_after == "losing":
            label = _at_least(label, "Blunder")
            r.annotations.append("Win turned into a loss")
        elif r.band_before == "winning" and r.band_after == "drawish":
            label = _at_least(label, "Mistake")
            r.annotations.append("Win turned into a draw")
        elif r.band_before == "drawish" and r.band_after == "losing":
            label = _at_least(label, "Mistake")
            r.annotations.append("Draw turned into a loss")

    # 4. Annotations (facts about the position; they never change the label).
    r.annotations.extend(_mate_annotations(r.best_eval, r.played_candidate_eval or r.after_eval))
    alternatives = _alternatives(r)
    alt_ep = expected_points(alternatives[0], t) if alternatives else None
    gap = (ep_played - alt_ep) if alt_ep is not None else None  # lead over the best alternative
    if r.legal_moves == 1:
        r.annotations.append("Only legal move")
    elif len(r.candidate_evals) >= 2:
        top_gap = expected_points(r.candidate_evals[0], t) - expected_points(r.candidate_evals[1], t)
        if top_gap >= t.forced_min_gap:
            if r.ep_loss <= t.excellent_max_loss:
                r.annotations.append("Forced move")
            elif r.ep_loss > t.good_max_loss:
                r.annotations.append("Missed the only good move")

    # 5. Explanation built only from numbers the engine produced.
    r.explanation.append(
        f"Expected points {ep_before:.2f} before the move, {ep_played:.2f} after it: loss {r.ep_loss:.3f}."
    )
    if r.played_rank == 0:
        r.explanation.append("The played move is the engine's first choice.")
    elif r.played_rank is not None:
        r.explanation.append(
            f"The played move is the engine's #{r.played_rank + 1} choice "
            f"out of {len(r.candidate_evals)} analysed candidates."
        )
    elif r.candidate_evals:
        r.explanation.append(
            f"The played move is not among the engine's top {len(r.candidate_evals)} candidates."
        )
    if r.band_before != r.band_after:
        r.explanation.append(f"The position changed from {r.band_before} to {r.band_after} for the player.")
    r.explanation.append(f"A loss of {r.ep_loss:.3f} is in the {base} range ({_range_text(base, t)}).")

    # 6. Book moves are verified against an opening book, never guessed.
    if book_move is True:
        r.label = "Book"
        r.classification_note = "Move found in the opening book."
        r.explanation.append("The move is in the opening book supplied with --book.")
        return

    # 7. Miss: the opponent's last move gave us a real chance and we threw it away.
    if (
        label in ("Mistake", "Blunder")
        and previous is not None
        and previous.color != r.color
        and previous.ep_loss is not None
        and previous.ep_loss >= t.miss_opponent_min_loss
        and ep_before >= t.miss_min_best_ep
        and r.ep_loss >= t.miss_min_loss
        and ep_played >= t.miss_min_played_ep
        and r.confidence == "normal"
    ):
        label = "Miss"
        r.classification_note = (
            "The opponent's previous move was a mistake, but this move did not exploit it."
        )
        r.explanation.append(
            f"The opponent's previous move lost {previous.ep_loss:.2f} expected points, "
            f"leaving a position worth {ep_before:.2f} to the player; the move played kept only {ep_played:.2f}."
        )

    # 8. Great and the Brilliant pre-check compare against the alternatives.
    if base in ("Best", "Excellent") and r.confidence == "normal":
        if gap is None:
            r.classification_note = (
                "Great and Brilliant need at least 2 candidate moves; use --multipv 2 or higher."
            )
        else:
            is_mate_move = r.played_san.endswith("#")
            routine = r.is_recapture or is_mate_move  # recaptures and mating blows are routine
            if (
                not routine
                and r.ep_loss <= t.great_max_loss
                and gap >= t.great_min_gap
                and ep_played >= t.great_min_ep
            ):
                label = "Great"
                r.classification_note = "Every other candidate move is clearly worse for the player."
                r.explanation.append(
                    f"The best alternative reaches only {alt_ep:.2f} expected points, "
                    f"{gap:.2f} less than the played move."
                )
            if (
                not routine
                and r.ep_loss <= t.brilliant_max_loss
                and r.sacrifice_points >= t.brilliant_min_sacrifice
                and alt_ep is not None
                and alt_ep <= t.brilliant_max_alt_ep
                and ep_played >= t.brilliant_min_ep_after
            ):
                r.brilliant_candidate = True  # needs the deeper check before it is final

    r.label = label


def confirm_brilliant(
    r: MoveResult,
    deep: DeepCheck,
    t: Thresholds = DEFAULT_THRESHOLDS,
) -> None:
    """Final Brilliant decision, using the deeper verification search."""
    if not r.brilliant_candidate:
        return
    r.brilliant_candidate = False

    ep_best = expected_points(deep.best_eval, t)
    ep_played = expected_points(deep.played_eval, t)
    loss = max(0.0, ep_best - ep_played)

    sound = loss <= t.brilliant_max_loss and ep_played >= t.brilliant_min_ep_after
    still_sacrifice = deep.sacrifice_points >= t.brilliant_min_sacrifice

    if sound and still_sacrifice:
        r.label = "Brilliant"
        r.classification_note = (
            f"Sound sacrifice: about {deep.sacrifice_points:.0f} points of material given up, "
            f"verified at depth {deep.depth}."
        )
        r.explanation.append(
            f"At depth {deep.depth} the move still loses only {loss:.3f} expected points "
            f"({ep_played:.2f} after the move) while giving up about {deep.sacrifice_points:.0f} points of material."
        )
    else:
        r.classification_note = (
            f"Possible sacrifice, but the deeper check (depth {deep.depth}) did not confirm it, "
            "so it is not labelled Brilliant."
        )
        r.explanation.append(
            f"Deeper check at depth {deep.depth}: loss {loss:.3f}, expected points after the move "
            f"{ep_played:.2f}, material given up {deep.sacrifice_points:.0f}."
        )
