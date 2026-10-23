"""ChessLens - command-line entry point.

Examples:
    python main.py games/opera_game.pgn
    python main.py games/opera_game.pgn --depth 14 --format html csv pgn json
    python main.py games/opera_game.pgn --stockfish "engines/stockfish.exe" --no-report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer import (
    DEFAULT_DEPTH,
    DEFAULT_MULTIPV,
    DEFAULT_VERIFY_EXTRA_DEPTH,
    find_stockfish,
    load_game,
)
from classifier import DEFAULT_THRESHOLDS, load_thresholds
from models import LABELS, ChessLensError, GameInfo, MoveResult, summarize
from opening_names import identify_opening
from pipeline import run_analysis
from reports import FORMAT_EXTENSIONS, prepare_output_dir, write_reports

FORMAT_CHOICES = list(FORMAT_EXTENSIONS) + ["all"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ChessLens: analyze a PGN game with Stockfish, classify every move and save reports."
    )
    parser.add_argument("pgn", help="path to a PGN file containing one game")
    parser.add_argument(
        "--stockfish",
        help="path to the Stockfish executable (optional if it is in the "
        "'engine' folder or on your PATH)",
    )
    parser.add_argument(
        "--depth", type=int, default=DEFAULT_DEPTH,
        help=f"engine search depth (default: {DEFAULT_DEPTH}; higher is slower)",
    )
    parser.add_argument(
        "--multipv", type=int, default=DEFAULT_MULTIPV,
        help=f"number of candidate moves Stockfish reports (default: {DEFAULT_MULTIPV})",
    )
    parser.add_argument(
        "--verify-depth", type=int, default=None,
        help="depth for the extra check of possible Brilliant moves "
        f"(default: --depth + {DEFAULT_VERIFY_EXTRA_DEPTH})",
    )
    parser.add_argument(
        "--book", help="optional Polyglot opening book (.bin file); enables the Book label",
    )
    parser.add_argument(
        "--opening-db", help="optional PGN database with Opening/ECO headers for opening-name detection",
    )
    parser.add_argument(
        "--config", help="optional JSON file that overrides classification thresholds "
        '(for example {"best_max_loss": 0.01})',
    )
    parser.add_argument(
        "--format", nargs="+", choices=FORMAT_CHOICES, default=["html"], metavar="FORMAT",
        help="report formats to save: html csv pgn json all (default: html). "
        "Put the PGN file name BEFORE this option.",
    )
    parser.add_argument(
        "--output-dir", default="reports", help="folder for the reports (default: reports)",
    )
    parser.add_argument("--no-report", action="store_true", help="only print in the terminal, save nothing")
    parser.add_argument(
        "--overwrite", action="store_true",
        help="replace existing report files instead of creating numbered copies",
    )
    parser.add_argument("--compact", action="store_true", help="print one short line per move")

    args = parser.parse_args()
    if args.depth < 1:
        parser.error("--depth must be 1 or higher")
    if not 1 <= args.multipv <= 10:
        parser.error("--multipv must be between 1 and 10")
    if args.verify_depth is not None and args.verify_depth < args.depth:
        parser.error("--verify-depth must not be lower than --depth")
    return args


def resolve_formats(chosen: list[str]) -> list[str]:
    if "all" in chosen:
        return list(FORMAT_EXTENSIONS)
    seen: list[str] = []
    for name in chosen:
        if name not in seen:
            seen.append(name)
    return seen


# --------------------------------------------------------------------------
# Terminal output
# --------------------------------------------------------------------------

def print_header(game, info: GameInfo) -> None:
    headers = game.headers
    print("ChessLens — Game Analysis\n")
    print(f"White: {headers.get('White', 'Unknown')}")
    print(f"Black: {headers.get('Black', 'Unknown')}")
    print(f"Result: {headers.get('Result', '*')}")
    opening = headers.get("Opening", "").strip()
    eco = headers.get("ECO", "").strip()
    if opening and opening != "?":
        print(f"Opening: {opening}" + (f" ({eco})" if eco and eco != "?" else ""))
    print(f"Engine: {info.engine_name or 'Stockfish'}")
    print(f"Analysis depth: {info.depth}   Candidate moves (MultiPV): {info.multipv}")
    print(f"Accuracy model: {info.accuracy_model} (custom estimate, not Chess.com's score)")
    book = info.book_file or "not used (Book labels disabled)"
    print(f"Opening book: {book}")
    for warning in info.warnings:
        print(f"Warning: {warning}")
    print()


def format_loss(result: MoveResult) -> str:
    if result.loss_cp is None:
        return "n/a (a forced mate is involved)"
    return f"{result.loss_cp} cp ({result.loss_cp / 100:.2f} pawns)"


def format_accuracy(value) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def print_move(result: MoveResult) -> None:
    print(f"{result.move_label} — {result.color}")
    print(f"Played: {result.played_san}")
    print(f"Stockfish's top move: {result.best_san or '(none)'}")
    if result.best_score_text is not None:
        print(f"Best-move evaluation: {result.best_score_text} (White's perspective)")
    if result.played_score_text is not None:
        print(f"Played-move evaluation: {result.played_score_text} (White's perspective)")
    if result.accuracy is not None:
        print(f"Evaluation loss: {format_loss(result)}")
        print(f"Win%: {result.win_before:.1f} -> {result.win_after:.1f} (for the player who moved)")
        print(f"ChessLens Accuracy: {result.accuracy:.1f} / 100")
    else:
        print(f"Not scored: {result.note}")
    if result.ep_loss is not None:
        print(f"Expected points: {result.ep_before:.2f} -> {result.ep_played:.2f} (loss {result.ep_loss:.3f})")
    print(f"Classification: {result.label}" + (" (low confidence)" if result.confidence == "low" else ""))
    for text in result.annotations:
        print(f"Annotation: {text}")
    if result.classification_note:
        print(f"Why: {result.classification_note}")
    if result.context:
        print(f"Position: {result.context}")
    if result.candidates:
        print(f"Top candidates: {', '.join(result.candidates)}")
    if result.matched is None:
        print("Matches Stockfish's top move: unknown (no recommendation)")
    else:
        print(f"Matches Stockfish's top move: {'yes' if result.matched else 'no'}")
    print()


def print_move_compact(result: MoveResult) -> None:
    notes = f"  [{'; '.join(result.annotations)}]" if result.annotations else ""
    print(
        f"{result.move_label:<9} {result.color:<5} {result.played_san:<8} "
        f"{result.label:<11} acc {format_accuracy(result.accuracy):>5}  "
        f"best {result.best_san or '-'}{notes}"
    )


def print_summary(summary: dict, ending: str) -> None:
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Game ending: {ending}")
    print(f"Moves analyzed: {summary['total']}  (scored: {summary['scored']})")
    print()
    print(f"ChessLens Accuracy — game accuracy, model {summary['accuracy_model']}")
    print(f"  White:   {format_accuracy(summary['white_accuracy'])}"
          f"   (plain average of move accuracies: {format_accuracy(summary['white_mean_move_accuracy'])})")
    print(f"  Black:   {format_accuracy(summary['black_accuracy'])}"
          f"   (plain average of move accuracies: {format_accuracy(summary['black_mean_move_accuracy'])})")
    print(f"  Overall: {format_accuracy(summary['overall_accuracy'])}")
    print()
    print("Move classifications")
    counts = summary["label_counts"]
    print(f"  {'':<13}{'White':>6}{'Black':>7}{'Total':>7}")
    for label in LABELS:
        if label == "Unclassified" and counts["Total"][label] == 0:
            continue
        print(
            f"  {label:<13}{counts['White'][label]:>6}{counts['Black'][label]:>7}"
            f"{counts['Total'][label]:>7}"
        )
    if summary["unscored"]:
        print("\nPositions that could not be scored reliably:")
        for line in summary["unscored"]:
            print(f"  - {line}")
    print()
    print("Top-move matches (separate from accuracy and classification)")
    print(f"  Matched Stockfish's top move: {summary['matched']}")
    print(f"  Did not match: {summary['not_matched']}")
    print(f"  Top-move match rate: {summary['match_rate']:.1f}%")
    print(
        "\nNote: ChessLens Accuracy and the move classifications are experimental metrics\n"
        "made for this project. They are NOT Chess.com's Accuracy or Game Review labels."
    )


# --------------------------------------------------------------------------
# Main program
# --------------------------------------------------------------------------

def main() -> int:
    # Make sure symbols like "—" print correctly in the Windows terminal.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    pgn_path = Path(args.pgn)
    formats = resolve_formats(args.format)
    output_dir = Path(args.output_dir)

    try:
        game = load_game(pgn_path)
        if args.opening_db:
            opening_name, eco_code = identify_opening(game, args.opening_db)
            if opening_name:
                game.headers["Opening"] = opening_name
                if eco_code:
                    game.headers["ECO"] = eco_code
            else:
                print("Opening detected: no matching named line found in the supplied database")
        stockfish_path = find_stockfish(args.stockfish)
        thresholds = load_thresholds(args.config) if args.config else DEFAULT_THRESHOLDS
        if not args.no_report:
            prepare_output_dir(output_dir)  # fail now, not after a long analysis

        def show_header(info: GameInfo) -> None:
            print_header(game, info)

        def show_move(result: MoveResult) -> None:
            # Print as we go; analysis can take a while.
            print_move_compact(result) if args.compact else print_move(result)

        info, results = run_analysis(
            game, stockfish_path, args.depth, args.multipv, args.verify_depth,
            args.book, thresholds, on_start=show_header, on_move=show_move,
        )
        summary = summarize(results)
        if args.compact:
            print()
        print_summary(summary, info.ending)

        exit_code = 0
        if not args.no_report:
            saved, errors = write_reports(
                info, results, summary, formats, output_dir, pgn_path.stem, args.overwrite
            )
            print("\nReports saved:")
            for path in saved:
                print(f"  {path.resolve()}")
            for message in errors:
                print(f"Error: {message}", file=sys.stderr)
                exit_code = 1
        return exit_code

    except (ChessLensError, OSError) as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
