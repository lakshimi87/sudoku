"""Pygame-ce front end for the sudoku solver."""

import random
import sys

import pygame

from . import logic

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
        self.givens = set()
        self.placed = set()
        self.mode = "idle"
        self.pad = None
        self.selected = None
        self.step = None
        self.reason = ()
        self.message = "Edit a problem or generate a random one."
        self.buttons = []
        self.running = True
        self.rebuild_buttons()

    # ---------------------------------------------------------------- layout
    def rebuild_buttons(self):
        defs = {
            "idle": [
                ("edit", self.start_edit),
                ("generate random", self.generate),
                ("solve", self.start_solve),
                ("clear board", self.clear_board),
                ("quit", self.quit),
            ],
            "edit": [
                ("done", self.finish_edit),
                ("clear board", self.clear_board),
                ("quit", self.quit),
            ],
            "solving": [
                ("next search", self.next_search),
                ("abort", self.abort),
                ("quit", self.quit),
            ],
            "stuck": [
                ("user solve", self.start_user_solve),
                ("abort", self.abort),
                ("quit", self.quit),
            ],
            "usersolve": [
                ("done", self.finish_user_solve),
                ("abort", self.abort),
                ("quit", self.quit),
            ],
            "finish": [
                ("new problem", self.abort),
                ("quit", self.quit),
            ],
        }[self.mode]
        self.buttons = []
        y = MARGIN_Y
        for label, action in defs:
            self.buttons.append(Button((PANEL_X, y, 200, 44), label, action))
            y += 54
        if self.mode == "solving" and self.step is None:
            self.buttons[0].enabled = False

    def set_mode(self, mode):
        self.mode = mode
        self.pad = None
        self.rebuild_buttons()

    # ---------------------------------------------------------------- actions
    def quit(self):
        self.running = False

    def clear_board(self):
        self.grid = logic.empty_grid()
        self.givens = set()
        self.placed = set()
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
        self.message = "Click a cell, pick a digit, then press <done>."
        self.set_mode("edit")

    def finish_edit(self):
        self.givens = {i for i in range(logic.CELLS) if self.grid[i]}
        bad = logic.conflicts(self.grid)
        if bad:
            self.message = "Problem has conflicting digits -- fix them first."
            return
        self.selected = None
        self.message = "Problem set (%d clues). Press <solve>." % len(self.givens)
        self.set_mode("idle")

    def generate(self):
        self.message = "Generating..."
        self.draw()
        pygame.display.flip()
        self.grid = logic.generate(self.rng)
        self.givens = {i for i in range(logic.CELLS) if self.grid[i]}
        self.placed = set()
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
        self.givens = {i for i in range(logic.CELLS) if self.grid[i]}
        self.placed = set()
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
        r, c = logic.rc(step.index)
        self.message = "R%dC%d = %d  (%s, %d cells tried)" % (
            r + 1, c + 1, step.value, step.kind, len(visited),
        )
        self.rebuild_buttons()

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

    def abort(self):
        self.step = None
        self.reason = ()
        self.selected = None
        for i in self.placed:
            self.grid[i] = 0
        self.placed = set()
        self.message = "Aborted. Edit or generate a problem."
        self.set_mode("idle")

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
            if self.pad is not None:
                self.pad = None
            else:
                self.running = False
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
        if self.step is not None:
            self.draw_wrapped(self.step.text, PANEL_X, MARGIN_Y + 5 * 54 + 10, 200)
        if self.pad is not None:
            self.pad.draw(self.screen, self.font, self.font_small, mouse)

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
            elif i == self.selected:
                fill = SEL_BG
            else:
                fill = (255, 255, 255)
            pygame.draw.rect(self.screen, fill, rect)
            value = self.grid[i]
            if value:
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

    # ------------------------------------------------------------------ loop
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.on_click(event.pos, event.button)
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event)
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()


def main():
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
