"""Pygame-ce front end for the sudoku solver."""

import pathlib
import random
import sys

import pygame

from . import logic

PUZZLE_DIR = pathlib.Path(__file__).resolve().parent.parent / "puzzles"
PUZZLE_EXT = ".sdk"
AUTO_DELAY = 3000  # ms a found cell stays up before <auto search> moves on

CELL = 60
GRID = CELL * logic.SIZE
MARGIN_X = 30
MARGIN_Y = 96
PANEL_X = MARGIN_X + GRID + 30
WIDTH = PANEL_X + 240
HEIGHT = MARGIN_Y + GRID + 34

BG = (245, 246, 240)
LINE = (60, 60, 60)
THIN = (170, 172, 168)
TEXT = (30, 30, 34)
GIVEN = (25, 28, 34)
PLACED = (24, 90, 190)
SEL_BG = (214, 231, 250)
REASON_BG = (255, 236, 176)
FOUND_BG = (176, 232, 184)
BAD_BG = (250, 200, 200)
BTN = (232, 234, 230)
BTN_HOVER = (214, 218, 212)
BTN_EDGE = (120, 124, 120)
BTN_OFF = (240, 240, 238)
PAD_BG = (252, 252, 250)
RESET_BG = (228, 228, 224)
SHADOW = (215, 215, 210)


class Button:
    def __init__(self, rect, label, action, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.enabled = enabled

    def draw(self, surf, font, mouse):
        if not self.enabled:
            color = BTN_OFF
        elif self.rect.collidepoint(mouse):
            color = BTN_HOVER
        else:
            color = BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, BTN_EDGE, self.rect, width=1, border_radius=6)
        fg = TEXT if self.enabled else THIN
        label = font.render(self.label, True, fg)
        surf.blit(label, label.get_rect(center=self.rect.center))


class NumPad:
    """Popup with 1-9 and clear, shown when a cell is clicked."""

    KEY = 46
    W = KEY * 3
    H = KEY * 4

    def __init__(self, cell_index, pos):
        self.cell = cell_index
        x = min(max(pos[0], 4), WIDTH - self.W - 4)
        y = min(max(pos[1], 4), HEIGHT - self.H - 4)
        self.rect = pygame.Rect(x, y, self.W, self.H)

    def key_rects(self):
        for n in range(9):
            r, c = divmod(n, 3)
            yield n + 1, pygame.Rect(
                self.rect.x + c * self.KEY, self.rect.y + r * self.KEY,
                self.KEY, self.KEY,
            )
        yield 0, pygame.Rect(self.rect.x, self.rect.y + 3 * self.KEY, self.W, self.KEY)

    def hit(self, pos):
        for value, rect in self.key_rects():
            if rect.collidepoint(pos):
                return value
        return None

    def draw(self, surf, font, small, mouse):
        shadow = self.rect.move(3, 3)
        pygame.draw.rect(surf, (215, 215, 210), shadow, border_radius=8)
        pygame.draw.rect(surf, PAD_BG, self.rect, border_radius=8)
        pygame.draw.rect(surf, BTN_EDGE, self.rect, width=2, border_radius=8)
        for value, rect in self.key_rects():
            inner = rect.inflate(-4, -4)
            hovered = rect.collidepoint(mouse)
            pygame.draw.rect(surf, BTN_HOVER if hovered else BTN, inner, border_radius=5)
            pygame.draw.rect(surf, BTN_EDGE, inner, width=1, border_radius=5)
            if value:
                label = font.render(str(value), True, TEXT)
            else:
                label = small.render("clear", True, TEXT)
            surf.blit(label, label.get_rect(center=inner.center))


class FileDialog:
    """Modal panel listing saved puzzles; also takes a name when saving."""

    W, H = 430, 410
    ROW = 26

    def __init__(self, kind, files, name=""):
        self.kind = kind  # "load" or "save"
        self.files = files
        self.name = name
        self.suggested = bool(name)  # first keystroke replaces the offered name
        self.selected = None
        self.scroll = 0
        self.rect = pygame.Rect(0, 0, self.W, self.H)
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        top = self.rect.y + (78 if kind == "save" else 44)
        self.list_rect = pygame.Rect(
            self.rect.x + 14, top, self.W - 28, self.rect.bottom - 52 - top
        )
        self.name_rect = pygame.Rect(self.rect.x + 14, self.rect.y + 40, self.W - 28, 30)
        self.ok_rect = pygame.Rect(self.rect.right - 210, self.rect.bottom - 44, 92, 32)
        self.cancel_rect = pygame.Rect(self.rect.right - 106, self.rect.bottom - 44, 92, 32)

    @property
    def visible(self):
        return max(1, self.list_rect.height // self.ROW)

    def rows(self):
        for n, path in enumerate(self.files[self.scroll : self.scroll + self.visible]):
            yield path, pygame.Rect(
                self.list_rect.x, self.list_rect.y + n * self.ROW,
                self.list_rect.width, self.ROW,
            )

    def scroll_by(self, amount):
        top = max(0, len(self.files) - self.visible)
        self.scroll = min(max(0, self.scroll + amount), top)

    def hit(self, pos):
        """('pick', path) | ('ok',) | ('cancel',) | None -- None keeps it open."""
        if self.ok_rect.collidepoint(pos):
            return ("ok",)
        if self.cancel_rect.collidepoint(pos) or not self.rect.collidepoint(pos):
            return ("cancel",)
        for path, rect in self.rows():
            if rect.collidepoint(pos):
                self.selected = path
                self.name = path.stem
                self.suggested = False
                return ("pick", path)
        return None

    def on_key(self, event):
        if self.kind != "save":
            return
        if event.key == pygame.K_BACKSPACE:
            self.name = "" if self.suggested else self.name[:-1]
        elif event.unicode and event.unicode.isprintable():
            self.name = ("" if self.suggested else self.name) + event.unicode
        else:
            return
        self.suggested = False

    def draw(self, surf, font, small, mouse):
        pygame.draw.rect(surf, SHADOW, self.rect.move(4, 4), border_radius=10)
        pygame.draw.rect(surf, PAD_BG, self.rect, border_radius=10)
        pygame.draw.rect(surf, BTN_EDGE, self.rect, width=2, border_radius=10)
        title = "save problem as" if self.kind == "save" else "load problem"
        surf.blit(font.render(title, True, TEXT), (self.rect.x + 14, self.rect.y + 12))

        if self.kind == "save":
            pygame.draw.rect(surf, (255, 255, 255), self.name_rect, border_radius=5)
            pygame.draw.rect(surf, BTN_EDGE, self.name_rect, width=1, border_radius=5)
            caret = self.name + "_"
            label = font.render(caret + PUZZLE_EXT, True, THIN if self.suggested else TEXT)
            surf.blit(label, (self.name_rect.x + 8, self.name_rect.y + 6))

        pygame.draw.rect(surf, (255, 255, 255), self.list_rect, border_radius=5)
        pygame.draw.rect(surf, BTN_EDGE, self.list_rect, width=1, border_radius=5)
        if not self.files:
            surf.blit(
                small.render("no saved puzzles yet", True, THIN),
                (self.list_rect.x + 8, self.list_rect.y + 8),
            )
        for path, rect in self.rows():
            inner = rect.inflate(-4, -2)
            if path == self.selected:
                pygame.draw.rect(surf, SEL_BG, inner, border_radius=4)
            elif rect.collidepoint(mouse):
                pygame.draw.rect(surf, BTN_HOVER, inner, border_radius=4)
            surf.blit(small.render(path.name, True, TEXT), (inner.x + 6, inner.y + 4))
        if len(self.files) > self.visible:
            more = "%d-%d of %d  (mouse wheel)" % (
                self.scroll + 1,
                min(self.scroll + self.visible, len(self.files)),
                len(self.files),
            )
            surf.blit(small.render(more, True, THIN), (self.list_rect.x, self.list_rect.bottom + 4))

        for rect, label in ((self.ok_rect, self.kind), (self.cancel_rect, "cancel")):
            color = BTN_HOVER if rect.collidepoint(mouse) else BTN
            pygame.draw.rect(surf, color, rect, border_radius=6)
            pygame.draw.rect(surf, BTN_EDGE, rect, width=1, border_radius=6)
            glyph = font.render(label, True, TEXT)
            surf.blit(glyph, glyph.get_rect(center=rect.center))


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Sudoku Solver")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont(None, 46)
        self.font = pygame.font.SysFont(None, 26)
        self.font_small = pygame.font.SysFont(None, 20)
        self.rng = random.Random()

        self.grid = logic.empty_grid()
        self.problem = None  # the puzzle as it was before any solving
        self.givens = set()
        self.placed = set()
        self.reverted = set()  # emptied by <reset>, drawn grey until the next move
        self.mode = "idle"
        self.pad = None
        self.dialog = None
        self.selected = None
        self.step = None
        self.reason = ()
        self.auto = False
        self.auto_at = 0
        self.message = "Edit a problem or generate a random one."
        self.buttons = []
        self.running = True
        self.rebuild_buttons()

    # ---------------------------------------------------------------- layout
    def rebuild_buttons(self):
        auto_label = "stop auto" if self.auto else "auto search"
        defs = {
            "idle": [
                ("edit", self.start_edit),
                ("generate random", self.generate),
                ("solve", self.start_solve),
                ("load", self.open_load),
                ("save", self.open_save),
                ("clear board", self.clear_board),
                ("quit", self.quit),
            ],
            "edit": [
                ("done", self.finish_edit),
                ("clear board", self.clear_board),
                ("load", self.open_load),
                ("quit", self.quit),
            ],
            "solving": [
                ("next search", self.next_search),
                (auto_label, self.toggle_auto),
                ("reset", self.reset),
                ("save", self.open_save),
                ("quit", self.quit),
            ],
            "stuck": [
                ("user solve", self.start_user_solve),
                ("reset", self.reset),
                ("save", self.open_save),
                ("quit", self.quit),
            ],
            "usersolve": [
                ("done", self.finish_user_solve),
                ("reset", self.reset),
                ("quit", self.quit),
            ],
            "finish": [
                ("reset", self.reset),
                ("save", self.open_save),
                ("clear board", self.clear_board),
                ("quit", self.quit),
            ],
        }[self.mode]
        self.buttons = []
        y = MARGIN_Y
        for label, action in defs:
            self.buttons.append(Button((PANEL_X, y, 200, 44), label, action))
            y += 48

    def set_mode(self, mode):
        self.mode = mode
        self.pad = None
        if mode != "solving":
            self.auto = False
        self.rebuild_buttons()

    # ---------------------------------------------------------------- actions
    def quit(self):
        self.running = False

    def clear_board(self):
        self.grid = logic.empty_grid()
        self.problem = None
        self.givens = set()
        self.placed = set()
        self.reverted = set()
        self.step = None
        self.reason = ()
        self.selected = None
        self.message = "Board cleared."
        if self.mode not in ("edit", "usersolve"):
            self.set_mode("idle")
        else:
            self.pad = None

    def start_edit(self):
        self.step = None
        self.reason = ()
        self.placed = set()
        self.reverted = set()
        self.message = "Click a cell, pick a digit, then press <done>."
        self.set_mode("edit")

    def finish_edit(self):
        bad = logic.conflicts(self.grid)
        if bad:
            self.message = "Problem has conflicting digits -- fix them first."
            return
        self.set_problem()
        self.selected = None
        self.message = "Problem set (%d clues). Press <solve>." % len(self.givens)
        self.set_mode("idle")

    def set_problem(self):
        """Remember the board as the problem to come back to on <reset>."""
        self.problem = list(self.grid)
        self.givens = {i for i in range(logic.CELLS) if self.grid[i]}
        self.placed = set()
        self.reverted = set()

    def generate(self):
        self.message = "Generating..."
        self.draw()
        pygame.display.flip()
        self.grid = logic.generate(self.rng)
        self.set_problem()
        self.step = None
        self.reason = ()
        self.selected = None
        self.message = "Random problem with %d clues. Press <solve>." % len(self.givens)
        self.set_mode("idle")

    def start_solve(self):
        if not any(self.grid):
            self.message = "Board is empty -- edit or generate a problem first."
            return
        if logic.conflicts(self.grid):
            self.message = "Problem has conflicting digits -- fix them first."
            return
        if self.problem is None:
            self.set_problem()  # solving a board that was never declared a problem
        self.reverted = set()
        self.step = None
        self.set_mode("solving")
        self.next_search()

    def next_search(self):
        if all(self.grid):
            self.step = None
            self.reason = ()
            self.message = "Finish! The puzzle is solved."
            self.set_mode("finish")
            return
        step, visited = logic.search_step(self.grid, rng=self.rng)
        if step is None:
            self.step = None
            self.reason = ()
            self.selected = None
            self.message = "Cannot be solved by search (%d cells tried)." % len(visited)
            self.set_mode("stuck")
            return
        self.grid[step.index] = step.value
        self.placed.add(step.index)
        self.step = step
        self.reason = tuple(step.reason)
        self.selected = step.index
        self.auto_at = pygame.time.get_ticks() + AUTO_DELAY
        r, c = logic.rc(step.index)
        self.message = "R%dC%d = %d  (%s, %d cells tried)" % (
            r + 1, c + 1, step.value, step.kind, len(visited),
        )
        self.rebuild_buttons()

    def toggle_auto(self):
        self.auto = not self.auto and self.mode == "solving"
        if self.auto:
            # a cell already on screen keeps its three seconds
            self.auto_at = pygame.time.get_ticks() + (AUTO_DELAY if self.step else 0)
        self.rebuild_buttons()

    def tick_auto(self):
        """Called every frame: run the next search once the pause is over."""
        if not self.auto or self.mode != "solving" or self.dialog is not None:
            return
        if pygame.time.get_ticks() >= self.auto_at:
            self.next_search()

    def start_user_solve(self):
        self.step = None
        self.reason = ()
        self.message = "Your turn: fill cells by hand, then press <done>."
        self.set_mode("usersolve")

    def finish_user_solve(self):
        if logic.is_complete(self.grid):
            self.message = "Finish! The puzzle is solved."
            self.set_mode("finish")
        elif logic.conflicts(self.grid):
            self.message = "There are conflicting digits."
        else:
            self.message = "Still incomplete -- back to the solver."
            self.set_mode("solving")
            self.next_search()

    def reset(self):
        """Put the original problem back on the board."""
        self.step = None
        self.reason = ()
        self.selected = None
        self.auto = False
        if self.problem is None:
            # nothing was ever recorded as the problem: leave the board alone
            self.reverted = {i for i in range(logic.CELLS) if self.grid[i]}
            self.message = "No original problem stored -- board kept as it is."
            self.set_mode("idle")
            return
        # cells the solver or the user filled in go back to empty; they stay
        # grey so it is clear they were not part of the problem
        self.reverted = {
            i for i in range(logic.CELLS) if self.grid[i] and not self.problem[i]
        }
        self.grid = list(self.problem)
        self.givens = {i for i in range(logic.CELLS) if self.problem[i]}
        self.placed = set()
        self.message = "Back to the original problem (%d clues)." % len(self.givens)
        self.set_mode("idle")

    # ------------------------------------------------------------ load / save
    def puzzle_files(self):
        if not PUZZLE_DIR.is_dir():
            return []
        return sorted(PUZZLE_DIR.glob("*" + PUZZLE_EXT))

    def open_load(self):
        self.auto = False
        self.dialog = FileDialog("load", self.puzzle_files())

    def open_save(self):
        if not any(self.grid):
            self.message = "Nothing to save -- the board is empty."
            return
        self.auto = False
        files = self.puzzle_files()
        self.dialog = FileDialog("save", files, name="puzzle%d" % (len(files) + 1))

    def do_load(self, path):
        try:
            problem, grid = logic.parse(path.read_text())
        except (OSError, ValueError) as exc:
            self.message = "Could not load %s: %s" % (path.name, exc)
            return
        self.grid = grid
        self.problem = problem
        self.givens = {i for i in range(logic.CELLS) if problem[i]}
        self.placed = {i for i in range(logic.CELLS) if grid[i] and not problem[i]}
        self.reverted = set()
        self.step = None
        self.reason = ()
        self.selected = None
        clues = len(self.givens)
        if logic.conflicts(self.grid):
            self.message = "Loaded %s -- it has conflicting digits." % path.name
        else:
            self.message = "Loaded %s (%d clues)." % (path.name, clues)
        self.set_mode("idle")

    def do_save(self, name):
        name = "".join(ch for ch in name.strip() if ch not in '/\\:*?"<>|')
        if not name:
            self.message = "Give the file a name first."
            return False
        path = PUZZLE_DIR / (name + PUZZLE_EXT)
        problem = self.problem if self.problem is not None else list(self.grid)
        try:
            PUZZLE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(logic.dump(problem, self.grid))
        except OSError as exc:
            self.message = "Could not save: %s" % exc
            return False
        self.message = "Saved %s." % path.name
        return True

    def dialog_click(self, pos):
        outcome = self.dialog.hit(pos)
        if outcome is None:
            return
        if outcome[0] == "cancel":
            self.dialog = None
        elif outcome[0] == "ok":
            if self.dialog.kind == "save":
                if self.do_save(self.dialog.name):
                    self.dialog = None
            elif self.dialog.selected is not None:
                path = self.dialog.selected
                self.dialog = None
                self.do_load(path)
            else:
                self.message = "Pick a file from the list."

    # ---------------------------------------------------------------- events
    def editable(self):
        return self.mode in ("edit", "usersolve")

    def cell_at(self, pos):
        x, y = pos
        if MARGIN_X <= x < MARGIN_X + GRID and MARGIN_Y <= y < MARGIN_Y + GRID:
            return logic.idx((y - MARGIN_Y) // CELL, (x - MARGIN_X) // CELL)
        return None

    def apply_value(self, cell, value):
        if self.mode == "usersolve" and cell in self.givens:
            self.message = "That digit is part of the problem."
            return
        self.grid[cell] = value
        self.placed.discard(cell)
        if value and self.mode == "usersolve":
            self.placed.add(cell)
        if self.mode == "usersolve" and logic.is_complete(self.grid):
            self.message = "Finish! The puzzle is solved."
            self.set_mode("finish")

    def on_click(self, pos, button):
        if self.dialog is not None:
            self.dialog_click(pos)
            return
        if self.pad is not None:
            value = self.pad.hit(pos)
            if value is not None:
                self.apply_value(self.pad.cell, value)
            self.pad = None
            return
        for btn in self.buttons:
            if btn.enabled and btn.rect.collidepoint(pos):
                btn.action()
                return
        cell = self.cell_at(pos)
        if cell is not None:
            self.selected = cell
            if self.editable() and button == 1:
                self.pad = NumPad(cell, (pos[0] + 8, pos[1] + 8))

    def on_key(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.dialog is not None:
                self.dialog = None
            elif self.pad is not None:
                self.pad = None
            else:
                self.running = False
            return
        if self.dialog is not None:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.dialog_click(self.dialog.ok_rect.center)
            else:
                self.dialog.on_key(event)
            return
        target = self.pad.cell if self.pad else self.selected
        if target is None or not self.editable():
            return
        if pygame.K_1 <= event.key <= pygame.K_9:
            self.apply_value(target, event.key - pygame.K_0)
            self.pad = None
        elif event.key in (pygame.K_0, pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_SPACE):
            self.apply_value(target, 0)
            self.pad = None

    # ---------------------------------------------------------------- drawing
    def draw(self):
        self.screen.fill(BG)
        mouse = pygame.mouse.get_pos()
        title = self.font_big.render("Sudoku Solver", True, TEXT)
        self.screen.blit(title, (MARGIN_X, 24))
        mode = self.font_small.render("mode: " + self.mode, True, THIN)
        self.screen.blit(mode, (MARGIN_X + GRID - mode.get_width(), 36))
        msg = self.font.render(self.message, True, TEXT)
        self.screen.blit(msg, (MARGIN_X, 66))

        self.draw_grid(mouse)
        for btn in self.buttons:
            btn.draw(self.screen, self.font, mouse)
        y = self.buttons[-1].rect.bottom + 12
        if self.auto:
            left = max(0, self.auto_at - pygame.time.get_ticks())
            note = "auto: next search in %.1fs" % (left / 1000.0)
            self.screen.blit(self.font_small.render(note, True, PLACED), (PANEL_X, y))
            y += 24
        if self.step is not None:
            y = self.draw_wrapped(self.step.text, PANEL_X, y, 200)
            self.draw_wrapped(
                "highlighted: %d cell(s)" % len(self.reason), PANEL_X, y + 6, 200
            )
        if self.pad is not None:
            self.pad.draw(self.screen, self.font, self.font_small, mouse)
        if self.dialog is not None:
            self.dialog.draw(self.screen, self.font, self.font_small, mouse)

    def draw_grid(self, mouse):
        bad = logic.conflicts(self.grid)
        reason = set(self.reason)
        for i in range(logic.CELLS):
            r, c = logic.rc(i)
            rect = pygame.Rect(MARGIN_X + c * CELL, MARGIN_Y + r * CELL, CELL, CELL)
            if i in bad:
                fill = BAD_BG
            elif self.step is not None and i == self.step.index:
                fill = FOUND_BG
            elif i in reason:
                fill = REASON_BG
            elif i in self.reverted:
                fill = RESET_BG
            elif i == self.selected:
                fill = SEL_BG
            else:
                fill = (255, 255, 255)
            pygame.draw.rect(self.screen, fill, rect)
            value = self.grid[i]
            if value:
                if i in self.reverted:
                    color = THIN  # kept on the board but not part of the problem
                else:
                    color = PLACED if i in self.placed else GIVEN
                glyph = self.font_big.render(str(value), True, color)
                self.screen.blit(glyph, glyph.get_rect(center=rect.center))

        for n in range(logic.SIZE + 1):
            width = 3 if n % 3 == 0 else 1
            color = LINE if n % 3 == 0 else THIN
            x = MARGIN_X + n * CELL
            y = MARGIN_Y + n * CELL
            pygame.draw.line(self.screen, color, (x, MARGIN_Y), (x, MARGIN_Y + GRID), width)
            pygame.draw.line(self.screen, color, (MARGIN_X, y), (MARGIN_X + GRID, y), width)

    def draw_wrapped(self, text, x, y, width):
        """Draw wrapped text; returns the y just below the last line."""
        words = text.split()
        line = ""
        for word in words:
            probe = (line + " " + word).strip()
            if self.font_small.size(probe)[0] > width and line:
                self.screen.blit(self.font_small.render(line, True, TEXT), (x, y))
                y += 20
                line = word
            else:
                line = probe
        if line:
            self.screen.blit(self.font_small.render(line, True, TEXT), (x, y))
            y += 20
        return y

    # ------------------------------------------------------------------ loop
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.on_click(event.pos, event.button)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.dialog is not None:
                        self.dialog.scroll_by(-event.y)
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event)
            self.tick_auto()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()


def main():
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
