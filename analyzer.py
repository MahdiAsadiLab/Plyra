"""ChessLens analysis logic: load a PGN, find Stockfish, analyze every move.

This file talks to python-chess and Stockfish and collects ENGINE FACTS for
each move. It decides nothing about labels itself: classifier.py does that.
It never prints the report; main.py and reports.py do that.
"""

from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

import chess
import chess.engine
import chess.pgn
import chess.polyglot

from classifier import DEFAULT_THRESHOLDS, Thresholds, classify_move, confirm_brilliant
from models import ChessLensError, DeepCheck, MoveResult
from scoring import Eval, describe_position, lichess_move_accuracy, win_percent

DEFAULT_DEPTH = 12
DEFAULT_MULTIPV = 3
DEFAULT_VERIFY_EXTRA_DEPTH = 4   # deeper check for Brilliant = depth + 4
PV_PLIES = 6                     # how many moves of the best line we keep for reports
SACRIFICE_MAX_PLIES = 8          # how far along a line we look for material changes

# Standard material values in pawns.
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}

# Folder where you can drop the Stockfish executable (next to this file).
ENGINE_DIR = Path(__file__).resolve().parent / "engine"

INSTALL_HELP = r"""Stockfish was not found. Do ONE of the following:

  1. (Recommended) Copy the Stockfish .exe file into the 'engine' folder that
     sits next to main.py. Its file name should start with "stockfish".
  2. Tell the program where it is:
         python main.py games/scholars_mate.pgn --stockfish "C:/path/to/stockfish.exe"
  3. Add the folder containing Stockfish to your system PATH.

Download Stockfish from: https://stockfishchess.org/download/
(Unzip the download first; you need the .exe file inside the zip.)"""


# --------------------------------------------------------------------------
# Loading the PGN
# --------------------------------------------------------------------------

def load_game(pgn_path: Path) -> chess.pgn.Game:
    """Read the first game from a PGN file, or raise ChessLensError."""
    if not pgn_path.exists():
        raise ChessLensError(f"PGN file not found: {pgn_path}")
    if not pgn_path.is_file():
        raise ChessLensError(f"This is not a file: {pgn_path}")

    try:
        # utf-8-sig quietly removes the invisible BOM some programs add.
        with open(pgn_path, encoding="utf-8-sig", errors="replace") as handle:
            game = chess.pgn.read_game(handle)
    except OSError as error:
        raise ChessLensError(f"Could not read {pgn_path}: {error}") from error

    if game is None:
        raise ChessLensError(f"The PGN file is empty or has no game: {pgn_path}")

    # python-chess does not crash on bad moves; it stops at the first problem
    # and records it in game.errors. If nothing was readable, give up.
    if game.next() is None:
        detail = f" ({game.errors[0]})" if game.errors else ""
        raise ChessLensError(
            f"No valid moves could be read from {pgn_path}{detail}. "
            "Is it a real PGN file?"
        )
    return game


# --------------------------------------------------------------------------
# Finding and starting Stockfish
# --------------------------------------------------------------------------

def _looks_like_executable(path: Path) -> bool:
    if not path.is_file():
        return False
    if os.name == "nt":  # Windows
        return path.suffix.lower() == ".exe"
    return os.access(path, os.X_OK)


def find_stockfish(explicit_path: Optional[str] = None) -> str:
    """Return the path to a Stockfish executable, or raise ChessLensError.

    Search order: --stockfish argument, then the 'engine' folder, then PATH.
    """
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.is_dir():
            raise ChessLensError(
                f"--stockfish points to a folder, not a file: {path}\n"
                "Point it at the stockfish .exe file itself."
            )
        if not path.is_file():
            raise ChessLensError(f"No file found at --stockfish path: {path}")
        return str(path)

    if ENGINE_DIR.is_dir():
        for candidate in sorted(ENGINE_DIR.glob("stockfish*")):
            if _looks_like_executable(candidate):
                return str(candidate)

    on_path = shutil.which("stockfish")
    if on_path:
        return on_path

    raise ChessLensError(INSTALL_HELP)


@contextmanager
def open_engine(engine_path: str) -> Iterator[chess.engine.SimpleEngine]:
    """Start Stockfish, hand it over, and always shut it down afterwards."""
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    except (OSError, chess.engine.EngineError) as error:
        raise ChessLensError(
            f"Could not start Stockfish at {engine_path}: {error}\n"
            "Check that this is the real Stockfish program for your computer. "
            "If you get an 'illegal instruction' style error, download a "
            "different build (for example the 'x86-64' or 'sse41-popcnt' one)."
        ) from error
    with engine:  # closes the engine process when the block ends
        yield engine


@contextmanager
def open_book(book_path: Optional[str]) -> Iterator[Optional[Any]]:
    """Open a Polyglot opening book (.bin), or yield None if none was given."""
    if not book_path:
        yield None
        return
    try:
        reader = chess.polyglot.open_reader(book_path)
    except FileNotFoundError as error:
        raise ChessLensError(f"Opening book not found: {book_path}") from error
    except (OSError, ValueError) as error:
        raise ChessLensError(
            f"Could not read the opening book {book_path}: {error}\n"
            "It must be a Polyglot .bin file."
        ) from error
    with reader:
        yield reader


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def format_score(score: chess.engine.PovScore) -> str:
    """Turn an engine score into text, always from White's point of view."""
    white_score = score.white()
    mate_in = white_score.mate()
    if mate_in is not None:
        winner = "White" if mate_in > 0 else "Black"
        return f"Mate in {abs(mate_in)} for {winner}"
    centipawns = white_score.score()
    return f"{centipawns / 100:+.2f}"  # +0.35 means White is ahead by 0.35 pawns


def pov_eval(score: chess.engine.PovScore, color: chess.Color) -> Eval:
    """Convert an engine score to the point of view of the player `color`.

    This is the ONE place where perspective is handled: afterwards, a positive
    number always means "good for the player who is making the move".
    """
    mover_score = score.pov(color)
    mate_in = mover_score.mate()
    if mate_in is not None:
        return Eval(mate=mate_in)
    return Eval(cp=mover_score.score())


def _run_engine(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    where: str,
    **options: Any,
) -> Any:
    """Call engine.analyse and turn engine failures into a friendly error."""
    try:
        return engine.analyse(board, limit, **options)
    except chess.engine.EngineError as error:
        raise ChessLensError(f"Stockfish stopped working at {where}: {error}") from error


def _valid_lines(infos: Any) -> list[dict]:
    """Keep only engine lines that have both a move and a score."""
    if isinstance(infos, dict):  # be safe if a single dict comes back
        infos = [infos]
    return [i for i in infos if i.get("pv") and i.get("score") is not None]


def _pv_to_san(board: chess.Board, pv: list[chess.Move], limit: int = PV_PLIES) -> list[str]:
    """Write the first moves of an engine line in SAN, starting from `board`."""
    temp = board.copy(stack=False)
    moves = []
    for move in pv[:limit]:
        moves.append(temp.san(move))
        temp.push(move)
    return moves


def _material_balance(board: chess.Board, color: chess.Color) -> int:
    """Material of `color` minus material of the opponent, in pawns."""
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += value * len(board.pieces(piece_type, color))
        total -= value * len(board.pieces(piece_type, not color))
    return total


def _sacrifice_points(board: chess.Board, pv: list[chess.Move], mover: chess.Color) -> float:
    """How much material the mover gives up along an engine line (in pawns).

    We play the line until the first QUIET move (not a capture) from the
    opponent's reply onwards, so ordinary exchanges are not mistaken for
    sacrifices. A positive number means the mover ended up with less material
    than before. This is a heuristic based on the engine's line, not proof.
    """
    if len(pv) < 2:
        return 0.0
    start = _material_balance(board, mover)
    temp = board.copy(stack=False)
    for ply, move in enumerate(pv[:SACRIFICE_MAX_PLIES], start=1):
        was_capture = temp.is_capture(move)
        temp.push(move)
        if ply >= 2 and not was_capture:
            break
    return float(start - _material_balance(temp, mover))


def _deep_check(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    played_move: chess.Move,
    deep_limit: chess.engine.Limit,
    multipv: int,
    where: str,
) -> Optional[DeepCheck]:
    """Re-analyze one position deeper to verify a possible Brilliant move."""
    mover = board.turn
    lines = _valid_lines(_run_engine(engine, board, deep_limit, where, multipv=multipv))
    if not lines:
        return None
    played_info = next((line for line in lines if line["pv"][0] == played_move), None)
    if played_info is None:
        played_info = _run_engine(engine, board, deep_limit, where, root_moves=[played_move])
    if played_info.get("score") is None:
        return None
    return DeepCheck(
        best_eval=pov_eval(lines[0]["score"], mover),
        played_eval=pov_eval(played_info["score"], mover),
        sacrifice_points=_sacrifice_points(board, played_info.get("pv") or [], mover),
        depth=deep_limit.depth,
    )


@dataclass
class PositionAnalysis:
    """The engine's answer for one position (analyzed only once)."""

    lines: list                 # valid MultiPV lines, best first (empty if terminal)
    terminal: Optional[str]     # "checkmate", "stalemate", "draw" or None
    turn: bool                  # side to move in this position


def terminal_kind(board: chess.Board) -> Optional[str]:
    """Name the way a position ended the game, or None if play continues."""
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_game_over():
        return "draw"
    return None


class PositionAnalyzer:
    """Analyzes positions with Stockfish and remembers the results.

    Every position of a game is searched once. The result is used twice: as
    the "after" evaluation of one move and the "before" evaluation of the next.
    Positions that repeat inside the game are reused instead of searched again.
    """

    def __init__(self, engine: chess.engine.SimpleEngine, limit: chess.engine.Limit, multipv: int):
        self.engine = engine
        self.limit = limit
        self.multipv = multipv
        self.cache: dict[str, PositionAnalysis] = {}
        self.searches = 0
        self.cache_hits = 0

    def analyse(self, board: chess.Board, where: str) -> PositionAnalysis:
        terminal = terminal_kind(board)
        if terminal is not None:  # no engine call: the game is over
            return PositionAnalysis([], terminal, board.turn)
        key = board.epd()
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        lines = _valid_lines(_run_engine(self.engine, board, self.limit, where, multipv=self.multipv))
        self.searches += 1
        analysis = PositionAnalysis(lines, None, board.turn)
        self.cache[key] = analysis
        return analysis


def _terminal_text(kind: str) -> str:
    return {"checkmate": "Checkmate", "stalemate": "Stalemate", "draw": "Draw"}[kind]


def _cp_loss(best: Optional[Eval], reference: Optional[Eval]) -> Optional[int]:
    """Centipawn loss between two mover-perspective evaluations (None if a mate is involved)."""
    if best is None or reference is None or best.mate is not None or reference.mate is not None:
        return None
    return max(0, best.cp - reference.cp)


def analyze_game(
    game: chess.pgn.Game,
    engine: chess.engine.SimpleEngine,
    depth: int,
    multipv: int = DEFAULT_MULTIPV,
    verify_depth: Optional[int] = None,
    book: Optional[Any] = None,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    stats: Optional[dict] = None,
) -> Iterator[MoveResult]:
    """Analyze each half-move and yield one classified MoveResult at a time.

    Each position of the game is searched ONCE (MultiPV). For move i:
        before = the search of the position before the move (candidates, best eval)
        after  = the search of the position after the move (it becomes `before`
                 of move i+1, so it is not searched twice)
    A deeper check is run only for a possible Brilliant move (rare).
    The board is advanced exactly once per move.

    stats (optional dict) receives positions_analyzed and cache_hits.
    """
    board = game.board()  # starting position (or the FEN given in the PGN)
    limit = chess.engine.Limit(depth=depth)
    deep_limit = chess.engine.Limit(depth=verify_depth or depth + DEFAULT_VERIFY_EXTRA_DEPTH)
    analyzer = PositionAnalyzer(engine, limit, multipv)

    previous: Optional[MoveResult] = None
    previous_move: Optional[chess.Move] = None
    previous_was_capture = False
    in_book = book is not None  # once a move leaves the book, the book phase is over

    try:
        before = analyzer.analyse(board, "the starting position")
        for ply, played_move in enumerate(game.mainline_moves(), start=1):
            if before.terminal is not None:
                break  # the game was already over; nothing sensible to analyze

            # Label and mover, read from the position before the move.
            mover = board.turn
            color = "White" if mover == chess.WHITE else "Black"
            number = board.fullmove_number
            label = f"Move {number}" if mover == chess.WHITE else f"Move {number}..."
            where = f"{label} ({color})"
            board_before = board.copy(stack=False)  # kept for SAN conversion after the push
            fen_before = board.fen()
            legal_moves = board.legal_moves.count()
            was_capture = board.is_capture(played_move)
            is_recapture = bool(
                previous_was_capture
                and was_capture
                and previous_move is not None
                and played_move.to_square == previous_move.to_square
            )

            # 1. Candidates come from the search of the position BEFORE the move.
            lines = before.lines
            played_san = board.san(played_move)
            best_move = lines[0]["pv"][0] if lines else None
            best_san = board.san(best_move) if best_move is not None else None
            candidates = [f"{board.san(i['pv'][0])} ({format_score(i['score'])})" for i in lines]
            candidate_evals = [pov_eval(i["score"], mover) for i in lines]
            best_line = _pv_to_san(board, lines[0]["pv"]) if lines else []
            matched = (played_move == best_move) if best_move is not None else None
            played_rank = next(
                (index for index, line in enumerate(lines) if line["pv"][0] == played_move), None
            )
            played_candidate_eval = candidate_evals[played_rank] if played_rank is not None else None

            # 2. Opening book: True / False, or None when no book is used.
            book_move = None
            if book is not None:
                if in_book:
                    in_book = any(entry.move == played_move for entry in book.find_all(board))
                book_move = in_book

            # 3. Play the move (the only push in the loop) and read the position AFTER it.
            board.push(played_move)
            fen_after = board.fen()
            after = analyzer.analyse(board, f"{where}, position after the move")
            after_eval = pov_eval(after.lines[0]["score"], mover) if after.lines else None
            after_pv = after.lines[0]["pv"] if after.lines else []
            played_line_moves = [played_move] + list(after_pv)
            played_line = _pv_to_san(board_before, played_line_moves)
            sacrifice = _sacrifice_points(board_before, played_line_moves, mover)

            # 4. ChessLens Accuracy (Lichess-inspired): Win% before vs after, mover's view.
            best_eval = candidate_evals[0] if candidate_evals else None
            win_before = win_percent(best_eval) if best_eval is not None else None
            if after.terminal is not None:
                win_after = 100.0 if after.terminal == "checkmate" else 50.0
            elif after_eval is not None:
                win_after = win_percent(after_eval)
            else:
                win_after = None
            accuracy = note = None
            if win_before is None:
                note = "Stockfish returned no evaluation for the position before the move."
            elif win_after is None:
                note = "Stockfish returned no evaluation for the position after the move."
            else:
                accuracy = lichess_move_accuracy(win_before, win_after)

            reference = played_candidate_eval or after_eval
            if after.terminal == "checkmate":
                loss_cp = 0
            elif after.terminal is not None:
                loss_cp = _cp_loss(best_eval, Eval(cp=0))
            else:
                loss_cp = _cp_loss(best_eval, reference)

            if after.terminal is not None:
                played_score_text = _terminal_text(after.terminal)
            elif after.lines:
                played_score_text = format_score(after.lines[0]["score"])
            else:
                played_score_text = None

            result = MoveResult(
                ply=ply,
                move_number=number,
                color=color,
                move_label=label,
                played_san=played_san,
                played_uci=played_move.uci(),
                fen_before=fen_before,
                fen_after=fen_after,
                depth=depth,
                best_san=best_san,
                best_uci=best_move.uci() if best_move is not None else None,
                matched=matched,
                best_eval=best_eval,
                candidate_evals=candidate_evals,
                played_rank=played_rank,
                played_candidate_eval=played_candidate_eval,
                after_eval=after_eval,
                after_terminal=after.terminal,
                best_score_text=format_score(lines[0]["score"]) if lines else None,
                played_score_text=played_score_text,
                candidates=candidates,
                best_line=best_line,
                played_line=played_line,
                legal_moves=legal_moves,
                is_recapture=is_recapture,
                sacrifice_points=sacrifice,
                win_before=win_before,
                win_after=win_after,
                accuracy=accuracy,
                loss_cp=loss_cp,
                context=describe_position(candidate_evals)[0] if candidate_evals else None,
                note=note,
            )

            # 5. Classify the move. A possible Brilliant move gets a deeper check first.
            classify_move(result, previous, thresholds, book_move)
            if result.brilliant_candidate:
                deep = _deep_check(engine, board_before, played_move, deep_limit, multipv, where)
                if deep is not None:
                    confirm_brilliant(result, deep, thresholds)
                else:
                    result.brilliant_candidate = False
                    result.classification_note = "Brilliant check could not be completed."

            yield result

            previous, previous_move, previous_was_capture = result, played_move, was_capture
            before = after  # the "after" search is reused as the next move's "before"
    finally:
        if stats is not None:
            stats["positions_analyzed"] = analyzer.searches
            stats["cache_hits"] = analyzer.cache_hits


def describe_ending(game: chess.pgn.Game) -> str:
    """Describe how the game ended on the board (not just the Result tag)."""
    board = game.end().board()
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate - {winner} won."
    if board.is_stalemate():
        return "Stalemate - draw."
    if board.is_insufficient_material():
        return "Draw by insufficient material."
    if board.is_game_over():
        return "Game over (draw by repetition or move rule)."
    return "The game did not end in a terminal position (resignation, time, draw agreement, or unfinished)."
