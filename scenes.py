import math
import array
import os
import json
import time
import sys
import pygame
from moles import Mole, MOLE_BROWN, MOLE_DARK, GOLD, HARDHAT_YELLOW, HARDHAT_DARK, WHITE, BLACK, RED, YELLOW, ORANGE


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GAME_DURATION = 60
SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

GREEN = (34, 139, 34)
DARK_GREEN = (20, 80, 20)
GRAY = (180, 180, 180)
LIGHT_GREEN = (80, 180, 80)


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


def init_sounds():
    return {
        "golden": make_golden_sound(),
        "hardhat_dink": make_sound(300, 60, 0.15),
        "hardhat_break": make_sound(200, 180, 0.15),
        "miss": make_sound(150, 150, 0.1),
    }


def make_fonts():
    return {
        "big": pygame.font.Font(None, 72),
        "medium": pygame.font.Font(None, 48),
        "small": pygame.font.Font(None, 32),
        "tiny": pygame.font.Font(None, 24),
        "combo": pygame.font.Font(None, 56),
    }


def draw_grass_background(screen):
    screen.fill(GREEN)
    for y in range(0, SCREEN_HEIGHT, 40):
        for x in range(0, SCREEN_WIDTH, 60):
            offset = (y // 40) % 2 * 30
            pygame.draw.ellipse(screen, DARK_GREEN, (x + offset, y, 50, 15), 2)


def draw_button(screen, rect, text, font, color=MOLE_BROWN, hover_color=LIGHT_GREEN, mouse_pos=None):
    is_hover = mouse_pos and rect.collidepoint(mouse_pos)
    current_color = hover_color if is_hover else color
    pygame.draw.rect(screen, current_color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    text_surf = font.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    return is_hover


def draw_mole_preview(screen, cx, cy, mole_type, scale=1.0):
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


def _check_quit(event):
    if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()


def start_screen(screen, clock, fonts):
    start_button = pygame.Rect(SCREEN_WIDTH // 2 - 120, 490, 240, 65)
    while True:
        draw_grass_background(screen)
        mouse_pos = pygame.mouse.get_pos()

        title_surf = fonts["big"].render("打 地 鼠", True, WHITE)
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
            draw_mole_preview(screen, 180, ly, mtype, scale=0.9)
            label_surf = fonts["small"].render(label, True, color)
            screen.blit(label_surf, (260, ly - label_surf.get_height() // 2))

        combo_surf = fonts["small"].render("连续打中分数翻倍!  连击断了就重来!", True, ORANGE)
        combo_rect = combo_surf.get_rect(center=(SCREEN_WIDTH // 2, 365))
        screen.blit(combo_surf, combo_rect)

        tip_surf = fonts["tiny"].render("点击冒出的地鼠得分，60秒内尽可能多得分！", True, GRAY)
        tip_rect = tip_surf.get_rect(center=(SCREEN_WIDTH // 2, 440))
        screen.blit(tip_surf, tip_rect)

        draw_button(screen, start_button, "开 始 游 戏", fonts["medium"], MOLE_BROWN, LIGHT_GREEN, mouse_pos)

        for event in pygame.event.get():
            _check_quit(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_button.collidepoint(event.pos):
                    return

        pygame.display.flip()
        clock.tick(FPS)


def end_screen(screen, clock, fonts, score):
    scores = save_high_score(score)
    restart_button = pygame.Rect(SCREEN_WIDTH // 2 - 260, 510, 220, 60)
    quit_button = pygame.Rect(SCREEN_WIDTH // 2 + 40, 510, 220, 60)

    while True:
        draw_grass_background(screen)
        mouse_pos = pygame.mouse.get_pos()

        panel = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
        pygame.draw.rect(screen, DARK_GREEN, panel, border_radius=20)
        pygame.draw.rect(screen, WHITE, panel, 4, border_radius=20)

        title_surf = fonts["big"].render("游戏结束", True, YELLOW)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title_surf, title_rect)

        score_surf = fonts["medium"].render(f"你的得分: {score}", True, WHITE)
        score_rect = score_surf.get_rect(center=(SCREEN_WIDTH // 2, 170))
        screen.blit(score_surf, score_rect)

        rank_title = fonts["medium"].render("排 行 榜 (前5名)", True, YELLOW)
        rank_rect = rank_title.get_rect(center=(SCREEN_WIDTH // 2, 230))
        screen.blit(rank_title, rank_rect)

        if not scores:
            no_surf = fonts["small"].render("暂无记录", True, GRAY)
            no_rect = no_surf.get_rect(center=(SCREEN_WIDTH // 2, 300))
            screen.blit(no_surf, no_rect)
        else:
            for i, entry in enumerate(scores):
                is_current = (entry["score"] == score and i == 0)
                color = YELLOW if is_current else WHITE
                prefix = "★ " if is_current else "   "
                rank_text = f"{prefix}第{i + 1}名: {entry['score']} 分   {entry['date']}"
                text_surf = fonts["small"].render(rank_text, True, color)
                text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, 280 + i * 40))
                screen.blit(text_surf, text_rect)

        hover_restart = draw_button(screen, restart_button, "再来一局", fonts["medium"], LIGHT_GREEN, YELLOW, mouse_pos)
        hover_quit = draw_button(screen, quit_button, "退出游戏", fonts["medium"], MOLE_BROWN, RED, mouse_pos)

        for event in pygame.event.get():
            _check_quit(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover_restart:
                    return True
                if hover_quit:
                    return False

        pygame.display.flip()
        clock.tick(FPS)
