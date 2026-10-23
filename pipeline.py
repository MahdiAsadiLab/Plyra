"""One function that runs a whole analysis: used by main.py and validate.py.

Keeping this in one place means the command line, the validation tool and the
tests all analyze games in exactly the same way.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import chess.pgn

from analyzer import (
    DEFAULT_VERIFY_EXTRA_DEPTH,
    analyze_game,
    describe_ending,
    open_book,
    open_engine,
)
from classifier import DEFAULT_THRESHOLDS, Thresholds, thresholds_to_dict
from models import GameInfo, MoveResult

SHALLOW_DEPTH = 10  # below this the engine results are less trustworthy


def run_analysis(
    game: chess.pgn.Game,
    stockfish_path: str,
    depth: int,
    multipv: int,
    verify_depth: Optional[int] = None,
    book_path: Optional[str] = None,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    on_start: Optional[Callable[[GameInfo], None]] = None,
    on_move: Optional[Callable[[MoveResult], None]] = None,
) -> tuple[GameInfo, list[MoveResult]]:
    """Analyze one game. Stockfish is always closed, even if something fails."""
    info = GameInfo(
        headers={str(k): str(v) for k, v in game.headers.items()},
        depth=depth,
        multipv=multipv,
        verify_depth=verify_depth or depth + DEFAULT_VERIFY_EXTRA_DEPTH,
        book_file=book_path,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        thresholds=thresholds_to_dict(thresholds),
    )
    if game.errors:
        info.warnings.append(
            "The PGN had a problem, so only the moves before it were analyzed "
            f"({game.errors[0]})."
        )
    if depth < SHALLOW_DEPTH:
        info.warnings.append(
            f"Shallow analysis (depth {depth}): evaluations, accuracy and labels are less reliable. "
            f"Depth {SHALLOW_DEPTH} or more is recommended."
        )
    if multipv < 2:
        info.warnings.append(
            "With --multipv 1 the Great, Brilliant and Forced-move checks cannot be made."
        )

    results: list[MoveResult] = []
    stats: dict = {}
    with open_engine(stockfish_path) as engine, open_book(book_path) as book:
        info.engine_name = engine.id.get("name")
        if on_start is not None:
            on_start(info)
        for result in analyze_game(
            game, engine, depth, multipv, verify_depth, book, thresholds, stats
        ):
            results.append(result)
            if on_move is not None:
                on_move(result)

    info.positions_analyzed = stats.get("positions_analyzed", 0)
    info.cache_hits = stats.get("cache_hits", 0)
    info.ending = describe_ending(game)
    return info, results
