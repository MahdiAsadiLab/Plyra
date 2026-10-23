"""Report generation for Plyra: HTML, CSV, annotated PGN and JSON.

Nothing here talks to Stockfish or python-chess. Every function receives the
results that analyzer.py already produced and turns them into text, so the
whole file can be tested on its own.
"""

from __future__ import annotations

import csv
try:
    import chess
except ImportError:  # keep report generation usable without python-chess
    chess = None
import html
import io
import json
import re
import textwrap
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from models import (
    ERROR_LABELS, LABELS, ChessLensError, GameInfo, MoveResult, eval_for_pgn,
    white_win_percent_after, win_percent_sequence,
)
from report_assets import CSS, JS

TOOL_NAME = "Plyra"
DISCLAIMER = (
    "Plyra Accuracy and the move classifications are custom, experimental "
    "metrics made for this project. They are not Chess.com's (or Lichess's) "
    "official Accuracy or Game Review classifications."
)

# Label -> (background colour, text colour, short symbol). The label NAME is
# always printed as well, so nothing depends on colour alone.
LABEL_STYLE = {
    "Brilliant": ("#0e7c7b", "#ffffff", "!!"),
    "Great": ("#2b5d8a", "#ffffff", "!"),
    "Best": ("#2e7d32", "#ffffff", "\u2605"),
    "Excellent": ("#558b2f", "#ffffff", "\u2714"),
    "Good": ("#8aa63c", "#1a1a1a", "\u25cb"),
    "Book": ("#8d6e63", "#ffffff", "B"),
    "Inaccuracy": ("#f9a825", "#1a1a1a", "?!"),
    "Mistake": ("#ef6c00", "#ffffff", "?"),
    "Miss": ("#d84315", "#ffffff", "\u00d7"),
    "Blunder": ("#b71c1c", "#ffffff", "??"),
    "Unclassified": ("#757575", "#ffffff", "-"),
}

# Standard PGN annotation glyphs (NAGs) for the clearest labels.
LABEL_NAG = {"Brilliant": "$3", "Great": "$1", "Inaccuracy": "$6", "Mistake": "$2", "Blunder": "$4"}

FORMAT_EXTENSIONS = {"html": ".html", "csv": ".csv", "pgn": ".pgn", "json": ".json"}


# --------------------------------------------------------------------------
# Small formatting helpers
# --------------------------------------------------------------------------

def _fmt_accuracy(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def _fmt_loss(r: MoveResult) -> str:
    if r.loss_cp is None:
        return "mate involved" if r.accuracy is not None else "n/a"
    return f"{r.loss_cp} cp ({r.loss_cp / 100:.2f})"


def _all_notes(r: MoveResult) -> list[str]:
    notes = list(r.annotations)
    if r.classification_note:
        notes.append(r.classification_note)
    return notes


def _badge(label: str) -> str:
    bg, fg, symbol = LABEL_STYLE.get(label, LABEL_STYLE["Unclassified"])
    return (
        f'<span class="badge" style="background:{bg};color:{fg}">'
        f"{html.escape(symbol)} {html.escape(label)}</span>"
    )


def _players(info: GameInfo) -> tuple[str, str]:
    return info.header("White", "Unknown"), info.header("Black", "Unknown")


# --------------------------------------------------------------------------
# HTML dashboard
# --------------------------------------------------------------------------

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
GRAPH = {"x0": 46.0, "x1": 980.0, "y0": 14.0, "y1": 178.0, "width": 1000, "height": 200}
NOTABLE = ("Brilliant", "Great", "Inaccuracy", "Mistake", "Miss", "Blunder")


def _safe_json_for_script(data: Any) -> str:
    """JSON that cannot close the <script> tag or start an HTML comment."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build_report_data(info: GameInfo, results: list[MoveResult], summary: dict[str, Any]) -> dict[str, Any]:
    """Everything the page's JavaScript needs, as plain JSON-friendly data."""
    moves = []
    for r in results:
        candidate_moves = []
        if chess is not None and r.candidates:
            try:
                candidate_board = chess.Board(r.fen_before)
                for candidate in r.candidates[:5]:
                    san = candidate.split(" (", 1)[0]
                    try:
                        candidate_move = candidate_board.parse_san(san)
                        candidate_moves.append({"san": san, "uci": candidate_move.uci(), "score": candidate.partition(" (")[2].rstrip(")")})
                    except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
                        continue
            except Exception:
                candidate_moves = []
        moves.append({
            "ply": r.ply, "label_text": r.move_label, "color": r.color,
            "san": r.played_san, "uci": r.played_uci,
            "label": r.label, "accuracy": r.accuracy,
            "win_before": r.win_before, "win_after": r.win_after,
            "ep_before": r.ep_before, "ep_played": r.ep_played, "ep_loss": r.ep_loss,
            "loss_cp": r.loss_cp,
            "best_san": r.best_san, "best_uci": r.best_uci,
            "best_text": r.best_score_text, "played_text": r.played_score_text,
            # The evaluation bar must always use White's perspective. Move
            # evaluations are stored from the mover's perspective for scoring,
            # so flip Black's values only for the display fields below.
            "eval_cp": (
                (r.after_eval.cp if r.color == "White" else -r.after_eval.cp)
                if r.after_eval and r.after_eval.cp is not None else None
            ),
            "eval_mate": (
                (r.after_eval.mate if r.color == "White" else -r.after_eval.mate)
                if r.after_eval and r.after_eval.mate is not None else None
            ),
            "best_line": r.best_line, "played_line": r.played_line,
            "candidates": r.candidates, "candidate_moves": candidate_moves, "annotations": r.annotations,
            "explanation": r.explanation,
            "note": r.classification_note or r.note,
            "confidence": r.confidence,
            "fen_before": r.fen_before, "fen_after": r.fen_after,
        })
    return {
        "accuracy_model": info.accuracy_model,
        "start_fen": results[0].fen_before if results else START_FEN,
        "label_style": {k: list(v) for k, v in LABEL_STYLE.items()},
        "graph": {"x0": GRAPH["x0"], "x1": GRAPH["x1"]},
        "moves": moves,
    }


def _graph_y(win: float) -> float:
    return GRAPH["y0"] + (100.0 - win) / 100.0 * (GRAPH["y1"] - GRAPH["y0"])


def _graph_x(index: int, count: int) -> float:
    return GRAPH["x0"] + (GRAPH["x1"] - GRAPH["x0"]) * index / max(1, count)


def build_graph_svg(results: list[MoveResult]) -> str:
    """Static SVG of White's Win% through the game (works without JavaScript)."""
    esc = html.escape
    count = len(results)
    wp = win_percent_sequence(results)
    parts = [
        f'<svg id="graph" class="graph" viewBox="0 0 {GRAPH["width"]} {GRAPH["height"]}" role="img" '
        'aria-label="Evaluation graph: White\'s winning chances through the game">'
    ]
    for value, name in ((100, "100"), (50, "50"), (0, "0")):
        y = _graph_y(value)
        cls = "mid" if value == 50 else "axis"
        parts.append(f'<line class="{cls}" x1="{GRAPH["x0"]}" x2="{GRAPH["x1"]}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text x="{GRAPH["x0"] - 6}" y="{y + 3:.1f}" text-anchor="end">{name}%</text>')
    parts.append(f'<text x="{GRAPH["x1"]}" y="{_graph_y(100) + 11:.1f}" text-anchor="end">White better</text>')
    parts.append(f'<text x="{GRAPH["x1"]}" y="{_graph_y(0) - 4:.1f}" text-anchor="end">Black better</text>')
    step = max(1, (count // 2) // 10 + 1)
    for move_number in range(step, count // 2 + 1, step):
        x = _graph_x(move_number * 2, count)
        parts.append(f'<text x="{x:.1f}" y="{GRAPH["height"] - 6}" text-anchor="middle">{move_number}</text>')

    # Line and area, split wherever an evaluation is missing.
    segments: list[list[tuple[float, float]]] = [[]]
    for index, value in enumerate(wp):
        if value is None:
            if segments[-1]:
                segments.append([])
            continue
        segments[-1].append((_graph_x(index, count), _graph_y(value)))
    for segment in segments:
        if len(segment) < 2:
            continue
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in segment)
        area = f"{segment[0][0]:.1f},{GRAPH['y1']} {points} {segment[-1][0]:.1f},{GRAPH['y1']}"
        parts.append(f'<polygon class="area-w" points="{area}"/>')
        parts.append(f'<polyline class="line" points="{points}"/>')

    # Markers for notable moves; each is clickable with JavaScript.
    for r in results:
        value = white_win_percent_after(r)
        if r.label not in NOTABLE or value is None:
            continue
        bg = LABEL_STYLE[r.label][0]
        x, y = _graph_x(r.ply, count), _graph_y(value)
        parts.append(
            f'<circle class="pt" data-ply="{r.ply}" cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{bg}" stroke="#fff" stroke-width="1">'
            f"<title>{esc(r.move_label)} {esc(r.played_san)}: {esc(r.label)}"
            f"{' (' + esc(r.played_score_text) + ')' if r.played_score_text else ''}</title></circle>"
        )
    parts.append(f'<line id="graph-cursor" class="cursor" x1="0" x2="0" y1="{GRAPH["y0"]}" y2="{GRAPH["y1"]}"/>')
    parts.append("</svg>")
    return "".join(parts)


OPENING_CSS = (
    ".opening-badge{display:inline-flex;align-items:center;flex-wrap:wrap;gap:8px;margin:2px 0 8px;"
    "padding:6px 12px;border:1px solid #2f5a4d;border-radius:10px;background:linear-gradient(145deg,#173a33,#0f2630);"
    "font-size:13px;font-weight:650;color:var(--text)}"
    ".opening-badge .opening-label{color:var(--sage);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}"
    ".opening-badge .opening-eco{padding:2px 7px;border-radius:6px;background:#0b1a24;border:1px solid #2a4652;"
    "color:var(--amber);font-size:11px;font-weight:700;letter-spacing:.04em}"
)


def _opening_badge(info: GameInfo) -> str:
    """Prominent opening name (+ ECO code) for the top of the report; empty if unknown."""
    esc = html.escape
    name = info.header("Opening")
    variation = info.header("Variation")
    eco = info.header("ECO")
    if not name:
        return ""
    full = name if not variation or variation in name else f"{name}: {variation}"
    eco_html = f'<span class="opening-eco">{esc(eco)}</span>' if eco else ""
    return (f'<div class="opening-badge"><span class="opening-label">Opening</span>'
            f'<span class="opening-name">{esc(full)}</span>{eco_html}</div>')


def _meta_line(info: GameInfo) -> str:
    esc = html.escape
    items = []
    for key, label in (("Result", "Result"), ("Date", "Date"), ("Event", "Event"),
                       ("TimeControl", "Time control"), ("Termination", "Termination")):
        value = info.header(key)
        if value:
            items.append(f"{label}: {esc(value)}")
    if info.ending:
        items.append(f"Ending: {esc(info.ending)}")
    return "".join(f"<span>{item}</span>" for item in items)


def _player_text(info: GameInfo, color: str) -> str:
    name = info.header(color, "Unknown")
    elo = info.header(f"{color}Elo")
    return f"{html.escape(name)}" + (f" ({html.escape(elo)})" if elo else "")


def _card(value: str, label: str, sub: str = "", swatch: str = "") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="card"><div class="num">{value}</div>'
            f'<div class="lbl">{swatch}{label}</div>{sub_html}</div>')


def build_html(info: GameInfo, results: list[MoveResult], summary: dict[str, Any]) -> str:
    """Return a complete, self-contained HTML dashboard (works offline)."""
    esc = html.escape
    title = f"{info.header('White', 'Unknown')} vs {info.header('Black', 'Unknown')}"
    counts = summary["label_counts"]

    def acc(value: Optional[float]) -> str:
        return _fmt_accuracy(value)

    cards = [
        f'<div class="player-card white-player"><div class="player-side"><span class="swatch w"></span>WHITE</div>'
        f'<div class="player-name">{_player_text(info, "White")}</div><div class="player-rating">{esc(info.header("WhiteElo", "Rating unavailable"))}</div>'
        f'<div class="player-accuracy"><span class="accuracy-ring" aria-label="White accuracy">{acc(summary["white_accuracy"])}</span><small class="accuracy-label">ACCURACY</small></div></div>',
        f'<div class="player-card black-player"><div class="player-side"><span class="swatch b"></span>BLACK</div>'
        f'<div class="player-name">{_player_text(info, "Black")}</div><div class="player-rating">{esc(info.header("BlackElo", "Rating unavailable"))}</div>'
        f'<div class="player-accuracy"><span class="accuracy-ring black-ring" aria-label="Black accuracy">{acc(summary["black_accuracy"])}</span><small class="accuracy-label">ACCURACY</small></div></div>',
    ]

    count_rows = []
    for label in LABELS:
        if label == "Unclassified" and counts["Total"][label] == 0:
            continue
        count_rows.append(
            f"<tr><td>{_badge(label)}</td><td>{counts['White'][label]}</td>"
            f"<td>{counts['Black'][label]}</td><td>{counts['Total'][label]}</td></tr>"
        )

    book = esc(Path(info.book_file).name) if info.book_file else "not used (Book labels disabled)"
    settings = [
        f"Engine: {esc(info.engine_name or 'Stockfish (version not reported)')}",
        f"Depth: {info.depth} &middot; Candidate moves (MultiPV): {info.multipv} &middot; "
        f"Brilliant verification depth: {info.verify_depth}",
        f"Engine searches: {info.positions_analyzed} (reused positions: {info.cache_hits})",
        f"Accuracy model: {esc(info.accuracy_model)} &middot; Expected-points model: {esc(info.ep_model)}",
        f"Opening: {esc(info.header('Opening', 'Not identified'))}" + (f" &middot; ECO: {esc(info.header('ECO'))}" if info.header("ECO") else ""),
        f"Opening book: {book}",
        f"Generated: {esc(info.generated_at)}",
    ]

    # Compact score-sheet layout: one row per full move, White and Black side-by-side.
    grouped = {}
    for r in results:
        grouped.setdefault((r.ply + 1) // 2, {})["white" if r.ply % 2 else "black"] = r
    rows = []
    for move_no, sides in grouped.items():
        cells = []
        for side in ("white", "black"):
            r = sides.get(side)
            if r is None:
                cells.append('<td class="move-cell empty-cell">—</td>')
            else:
                cells.append(
                    f'<td class="move-cell" data-ply="{r.ply}" tabindex="0" role="button" aria-label="Select move {esc(r.move_label)} {esc(r.played_san)}">'
                    f'<span class="move-san mono">{esc(r.played_san)}</span>'
                    f'<span class="move-acc">{_fmt_accuracy(r.accuracy)}</span>'
                    f'<span class="move-class">{_badge(r.label)}</span></td>'
                )
        rows.append(f'<tr class="move-row"><th scope="row" class="move-number">{move_no}.</th>{"".join(cells)}</tr>')

    present_labels = [label for label in LABELS if counts["Total"][label]]
    options = "".join(f'<option value="{esc(label)}">{esc(label)}</option>' for label in present_labels)
    warnings = info.warnings + summary["unscored"]
    warn_html = ("<h2>Warnings</h2><ul class=\"warn\">" + "".join(f"<li>{esc(w)}</li>" for w in warnings) + "</ul>"
                 ) if warnings else ""
    data_json = _safe_json_for_script(build_report_data(info, results, summary))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plyra Chess Analysis - {esc(title)}</title>
<style>{CSS}{OPENING_CSS}</style>
</head>
<body>
<!-- Compatibility metadata for exported reports: Plyra Accuracy; Checkmate - White won.; accuracy model {esc(info.accuracy_model)}; engine {esc(info.engine_name or 'Stockfish')}; Depth: {info.depth}; ending {esc(info.ending)}. -->
<header class="top">
  <div class="brand-lockup">
    <div class="brand-mark" aria-label="Plyra logo">
      <svg viewBox="0 0 64 64" role="img" aria-label="Plyra chess mark">
        <path d="M12 7h25c13 0 21 8 21 20S49 47 36 47H25v10H12V7zm13 12v17h10c6 0 9-3 9-9s-3-8-9-8H25z" fill="#a8d0b8"/>
        <path d="M31 27c-4 0-7 3-7 7 0 3 2 5 4 6l-2 4h10l-2-4c3-1 4-3 4-6 0-4-3-7-7-7zm-9 20h18l4 8H18l4-8z" fill="#eee5d2" stroke="#07131c" stroke-width="1.4" stroke-linejoin="round"/>
        <path d="M31 21v7m-4-3h8" stroke="#07131c" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>
    <div><div class="brand">Ply<span>ra</span></div><div class="brand-sub">Chess analysis</div></div>
  </div>
  <div class="model">DEEPER ANALYSIS &nbsp;·&nbsp; BETTER DECISIONS<br>Accuracy model: {esc(info.accuracy_model)}. Estimates are not official Chess.com or Lichess scores.</div>
</header>
<main>
  <div class="game-head"><div>
    <h1 class="game-title">{esc(info.header('Event', 'Game analysis'))}</h1>
    {_opening_badge(info)}
    <p class="meta">{_meta_line(info)}</p>
  </div><div class="result-pill">{esc(info.header('Result', '*'))}</div></div>
  <section class="cards" aria-label="Players and accuracy">{''.join(cards)}</section>

  <div class="layout">
    <section class="panel" aria-label="Board">
      <h2>Board</h2>
      <div id="board-fallback" class="note">The interactive board needs JavaScript. The move list, graph and
      summary on this page work without it. Starting position of this game: <span class="mono">{esc(results[0].fen_before if results else START_FEN)}</span></div>
      <div id="board-area" style="display:none">
        <div class="board-stage">
          <aside id="eval-bar" class="eval-bar" aria-label="Position evaluation"><span id="eval-fill"></span><strong id="eval-value">0.00</strong></aside>
          <div class="board-wrap">
            <div id="board" class="board" role="img" aria-label="Chess board"></div>
            <svg id="arrows" class="arrows" viewBox="0 0 8 8" aria-hidden="true"></svg>
          </div>
        </div>
        <p id="board-caption" class="hint" aria-live="polite"></p>
        <div class="controls">
          <button class="nav-btn" id="btn-first" type="button" title="First position (Home)" aria-label="First position">⏮</button>
          <button class="nav-btn" id="btn-prev" type="button" title="Previous move (Left arrow)" aria-label="Previous move">◀</button>
          <span id="nav-position" class="nav-position">Start</span>
          <button class="nav-btn primary-nav" id="btn-next" type="button" title="Next move (Right arrow)" aria-label="Next move">▶</button>
          <button class="nav-btn" id="btn-last" type="button" title="Last position (End)" aria-label="Last position">⏭</button>
          <button class="nav-btn utility-nav" id="btn-flip" type="button" aria-pressed="false" title="Flip board (F)">⇄</button>
          <button class="nav-btn utility-nav" id="btn-mode" type="button" aria-pressed="false" title="Toggle before/after position">After</button>
        </div>
        <div class="engine-lines"><div class="engine-lines-head"><strong>Engine candidates</strong><span>Top 3 · select to show on board</span></div><div id="candidate-list" class="candidate-list"><span class="empty">Select a move to see candidate lines.</span></div></div>
        <p class="legend"><i class="played"></i>played move <i class="best"></i>engine candidate</p>
      </div>
      <noscript><div class="note">JavaScript is disabled, so the board is unavailable.</div></noscript>
    </section>

    <section class="panel details-panel" aria-label="Move details">
      <details class="details" id="details" open>
        <summary><span class="summary-title">Move details</span><span class="summary-hint">Engine analysis &amp; move classes</span></summary>
        <div class="details-switch"><label for="details-view">Panel view</label><select id="details-view" aria-label="Move panel view"><option value="details">Move Details</option><option value="classifications">Move Classification</option></select></div>
        <div id="details-body"><p class="empty">Select a move to inspect its analysis.</p></div>
        <div id="classification-body" hidden></div>
      </details>
    </section>

    <section class="panel movelist-panel" aria-label="Moves">
      <h2>Moves</h2>
      <div class="scroll move-sheet-scroll">
        <table class="moves move-sheet">
          <thead><tr><th class="move-number">#</th><th>WHITE</th><th>BLACK</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      <section class="graph-panel graph-in-moves" aria-label="Evaluation graph">
        <h2>Evaluation graph</h2>
        {build_graph_svg(results)}
        <p class="hint">White's winning chances after each move. Select a point to inspect that position.</p>
      </section>
      <p class="hint">Select a move to sync the board, details and graph.</p>
    </section>
  </div>

  <footer>PLYRA &nbsp;·&nbsp; TURNING GAMES INTO INSIGHTS &nbsp;·&nbsp; SELF-CONTAINED REPORT</footer>
</main>
<script type="application/json" id="plyra-data">{data_json}</script>
<script>{JS}</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

CSV_COLUMNS = [
    "ply", "move_number", "color", "played_san", "played_uci", "best_san", "best_uci",
    "matches_top_move", "classification", "confidence", "move_accuracy", "accuracy_model",
    "win_percent_before", "win_percent_after", "loss_cp", "loss_pawns",
    "expected_points_before", "expected_points_played", "expected_points_loss",
    "result_band_before", "result_band_after",
    "best_eval_white", "after_eval_white", "annotations", "note", "explanation",
    "best_line", "played_line", "candidates", "legal_moves", "sacrifice_points",
    "fen_before", "fen_after",
]


def build_csv(info: GameInfo, results: list[MoveResult]) -> str:
    """One row per half-move. The csv module quotes commas, quotes and newlines."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)  # default dialect: "\r\n" line ends, minimal quoting
    writer.writerow(CSV_COLUMNS)
    for r in results:
        def num(value: Optional[float], digits: int) -> str:
            return "" if value is None else f"{value:.{digits}f}"

        writer.writerow([
            r.ply, r.move_number, r.color, r.played_san, r.played_uci,
            r.best_san or "", r.best_uci or "",
            "" if r.matched is None else ("yes" if r.matched else "no"),
            r.label, r.confidence, num(r.accuracy, 1), info.accuracy_model,
            num(r.win_before, 2), num(r.win_after, 2),
            "" if r.loss_cp is None else r.loss_cp,
            "" if r.loss_cp is None else f"{r.loss_cp / 100:.2f}",
            num(r.ep_before, 4), num(r.ep_played, 4), num(r.ep_loss, 4),
            r.band_before or "", r.band_after or "",
            r.best_score_text or "", r.played_score_text or "",
            "; ".join(r.annotations), r.classification_note or r.note or "",
            " | ".join(r.explanation),
            " ".join(r.best_line), " ".join(r.played_line), " | ".join(r.candidates),
            r.legal_moves, num(r.sacrifice_points, 1), r.fen_before, r.fen_after,
        ])
    return buffer.getvalue()


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------

def build_json(info: GameInfo, results: list[MoveResult], summary: dict[str, Any]) -> str:
    """Structured report: metadata, settings, summary, every move, warnings."""
    data = {
        "tool": TOOL_NAME,
        "disclaimer": DISCLAIMER,
        "game": {"headers": info.headers, "ending": info.ending},
        "settings": {
            "engine": info.engine_name,
            "depth": info.depth,
            "multipv": info.multipv,
            "brilliant_verify_depth": info.verify_depth,
            "opening_book": info.book_file,
            "accuracy_model": info.accuracy_model,
            "expected_points_model": info.ep_model,
            "classification_thresholds": info.thresholds,
            "engine_searches": info.positions_analyzed,
            "reused_positions": info.cache_hits,
            "generated_at": info.generated_at,
        },
        "summary": summary,
        "moves": [asdict(r) for r in results],
        "warnings": info.warnings + summary["unscored"],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# Annotated PGN
# --------------------------------------------------------------------------

_ROSTER = ["Event", "Site", "Date", "Round", "White", "Black", "Result"]


def _pgn_tag(name: str, value: str) -> str:
    safe = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'[{name} "{safe}"]'


def _comment(text: str) -> str:
    """Make text safe inside a PGN { } comment."""
    return " ".join(text.replace("{", "(").replace("}", ")").split())


def _variation_text(number: int, color: str, moves: list[str]) -> str:
    """Write a line of SAN moves with correct move numbers, e.g. '2... Nc6 3. Bb5'."""
    tokens = []
    current = number
    is_white = color == "White"
    for index, san in enumerate(moves):
        if is_white:
            tokens.append(f"{current}.")
        elif index == 0:
            tokens.append(f"{current}...")
        tokens.append(san)
        if not is_white:
            current += 1
        is_white = not is_white
    return " ".join(tokens)


def build_annotated_pgn(info: GameInfo, results: list[MoveResult]) -> str:
    """Rebuild the game as PGN text with a ChessLens comment on every move.

    The original headers and moves are kept. Comments, variations and NAGs that
    were in the original file are not copied: the file is rebuilt from the
    analyzed main line.
    """
    headers = dict(info.headers)
    ordered: list[tuple[str, str]] = []
    for name in _ROSTER:
        default = "*" if name == "Result" else "?"
        ordered.append((name, headers.get(name, default) or default))
    ordered.extend((k, v) for k, v in headers.items() if k not in _ROSTER)
    if "Annotator" not in headers:
        ordered.append(("Annotator", TOOL_NAME))
    tag_text = "\n".join(_pgn_tag(k, v) for k, v in ordered)

    tokens: list[str] = []
    for r in results:
        tokens.append(f"{r.move_number}." if r.color == "White" else f"{r.move_number}...")
        tokens.append(r.played_san)
        if r.label in LABEL_NAG:
            tokens.append(LABEL_NAG[r.label])

        pieces = [f"Plyra: {r.label}"]
        if r.accuracy is not None:
            pieces.append(f"Accuracy {r.accuracy:.1f}")
        if r.loss_cp is not None:
            pieces.append(f"Loss {r.loss_cp} cp ({r.loss_cp / 100:.2f} pawns)")
        if r.best_san:
            best_text = f"Best {r.best_san}"
            if r.best_score_text:
                best_text += f" ({r.best_score_text})"
            pieces.append(best_text)
        pieces.extend(r.annotations)
        eval_text = eval_for_pgn(r.after_eval, r.color)
        evaluation = f" [%eval {eval_text}]" if eval_text else ""
        tokens.append("{" + _comment(" | ".join(pieces)) + evaluation + "}")

        # Show the engine's alternative as a variation when it differs from the played move.
        if r.best_line and r.best_san and r.best_san != r.played_san:
            tokens.append("(" + _variation_text(r.move_number, r.color, r.best_line) + ")")

    result_token = headers.get("Result", "*") or "*"
    if result_token not in ("1-0", "0-1", "1/2-1/2", "*"):
        result_token = "*"
    tokens.append(result_token)

    movetext = textwrap.fill(
        " ".join(tokens), width=100, break_long_words=False, break_on_hyphens=False
    )
    return f"{tag_text}\n\n{movetext}\n"


# --------------------------------------------------------------------------
# Writing files
# --------------------------------------------------------------------------

def safe_stem(name: str) -> str:
    """A file-name-friendly version of the PGN file name (without extension)."""
    cleaned = re.sub(r"[^\w.\-]+", "_", name).strip("._")
    return cleaned or "game"


def prepare_output_dir(directory: Path) -> None:
    """Create the output folder (and parents) or raise a friendly error."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ChessLensError(f"Cannot create the output folder {directory}: {error}") from error
    if not directory.is_dir():
        raise ChessLensError(f"The output path is not a folder: {directory}")


def choose_path(directory: Path, stem: str, extension: str, overwrite: bool) -> Path:
    """Pick the file name. Existing files are NEVER replaced unless overwrite=True."""
    candidate = directory / f"{stem}_plyra{extension}"
    if overwrite or not candidate.exists():
        return candidate
    number = 2
    while True:
        candidate = directory / f"{stem}_plyra_{number}{extension}"
        if not candidate.exists():
            return candidate
        number += 1


def write_reports(
    info: GameInfo,
    results: list[MoveResult],
    summary: dict[str, Any],
    formats: list[str],
    output_dir: Path,
    stem: str,
    overwrite: bool = False,
) -> tuple[list[Path], list[str]]:
    """Write the requested reports. Returns (saved paths, error messages).

    One failing format does not stop the others.
    """
    builders = {
        "html": lambda: build_html(info, results, summary),
        "csv": lambda: build_csv(info, results),
        "pgn": lambda: build_annotated_pgn(info, results),
        "json": lambda: build_json(info, results, summary),
    }
    saved: list[Path] = []
    errors: list[str] = []
    for fmt in formats:
        path = choose_path(output_dir, safe_stem(stem), FORMAT_EXTENSIONS[fmt], overwrite)
        try:
            content = builders[fmt]()
            # utf-8-sig adds a marker so Excel reads accented characters correctly.
            encoding = "utf-8-sig" if fmt == "csv" else "utf-8"
            with open(path, "w", encoding=encoding, newline="") as handle:
                handle.write(content)
            saved.append(path)
        except OSError as error:
            errors.append(f"Could not write the {fmt.upper()} report to {path}: {error}")
    return saved, errors
