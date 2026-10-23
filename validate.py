"""Compare ChessLens Accuracy with reference accuracies you collected yourself.

You provide the games and the reference numbers (for example from the
Chess.com or Lichess analysis page of the same games). ChessLens never invents
reference data. See validation/README.md for the step-by-step guide.

    python validate.py validation/manifest.csv --stockfish "engines/stockfish.exe" --depth 12
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MIN_RELIABLE_GAMES = 20   # fewer samples than this cannot support conclusions
REFERENCE_COLUMNS = {
    "chesscom": ("white_chesscom", "black_chesscom"),
    "lichess": ("white_lichess", "black_lichess"),
}


@dataclass
class Row:
    """One player's game accuracy: ours and one reference system's."""

    game: str
    color: str
    reference: str
    chesslens: float
    value: float


class ValidationError(Exception):
    pass


def _number(text: str, column: str, line: int) -> Optional[float]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = float(text.replace("%", ""))
    except ValueError as error:
        raise ValidationError(f"Line {line}: {column} must be a number, got {text!r}.") from error
    if not 0 <= value <= 100:
        raise ValidationError(f"Line {line}: {column} must be between 0 and 100, got {value}.")
    return value


def load_manifest(path: Path) -> list[dict]:
    """Read the manifest CSV: one game per line, blank reference cells are allowed."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "pgn" not in reader.fieldnames:
                raise ValidationError("The manifest needs a header line with a 'pgn' column.")
            entries = []
            for line, record in enumerate(reader, start=2):
                pgn = (record.get("pgn") or "").strip()
                if not pgn or pgn.startswith("#"):
                    continue
                refs = {}
                for system, (white_col, black_col) in REFERENCE_COLUMNS.items():
                    refs[(system, "White")] = _number(record.get(white_col, ""), white_col, line)
                    refs[(system, "Black")] = _number(record.get(black_col, ""), black_col, line)
                entries.append({"pgn": pgn, "refs": refs})
            return entries
    except OSError as error:
        raise ValidationError(f"Could not read the manifest {path}: {error}") from error


def pearson(pairs: list[tuple[float, float]]) -> Optional[float]:
    if len(pairs) < 3:
        return None
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def compare(rows: list[Row]) -> dict:
    """Difference statistics (ChessLens minus reference) for one reference system."""
    diffs = [r.chesslens - r.value for r in rows]
    n = len(diffs)
    if n == 0:
        return {"n": 0, "mean_difference": None, "mean_absolute_error": None,
                "max_absolute_error": None, "correlation": None,
                "warning": "No reference values were provided."}
    result = {
        "n": n,
        "mean_difference": sum(diffs) / n,           # > 0 means ChessLens is higher
        "mean_absolute_error": sum(abs(d) for d in diffs) / n,
        "max_absolute_error": max(abs(d) for d in diffs),
        "correlation": pearson([(r.chesslens, r.value) for r in rows]),
        "warning": None,
    }
    if n < MIN_RELIABLE_GAMES:
        result["warning"] = (
            f"Only {n} player-games: too few to say the metrics agree or disagree "
            f"(use at least {MIN_RELIABLE_GAMES}, preferably many more and varied strengths)."
        )
    return result


def build_rows(game: str, chesslens: dict[str, Optional[float]], refs: dict) -> list[Row]:
    rows = []
    for (system, color), value in refs.items():
        mine = chesslens.get(color)
        if value is not None and mine is not None:
            rows.append(Row(game, color, system, mine, value))
    return rows


def format_report(rows: list[Row]) -> str:
    lines = [f"{'Game':<32}{'Side':<7}{'Reference':<10}{'ChessLens':>10}{'Reference':>10}{'Diff':>8}"]
    for r in rows:
        lines.append(f"{r.game[:31]:<32}{r.color:<7}{r.reference:<10}{r.chesslens:>10.1f}{r.value:>10.1f}{r.chesslens - r.value:>+8.1f}")
    for system in sorted({r.reference for r in rows}):
        stats = compare([r for r in rows if r.reference == system])
        lines.append("")
        lines.append(f"Summary against {system} (difference = ChessLens - reference)")
        lines.append(f"  player-games: {stats['n']}")
        lines.append(f"  mean difference: {stats['mean_difference']:+.2f}")
        lines.append(f"  mean absolute error: {stats['mean_absolute_error']:.2f}")
        lines.append(f"  largest absolute error: {stats['max_absolute_error']:.2f}")
        corr = stats["correlation"]
        lines.append(f"  correlation: {'n/a (needs 3+ games with varied scores)' if corr is None else f'{corr:.2f}'}")
        if stats["warning"]:
            lines.append(f"  WARNING: {stats['warning']}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare ChessLens game accuracy with reference values.")
    parser.add_argument("manifest", help="CSV with columns: pgn, white_chesscom, black_chesscom, white_lichess, black_lichess")
    parser.add_argument("--stockfish", help="path to the Stockfish executable")
    parser.add_argument("--depth", type=int, default=12)
    parser.add_argument("--multipv", type=int, default=3)
    parser.add_argument("--output", help="optional CSV file for the per-game comparison")
    args = parser.parse_args(argv)

    # Imported here so the statistics above can be tested without python-chess.
    from analyzer import find_stockfish, load_game
    from models import ChessLensError, summarize
    from pipeline import run_analysis

    try:
        entries = load_manifest(Path(args.manifest))
        if not entries:
            raise ValidationError("The manifest has no games.")
        stockfish = find_stockfish(args.stockfish)
        base = Path(args.manifest).resolve().parent
        rows: list[Row] = []
        for entry in entries:
            pgn_path = Path(entry["pgn"])
            if not pgn_path.is_absolute() and not pgn_path.exists():
                pgn_path = base / pgn_path
            print(f"Analyzing {pgn_path} ...", flush=True)
            _, results = run_analysis(load_game(pgn_path), stockfish, args.depth, args.multipv)
            summary = summarize(results)
            mine = {"White": summary["white_accuracy"], "Black": summary["black_accuracy"]}
            rows.extend(build_rows(pgn_path.name, mine, entry["refs"]))
        if not rows:
            raise ValidationError("No reference values were found in the manifest, so there is nothing to compare.")
        print()
        print(format_report(rows))
        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["game", "color", "reference", "chesslens", "reference_value", "difference"])
                for r in rows:
                    writer.writerow([r.game, r.color, r.reference, f"{r.chesslens:.2f}", f"{r.value:.2f}", f"{r.chesslens - r.value:.2f}"])
            print(f"\nSaved: {Path(args.output).resolve()}")
        return 0
    except (ValidationError, ChessLensError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
