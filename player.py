# player.py
# 플레이어(시간여행자)의 입력(키보드 / 터치 조이스틱)과 이동을 담당하는 파일입니다.
# 이동/충돌/그리기는 character.py의 Character에서 물려받습니다.

import pygame
from settings import PLAYER_SPEED, COLOR_PLAYER
from character import Character


class Player(Character):
    def __init__(self, x, y):
        # 그림 파일: assets/characters/player.png (없으면 파란 사각형)
        super().__init__(x, y, COLOR_PLAYER, "characters/player.png")

    def handle_input(self, touch_vector=(0, 0)):
        """
        키보드 상태를 읽어서 이동 방향(dx, dy)을 돌려줍니다.
        키보드를 안 누르고 있으면 터치 조이스틱 방향(touch_vector)을 사용합니다.
        """
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1

        # 대각선 이동 시 속도가 빨라지지 않도록 보정 (1/√2 ≈ 0.7071)
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        if dx == 0 and dy == 0:
            dx, dy = touch_vector     # 조이스틱은 이미 길이가 0~1이라 보정 필요 없음
        if dx != 0 or dy != 0:
            self.facing = (dx, dy)
        return dx, dy

    def update(self, dt, obstacles, touch_vector=(0, 0), absolute_path=None):
        """매 프레임 호출: 입력 읽기 → 이동 → 애니메이션"""
        dx, dy = self.handle_input(touch_vector)
        self.moving = self.move(dx, dy, PLAYER_SPEED, dt, obstacles,
                                absolute_path)
        self.anim.update(dt, self.moving, self.facing)
