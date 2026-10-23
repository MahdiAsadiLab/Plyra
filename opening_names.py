"""Identify named openings from a PGN opening database.

The Polyglot .bin book is used separately for book-move detection. This module
uses a PGN database with [Opening "..."] and optionally [ECO "..."] headers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import chess.pgn


def identify_opening(game: chess.pgn.Game, database_path: str | Path) -> tuple[Optional[str], Optional[str]]:
    """Return the longest matching opening name and ECO code for ``game``.

    The database should contain standard-start-position opening lines as PGN
    games. Matching is based on UCI moves, so SAN spelling and annotations do
    not affect the result. Returns (None, None) when no named line matches.
    """
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(f"Opening-name database not found: {path}")

    played = [move.uci() for move in game.mainline_moves()]
    best_name: Optional[str] = None
    best_eco: Optional[str] = None
    best_length = -1

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            while True:
                candidate = chess.pgn.read_game(handle)
                if candidate is None:
                    break
                # Skip records whose move sequence cannot be read or whose
                # PGN begins from a non-standard position.
                if candidate.errors:
                    continue
                if candidate.headers.get("SetUp") == "1" and candidate.headers.get("FEN"):
                    continue

                moves = [move.uci() for move in candidate.mainline_moves()]
                if not moves or len(moves) > len(played) or len(moves) <= best_length:
                    continue
                if played[:len(moves)] != moves:
                    continue

                name = candidate.headers.get("Opening", "").strip()
                eco = candidate.headers.get("ECO", "").strip()
                if name and name != "?":
                    best_name = name
                    best_eco = eco if eco and eco != "?" else None
                    best_length = len(moves)
    except OSError as exc:
        raise OSError(f"Could not read opening-name database '{path}': {exc}") from exc

    return best_name, best_eco
