# tiles.py
# 바닥 타일 그림을 준비하는 파일입니다. (world.py가 맵을 그릴 때 사용)
#
#   풀밭: grass.png + grass_1.png, grass_2.png ... 를 칸마다 섞어서 깔아 반복무늬를 줄입니다.
#   흙길: 큰길(=, 3칸)과 골목(,, 2칸)의 모양을 맵 전체에서 한 번에 계산해서 깝니다.
#         - 길 폭은 타일 칸에 딱 맞음 (큰길 96px, 골목 64px)
#         - 모서리는 둥글게, 가장자리는 살짝 울퉁불퉁하게, 길 바로 옆 풀은 살짝 어둡게
#         흙 그림: 골목 = path.png, 큰길 = road.png (없으면 path.png)
#   그림 가장자리에 잘못 잘린 어두운 줄이 있으면 불러올 때 자동으로 지웁니다. (원본 파일은 그대로)

import random
import pygame
from settings import TILE_SIZE
from assets import load_image

# 풀밭 변형마다 나오는 비율 (적지 않은 파일은 1). 큰 덤불이 있는 그림은 자주 나오면 티가 나서 낮춤
GRASS_WEIGHTS = {"grass.png": 6, "grass_2.png": 0.4, "grass_6.png": 0.4}
MAX_GRASS_VARIANTS = 20   # grass_1.png ~ grass_20.png 까지 찾아봄

ROUNDNESS = 2       # 모서리 둥글기 (1~3, 클수록 더 둥글게)
WOBBLE = 18         # 길 가장자리 울퉁불퉁한 정도 (0이면 매끈한 직선)
RIM_ALPHA = 70      # 길 바로 옆 풀을 어둡게 하는 정도 (0~255)

def _brightness(surface, points):
    return sum(sum(surface.get_at(p)[:3]) for p in points) / len(points)


def clean_edges(image):
    """
    가장자리 1~3줄이 안쪽보다 훨씬 어두우면(잘라낼 때 생긴 검은 줄) 안쪽 줄로 덮어씁니다.
    원본 파일은 바꾸지 않고, 불러온 그림만 고칩니다.
    """
    image = image.copy()
    w, h = image.get_size()
    # i번째 줄(바깥에서부터)의 픽셀 좌표 목록을 만드는 함수: 왼쪽, 오른쪽, 위, 아래
    sides = [lambda i: [(i, y) for y in range(h)],
             lambda i: [(w - 1 - i, y) for y in range(h)],
             lambda i: [(x, i) for x in range(w)],
             lambda i: [(x, h - 1 - i) for x in range(w)]]
    for line in sides:
        inner = _brightness(image, line(4))
        # 바깥에서부터 어두운 줄이 몇 줄인지 (최대 3줄)
        bad = 0
        while bad < 3 and _brightness(image, line(bad)) < inner * 0.75:
            bad += 1
        for i in range(bad):
            for src, dst in zip(line(bad), line(i)):
                image.set_at(dst, image.get_at(src))
    return image


def load_tile(name):
    """assets/tiles/<name>을 32×32로 불러와서 가장자리를 정리합니다. 없으면 None"""
    image = load_image(f"tiles/{name}", (TILE_SIZE, TILE_SIZE))
    return clean_edges(image) if image else None


class TileSet:
    def __init__(self):
        # Exact pixel mask of the brown dirt finally drawn on the floor.
        # World movement uses this as the authoritative walkable-path area.
        self.path_mask = None
        # 풀밭 변형들: [(그림, 비율), ...]
        self.grass = []
        names = ["grass.png"] + [f"grass_{i}.png" for i in range(1, MAX_GRASS_VARIANTS + 1)]
        for name in names:
            image = load_tile(name)
            if image:
                self.grass.append((image, GRASS_WEIGHTS.get(name, 1)))

        # 흙 그림: 맵 글자 → 그림 (큰길 그림이 없으면 골목 그림을 같이 씀)
        alley = load_tile("path.png")
        self.dirt = {",": alley, "=": load_tile("road.png") or alley}
        self.dirt["P"] = self.dirt["="]

    def has_grass(self):
        return bool(self.grass)

    def grass_for(self, col, row):
        """이 칸에 깔 풀밭 그림 (칸 위치로 정해서 매번 같은 그림이 나옴)"""
        rng = random.Random(col * 7919 + row * 104729)
        images = [g for g, _ in self.grass]
        weights = [w for _, w in self.grass]
        return rng.choices(images, weights)[0]

    # ---------------- 길 깔기 ----------------
    def draw_paths(self, surface, map_data, path_chars):
        """
        풀밭이 깔린 맵 그림(surface) 위에 흙길을 덮어 그립니다.
        map_data = 맵 글자 목록, path_chars = 길로 취급하는 글자들
        흙 그림이 없으면 False (→ world.py가 색깔로 그림)
        """
        alley = self.dirt[","]
        if alley is None:
            return False
        rows, cols = len(map_data), len(map_data[0])
        size = (cols * TILE_SIZE, rows * TILE_SIZE)

        # 1) 길 모양: 길 칸 = 흰색, 나머지 = 검은색인 작은 그림(한 칸 = 1픽셀)을
        #    부드럽게 크게 늘리면 칸 사이가 흐릿하게 이어지는데, 그 중간값(128)을 경계로 쓰면
        #    직선 부분은 정확히 칸 경계, 모서리는 둥글게 됨
        def is_path(c, r):
            return 0 <= r < rows and 0 <= c < cols and map_data[r][c] in path_chars

        small = pygame.Surface((cols, rows))
        for r, line in enumerate(map_data):
            for c, ch in enumerate(line):
                touches_path = any(is_path(c + dc, r + dr)
                                   for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)))
                on_border = r in (0, rows - 1) or c in (0, cols - 1)
                # 길 칸 + 길에 닿은 집(문 앞) + 길이 닿은 바깥 담(성문)도 길로 침
                # → 짧은 골목도 집 문/성문까지 끊기지 않고 이어짐 (집·담은 위에 그려져서 안 보임)
                if ch in path_chars or (touches_path and (ch == "H" or (ch == "W" and on_border))):
                    small.set_at((c, r), (255, 255, 255))
        shape = small
        for _ in range(ROUNDNESS):   # 여러 번 나눠서 늘리면 모서리가 더 둥글어짐
            w, h = shape.get_size()
            shape = pygame.transform.smoothscale(shape, (w * 2, h * 2))
        shape = pygame.transform.smoothscale(shape, size)

        # 2) 가장자리 울퉁불퉁: 작은 잡음 그림을 늘려서 더하고 빼기
        if WOBBLE:
            rng = random.Random(1347)
            noise = pygame.Surface((cols * 4, rows * 4))
            for y in range(rows * 4):
                for x in range(cols * 4):
                    v = rng.randint(0, WOBBLE * 2)
                    noise.set_at((x, y), (v, v, v))
            noise = pygame.transform.smoothscale(noise, size)
            shape.blit(noise, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            shape.fill((WOBBLE, WOBBLE, WOBBLE), special_flags=pygame.BLEND_RGB_SUB)

        # 3) 경계값(128)보다 밝은 곳 = 흙
        dirt_mask = pygame.mask.from_threshold(shape, (255, 255, 255), (128, 128, 128, 255))
        self.path_mask = dirt_mask

        # 4) 흙 그림 깔기: 골목 흙을 전체에 깔고, 큰길 칸은 큰길 흙으로 덮음
        dirt_layer = pygame.Surface(size, pygame.SRCALPHA)
        for r in range(rows):
            for c in range(cols):
                image = self.dirt.get(map_data[r][c]) or alley
                dirt_layer.blit(image, (c * TILE_SIZE, r * TILE_SIZE))

        # 5) 길 바로 옆 풀을 어둡게 (흙 모양을 1픽셀씩 넓힌 부분 = 테두리)
        wider = pygame.mask.Mask((3, 3), fill=True)
        rim = dirt_mask.convolve(wider, None, (-1, -1))
        rim_surface = rim.to_surface(setcolor=(0, 0, 0, RIM_ALPHA), unsetcolor=(0, 0, 0, 0))
        surface.blit(rim_surface, (0, 0))

        # 6) 흙 덮기
        surface.blit(dirt_mask.to_surface(setsurface=dirt_layer, unsetcolor=(0, 0, 0, 0)), (0, 0))
        return True
