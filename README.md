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
| `next search` | Finds the next cell that can be settled. |
| `auto search` | Keeps searching on its own, 3 s per cell, until finish or stuck. |
| `reset` | Puts the original problem back. |
| `load` / `save` | Reads and writes puzzles under `puzzles/`. |
| `clear board` | Empties the board. |
| `quit` | Exits (also `Esc`). |

**edit** — left-click a cell to pop up a 1–9 / `clear` pad; `1`–`9` writes the
digit, `clear` erases it. `done` leaves edit mode and refuses to exit while two
clues conflict. Keyboard digits work too.

**solve** — empty cells are searched in random order. For each one the solver
checks whether its value is already forced (naked single: every other digit is
taken by a peer; hidden single: the digit fits nowhere else in a row, column or
box). If not, that cell is dropped from this round and the search moves on.
When a cell is settled, its digit is filled in (blue) and the cell turns green.

Both rules are tried on every cell and the shorter justification wins, so the
amber highlight stays as small as it can be. For a hidden single that means
only the cells holding that same digit — the ones that keep it out of every
other square of the row, column or box — and never more of them than needed to
cover them all; squares of the unit that are already filled argue for
themselves and stay unmarked. A naked single needs one peer per eliminated
digit, so it highlights eight.

- Puzzle completed → `Finish!`
- No remaining cell can be determined → `Cannot be solved by search`, with
  `user solve` (fill cells yourself, given clues stay locked) or `reset`.

**auto search** — after a cell is found the answer stays up for three seconds,
then the next search starts by itself; the panel counts the pause down. The
button turns into `stop auto`, and the run ends on its own at `Finish!` or when
nothing more can be determined.

**reset** — restores the problem as it was before solving started. Everything
the solver or the `user solve` mode placed is removed, and those squares keep a
grey background so it stays visible that they were never part of the problem.

**load / save** — puzzles live in `puzzles/*.sdk`, nine rows of `1`-`9` and `.`
for the original problem, a blank line, then the board as it stands, so saving
mid-solve keeps the progress *and* the problem to reset to. `#` starts a
comment, and a file holding just one block loads as a problem, so hand-written
grids work. `save` asks for a name (Enter confirms); `load` lists what is in the
folder — click a row, then `load`.

## Layout

- `main.py` — entry point
- `sudoku/logic.py` — board representation, candidates, deduction steps
  (`search_step`) with minimal reasons, the `.sdk` text format (`dump`/`parse`),
  brute-force solution counting, puzzle generation
- `sudoku/app.py` — pygame-ce window, modes, number pad, file dialog, rendering
- `puzzles/` — saved puzzles

Generated puzzles are checked for a unique solution *and* for being solvable by
singles alone, so `solve` can always take them to the finish.
