"""Round-trip tests for tools/build_book.py and tools/build_openings_pgn.py (need python-chess)."""
import io
import sys
from pathlib import Path

import pytest

chess = pytest.importorskip("chess")
import chess.pgn  # noqa: E402
import chess.polyglot  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_book  # noqa: E402

GAME = """[Event "Rated Blitz game"]
[WhiteElo "2300"]
[BlackElo "2250"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 O-O 1-0

"""


def _build(tmp_path, repeats=3, min_games=2):
    pgn = tmp_path / "games.pgn"
    pgn.write_text(GAME * repeats)
    out = tmp_path / "book.bin"
    counts = {}
    with build_book.open_pgn(pgn) as handle:
        while True:
            game = chess.pgn.read_game(handle, Visitor=lambda: build_book._Collector(2000, True, 20))
            if game is None:
                break
            for key, raw in game.entries:
                counts[(key << 16) | raw] = counts.get((key << 16) | raw, 0) + 1
    build_book.write_book(build_book.build_entries(counts, min_games), out)
    return out


def test_book_contains_played_moves_including_castling(tmp_path):
    out = _build(tmp_path)
    board = chess.Board()
    with chess.polyglot.open_reader(str(out)) as reader:
        for san in "e4 e5 Nf3 Nc6 Bc4 Bc5 O-O Nf6 d3 O-O".split():
            move = board.parse_san(san)
            assert any(e.move == move for e in reader.find_all(board)), san
            board.push(move)


def test_rare_moves_are_dropped(tmp_path):
    out = _build(tmp_path, repeats=1, min_games=2)  # every move seen only once
    assert out.stat().st_size == 0


def test_low_rated_games_are_ignored(tmp_path):
    pgn = tmp_path / "low.pgn"
    pgn.write_text(GAME.replace("2300", "1500"))
    with build_book.open_pgn(pgn) as handle:
        game = chess.pgn.read_game(handle, Visitor=lambda: build_book._Collector(2000, True, 20))
    assert not game.entries
