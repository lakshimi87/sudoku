"""Sudoku board logic: candidates, human-style deduction, generation."""

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


def naked_single(grid, i):
    """Only one digit fits in cell `i` -- everything else is taken by a peer."""
    cands = candidates(grid, i)
    if len(cands) != 1:
        return None
    value = cands[0]
    reason = sorted(j for j in PEERS[i] if grid[j] and grid[j] != value)
    r, c = rc(i)
    text = "R%dC%d: every other digit is already used by a peer." % (r + 1, c + 1)
    return Step(i, value, reason, "naked single", text)


def hidden_single(grid, i):
    """Cell `i` is the only place in one of its units for some digit."""
    for unit, name in zip(UNITS, UNIT_NAMES):
        if i not in unit:
            continue
        others = [j for j in unit if j != i]
        for value in candidates(grid, i):
            spots = [j for j in others if not grid[j] and value in candidates(grid, j)]
            if spots:
                continue
            reason = []
            for j in others:
                if grid[j]:
                    reason.append(j)  # occupies a slot in this unit
                else:
                    # blocked from taking `value` by a peer outside the unit
                    reason.extend(k for k in PEERS[j] if grid[k] == value)
            r, c = rc(i)
            text = "R%dC%d: %d fits nowhere else in this %s." % (
                r + 1,
                c + 1,
                value,
                name,
            )
            return Step(i, value, sorted(set(reason)), "hidden single", text)
    return None


def deduce_cell(grid, i):
    """Try to pin down cell `i`; return a Step or None."""
    if grid[i]:
        return None
    return naked_single(grid, i) or hidden_single(grid, i)


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
        step, _ = search_step(work, rng=_StableRandom())
        if not step:
            return work if all(work) else None
        work[step.index] = step.value


class _StableRandom:
    """random-like object with a no-op shuffle, for deterministic solving."""

    @staticmethod
    def shuffle(seq):
        return None


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
