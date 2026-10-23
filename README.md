# Plyra 1.3.2 — Final Premium Dashboard UI

A final presentation-layer refinement of the existing Plyra 1.3.2 report. The analysis pipeline and offline report structure are retained.

## UI refinements
- Player and accuracy cards span the full report width, with balanced White/Black presentation.
- Chessboard pieces use a warm, wood-inspired treatment using offline system chess glyphs and CSS shading (not an external piece image set).
- Classification badges on the board are compact colored symbols rather than move-label text.
- A slim evaluation bar beside the board displays the post-move engine score in pawns and centipawns when available.
- The move list and evaluation graph share one panel; the graph is compact and sits directly beneath the move sheet.
- The move navigator is compact, and the engine candidate panel presents up to three candidates from the stored MultiPV analysis. Selecting one draws its move arrow on the board.
- Plyra branding is used in the dashboard and generated report metadata where appropriate. Legacy internal identifiers remain where changing them would risk breaking compatibility.

## Important behavior
- Candidate lines are limited to the candidates saved during the original engine analysis. If the report only contains fewer than three candidates, it cannot invent additional engine lines.
- Evaluation is shown only when the report has a numeric centipawn or mate score for the selected position. The position before the first move has no separately stored after-move score and displays a dash.
- The wood-inspired pieces are CSS-styled system chess symbols, not a bundled Chess.com wood-piece asset set; exact rendering can vary slightly by operating system and browser.
- This UI has not been visually verified in every browser. Run the existing tests and open a newly generated report locally before replacing your working copy.


## Opening book and opening-name database

Polyglot move-book detection and opening-name detection are separate features.
Place your Polyglot `.bin` file at `books/book.bin`. Place a PGN opening database
with `[Opening "..."]` and optional `[ECO "..."]` headers at `books/openings.pgn`.
Then run from this project directory:

```bash
python main.py games/opera_game.pgn --book books/book.bin --opening-db books/openings.pgn
```

`--book` enables the existing Polyglot Book move classification. `--opening-db`
identifies the longest matching opening line and adds its name/ECO to terminal
output and the HTML report. The `.bin` file alone usually cannot provide names.
See `books/README.txt` for details.

### Building the databases

See `books/README.txt` for the exact steps. In short: `tools/build_openings_pgn.py` converts the Lichess chess-openings TSV files into `books/openings.pgn`, and `tools/build_book.py` builds `books/book.bin` from a Lichess / Lichess Elite game dump.
