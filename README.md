# sudoku

A pygame-ce sudoku program that solves puzzles the way a person would — one
deduction at a time, showing which known cells force each answer.

## Install / run

```sh
./setup.sh    # creates .venv and installs pygame-ce
./play.sh     # starts the program
```

## Modes

| Button | What it does |
| --- | --- |
| `edit` | Enter a problem by hand. Turns into `done` while editing. |
| `generate random` | Builds a random puzzle with a unique solution. |
| `solve` | Steps through the puzzle one determined cell at a time. |
| `clear board` | Empties the board. |
| `quit` | Exits (also `Esc`). |

**edit** — left-click a cell to pop up a 1–9 / `clear` pad; `1`–`9` writes the
digit, `clear` erases it. `done` leaves edit mode and refuses to exit while two
clues conflict. Keyboard digits work too.

**solve** — empty cells are searched in random order. For each one the solver
checks whether its value is already forced (naked single: every other digit is
taken by a peer; hidden single: the digit fits nowhere else in a row, column or
box). If not, that cell is dropped from this round and the search moves on.
When a cell is settled, its digit is filled in (blue), the cell turns green, the
existing cells that justify it are highlighted amber, and `next search`
continues.

- Puzzle completed → `Finish!`
- No remaining cell can be determined → `Cannot be solved by search`, with
  `user solve` (fill cells yourself, given clues stay locked) or `abort`.

`abort` removes everything the solver placed and returns to the original problem.

## Layout

- `main.py` — entry point
- `sudoku/logic.py` — board representation, candidates, deduction steps
  (`search_step`), brute-force solution counting, puzzle generation
- `sudoku/app.py` — pygame-ce window, modes, number pad, rendering

Generated puzzles are checked for a unique solution *and* for being solvable by
singles alone, so `solve` can always take them to the finish.
