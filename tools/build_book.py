#!/usr/bin/env python3
"""Build a Polyglot opening book (.bin) from PGN game dumps.

Works with Lichess database dumps (.pgn.zst or .pgn.bz2), the Lichess Elite
Database (.zip) or any plain .pgn. For every position in the first
--max-plies half-moves of each game, it counts how often each move was played.
Moves seen fewer than --min-games times are dropped, so rare mistakes do not
count as "book". The result is a standard Polyglot file that
`main.py --book` can read.

Examples:
    python tools/build_book.py lichess_elite_2024-01.zip -o books/book.bin
    python tools/build_book.py lichess_db_standard_rated_2016-03.pgn.zst \\
        --min-rating 2000 --max-plies 20 --min-games 10 -o books/book.bin
    python tools/build_book.py --verify-only books/book.bin
"""
from __future__ import annotations

import argparse
import bz2
import io
import struct
import subprocess
import sys
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import chess
import chess.pgn
import chess.polyglot

ENTRY = struct.Struct(">QHHI")  # key, move, weight, learn (big-endian, 16 bytes)
MAX_WEIGHT = 0xFFFF
_PROMOTION = {None: 0, chess.KNIGHT: 1, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 4}


# ---------------------------------------------------------------- encoding

def encode_move(board: chess.Board, move: chess.Move) -> int:
    """Polyglot move: to | from << 6 | promotion << 12.

    Polyglot writes castling as "king takes own rook" (e1h1, e1a1, ...).
    """
    to_square = move.to_square
    if board.is_castling(move):
        rank = chess.square_rank(move.from_square)
        to_square = chess.square(7 if board.is_kingside_castling(move) else 0, rank)
    return to_square | (move.from_square << 6) | (_PROMOTION[move.promotion] << 12)


def build_entries(counts: dict[int, int], min_games: int) -> list[tuple[int, int, int]]:
    """Turn {(key << 16 | move): count} into sorted (key, move, weight) rows."""
    by_key: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for packed, n in counts.items():
        if n >= min_games:
            by_key[packed >> 16].append((packed & 0xFFFF, n))
    rows: list[tuple[int, int, int]] = []
    for key in sorted(by_key):  # Polyglot requires entries sorted by key
        moves = by_key[key]
        top = max(n for _, n in moves)
        scale = MAX_WEIGHT / top if top > MAX_WEIGHT else 1.0
        for raw, n in sorted(moves, key=lambda item: -item[1]):
            rows.append((key, raw, max(1, int(n * scale))))
    return rows


def write_book(rows: list[tuple[int, int, int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for key, raw, weight in rows:
            handle.write(ENTRY.pack(key, raw, weight, 0))


# ---------------------------------------------------------------- reading

@contextmanager
def open_pgn(path: Path) -> Iterator[io.TextIOBase]:
    suffix = path.suffix.lower()
    if suffix == ".zst":
        try:
            import zstandard
        except ImportError:
            zstandard = None
        if zstandard is not None:
            with path.open("rb") as raw:
                reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(raw)
                with io.TextIOWrapper(reader, encoding="utf-8", errors="replace") as text:
                    yield text
            return
        try:
            proc = subprocess.Popen(["zstd", "-dc", "--long=31", str(path)], stdout=subprocess.PIPE)
        except FileNotFoundError:
            raise SystemExit("Reading .zst needs:  pip install zstandard   (or install the 'zstd' program)")
        try:
            with io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace") as text:
                yield text
        finally:
            proc.terminate()
        return
    if suffix == ".bz2":
        with bz2.open(path, "rt", encoding="utf-8", errors="replace") as text:
            yield text
        return
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".pgn")]
            if not names:
                raise SystemExit(f"No .pgn file inside {path}")
            with archive.open(names[0]) as raw:
                with io.TextIOWrapper(raw, encoding="utf-8", errors="replace") as text:
                    yield text
        return
    with path.open("r", encoding="utf-8-sig", errors="replace") as text:
        yield text


class _Collector(chess.pgn.BaseVisitor):
    """Reads one game, keeping only the first moves of games that pass the filters."""

    def __init__(self, min_rating: int, skip_bullet: bool, max_plies: int):
        self.min_rating = min_rating
        self.skip_bullet = skip_bullet
        self.max_plies = max_plies
        self.headers: dict[str, str] = {}
        self.keep = True
        self.entries: list[tuple[int, int]] = []

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        self.headers[tagname] = tagvalue

    def end_headers(self):
        self.keep = self._accept()
        return None if self.keep else chess.pgn.SKIP

    def _accept(self) -> bool:
        h = self.headers
        try:
            white, black = int(h.get("WhiteElo", 0)), int(h.get("BlackElo", 0))
        except ValueError:
            return False
        if min(white, black) < self.min_rating:
            return False
        if h.get("Variant", "Standard") not in ("Standard", "From Position"):
            return False
        if h.get("Termination") == "Abandoned":
            return False
        if self.skip_bullet and "bullet" in h.get("Event", "").lower():
            return False
        return True

    def begin_variation(self):
        return chess.pgn.SKIP

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        if self.keep and len(self.entries) < self.max_plies:
            self.entries.append((chess.polyglot.zobrist_hash(board), encode_move(board, move)))

    def result(self) -> "_Collector":
        return self


# ---------------------------------------------------------------- verify

def verify(path: Path) -> None:
    size = path.stat().st_size
    print(f"\nVerifying {path} ({size:,} bytes, {size // ENTRY.size:,} entries)")
    with chess.polyglot.open_reader(str(path)) as reader:
        board = chess.Board()
        start = sorted(reader.find_all(board), key=lambda e: -e.weight)
        if not start:
            print("  WARNING: no entries for the starting position. The book is empty or broken.")
            return
        print("  First moves in the book:", ", ".join(f"{board.san(e.move)} ({e.weight})" for e in start[:6]))
        line = []
        for _ in range(16):
            options = list(reader.find_all(board))
            if not options:
                break
            best = max(options, key=lambda e: e.weight)
            line.append(board.san(best.move))
            board.push(best.move)
        print("  Most popular line:", " ".join(line))


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*", help="PGN dumps (.pgn, .pgn.zst, .pgn.bz2, .zip)")
    parser.add_argument("-o", "--output", default="books/book.bin")
    parser.add_argument("--min-rating", type=int, default=2000, help="both players must be at least this rating (default 2000)")
    parser.add_argument("--max-plies", type=int, default=20, help="half-moves per game to include (default 20 = 10 full moves)")
    parser.add_argument("--min-games", type=int, default=10, help="drop moves played fewer times than this (default 10)")
    parser.add_argument("--max-games", type=int, default=0, help="stop after this many accepted games (0 = no limit)")
    parser.add_argument("--allow-bullet", action="store_true", help="include bullet games (skipped by default)")
    parser.add_argument("--verify-only", metavar="BOOK", help="just check an existing .bin file and exit")
    args = parser.parse_args()

    if args.verify_only:
        verify(Path(args.verify_only))
        return 0
    if not args.inputs:
        parser.error("give at least one PGN dump, or use --verify-only")

    counts: dict[int, int] = {}
    seen = used = 0
    done = False
    for name in args.inputs:
        path = Path(name)
        if not path.is_file():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        print(f"Reading {path} ...")
        with open_pgn(path) as handle:
            while True:
                game = chess.pgn.read_game(
                    handle,
                    Visitor=lambda: _Collector(args.min_rating, not args.allow_bullet, args.max_plies),
                )
                if game is None:
                    break
                seen += 1
                if game.keep and game.entries:
                    used += 1
                    for key, raw in game.entries:
                        packed = (key << 16) | raw
                        counts[packed] = counts.get(packed, 0) + 1
                if seen % 100_000 == 0:
                    print(f"  {seen:,} games read, {used:,} used, {len(counts):,} distinct moves")
                if args.max_games and used >= args.max_games:
                    done = True
                    break
        if done:
            break

    rows = build_entries(counts, args.min_games)
    if not rows:
        print("No moves survived the filters. Lower --min-rating or --min-games, or use a bigger dump.", file=sys.stderr)
        return 1
    out = Path(args.output)
    write_book(rows, out)
    print(f"{seen:,} games read, {used:,} used. Wrote {len(rows):,} book entries to {out}")
    verify(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
