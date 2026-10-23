# Plyra

Chess game analyzer. Give it a PGN file; it uses Stockfish to classify every move (Brilliant, Best, Mistake, Blunder, ...), estimate accuracy for both players, detect the opening, and save an interactive HTML report. Everything runs locally and offline.

Accuracy is Plyra's own estimate, not the official Chess.com or Lichess score. This is an early version.

## 1. Install

```bash
git clone https://github.com/MahdiAsadiLab/Plyra.git
cd Plyra
pip install -r requirements.txt
```

## 2. Install Stockfish

Stockfish is not included. Download it from <https://stockfishchess.org/download/> and unzip it. Copy the executable into the `engine/` folder next to `main.py` (create the folder if it is missing).

Plyra picks up a file in `engine/` only if its name **starts with `stockfish`** and:
- **Windows:** it ends with `.exe`, for example `engine/stockfish-windows-x86-64-avx2.exe`
- **macOS / Linux:** it is executable: `chmod +x engine/stockfish*`

Alternatives, in this search order: pass `--stockfish PATH` to the run command, or have `stockfish` on your system `PATH`.

- **macOS:** `brew install stockfish`
- **Linux:** `sudo apt install stockfish` (the binary may be in `/usr/games/`; if Plyra can't find it, add `--stockfish /usr/games/stockfish`)
- "Illegal instruction" error: download a more basic build (`sse41-popcnt` or `x86-64`).

## 3. Quick start

```bash
python main.py games/opera_game.pgn
```

This needs nothing else. The terminal shows the analysis and the report is saved as `reports/opera_game_plyra.html` (the `reports/` folder is created automatically). Open the HTML file in your browser.

## 4. Optional: opening book and opening names

Without these, the analysis still works; you just won't get the **Book** label or the opening name. Build them once:

**Opening names:** download `a.tsv` to `e.tsv` from <https://github.com/lichess-org/chess-openings>, put them in `books/raw/`, then:

```bash
python tools/build_openings_pgn.py books/raw -o books/openings.pgn
```

**Opening book:** download a game dump, for example the Lichess Elite Database from <https://database.nikonoel.fr> (a `.zip`), then:

```bash
python tools/build_book.py path/to/dump.zip -o books/book.bin
```

`pip install zstandard` is only needed if your dump is a `.zst` file (such as the ones from database.lichess.org). It is not needed for normal analysis.

## 5. Full command

```bash
python main.py games/opera_game.pgn --book books/book.bin --opening-db books/openings.pgn --depth 16 --format all --overwrite
```

| Option | Description |
| --- | --- |
| `--stockfish PATH` | Path to the Stockfish executable (if not in `engine/`) |
| `--depth N` | Search depth, default 12 (higher is slower and more accurate) |
| `--book FILE` | Polyglot `.bin` book, enables the Book label |
| `--opening-db FILE` | PGN opening database, enables opening name and ECO |
| `--format ...` | `html csv pgn json all` (default `html`) |
| `--output-dir DIR` | Report folder (default `reports`) |
| `--overwrite` | Replace the old report instead of making a numbered copy |

## Third-party

[Stockfish](https://stockfishchess.org/) (GPL) is a separate download and is not part of this repository. PGN and Polyglot handling uses [python-chess](https://github.com/niklasf/python-chess). Opening names come from [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) (CC0).
