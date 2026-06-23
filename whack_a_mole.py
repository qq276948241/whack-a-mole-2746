import pygame
import random
import sys
import os
import json
import time
import math
import array

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GAME_DURATION = 60
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
GOLD = (255, 200, 40)
GOLD_DARK = (200, 150, 20)
HARDHAT_YELLOW = (255, 230, 50)
HARDHAT_DARK = (200, 180, 30)
ORANGE = (255, 140, 0)
CYAN = (0, 220, 255)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("打地鼠 Whack-a-Mole")
clock = pygame.time.Clock()

font_big = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 32)
font_tiny = pygame.font.Font(None, 24)
font_combo = pygame.font.Font(None, 56)


def make_sound(frequency, duration_ms, volume=0.25):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array('h')
    max_val = 2 ** 15 - 1
    for i in range(n_samples):
        t = i / sample_rate
        env = 1.0
        attack = int(n_samples * 0.05)
        release = int(n_samples * 0.4)
        if i < attack:
            env = i / max(attack, 1)
        elif i > n_samples - release:
            env = (n_samples - i) / max(release, 1)
        val = int(volume * max_val * math.sin(2 * math.pi * frequency * t) * env)
        val = max(-max_val, min(max_val, val))
        buf.append(val)
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf)


def make_combo_sound(combo):
    freq = min(400 + combo * 80, 1600)
    return make_sound(freq, 80, 0.2)


def make_golden_sound():
    sample_rate = 44100
    duration_ms = 200
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array('h')
    max_val = 2 ** 15 - 1
    for i in range(n_samples):
        t = i / sample_rate
        env = 1.0
        attack = int(n_samples * 0.05)
        release = int(n_samples * 0.5)
        if i < attack:
            env = i / max(attack, 1)
        elif i > n_samples - release:
            env = (n_samples - i) / max(release, 1)
        val = int(0.2 * max_val * (
            math.sin(2 * math.pi * 1047 * t) * 0.5 +
            math.sin(2 * math.pi * 1319 * t) * 0.3 +
            math.sin(2 * math.pi * 1568 * t) * 0.2
        ) * env)
        val = max(-max_val, min(max_val, val))
        buf.append(val)
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf)


def make_hardhat_sound():
    return make_sound(300, 60, 0.15)


def make_break_sound():
    return make_sound(200, 180, 0.15)


def make_miss_sound():
    return make_sound(150, 150, 0.1)


def init_sounds():
    return {
        "hit_base": make_sound(523, 80, 0.2),
        "golden": make_golden_sound(),
        "hardhat_dink": make_hardhat_sound(),
        "hardhat_break": make_break_sound(),
        "miss": make_miss_sound(),
    }


SOUNDS = init_sounds()


def draw_grass_background():
    screen.fill(GREEN)
    for y in range(0, SCREEN_HEIGHT, 40):
        for x in range(0, SCREEN_WIDTH, 60):
            offset = (y // 40) % 2 * 30
            pygame.draw.ellipse(screen, DARK_GREEN, (x + offset, y, 50, 15), 2)


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 45
        self.max_life = 45

    def update(self):
        self.y -= 1.5
        self.life -= 1
        return self.life > 0

    def draw(self):
        if self.life <= 0:
            return
        alpha_ratio = self.life / self.max_life
        r, g, b = self.color
        faded = (max(0, int(r * alpha_ratio)), max(0, int(g * alpha_ratio)), max(0, int(b * alpha_ratio)))
        surf = font_small.render(self.text, True, faded)
        screen.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))


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


class Mole:
    NORMAL = "normal"
    GOLDEN = "golden"
    HARDHAT = "hardhat"

    def __init__(self, mole_type="normal"):
        self.mole_type = mole_type
        self.max_height = 70
        self.current_height = 0
        self.state = "rising"
        self.hit = False
        self.escaped = False
        self.speed = 3
        self.stay_counter = 0
        self.stay_time = 30
        self.hits_remaining = 2 if mole_type == self.HARDHAT else 1
        self.hat_cracked = False
        if mole_type == self.GOLDEN:
            self.stay_time = max(10, self.stay_time - 5)

    def _body_color(self):
        if self.mole_type == self.GOLDEN:
            return GOLD
        return MOLE_BROWN

    def _outline_color(self):
        if self.mole_type == self.GOLDEN:
            return GOLD_DARK
        return MOLE_DARK

    def _base_score(self):
        if self.mole_type == self.GOLDEN:
            return 50
        if self.mole_type == self.HARDHAT:
            return 20
        return 10

    def draw(self, center_x, ground_y):
        h = self.current_height
        if h <= 0:
            return
        mole_top = ground_y - h
        body_c = self._body_color()
        outline_c = self._outline_color()

        pygame.draw.circle(screen, body_c, (center_x, mole_top + 30), 38)
        pygame.draw.circle(screen, outline_c, (center_x, mole_top + 45), 30, 2)

        if self.mole_type == self.GOLDEN and not self.hit:
            sparkle_t = pygame.time.get_ticks() / 200.0
            for si in range(3):
                angle = sparkle_t + si * 2.094
                sx = center_x + int(25 * math.cos(angle))
                sy = mole_top + 10 + int(10 * math.sin(angle))
                pygame.draw.circle(screen, WHITE, (sx, sy), 3)

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

        pygame.draw.ellipse(screen, outline_c, (center_x - 8, mole_top + 38, 16, 10))
        pygame.draw.circle(screen, outline_c, (center_x - 30, mole_top + 30), 10)
        pygame.draw.circle(screen, outline_c, (center_x + 30, mole_top + 30), 10)

        if self.mole_type == self.HARDHAT:
            hat_y = mole_top - 8
            pygame.draw.ellipse(screen, HARDHAT_YELLOW, (center_x - 30, hat_y, 60, 22))
            pygame.draw.ellipse(screen, HARDHAT_DARK, (center_x - 35, hat_y + 12, 70, 12))
            pygame.draw.ellipse(screen, HARDHAT_YELLOW, (center_x - 28, hat_y + 3, 56, 14), 2)
            if self.hat_cracked:
                pygame.draw.line(screen, BLACK, (center_x - 8, hat_y + 2), (center_x + 3, hat_y + 16), 3)
                pygame.draw.line(screen, BLACK, (center_x + 2, hat_y + 1), (center_x - 5, hat_y + 15), 2)
                pygame.draw.line(screen, BLACK, (center_x + 8, hat_y + 4), (center_x + 12, hat_y + 14), 2)

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
                self.escaped = True
                return False
        return True

    def check_hit(self, pos_x, pos_y, center_x, ground_y):
        if self.hit or self.current_height < 30:
            return False
        mole_top = ground_y - self.current_height
        dx = pos_x - center_x
        dy = pos_y - (mole_top + 30)
        if (dx * dx + dy * dy) <= 45 * 45:
            self.hits_remaining -= 1
            if self.hits_remaining <= 0:
                self.hit = True
            elif self.mole_type == self.HARDHAT:
                self.hat_cracked = True
            return True
        return False


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


def draw_mole_preview(cx, cy, mole_type, scale=1.0):
    r = int(30 * scale)
    if mole_type == Mole.GOLDEN:
        pygame.draw.circle(screen, GOLD, (cx, cy), r)
        pygame.draw.circle(screen, WHITE, (cx - int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, WHITE, (cx + int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, BLACK, (cx - int(8 * scale), cy - int(3 * scale)), int(3 * scale))
        pygame.draw.circle(screen, BLACK, (cx + int(12 * scale), cy - int(3 * scale)), int(3 * scale))
        pygame.draw.circle(screen, WHITE, (cx + int(15 * scale), cy - int(15 * scale)), int(4 * scale))
    elif mole_type == Mole.HARDHAT:
        pygame.draw.circle(screen, MOLE_BROWN, (cx, cy), r)
        pygame.draw.circle(screen, WHITE, (cx - int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, WHITE, (cx + int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, BLACK, (cx - int(8 * scale), cy - int(3 * scale)), int(3 * scale))
        pygame.draw.circle(screen, BLACK, (cx + int(12 * scale), cy - int(3 * scale)), int(3 * scale))
        hat_y = cy - int(28 * scale)
        pygame.draw.ellipse(screen, HARDHAT_YELLOW, (cx - int(22 * scale), hat_y, int(44 * scale), int(16 * scale)))
        pygame.draw.ellipse(screen, HARDHAT_DARK, (cx - int(26 * scale), hat_y + int(9 * scale), int(52 * scale), int(9 * scale)))
    else:
        pygame.draw.circle(screen, MOLE_BROWN, (cx, cy), r)
        pygame.draw.circle(screen, WHITE, (cx - int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, WHITE, (cx + int(10 * scale), cy - int(5 * scale)), int(6 * scale))
        pygame.draw.circle(screen, BLACK, (cx - int(8 * scale), cy - int(3 * scale)), int(3 * scale))
        pygame.draw.circle(screen, BLACK, (cx + int(12 * scale), cy - int(3 * scale)), int(3 * scale))


def start_screen():
    start_button = pygame.Rect(SCREEN_WIDTH // 2 - 120, 490, 240, 65)
    while True:
        draw_grass_background()
        mouse_pos = pygame.mouse.get_pos()

        title_surf = font_big.render("打 地 鼠", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60))
        pygame.draw.rect(screen, DARK_GREEN, title_rect.inflate(40, 20), border_radius=15)
        screen.blit(title_surf, title_rect)

        info_y = 130
        legends = [
            (Mole.NORMAL, "普通地鼠  +10分", WHITE),
            (Mole.GOLDEN, "金色地鼠  +50分!", GOLD),
            (Mole.HARDHAT, "安全帽地鼠  敲2下  +20分", HARDHAT_YELLOW),
        ]
        for i, (mtype, label, color) in enumerate(legends):
            ly = info_y + i * 75
            draw_mole_preview(180, ly, mtype, scale=0.9)
            label_surf = font_small.render(label, True, color)
            screen.blit(label_surf, (260, ly - label_surf.get_height() // 2))

        combo_surf = font_small.render("连续打中分数翻倍!  连击断了就重来!", True, ORANGE)
        combo_rect = combo_surf.get_rect(center=(SCREEN_WIDTH // 2, 365))
        screen.blit(combo_surf, combo_rect)

        tip_surf = font_tiny.render("点击冒出的地鼠得分，60秒内尽可能多得分！", True, GRAY)
        tip_rect = tip_surf.get_rect(center=(SCREEN_WIDTH // 2, 440))
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
    combo = 0
    floating_texts = []
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

        if combo >= 2:
            if combo >= 10:
                combo_color = YELLOW
                combo_font = font_combo
                combo_label = f"超级连击 x{combo}!!"
            elif combo >= 5:
                combo_color = ORANGE
                combo_font = font_medium
                combo_label = f"连击 x{combo}!"
            else:
                combo_color = ORANGE
                combo_font = font_medium
                combo_label = f"连击 x{combo}"
            combo_surf = combo_font.render(combo_label, True, combo_color)
            screen.blit(combo_surf, (SCREEN_WIDTH - combo_surf.get_width() - 20, 15))
            multiplier_surf = font_tiny.render(f"分数x{combo}", True, combo_color)
            screen.blit(multiplier_surf, (SCREEN_WIDTH - multiplier_surf.get_width() - 20, 60))

        spawn_timer += 1
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            empty_holes = [h for h in holes if h.mole is None]
            if empty_holes:
                hole = random.choice(empty_holes)
                roll = random.random()
                if roll < 0.10:
                    mole_type = Mole.GOLDEN
                elif roll < 0.25:
                    mole_type = Mole.HARDHAT
                else:
                    mole_type = Mole.NORMAL
                hole.mole = Mole(mole_type)
                hole.mole.speed = 2 + int(3 * progress)
                hole.mole.stay_time = max(10, 35 - int(20 * progress))

        hit_any = False
        for hole in holes:
            if hole.mole:
                center_x = hole.x + hole.width // 2
                ground_y = hole.y + 30
                if mouse_clicked and hole.mole.check_hit(click_x, click_y, center_x, ground_y):
                    hit_any = True
                    mouse_clicked = False
                    if hole.mole.hit:
                        combo += 1
                        base = hole.mole._base_score()
                        earned = base * combo
                        score += earned
                        if hole.mole.mole_type == Mole.GOLDEN:
                            SOUNDS["golden"].play()
                        elif hole.mole.mole_type == Mole.HARDHAT:
                            SOUNDS["hardhat_break"].play()
                        else:
                            make_combo_sound(combo).play()
                        ft_color = GOLD if hole.mole.mole_type == Mole.GOLDEN else (
                            ORANGE if combo >= 5 else YELLOW if combo >= 3 else WHITE
                        )
                        floating_texts.append(FloatingText(center_x, ground_y - 80, f"+{earned}", ft_color))
                    else:
                        SOUNDS["hardhat_dink"].play()
                        floating_texts.append(FloatingText(center_x, ground_y - 80, "叮!", CYAN))
                if not hole.mole.update():
                    if hole.mole.escaped and not hole.mole.hit:
                        if combo >= 2:
                            floating_texts.append(FloatingText(
                                hole.x + hole.width // 2, hole.y,
                                "连击断了!", RED
                            ))
                        combo = 0
                    hole.mole = None
            hole.draw()

        if mouse_clicked and not hit_any:
            if combo >= 2:
                floating_texts.append(FloatingText(click_x, click_y - 20, "连击断了!", RED))
            combo = 0
            SOUNDS["miss"].play()

        floating_texts = [ft for ft in floating_texts if ft.update()]
        for ft in floating_texts:
            ft.draw()

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
