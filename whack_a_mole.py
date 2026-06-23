import sys
import time
import random
import pygame

from moles import Mole, create_holes, random_mole_type, ScoreManager, RED
from scenes import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_DURATION,
    init_sounds, make_combo_sound, make_fonts,
    draw_grass_background, start_screen, end_screen,
)

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()


def game_loop(screen, clock, fonts, sounds):
    holes = create_holes()
    score_mgr = ScoreManager()
    start_time = time.time()
    spawn_timer = 0
    spawn_interval = 60

    while True:
        draw_grass_background(screen)
        mouse_clicked = False
        click_x = click_y = 0

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

        score_mgr.draw_hud(screen, fonts["medium"], fonts["combo"], fonts["tiny"], SCREEN_WIDTH)

        time_color = RED if remaining <= 10 else (255, 255, 255)
        time_surf = fonts["medium"].render(f"时间: {remaining}s", True, time_color)
        screen.blit(time_surf, (20, 60))

        spawn_timer += 1
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            empty_holes = [h for h in holes if h.mole is None]
            if empty_holes:
                hole = random.choice(empty_holes)
                hole.mole = Mole(random_mole_type())
                hole.mole.speed = 2 + int(3 * progress)
                hole.mole.stay_time = max(10, 35 - int(20 * progress))

        hit_any = False
        for hole in holes:
            if hole.mole:
                center_x = hole.x + hole.width // 2
                ground_y = hole.y + 30
                if mouse_clicked:
                    hit_registered, fully_killed, dink = hole.mole.check_hit(
                        click_x, click_y, center_x, ground_y
                    )
                    if hit_registered:
                        hit_any = True
                        mouse_clicked = False
                        if fully_killed:
                            sound_key, _earned = score_mgr.register_hit(hole.mole, center_x, ground_y)
                            if sound_key:
                                sounds[sound_key].play()
                            else:
                                make_combo_sound(score_mgr.combo).play()
                        elif dink:
                            sounds[score_mgr.register_hardhat_dink(center_x, ground_y)].play()
                hole_center_x = hole.x + hole.width // 2
                if not hole.mole.update():
                    if hole.mole.escaped and not hole.mole.hit:
                        score_mgr.break_combo(
                            hole_center_x, hole.y, reason="escape"
                        )
                    hole.mole = None
            hole.draw(screen)

        if mouse_clicked and not hit_any:
            snd_key = score_mgr.break_combo(click_x, click_y - 20, reason="miss")
            if snd_key:
                sounds[snd_key].play()

        score_mgr.update_and_draw_texts(screen, fonts["small"])

        pygame.display.flip()
        clock.tick(FPS)

        if remaining <= 0:
            break

    return score_mgr.score


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("打地鼠 Whack-a-Mole")
    clock = pygame.time.Clock()
    fonts = make_fonts()
    sounds = init_sounds()

    while True:
        start_screen(screen, clock, fonts)
        final_score = game_loop(screen, clock, fonts, sounds)
        if not end_screen(screen, clock, fonts, final_score):
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
