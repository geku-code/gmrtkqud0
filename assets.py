# assets.py
# 이미지 파일을 불러오는 파일입니다.
# 그림 파일이 없으면 None을 돌려주고, 그리는 쪽에서 색깔 도형으로 대신 그립니다.
# → assets 폴더에 png만 넣으면 코드 수정 없이 그림이 바뀝니다.
#
# 캐릭터 스프라이트 시트 규칙 (4×4 = 16장, 투명 PNG)
#   1줄: 아래(↓)   2줄: 왼쪽(←)   3줄: 오른쪽(→)   4줄: 위(↑)
#   각 줄의 1~4칸 = 걷기 프레임 (1칸 = 서 있는 모습)
#
# 정면 그림 1장만 있는 캐릭터는 load_still()로 불러옵니다.
#   (원래 크기 그대로 사용 → 도트가 선명함. 걸을 때는 살짝 통통 튀는 효과만 줌)

import os
import pygame
from settings import SPRITE_SIZE, ANIM_FPS

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# 스프라이트 시트의 줄 번호 (줄 순서가 다른 그림이면 여기 숫자만 바꾸면 됨)
ROW_DOWN, ROW_LEFT, ROW_RIGHT, ROW_UP = 0, 1, 2, 3

_cache = {}   # 같은 파일을 여러 번 읽지 않도록 저장


def load_image(rel_path, size=None):
    """
    assets 폴더 안의 그림 하나를 불러옵니다. 예) load_image("tiles/grass.png", (32, 32))
    파일이 없으면 None
    """
    key = (rel_path, size)
    if key not in _cache:
        path = os.path.join(ASSET_DIR, rel_path)
        image = None
        if os.path.exists(path):
            image = pygame.image.load(path).convert_alpha()
            if size:
                image = pygame.transform.scale(image, size)
        _cache[key] = image
    return _cache[key]


def load_sheet(rel_path, cols=4, rows=4, size=SPRITE_SIZE):
    """
    스프라이트 시트를 잘라서 frames[줄][칸] 형태로 돌려줍니다.
    한 칸 크기는 그림 크기 ÷ 4로 자동 계산하고, size×size로 맞춥니다.
    파일이 없으면 None
    """
    key = ("sheet", rel_path, cols, rows, size)
    if key in _cache:
        return _cache[key]
    sheet = load_image(rel_path)
    if sheet is None:
        _cache[key] = None
        return None
    fw = sheet.get_width() // cols
    fh = sheet.get_height() // rows
    frames = []
    for r in range(rows):
        row = []
        for c in range(cols):
            frame = sheet.subsurface(pygame.Rect(c * fw, r * fh, fw, fh))
            row.append(pygame.transform.scale(frame, (size, size)))
        frames.append(row)
    _cache[key] = frames
    return frames


def load_still(rel_path):
    """
    정면 그림 1장을 불러와서 load_sheet와 같은 형태(frames[줄][칸])로 돌려줍니다.
    4방향 모두 같은 그림 1칸 → Animator를 그대로 쓸 수 있음.
    그림 주변의 투명한 여백은 잘라내고, 크기는 원본 그대로 둡니다. 파일이 없으면 None
    """
    key = ("still", rel_path)
    if key in _cache:
        return _cache[key]
    image = load_image(rel_path)
    frames = None
    if image is not None:
        image = image.subsurface(image.get_bounding_rect()).copy()
        frames = [[image] for _ in range(4)]
    _cache[key] = frames
    return frames


def facing_to_row(facing):
    """바라보는 방향 (dx, dy) → 스프라이트 시트 줄 번호"""
    fx, fy = facing
    if abs(fx) > abs(fy):
        return ROW_RIGHT if fx > 0 else ROW_LEFT
    return ROW_UP if fy < 0 else ROW_DOWN


class Animator:
    """
    걷기 애니메이션 담당.
    움직이는 중이면 1→2→3→4칸을 반복하고, 멈추면 1칸(서 있는 모습)을 보여줍니다.
    """

    def __init__(self, frames):
        self.frames = frames    # None이면 그림 없음
        self.row = ROW_DOWN
        self.frame = 0
        self.timer = 0.0
        self.step = 0           # 걸음 수 (그림이 1장일 때 통통 튀는 효과에 사용)
        self.moving = False

    def update(self, dt, moving, facing):
        if self.frames is None:
            return
        self.row = facing_to_row(facing)
        self.moving = moving
        if moving:
            self.timer += dt
            if self.timer >= 1 / ANIM_FPS:
                self.timer -= 1 / ANIM_FPS
                self.step += 1
                self.frame = self.step % len(self.frames[self.row])
        else:
            self.frame = 0
            self.step = 0
            self.timer = 0.0

    @property
    def bob(self):
        """그림이 1장뿐인 캐릭터가 걸을 때 위로 살짝 뜨는 픽셀 수 (0 또는 2)"""
        if self.frames is None or len(self.frames[self.row]) > 1 or not self.moving:
            return 0
        return 2 if self.step % 2 else 0

    @property
    def image(self):
        """지금 보여줄 그림 (그림이 없으면 None)"""
        if self.frames is None:
            return None
        return self.frames[self.row][self.frame]
