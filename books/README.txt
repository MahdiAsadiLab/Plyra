PLYRA OPENING DATABASES
=======================
Two files live here:
  books/book.bin       Polyglot move book    -> used by  --book        ("Book" label)
  books/openings.pgn   opening names + ECO   -> used by  --opening-db  (name in report)

Both are built with the scripts in tools/. Install the dependencies first:
  pip install chess zstandard

STEP 1 - opening names (about 3,500 openings, free, CC0)
  a) Download a.tsv, b.tsv, c.tsv, d.tsv, e.tsv from
     https://github.com/lichess-org/chess-openings   (or: git clone that repo)
  b) Put them in  books/raw/
  c) python tools/build_openings_pgn.py books/raw -o books/openings.pgn

STEP 2 - opening book
  a) Download ONE game dump:
       - Lichess Elite Database (small, strong players):  https://database.nikonoel.fr
       - or Lichess standard rated games: https://database.lichess.org
         (recent months are huge - pick a small/old month, or use --max-games)
  b) python tools/build_book.py <downloaded file> -o books/book.bin
       useful options:  --min-rating 2200  --max-plies 24  --min-games 10  --max-games 2000000
  c) The script prints the first moves and the most popular line when it finishes.
     Check that they look like real chess theory.
     To check any other .bin later:  python tools/build_book.py --verify-only books/book.bin

STEP 3 - run
  python main.py games/opera_game.pgn --book books/book.bin --opening-db books/openings.pgn

Notes
  - A Polyglot .bin has no opening names; that is why names come from openings.pgn.
  - --min-games decides what counts as "book": a move must have been played at
    least that many times. Raise it for a stricter book, lower it for a wider one.
  - openings.pgn is matched by move order, so a game that reaches a known
    position by a different move order may not get a name.
