"""Shared test helpers (no python-chess needed)."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from classifier import classify_move  # noqa: E402
from models import GameInfo, MoveResult  # noqa: E402
from scoring import Eval, lichess_move_accuracy, win_percent  # noqa: E402


def cp(value: int) -> Eval:
    return Eval(cp=value)


def make_result(
    best,
    played=None,
    candidates=None,
    played_rank="auto",
    after="same",
    terminal=None,
    color="White",
    san="Nf3",
    uci="g1f3",
    best_san="Nf3",
    best_uci="g1f3",
    legal_moves=30,
    is_recapture=False,
    sacrifice=0.0,
    move_number=1,
    ply=1,
    previous=None,
    book_move=None,
    best_line=None,
    fen_before="",
    fen_after="",
    classify=True,
) -> MoveResult:
    """Build a MoveResult from mover-perspective evaluations, then classify it.

    best        evaluation of the position before the move (engine's best candidate)
    played      the played move's evaluation in the SAME search (default: best)
    candidates  the candidate list (default: [best] or [best, played])
    played_rank index of the played move in `candidates` ("auto" finds it; None = not a candidate)
    after       evaluation of the position after the move (default: same as `played`)
    terminal    "checkmate" / "stalemate" / "draw" if the move ended the game
    """
    played = best if played is None else played
    if candidates is None:
        candidates = [best] if played == best else [best, played]
    if played_rank == "auto":
        if played == best:
            played_rank = 0
        else:
            played_rank = candidates.index(played) if played in candidates else None
    after_eval = played if after == "same" else after

    win_before = win_percent(best)
    if terminal is not None:
        win_after = 100.0 if terminal == "checkmate" else 50.0
        after_eval = None
    else:
        win_after = win_percent(after_eval)
    reference = after_eval if played_rank is None else played
    loss = None
    if reference is not None and best.mate is None and reference.mate is None:
        loss = max(0, best.cp - reference.cp)

    result = MoveResult(
        ply=ply,
        move_number=move_number,
        color=color,
        move_label=f"Move {move_number}" if color == "White" else f"Move {move_number}...",
        played_san=san,
        played_uci=uci,
        fen_before=fen_before,
        fen_after=fen_after,
        depth=12,
        best_san=best_san,
        best_uci=best_uci,
        matched=(played_rank == 0),
        best_eval=best,
        candidate_evals=list(candidates),
        played_rank=played_rank,
        played_candidate_eval=played if played_rank is not None else None,
        after_eval=after_eval,
        after_terminal=terminal,
        best_score_text="+0.30",
        played_score_text="+0.30" if terminal is None else terminal.capitalize(),
        candidates=["Nf3 (+0.30)"],
        best_line=best_line if best_line is not None else [best_san],
        played_line=[san],
        legal_moves=legal_moves,
        is_recapture=is_recapture,
        sacrifice_points=sacrifice,
        win_before=win_before,
        win_after=win_after,
        accuracy=lichess_move_accuracy(win_before, win_after),
        loss_cp=loss,
        context="Normal position",
    )
    if classify:
        classify_move(result, previous, book_move=book_move)
    return result


def sample_game():
    """A small, hand-made game: (GameInfo, [MoveResult, ...])."""
    info = GameInfo(
        headers={"Event": "Test", "White": "Alice", "Black": "Bob", "Result": "1-0", "Date": "2026.01.01"},
        depth=12, multipv=3, verify_depth=16, engine_name="Fake Engine 1", ending="Checkmate - White won.",
        generated_at="2026-01-01 12:00", positions_analyzed=5,
    )
    results = [
        make_result(cp(30), san="e4", best_san="e4", move_number=1, ply=1),
        make_result(cp(-30), cp(-60), color="Black", san="d6", best_san="e5",
                    move_number=1, ply=2, best_line=["e5", "Nf3", "Nc6"]),
        make_result(cp(40), san="Nf3", best_san="Nf3", move_number=2, ply=3),
        make_result(cp(-40), cp(-500), color="Black", san="Qh4", best_san="Nc6",
                    move_number=2, ply=4, best_line=["Nc6", "Bb5"]),
    ]
    return info, results


# Real positions of Scholar's mate, for tests of the board in the HTML report.
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
SCHOLARS = [
    # (san, uci, best_san, best_uci, fen_after)
    ("e4", "e2e4", "e4", "e2e4", "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"),
    ("e5", "e7e5", "c5", "c7c5", "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"),
    ("Bc4", "f1c4", "Nf3", "g1f3", "rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2"),
    ("Nc6", "b8c6", "Nf6", "g8f6", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3"),
    ("Qh5", "d1h5", "Nc3", "b1c3", "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"),
    ("Nf6", "g8f6", "Nf6", "g8f6", "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"),
    ("Qxf7#", "h5f7", "Qxf7#", "h5f7", "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"),
]


def scholars_mate_game():
    """Scholar's mate with real FENs and invented (clearly synthetic) evaluations."""
    info = GameInfo(
        headers={"Event": "Synthetic test game", "White": "Player A", "Black": "Player B",
                 "Result": "1-0", "WhiteElo": "1500", "BlackElo": "1480", "Date": "2026.01.01"},
        depth=12, multipv=3, verify_depth=16, engine_name="Synthetic data (not Stockfish)",
        ending="Checkmate - White won.", generated_at="2026-01-01 12:00",
        positions_analyzed=7,
    )
    evals_before = [30, -30, 40, -40, 300, -200, 3000]
    played_cp = [30, -45, 40, -50, 290, -900, 3000]
    results = []
    fen_before = START_FEN
    for i, (san, uci, best_san, best_uci, fen_after) in enumerate(SCHOLARS):
        color = "White" if i % 2 == 0 else "Black"
        last = i == len(SCHOLARS) - 1
        results.append(make_result(
            cp(evals_before[i]), cp(played_cp[i]) if not last else cp(evals_before[i]),
            terminal="checkmate" if last else None,
            color=color, san=san, uci=uci, best_san=best_san, best_uci=best_uci,
            move_number=i // 2 + 1, ply=i + 1, previous=results[-1] if results else None,
            best_line=[best_san, "Nc6", "Bb5"] if not last else [best_san],
            fen_before=fen_before, fen_after=fen_after,
        ))
        fen_before = fen_after
    return info, results
