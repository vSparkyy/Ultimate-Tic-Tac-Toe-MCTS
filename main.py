import os
import sys
import random
import pygame
import threading
from game import UltimateTTTState, mcts

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Ultimate Tic Tac Toe")
clock = pygame.time.Clock()

base_dir = os.path.dirname(__file__)
default_font = pygame.font.Font(
    os.path.join(base_dir, "assets/montserrat_regular.ttf"), 36
)
text_font = pygame.font.Font(
    os.path.join(base_dir, "assets/montserrat_regular.ttf"), 24
)
bold_font = pygame.font.Font(
    os.path.join(base_dir, "assets/montserrat_bold.ttf"), 42
)
winner_font = pygame.font.Font(
    os.path.join(base_dir, "assets/montserrat_bold.ttf"), 72
)

colours = {
    "background": (219, 219, 219),
    "line": (50, 50, 50),
    "green": (0, 200, 0),
    "x": (50, 50, 200),
    "o": (200, 50, 50),
    "black": (28, 28, 28),
    "button": (70, 70, 70),
    "button_hover": (100, 100, 100),
    "button_text": (255, 255, 255),
    "translucent": (255, 255, 255, 150),
}

CONTROL_PANEL_WIDTH = 160
LEFT_OFFSET = CONTROL_PANEL_WIDTH + 60
TOP_OFFSET = 100
BOARD_SIZE = 540
CELL_SIZE = BOARD_SIZE // 9
INNER_LINE_WIDTH = 2
SUBBOARD_LINE_WIDTH = 5

def load_marker_images():
    x_img = pygame.image.load(os.path.join(base_dir, "assets/x.png")).convert_alpha()
    o_img = pygame.image.load(os.path.join(base_dir, "assets/o.png")).convert_alpha()
    d_img = pygame.image.load(os.path.join(base_dir, "assets/d.png")).convert_alpha()

    small_size = (CELL_SIZE - 10, CELL_SIZE - 10)
    big_size = (3 * CELL_SIZE - 20, 3 * CELL_SIZE - 20)

    small_x = pygame.transform.smoothscale(x_img, small_size)
    small_o = pygame.transform.smoothscale(o_img, small_size)
    small_d = pygame.transform.smoothscale(d_img, small_size)

    big_x = pygame.transform.smoothscale(x_img, big_size)
    big_o = pygame.transform.smoothscale(o_img, big_size)
    big_d = pygame.transform.smoothscale(d_img, big_size)

    return {
        "small": {"X": small_x, "O": small_o, "D": small_d},
        "big": {"X": big_x, "O": big_o, "D": big_d},
    }

marker_images = load_marker_images()

scene = "menu"
game_mode = None
human_player = None
game_state = None
mcts_iterations = 500

pvp_score_x = 0
pvp_score_o = 0
pvp_draws = 0

ai_info = {"thread": None, "result": None}
thinking_counter = 0


class Slider:
    def __init__(self, rect, min_value, max_value, value):
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.dragging = False

    def draw(self, surf):
        pygame.draw.line(
            surf,
            colours["black"],
            (self.rect.x, self.rect.centery),
            (self.rect.right, self.rect.centery),
            3,
        )
        knob_x = self.rect.x + int(
            (self.value - self.min_value) / (self.max_value - self.min_value) * self.rect.width
        )
        knob_radius = 10
        pygame.draw.circle(surf, colours["black"], (knob_x, self.rect.centery), knob_radius)
        value_text = text_font.render(str(self.value), True, colours["black"])
        surf.blit(
            value_text,
            (self.rect.centerx - value_text.get_width() // 2, self.rect.y - 25),
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.update_value(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def update(self, mouse_pos=None):
        if self.dragging:
            if mouse_pos is None:
                mouse_pos = pygame.mouse.get_pos()
            self.update_value(mouse_pos)

    def update_value(self, pos):
        rel_x = pos[0] - self.rect.x
        rel_x = max(0, min(rel_x, self.rect.width))
        self.value = self.min_value + int(rel_x / self.rect.width * (self.max_value - self.min_value))
        global mcts_iterations
        mcts_iterations = self.value


class Button:
    def __init__(self, rect, text, font, callback):
        self.rect = pygame.Rect(rect)
        self.original_text = text
        self.font = font
        self.callback = callback
        self.bg_color = colours["button"]
        self.hover_color = colours["button_hover"]
        self.text_color = colours["button_text"]
        self.corner_radius = 10

    def draw(self, surf):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.bg_color
        pygame.draw.rect(surf, color, self.rect, border_radius=self.corner_radius)
        pygame.draw.rect(surf, colours["black"], self.rect, 2, border_radius=self.corner_radius)
        text_surf = self.font.render(self.original_text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surf.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


def preset_easy():
    global mcts_iterations
    mcts_iterations = 100
    slider.value = 100


def preset_medium():
    global mcts_iterations
    mcts_iterations = 500
    slider.value = 500


def preset_hard():
    global mcts_iterations
    mcts_iterations = 1000
    slider.value = 1000


slider = Slider((50, 250, CONTROL_PANEL_WIDTH - 40, 20), 100, 2000, mcts_iterations)
preset_easy_button = Button(
    (50, 290, CONTROL_PANEL_WIDTH - 40, 40), "Easy", text_font, preset_easy
)
preset_medium_button = Button(
    (50, 340, CONTROL_PANEL_WIDTH - 40, 40), "Medium", text_font, preset_medium
)
preset_hard_button = Button(
    (50, 390, CONTROL_PANEL_WIDTH - 40, 40), "Hard", text_font, preset_hard
)


def on_reset():
    global game_state
    game_state = UltimateTTTState()


def on_return():
    global scene, game_state, ai_info
    scene = "menu"
    game_state = None
    ai_info["thread"] = None
    ai_info["result"] = None


reset_button = Button((SCREEN_WIDTH - 230, 20, 100, 60), "Reset", text_font, on_reset)
return_button = Button((SCREEN_WIDTH - 120, 20, 100, 60), "Menu", text_font, on_return)


def menu_2p():
    global game_mode, scene
    game_mode = "2p"
    scene = "game"


def menu_1p():
    global game_mode, scene
    game_mode = "1p"
    scene = "player_select"


def menu_cpu():
    global game_mode, scene
    game_mode = "cpu"
    scene = "game"


menu_buttons = [
    Button((250, 220, 300, 80), "2 Player", default_font, menu_2p),
    Button((250, 320, 300, 80), "1 Player", default_font, menu_1p),
    Button((250, 420, 300, 80), "CPU vs CPU", default_font, menu_cpu),
]


def select_x():
    global human_player, scene
    human_player = "X"
    scene = "game"


def select_o():
    global human_player, scene
    human_player = "O"
    scene = "game"


player_select_buttons = [
    Button((250, 300, 300, 80), "Play as X", default_font, select_x),
    Button((250, 420, 300, 80), "Play as O", default_font, select_o),
]


class FallingMarker:
    def __init__(self):
        self.marker = random.choice(["X", "O"])
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(-SCREEN_HEIGHT, 0)
        self.speed = random.uniform(1, 3)
        self.img = pygame.transform.smoothscale(
            marker_images["small"][self.marker], (30, 30)
        )
        self.alpha = random.randint(50, 150)

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.y = random.randint(-SCREEN_HEIGHT, 0)
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surf):
        temp_img = self.img.copy()
        temp_img.set_alpha(self.alpha)
        surf.blit(temp_img, (self.x, self.y))


falling_markers = [FallingMarker() for _ in range(30)]


def draw_text_with_outline(surf, text, font, pos, color, outline_color, outline_width=2):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            outline_surf = font.render(text, True, outline_color)
            surf.blit(outline_surf, (x + dx, y + dy))
    text_surf = font.render(text, True, color)
    surf.blit(text_surf, pos)


def draw_controls():
    if game_mode == "2p":
        global pvp_score_x, pvp_score_o, pvp_draws
        y_offset = 100
        title = text_font.render("Scoreboard", True, colours["black"])
        screen.blit(title, (20, y_offset))
        y_offset += 40

        o_img = marker_images["small"]["O"]
        o_text = text_font.render(str(pvp_score_o), True, colours["black"])
        screen.blit(o_img, (20, y_offset))
        screen.blit(
            o_text,
            (
                20 + o_img.get_width() + 10,
                y_offset + (o_img.get_height() - o_text.get_height()) // 2,
            ),
        )
        y_offset += max(o_img.get_height(), o_text.get_height()) + 20

        x_img = marker_images["small"]["X"]
        x_text = text_font.render(str(pvp_score_x), True, colours["black"])
        screen.blit(x_img, (20, y_offset))
        screen.blit(
            x_text,
            (
                20 + x_img.get_width() + 10,
                y_offset + (x_img.get_height() - x_text.get_height()) // 2,
            ),
        )
        y_offset += max(x_img.get_height(), x_text.get_height()) + 20

        d_img = marker_images["small"]["D"]
        d_text = text_font.render(str(pvp_draws), True, colours["black"])
        screen.blit(d_img, (20, y_offset))
        screen.blit(
            d_text,
            (
                20 + d_img.get_width() + 10,
                y_offset + (d_img.get_height() - d_text.get_height()) // 2,
            ),
        )
    else:
        label = text_font.render("MCTS Iterations", True, colours["black"])
        screen.blit(label, (slider.rect.x - 35, slider.rect.y - 50))
        slider.draw(screen)
        preset_easy_button.draw(screen)
        preset_medium_button.draw(screen)
        preset_hard_button.draw(screen)


def draw_turn_indicator():
    base_text = "It's the turn of:"
    base_surf = text_font.render(base_text, True, colours["black"])
    screen.blit(base_surf, (LEFT_OFFSET, TOP_OFFSET - 40))
    curr_img = marker_images["small"][game_state.current_player]
    screen.blit(curr_img, (LEFT_OFFSET + base_surf.get_width() + 10, TOP_OFFSET - 50))

    if (game_mode in ("1p", "cpu")
            and ai_info["thread"] is not None
            and ai_info["thread"].is_alive()):
        dots = (thinking_counter // 20) % 4
        think_text = "Thinking" + "." * dots
        think_surf = text_font.render(think_text, True, colours["black"])
        screen.blit(think_surf, (LEFT_OFFSET, TOP_OFFSET - 70))


def draw_small_marks():
    for row in range(9):
        for col in range(9):
            b_index = 3 * (row // 3) + (col // 3)
            c_index = 3 * (row % 3) + (col % 3)
            mark = game_state.boards[b_index][c_index]
            if mark != " ":
                img = marker_images["small"][mark]
                x_pos = LEFT_OFFSET + col * CELL_SIZE + (CELL_SIZE - img.get_width()) // 2
                y_pos = TOP_OFFSET + row * CELL_SIZE + (CELL_SIZE - img.get_height()) // 2
                screen.blit(img, (x_pos, y_pos))


def draw_captured_overlays():
    for board_index in range(9):
        if game_state.board_winners[board_index] is not None:
            sub_row = board_index // 3
            sub_col = board_index % 3
            x0 = LEFT_OFFSET + sub_col * 3 * CELL_SIZE
            y0 = TOP_OFFSET + sub_row * 3 * CELL_SIZE
            overlay = pygame.Surface((3 * CELL_SIZE, 3 * CELL_SIZE), pygame.SRCALPHA)
            overlay.fill(colours["translucent"])
            screen.blit(overlay, (x0, y0))


def draw_ultimate_grid():
    for i in range(1, 9):
        y = TOP_OFFSET + i * CELL_SIZE
        if i % 3 == 0:
            pygame.draw.line(
                screen,
                colours["line"],
                (LEFT_OFFSET, y),
                (LEFT_OFFSET + BOARD_SIZE, y),
                SUBBOARD_LINE_WIDTH,
            )
        else:
            for j in range(3):
                seg_start_x = LEFT_OFFSET + j * 3 * CELL_SIZE + 6
                seg_end_x = LEFT_OFFSET + j * 3 * CELL_SIZE + 3 * CELL_SIZE - 6
                pygame.draw.line(
                    screen,
                    colours["line"],
                    (seg_start_x, y),
                    (seg_end_x, y),
                    INNER_LINE_WIDTH,
                )
    for i in range(1, 9):
        x = LEFT_OFFSET + i * CELL_SIZE
        if i % 3 == 0:
            pygame.draw.line(
                screen,
                colours["line"],
                (x, TOP_OFFSET),
                (x, TOP_OFFSET + BOARD_SIZE),
                SUBBOARD_LINE_WIDTH,
            )
        else:
            for j in range(3):
                seg_start_y = TOP_OFFSET + j * 3 * CELL_SIZE + 6
                seg_end_y = TOP_OFFSET + j * 3 * CELL_SIZE + 3 * CELL_SIZE - 6
                pygame.draw.line(
                    screen,
                    colours["line"],
                    (x, seg_start_y),
                    (x, seg_end_y),
                    INNER_LINE_WIDTH,
                )


def draw_big_marks():
    for board_index in range(9):
        if game_state.board_winners[board_index] is not None:
            sub_row = board_index // 3
            sub_col = board_index % 3
            x0 = LEFT_OFFSET + sub_col * 3 * CELL_SIZE
            y0 = TOP_OFFSET + sub_row * 3 * CELL_SIZE
            winner = game_state.board_winners[board_index]
            img = marker_images["big"][winner]
            img_rect = img.get_rect(
                center=(x0 + (3 * CELL_SIZE) // 2, y0 + (3 * CELL_SIZE) // 2)
            )
            screen.blit(img, img_rect)


def draw_legal_border():
    if game_state.next_board is not None:
        sub_row = game_state.next_board // 3
        sub_col = game_state.next_board % 3
        x0 = LEFT_OFFSET + sub_col * 3 * CELL_SIZE
        y0 = TOP_OFFSET + sub_row * 3 * CELL_SIZE
        color = colours["x"] if game_state.current_player == "X" else colours["o"]
        pygame.draw.rect(screen, color, (x0, y0, 3 * CELL_SIZE, 3 * CELL_SIZE), 3)
    else:
        pygame.draw.rect(
            screen,
            colours["green"],
            (LEFT_OFFSET, TOP_OFFSET, BOARD_SIZE, BOARD_SIZE),
            3,
        )


def draw_winner_text():
    if game_state.overall_winner is not None:
        if game_state.overall_winner == "D":
            win_text = "Draw!"
            color = colours["black"]
            surf = winner_font.render(win_text, True, color)
            pos = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            draw_text_with_outline(
                screen, win_text, winner_font, (pos.x, pos.y), color, colours["black"]
            )
        else:
            win_color = colours["x"] if game_state.overall_winner == "X" else colours["o"]
            text1 = "Player"
            text2 = "wins!"
            text1_surf = winner_font.render(text1, True, win_color)
            text2_surf = winner_font.render(text2, True, win_color)
            marker_img = marker_images["big"][game_state.overall_winner]
            spacing = 20
            total_width = (
                text1_surf.get_width()
                + spacing
                + marker_img.get_width()
                + spacing
                + text2_surf.get_width()
            )
            scale = min(1, (SCREEN_WIDTH - 40) / total_width)
            if scale < 1:
                new_w1 = int(text1_surf.get_width() * scale)
                new_h1 = int(text1_surf.get_height() * scale)
                text1_surf = pygame.transform.smoothscale(text1_surf, (new_w1, new_h1))
                new_w2 = int(text2_surf.get_width() * scale)
                new_h2 = int(text2_surf.get_height() * scale)
                text2_surf = pygame.transform.smoothscale(text2_surf, (new_w2, new_h2))
                marker_img = pygame.transform.smoothscale(
                    marker_img,
                    (
                        int(marker_img.get_width() * scale),
                        int(marker_img.get_height() * scale),
                    ),
                )
                total_width = (
                    text1_surf.get_width()
                    + spacing
                    + marker_img.get_width()
                    + spacing
                    + text2_surf.get_width()
                )
            start_x = (SCREEN_WIDTH - total_width) // 2
            y_center = SCREEN_HEIGHT // 2
            draw_text_with_outline(
                screen,
                text1,
                winner_font,
                (start_x, y_center - text1_surf.get_height() // 2),
                win_color,
                colours["black"],
            )
            x_marker = start_x + text1_surf.get_width() + spacing
            marker_rect = marker_img.get_rect(
                center=(x_marker + marker_img.get_width() // 2, y_center)
            )
            screen.blit(marker_img, marker_rect)
            x_text2 = x_marker + marker_img.get_width() + spacing
            draw_text_with_outline(
                screen,
                text2,
                winner_font,
                (x_text2, y_center - text2_surf.get_height() // 2),
                win_color,
                colours["black"],
            )


def draw_game_scene():
    screen.fill(colours["background"])
    draw_controls()
    draw_turn_indicator()
    draw_small_marks()
    draw_captured_overlays()
    draw_ultimate_grid()
    draw_big_marks()
    draw_legal_border()

    if game_state.overall_winner is not None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        screen.blit(overlay, (0, 0))
        draw_winner_text()

    reset_button.draw(screen)
    return_button.draw(screen)


def run_mcts_in_thread(state, iterations, ai_info_dict):
    ai_info_dict["result"] = mcts(state, iterations=iterations)


falling_markers = [FallingMarker() for _ in range(30)]

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if scene == "menu":
            for button in menu_buttons:
                button.handle_event(event)

        elif scene == "player_select":
            for button in player_select_buttons:
                button.handle_event(event)

        elif scene == "game":
            if game_state is not None and game_state.overall_winner is None:
                is_human_turn = False
                if game_mode == "2p":
                    is_human_turn = True

                elif game_mode == "1p":
                    is_human_turn = game_state.current_player == human_player

                if (
                    is_human_turn
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):
                    mx, my = event.pos
                    if LEFT_OFFSET <= mx < LEFT_OFFSET + BOARD_SIZE and TOP_OFFSET <= my < TOP_OFFSET + BOARD_SIZE:
                        col = (mx - LEFT_OFFSET) // CELL_SIZE
                        row = (my - TOP_OFFSET) // CELL_SIZE
                        b_index = 3 * (row // 3) + (col // 3)
                        c_index = 3 * (row % 3) + (col % 3)
                        if not(game_state.next_board is not None and b_index != game_state.next_board):
                            if game_state.boards[b_index][c_index] == " ":
                                game_state.make_move((b_index, c_index))

            reset_button.handle_event(event)
            return_button.handle_event(event)

            if game_mode in ("1p", "cpu") and (game_state is None or game_state.overall_winner is None):
                slider.handle_event(event)
                preset_easy_button.handle_event(event)
                preset_medium_button.handle_event(event)
                preset_hard_button.handle_event(event)

    if scene == "game" and game_mode in ("1p", "cpu") and (game_state is None or game_state.overall_winner is None):
        slider.update()

    if scene == "menu":
        screen.fill(colours["background"])

        for fm in falling_markers:
            fm.update()
            fm.draw(screen)

        title = bold_font.render("Ultimate Tic Tac Toe", True, colours["black"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        for button in menu_buttons:
            button.draw(screen)

    elif scene == "player_select":
        screen.fill(colours["background"])
        prompt = bold_font.render("Select Your Marker", True, colours["black"])
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, 150))
        screen.blit(prompt, prompt_rect)

        for button in player_select_buttons:
            button.draw(screen)

    elif scene == "game":
        if game_state is None:
            game_state = UltimateTTTState()

        if game_state.overall_winner is None:
            need_ai_move = False

            if game_mode == "cpu":
                need_ai_move = True

            elif game_mode == "1p" and game_state.current_player != human_player:
                need_ai_move = True

            if need_ai_move:
                if ai_info["thread"] is None:
                    ai_info["result"] = None
                    ai_info["thread"] = threading.Thread(
                        target=run_mcts_in_thread,
                        args=(game_state, mcts_iterations, ai_info),
                    )
                    ai_info["thread"].start()

                elif not ai_info["thread"].is_alive():
                    if ai_info["result"] is not None:
                        game_state.make_move(ai_info["result"])
                        ai_info["result"] = None
                    ai_info["thread"] = None
        thinking_counter += 1
        draw_game_scene()

    pygame.display.flip()
    clock.tick(60)
