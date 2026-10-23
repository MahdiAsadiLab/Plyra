#!/usr/bin/env python3
"""Convert the Lichess chess-openings TSV files into books/openings.pgn.

Input : a.tsv ... e.tsv from https://github.com/lichess-org/chess-openings
        (columns: eco, name, pgn). Give files, a folder, or a wildcard.
Output: a PGN file with one short game per named opening, with [ECO] and
        [Opening] headers. This is the format `main.py --opening-db` reads.

Example:
    python tools/build_openings_pgn.py books/raw -o books/openings.pgn
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import sys
from pathlib import Path

import chess.pgn


def expand_inputs(inputs: list[str]) -> list[Path]:
    """Accept files, folders (all *.tsv inside) and wildcards (for Windows cmd)."""
    paths: list[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.tsv")))
        elif any(ch in item for ch in "*?["):
            paths.extend(Path(m) for m in sorted(glob.glob(item)))
        else:
            paths.append(p)
    return paths


def escape_tag(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="TSV files, a folder containing them, or a wildcard")
    parser.add_argument("-o", "--output", default="books/openings.pgn")
    args = parser.parse_args()

    files = expand_inputs(args.inputs)
    if not files:
        parser.error("no .tsv files found")

    written = skipped = 0
    seen: set[str] = set()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        for path in files:
            if not path.is_file():
                print(f"Skipping missing file: {path}", file=sys.stderr)
                continue
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if not reader.fieldnames or not {"eco", "name", "pgn"} <= set(reader.fieldnames):
                    print(f"Skipping {path}: expected columns eco, name, pgn", file=sys.stderr)
                    continue
                for row in reader:
                    eco = (row["eco"] or "").strip()
                    name = (row["name"] or "").strip()
                    movetext = (row["pgn"] or "").strip()
                    if not name or not movetext or movetext in seen:
                        skipped += 1
                        continue
                    # Make sure python-chess can really read the line.
                    game = chess.pgn.read_game(io.StringIO(movetext))
                    if game is None or game.errors or not list(game.mainline_moves()):
                        skipped += 1
                        continue
                    seen.add(movetext)
                    out.write('[Event "Opening line"]\n')
                    out.write(f'[ECO "{escape_tag(eco)}"]\n')
                    out.write(f'[Opening "{escape_tag(name)}"]\n\n')
                    out.write(f"{movetext} *\n\n")
                    written += 1

    print(f"Wrote {written} opening lines to {out_path} ({skipped} skipped).")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
