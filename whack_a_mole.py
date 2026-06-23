import pygame
import random
import sys
import os
import json
import time

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GAME_DURATION = 60
HOLE_COUNT = 9
SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
DARK_GREEN = (20, 80, 20)
BROWN = (139, 69, 19)
DARK_BROWN = (80, 40, 10)
MOLE_BROWN = (160, 110, 60)
MOLE_DARK = (120, 80, 40)
RED = (220, 50, 50)
YELLOW = (255, 215, 0)
GRAY = (180, 180, 180)
LIGHT_GREEN = (80, 180, 80)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("打地鼠 Whack-a-Mole")
clock = pygame.time.Clock()

font_big = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 32)
font_tiny = pygame.font.Font(None, 24)


def draw_grass_background():
    screen.fill(GREEN)
    for y in range(0, SCREEN_HEIGHT, 40):
        for x in range(0, SCREEN_WIDTH, 60):
            offset = (y // 40) % 2 * 30
            pygame.draw.ellipse(screen, DARK_GREEN, (x + offset, y, 50, 15), 2)


class Hole:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 140
        self.height = 80
        self.mole = None

    def draw(self):
        pygame.draw.ellipse(screen, DARK_BROWN, (self.x, self.y + 30, self.width, self.height))
        pygame.draw.ellipse(screen, BROWN, (self.x + 5, self.y + 35, self.width - 10, self.height - 10))
        if self.mole:
            self.mole.draw(self.x + self.width // 2, self.y + 30)

    def is_inside(self, pos_x, pos_y):
        hole_rect = pygame.Rect(self.x, self.y, self.width, self.height + 40)
        return hole_rect.collidepoint(pos_x, pos_y)


class Mole:
    def __init__(self):
        self.max_height = 70
        self.current_height = 0
        self.state = "rising"
        self.hit = False
        self.speed = 3
        self.stay_counter = 0
        self.stay_time = 30

    def draw(self, center_x, ground_y):
        h = self.current_height
        if h <= 0:
            return
        mole_top = ground_y - h
        pygame.draw.circle(screen, MOLE_BROWN, (center_x, mole_top + 30), 38)
        pygame.draw.circle(screen, MOLE_DARK, (center_x, mole_top + 45), 30, 2)

        if self.hit:
            pygame.draw.line(screen, BLACK, (center_x - 18, mole_top + 20), (center_x - 6, mole_top + 32), 3)
            pygame.draw.line(screen, BLACK, (center_x - 6, mole_top + 20), (center_x - 18, mole_top + 32), 3)
            pygame.draw.line(screen, BLACK, (center_x + 6, mole_top + 20), (center_x + 18, mole_top + 32), 3)
            pygame.draw.line(screen, BLACK, (center_x + 18, mole_top + 20), (center_x + 6, mole_top + 32), 3)
        else:
            pygame.draw.circle(screen, WHITE, (center_x - 12, mole_top + 25), 8)
            pygame.draw.circle(screen, WHITE, (center_x + 12, mole_top + 25), 8)
            pygame.draw.circle(screen, BLACK, (center_x - 10, mole_top + 27), 4)
            pygame.draw.circle(screen, BLACK, (center_x + 14, mole_top + 27), 4)

        pygame.draw.ellipse(screen, MOLE_DARK, (center_x - 8, mole_top + 38, 16, 10))
        pygame.draw.circle(screen, MOLE_DARK, (center_x - 30, mole_top + 30), 10)
        pygame.draw.circle(screen, MOLE_DARK, (center_x + 30, mole_top + 30), 10)

    def update(self):
        if self.hit:
            self.current_height -= self.speed * 2
            if self.current_height <= 0:
                self.current_height = 0
                return False
            return True

        if self.state == "rising":
            self.current_height += self.speed
            if self.current_height >= self.max_height:
                self.current_height = self.max_height
                self.state = "staying"
        elif self.state == "staying":
            self.stay_counter += 1
            if self.stay_counter >= self.stay_time:
                self.state = "falling"
        elif self.state == "falling":
            self.current_height -= self.speed
            if self.current_height <= 0:
                self.current_height = 0
                return False
        return True

    def check_hit(self, pos_x, pos_y, center_x, ground_y):
        if self.hit or self.current_height < 30:
            return False
        mole_top = ground_y - self.current_height
        dx = pos_x - center_x
        dy = pos_y - (mole_top + 30)
        return (dx * dx + dy * dy) <= 45 * 45


def create_holes():
    holes = []
    positions = [
        (60, 180), (330, 180), (600, 180),
        (60, 310), (330, 310), (600, 310),
        (60, 440), (330, 440), (600, 440),
    ]
    for x, y in positions:
        holes.append(Hole(x, y))
    return holes


def load_high_scores():
    if not os.path.exists(SCORE_FILE):
        return []
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_high_score(score):
    scores = load_high_scores()
    scores.append({"score": score, "date": time.strftime("%Y-%m-%d %H:%M")})
    scores.sort(key=lambda x: x["score"], reverse=True)
    scores = scores[:5]
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return scores


def draw_button(rect, text, color=MOLE_BROWN, hover_color=LIGHT_GREEN, mouse_pos=None):
    is_hover = mouse_pos and rect.collidepoint(mouse_pos)
    current_color = hover_color if is_hover else color
    pygame.draw.rect(screen, current_color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    text_surf = font_medium.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    return is_hover


def start_screen():
    start_button = pygame.Rect(SCREEN_WIDTH // 2 - 120, 400, 240, 70)
    while True:
        draw_grass_background()
        mouse_pos = pygame.mouse.get_pos()

        title_surf = font_big.render("打 地 鼠", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 120))
        pygame.draw.rect(screen, DARK_GREEN, title_rect.inflate(40, 20), border_radius=15)
        screen.blit(title_surf, title_rect)

        pygame.draw.circle(screen, MOLE_BROWN, (SCREEN_WIDTH // 2, 270), 60)
        pygame.draw.circle(screen, WHITE, (SCREEN_WIDTH // 2 - 20, 250), 14)
        pygame.draw.circle(screen, WHITE, (SCREEN_WIDTH // 2 + 20, 250), 14)
        pygame.draw.circle(screen, BLACK, (SCREEN_WIDTH // 2 - 17, 253), 7)
        pygame.draw.circle(screen, BLACK, (SCREEN_WIDTH // 2 + 23, 253), 7)
        pygame.draw.ellipse(screen, MOLE_DARK, (SCREEN_WIDTH // 2 - 14, 278, 28, 16))

        tip_surf = font_small.render("点击冒出的地鼠得分！", True, WHITE)
        tip_rect = tip_surf.get_rect(center=(SCREEN_WIDTH // 2, 360))
        screen.blit(tip_surf, tip_rect)

        draw_button(start_button, "开 始 游 戏", MOLE_BROWN, LIGHT_GREEN, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_button.collidepoint(event.pos):
                    return

        pygame.display.flip()
        clock.tick(FPS)


def game_loop():
    holes = create_holes()
    score = 0
    start_time = time.time()
    spawn_timer = 0
    spawn_interval = 60
    elapsed = 0

    while True:
        draw_grass_background()
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True
                click_x, click_y = event.pos

        elapsed = time.time() - start_time
        remaining = max(0, GAME_DURATION - int(elapsed))

        progress = min(elapsed / GAME_DURATION, 1.0)
        spawn_interval = int(60 - 35 * progress)

        score_surf = font_medium.render(f"分数: {score}", True, WHITE)
        screen.blit(score_surf, (20, 15))

        time_color = RED if remaining <= 10 else WHITE
        time_surf = font_medium.render(f"时间: {remaining}s", True, time_color)
        screen.blit(time_surf, (20, 60))

        spawn_timer += 1
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            empty_holes = [h for h in holes if h.mole is None]
            if empty_holes:
                hole = random.choice(empty_holes)
                hole.mole = Mole()
                hole.mole.speed = 2 + int(3 * progress)
                hole.mole.stay_time = max(10, 35 - int(20 * progress))

        for hole in holes:
            if hole.mole:
                center_x = hole.x + hole.width // 2
                ground_y = hole.y + 30
                if mouse_clicked and hole.mole.check_hit(click_x, click_y, center_x, ground_y):
                    hole.mole.hit = True
                    score += 10
                    mouse_clicked = False
                if not hole.mole.update():
                    hole.mole = None
            hole.draw()

        pygame.display.flip()
        clock.tick(FPS)

        if remaining <= 0:
            break

    return score


def end_screen(score):
    scores = save_high_score(score)
    restart_button = pygame.Rect(SCREEN_WIDTH // 2 - 260, 510, 220, 60)
    quit_button = pygame.Rect(SCREEN_WIDTH // 2 + 40, 510, 220, 60)

    while True:
        draw_grass_background()
        mouse_pos = pygame.mouse.get_pos()

        panel = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
        pygame.draw.rect(screen, DARK_GREEN, panel, border_radius=20)
        pygame.draw.rect(screen, WHITE, panel, 4, border_radius=20)

        title_surf = font_big.render("游戏结束", True, YELLOW)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title_surf, title_rect)

        score_surf = font_medium.render(f"你的得分: {score}", True, WHITE)
        score_rect = score_surf.get_rect(center=(SCREEN_WIDTH // 2, 170))
        screen.blit(score_surf, score_rect)

        rank_title = font_medium.render("排 行 榜 (前5名)", True, YELLOW)
        rank_rect = rank_title.get_rect(center=(SCREEN_WIDTH // 2, 230))
        screen.blit(rank_title, rank_rect)

        if not scores:
            no_surf = font_small.render("暂无记录", True, GRAY)
            no_rect = no_surf.get_rect(center=(SCREEN_WIDTH // 2, 300))
            screen.blit(no_surf, no_rect)
        else:
            for i, entry in enumerate(scores):
                is_current = (entry["score"] == score and i == 0)
                color = YELLOW if is_current else WHITE
                prefix = "★ " if is_current else "   "
                rank_text = f"{prefix}第{i + 1}名: {entry['score']} 分   {entry['date']}"
                text_surf = font_small.render(rank_text, True, color)
                text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, 280 + i * 40))
                screen.blit(text_surf, text_rect)

        hover_restart = draw_button(restart_button, "再来一局", LIGHT_GREEN, YELLOW, mouse_pos)
        hover_quit = draw_button(quit_button, "退出游戏", MOLE_BROWN, RED, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover_restart:
                    return True
                if hover_quit:
                    return False

        pygame.display.flip()
        clock.tick(FPS)


def main():
    while True:
        start_screen()
        final_score = game_loop()
        if not end_screen(final_score):
            break
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
