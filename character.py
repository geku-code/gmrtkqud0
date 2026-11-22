# character.py
# 플레이어와 NPC가 함께 쓰는 '캐릭터' 기본 클래스입니다.
# 위치, 벽 충돌 이동, 걷기 애니메이션, 그리기를 담당합니다.

import pygame
from settings import PLAYER_SIZE, WHITE
from assets import load_sheet, load_still, Animator


class Character:
    def __init__(self, x, y, color, sprite_path, still_path=None):
        """
        x, y = 캐릭터 중심 좌표, sprite_path = assets 폴더 안의 스프라이트 시트(4×4) 경로
        still_path = 시트가 없을 때 쓸 정면 그림 1장 경로 (없으면 None)
        """
        # 위치는 소수점까지 정확하게 저장 (부드러운 이동을 위해)
        self.x = float(x - PLAYER_SIZE / 2)
        self.y = float(y - PLAYER_SIZE / 2)
        # 충돌 판정용 사각형
        self.rect = pygame.Rect(int(self.x), int(self.y), PLAYER_SIZE, PLAYER_SIZE)
        self.facing = (0, 1)    # 바라보는 방향 (처음엔 아래)
        self.moving = False     # 이번 프레임에 움직였는지 (애니메이션용)
        self.color = color      # 그림이 없을 때 쓰는 색
        frames = load_sheet(sprite_path)
        if frames is None and still_path:
            frames = load_still(still_path)
        self.anim = Animator(frames)

    def move(self, dx, dy, speed, dt, obstacles, absolute_path=None):
        """
        이동 후 장애물(벽 등)과 부딪히면 위치를 되돌립니다.
        가로(x)와 세로(y)를 따로 처리해야 벽에 붙어서 미끄러지듯 이동할 수 있습니다.
        실제로 움직였으면 True를 돌려줍니다.
        """
        start = self.rect.topleft

        # 1) 가로 이동
        old_x = self.x
        old_rect_x = self.rect.x
        was_on_path = absolute_path is not None and absolute_path(self.rect)
        self.x += dx * speed * dt
        self.rect.x = round(self.x)
        on_path = absolute_path is not None and absolute_path(self.rect)
        path_exit_blocked = (was_on_path and not on_path and
                             any(self.rect.colliderect(wall)
                                 for wall in obstacles))
        if path_exit_blocked:
            # Cancel at the boundary instead of entering the building first
            # and snapping the character backwards afterwards.
            self.x = old_x
            self.rect.x = old_rect_x
        for wall in (() if on_path or path_exit_blocked else obstacles):
            if self.rect.colliderect(wall):
                if dx > 0:      # 오른쪽으로 가다 부딪힘 → 벽 왼쪽에 붙임
                    self.rect.right = wall.left
                elif dx < 0:    # 왼쪽으로 가다 부딪힘 → 벽 오른쪽에 붙임
                    self.rect.left = wall.right
                self.x = self.rect.x

        # 2) 세로 이동
        old_y = self.y
        old_rect_y = self.rect.y
        was_on_path = absolute_path is not None and absolute_path(self.rect)
        self.y += dy * speed * dt
        self.rect.y = round(self.y)
        on_path = absolute_path is not None and absolute_path(self.rect)
        path_exit_blocked = (was_on_path and not on_path and
                             any(self.rect.colliderect(wall)
                                 for wall in obstacles))
        if path_exit_blocked:
            self.y = old_y
            self.rect.y = old_rect_y
        for wall in (() if on_path or path_exit_blocked else obstacles):
            if self.rect.colliderect(wall):
                if dy > 0:      # 아래로 가다 부딪힘 → 벽 위에 붙임
                    self.rect.bottom = wall.top
                elif dy < 0:    # 위로 가다 부딪힘 → 벽 아래에 붙임
                    self.rect.top = wall.bottom
                self.y = self.rect.y

        return self.rect.topleft != start

    def face_towards(self, other_rect):
        """다른 대상을 바라보게 합니다. (대화할 때 플레이어 쪽을 보게 함)"""
        dx = other_rect.centerx - self.rect.centerx
        dy = other_rect.centery - self.rect.centery
        if abs(dx) > abs(dy):
            self.facing = (1 if dx > 0 else -1, 0)
        else:
            self.facing = (0, 1 if dy > 0 else -1)
        self.anim.update(0, False, self.facing)

    @property
    def top(self):
        """화면에 그려지는 모습의 맨 위(머리) y좌표 - 맵 기준. 안내 글자/느낌표 위치에 사용"""
        image = self.anim.image
        if image:
            return self.rect.bottom - image.get_height()
        return self.rect.top

    def draw(self, surface, camera, time_sec=0.0):
        """카메라 위치를 빼서 화면 좌표로 바꾼 뒤 그립니다. (time_sec는 오브젝트와 형식을 맞추기 위함)"""
        cam_x, cam_y = camera
        screen_rect = self.rect.move(-cam_x, -cam_y)

        image = self.anim.image
        if image:
            # 그림이 있으면: 그림의 발밑을 충돌 사각형의 발밑에 맞춰서 그림
            x, y = screen_rect.midbottom
            surface.blit(image, image.get_rect(midbottom=(x, y - self.anim.bob)))
            return

        # 그림이 없으면: 색깔 사각형 + 바라보는 방향에 작은 점(눈)
        pygame.draw.rect(surface, self.color, screen_rect, border_radius=6)
        darker = tuple(max(0, c - 60) for c in self.color)
        pygame.draw.rect(surface, darker, screen_rect, 2, border_radius=6)
        cx, cy = screen_rect.center
        fx, fy = self.facing
        pygame.draw.circle(surface, WHITE, (int(cx + fx * 7), int(cy + fy * 7)), 3)
