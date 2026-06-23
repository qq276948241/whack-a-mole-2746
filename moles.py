import random
import math
import pygame


MOLE_BROWN = (160, 110, 60)
MOLE_DARK = (120, 80, 40)
GOLD = (255, 200, 40)
GOLD_DARK = (200, 150, 20)
HARDHAT_YELLOW = (255, 230, 50)
HARDHAT_DARK = (200, 180, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
YELLOW = (255, 215, 0)
ORANGE = (255, 140, 0)
CYAN = (0, 220, 255)


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

    def draw(self, screen, font):
        if self.life <= 0:
            return
        alpha_ratio = self.life / self.max_life
        r, g, b = self.color
        faded = (max(0, int(r * alpha_ratio)), max(0, int(g * alpha_ratio)), max(0, int(b * alpha_ratio)))
        surf = font.render(self.text, True, faded)
        screen.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))


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

    def body_color(self):
        if self.mole_type == self.GOLDEN:
            return GOLD
        return MOLE_BROWN

    def outline_color(self):
        if self.mole_type == self.GOLDEN:
            return GOLD_DARK
        return MOLE_DARK

    def base_score(self):
        if self.mole_type == self.GOLDEN:
            return 50
        if self.mole_type == self.HARDHAT:
            return 20
        return 10

    def draw(self, screen, center_x, ground_y):
        h = self.current_height
        if h <= 0:
            return
        mole_top = ground_y - h
        body_c = self.body_color()
        outline_c = self.outline_color()

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
            return False, False, False
        mole_top = ground_y - self.current_height
        dx = pos_x - center_x
        dy = pos_y - (mole_top + 30)
        if (dx * dx + dy * dy) <= 45 * 45:
            self.hits_remaining -= 1
            hardhat_dink = False
            if self.hits_remaining <= 0:
                self.hit = True
                fully_killed = True
            else:
                if self.mole_type == self.HARDHAT:
                    self.hat_cracked = True
                    hardhat_dink = True
                fully_killed = False
            return True, fully_killed, hardhat_dink
        return False, False, False


class Hole:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 140
        self.height = 80
        self.mole = None

    def draw(self, screen):
        BROWN_CLR = (139, 69, 19)
        DARK_BROWN_CLR = (80, 40, 10)
        pygame.draw.ellipse(screen, DARK_BROWN_CLR, (self.x, self.y + 30, self.width, self.height))
        pygame.draw.ellipse(screen, BROWN_CLR, (self.x + 5, self.y + 35, self.width - 10, self.height - 10))
        if self.mole:
            self.mole.draw(screen, self.x + self.width // 2, self.y + 30)


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


def random_mole_type():
    roll = random.random()
    if roll < 0.10:
        return Mole.GOLDEN
    if roll < 0.25:
        return Mole.HARDHAT
    return Mole.NORMAL


class ScoreManager:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.floating_texts = []

    def reset(self):
        self.score = 0
        self.combo = 0
        self.floating_texts.clear()

    def register_hit(self, mole, center_x, ground_y):
        if not mole.hit:
            return None, 0
        self.combo += 1
        base = mole.base_score()
        earned = base * self.combo
        self.score += earned

        if mole.mole_type == Mole.GOLDEN:
            ft_color = GOLD
        elif self.combo >= 5:
            ft_color = ORANGE
        elif self.combo >= 3:
            ft_color = YELLOW
        else:
            ft_color = WHITE

        label = f"+{earned}"
        self.floating_texts.append(FloatingText(center_x, ground_y - 80, label, ft_color))

        sound_key = "golden" if mole.mole_type == Mole.GOLDEN else (
            "hardhat_break" if mole.mole_type == Mole.HARDHAT else None
        )
        return sound_key, earned

    def register_hardhat_dink(self, center_x, ground_y):
        self.floating_texts.append(FloatingText(center_x, ground_y - 80, "叮!", CYAN))
        return "hardhat_dink"

    def break_combo(self, x=None, y=None, reason="miss"):
        if self.combo >= 2:
            fx = x if x is not None else 400
            fy = y if y is not None else 300
            self.floating_texts.append(FloatingText(fx, fy, "连击断了!", RED))
        self.combo = 0
        if reason == "miss":
            return "miss"
        return None

    def update_and_draw_texts(self, screen, font):
        self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
        for ft in self.floating_texts:
            ft.draw(screen, font)

    def draw_hud(self, screen, font_medium, font_combo, font_tiny, screen_width):
        score_surf = font_medium.render(f"分数: {self.score}", True, WHITE)
        screen.blit(score_surf, (20, 15))

        if self.combo >= 2:
            if self.combo >= 10:
                combo_color = YELLOW
                combo_font = font_combo
                combo_label = f"超级连击 x{self.combo}!!"
            elif self.combo >= 5:
                combo_color = ORANGE
                combo_font = font_medium
                combo_label = f"连击 x{self.combo}!"
            else:
                combo_color = ORANGE
                combo_font = font_medium
                combo_label = f"连击 x{self.combo}"
            combo_surf = combo_font.render(combo_label, True, combo_color)
            screen.blit(combo_surf, (screen_width - combo_surf.get_width() - 20, 15))
            multiplier_surf = font_tiny.render(f"分数x{self.combo}", True, combo_color)
            screen.blit(multiplier_surf, (screen_width - multiplier_surf.get_width() - 20, 60))
