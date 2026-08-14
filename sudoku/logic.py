"""Sudoku board logic: candidates, human-style deduction, generation."""

import itertools
import random
from collections import namedtuple

SIZE = 9
CELLS = SIZE * SIZE
DIGITS = tuple(range(1, 10))


def rc(i):
    return divmod(i, SIZE)


def idx(r, c):
    return r * SIZE + c


ROW_UNITS = [[idx(r, c) for c in range(SIZE)] for r in range(SIZE)]
COL_UNITS = [[idx(r, c) for r in range(SIZE)] for c in range(SIZE)]
BOX_UNITS = [
    [idx(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3)]
    for br in range(3)
    for bc in range(3)
]
UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS

UNIT_NAMES = ["row"] * SIZE + ["column"] * SIZE + ["box"] * SIZE

# units containing each cell, and the peers of each cell
UNITS_OF = [[u for u in UNITS if i in u] for i in range(CELLS)]
PEERS = [
    frozenset(j for u in UNITS_OF[i] for j in u if j != i) for i in range(CELLS)
]

# A single deduction: cell `index` must hold `value`, justified by `reason`
# (the already-known cells that force it).
Step = namedtuple("Step", "index value reason kind text")


def empty_grid():
    return [0] * CELLS


def candidates(grid, i):
    """Digits that may still be placed in empty cell `i`."""
    used = {grid[j] for j in PEERS[i]}
    return [d for d in DIGITS if d not in used]


def conflicts(grid):
    """Indices of filled cells that clash with another filled cell."""
    bad = set()
    for u in UNITS:
        seen = {}
        for i in u:
            v = grid[i]
            if not v:
                continue
            if v in seen:
                bad.add(i)
                bad.add(seen[v])
            else:
                seen[v] = i
    return bad


def is_complete(grid):
    return all(grid) and not conflicts(grid)


# --------------------------------------------------------------------------
# human-style deduction
# --------------------------------------------------------------------------


def _min_cover(choices):
    """Fewest cells that hit every list in `choices` (each list is non-empty).

    Each list holds the cells that could justify one obligation; picking one
    cell from every list is enough, but a single cell often covers several, so
    the smallest hitting set is what gets highlighted.
    """
    if not choices:
        return []
    sets = [set(c) for c in choices]
    universe = sorted(set().union(*sets))
    for size in range(1, len(universe) + 1):
        for combo in itertools.combinations(universe, size):
            picked = set(combo)
            if all(picked & s for s in sets):
                return sorted(picked)
    return universe


def naked_single(grid, i):
    """Only one digit fits in cell `i` -- everything else is taken by a peer.

    One peer per eliminated digit is shown; more would be redundant.
    """
    cands = candidates(grid, i)
    if len(cands) != 1:
        return None
    value = cands[0]
    reason = sorted(
        next(j for j in PEERS[i] if grid[j] == d) for d in DIGITS if d != value
    )
    r, c = rc(i)
    text = "R%dC%d = %d: the other eight digits sit in a peer of this cell." % (
        r + 1, c + 1, value,
    )
    return Step(i, value, reason, "naked single", text)


def hidden_single(grid, i):
    """Cell `i` is the only place in one of its units for some digit.

    Every other empty cell of the unit must be barred from `value` by a peer
    already holding it; the reason keeps the smallest set of those holders
    that covers them all.  Cells of the unit that are already filled speak for
    themselves and are left out -- unless they are the whole argument.
    """
    best = None
    cands = candidates(grid, i)
    for unit, name in zip(UNITS, UNIT_NAMES):
        if i not in unit:
            continue
        others = [j for j in unit if j != i]
        filled = [j for j in others if grid[j]]
        empties = [j for j in others if not grid[j]]
        for value in cands:
            choices = []
            for j in empties:
                holders = [k for k in PEERS[j] if grid[k] == value]
                if not holders:
                    break  # `value` still fits in j, so i is not forced here
                choices.append(holders)
            else:
                reason = _min_cover(choices) or filled
                r, c = rc(i)
                text = "R%dC%d = %d: %d fits nowhere else in this %s." % (
                    r + 1, c + 1, value, value, name,
                )
                step = Step(i, value, reason, "hidden single", text)
                if best is None or len(step.reason) < len(best.reason):
                    best = step
                    if len(best.reason) <= 1:
                        return best
    return best


def deduce_cell(grid, i):
    """Try to pin down cell `i`; return the best-justified Step, or None."""
    if grid[i]:
        return None
    steps = [s for s in (naked_single(grid, i), hidden_single(grid, i)) if s]
    if not steps:
        return None
    return min(steps, key=lambda s: len(s.reason))


def quick_deduce(grid, i):
    """Value forced in cell `i`, or None -- same rules, no reason built."""
    cands = candidates(grid, i)
    if len(cands) == 1:
        return cands[0]
    for unit in UNITS_OF[i]:
        for value in cands:
            if all(
                grid[j] or value not in candidates(grid, j)
                for j in unit
                if j != i
            ):
                return value
    return None


def search_step(grid, excluded=(), rng=random):
    """Scan empty cells in random order for one that can be determined.

    Returns (step, visited) where `visited` lists the cells examined before the
    deduction succeeded.  step is None when no remaining cell can be settled.
    """
    empties = [i for i in range(CELLS) if not grid[i] and i not in excluded]
    rng.shuffle(empties)
    visited = []
    for i in empties:
        visited.append(i)
        step = deduce_cell(grid, i)
        if step:
            return step, visited
    return None, visited


def logic_solve(grid):
    """Solve using singles only. Returns the solved grid, or None if stuck."""
    work = list(grid)
    while True:
        progress = False
        for i in range(CELLS):
            if work[i]:
                continue
            value = quick_deduce(work, i)
            if value:
                work[i] = value
                progress = True
        if not progress:
            return work if all(work) else None


# --------------------------------------------------------------------------
# brute force solving / generation
# --------------------------------------------------------------------------


def count_solutions(grid, limit=2):
    work = list(grid)

    def rec():
        best, best_cands = -1, None
        for i in range(CELLS):
            if work[i]:
                continue
            cands = candidates(work, i)
            if len(cands) < 2:
                best, best_cands = i, cands
                break
            if best_cands is None or len(cands) < len(best_cands):
                best, best_cands = i, cands
        if best < 0:
            return 1
        total = 0
        for d in best_cands:
            work[best] = d
            total += rec()
            work[best] = 0
            if total >= limit:
                break
        return total

    return rec()


def solved_grid(rng=random):
    """Build a random complete grid."""
    grid = empty_grid()

    def rec(i=0):
        if i == CELLS:
            return True
        cands = candidates(grid, i)
        rng.shuffle(cands)
        for d in cands:
            grid[i] = d
            if rec(i + 1):
                return True
            grid[i] = 0
        return False

    rec()
    return grid


def _rows(grid):
    return [
        "".join(str(grid[idx(r, c)]) if grid[idx(r, c)] else "." for c in range(SIZE))
        for r in range(SIZE)
    ]


def dump(problem, grid):
    """Text form of a puzzle: the problem block, then the board as it stands."""
    lines = ["# sudoku -- original problem, then current board"]
    lines += _rows(problem)
    lines.append("")
    lines += _rows(grid)
    return "\n".join(lines) + "\n"


def parse(text):
    """Read `dump` output; returns (problem, grid).

    A file with a single block is taken as the problem alone.  Anything after
    a `#` is a comment and every character other than 1-9 and the empty marks
    (`.`, `0`, `_`) is ignored, so hand-written layouts load too.
    """
    cells = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        for ch in line:
            if ch in "123456789":
                cells.append(int(ch))
            elif ch in "._0":
                cells.append(0)
    if len(cells) == CELLS:
        return list(cells), list(cells)
    if len(cells) >= 2 * CELLS:
        return cells[:CELLS], cells[CELLS : 2 * CELLS]
    raise ValueError("expected %d digits, found %d" % (CELLS, len(cells)))


def generate(rng=random, min_clues=30, logic_only=True):
    """Random puzzle with a unique solution.

    With logic_only the puzzle is kept solvable by singles alone, so the
    step-by-step solver can always finish it.
    """
    grid = solved_grid(rng)
    order = list(range(CELLS))
    rng.shuffle(order)
    clues = CELLS
    for i in order:
        if clues <= min_clues:
            break
        saved = grid[i]
        grid[i] = 0
        ok = count_solutions(grid) == 1
        if ok and logic_only:
            ok = logic_solve(grid) is not None
        if ok:
            clues -= 1
        else:
            grid[i] = saved
    return grid
