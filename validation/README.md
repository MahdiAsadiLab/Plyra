# Validating ChessLens Accuracy

ChessLens does not ship reference data and never invents any. To compare it
with Chess.com or Lichess you collect the numbers yourself.

1. Put your PGN files in the `games` folder (one game per file).
2. For each game open its analysis on Chess.com and/or Lichess and write down the
   accuracy shown for White and for Black. Use the same game and, ideally, mention
   which site and date you used.
3. Copy `manifest_template.csv` to `manifest.csv` and add one line per game
   (leave a cell empty when you do not have that value).
4. Run:
   ```
   python validate.py validation/manifest.csv --stockfish "engines/stockfish-windows-x86-64-universal.exe" --depth 12 --output validation/results.csv
   ```
5. Read the summary: mean difference (positive = ChessLens is higher), mean
   absolute error, largest error and correlation, per reference site.

Rules of thumb
- Fewer than 20 player-games cannot show agreement or disagreement; the tool prints a warning.
- Use games of different results, lengths and rating levels. Do not tune the model on
  the same few games you use to judge it.
- Chess.com's formula (CAPS2) is not public, and each site uses a different engine,
  depth and win-probability curve, so exact equality is not expected. The goal is a
  measured, stable relationship, not an identical number.
- Lichess numbers can be compared with the `lichess-inspired-v1` model most
  directly, but remember ChessLens runs its own Stockfish at your chosen depth.
