# world.py
# 타일 맵(마을 지도)을 관리하는 파일입니다.
# 맵은 문자열로 그리고, 각 글자가 타일 한 칸을 뜻합니다.

import pygame
from settings import (TILE_SIZE, PLAYER_SIZE, COLOR_GRASS, COLOR_PATH,
                      COLOR_WALL, COLOR_HOUSE, COLOR_WATER, COLOR_BG)
from assets import load_image
from tiles import TileSet

# ---------------- 맵 데이터 ----------------
# 글자 의미:
#   W = 돌담(벽)      H = 집(벽)      ~ = 물(벽)
#   . = 풀밭          = = 큰길(3칸 폭)  , = 골목길(2칸 폭)
#   P = 플레이어 시작 위치 (큰길 위)
# 큰길 끝 세 곳(북쪽, 서쪽, 동쪽)이 마을 담에 닿는 자리 = 성문 (6부)
# (모든 줄의 길이가 같아야 합니다)
VILLAGE_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "W................===...................W",
    "W................===...................W",
    "W................===...................W",
    "W................===...................W",
    "W...,,.....,,....===.....,,.....,,.....W",
    "W..,,,,,,,,,,,,,,===,,,,,,,,,,,,,,,,,..W",
    "W..,,,,,,,,,,,,,,===,,,,,,,,,,,,,,,,,..W",
    "W................===...................W",
    "W................===...................W",
    "W................===...................W",
    "W................===...................W",
    "W.........,,.....===......,,...........W",
    "W======================================W",
    "W=================P====================W",
    "W======================================W",
    "WWWWWWWW.........===........WWWWW......W",
    "W......W.........===........W...W......W",
    "W................===........W..........W",
    "W................===........W...W......W",
    "W......W.........===....,,..WWWWW......W",
    "WWWWWWWW.........===....,,.............W",
    "W..,,,,,,,,,,,,,,===,,,,,,,,,,,,,,,,,..W",
    "W..,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,..W",
    "W......................................W",
    "W......................................W",
    "W......................................W",
    "W......................................W",
    "W......................................W",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

# 지나갈 수 없는(충돌하는) 타일 글자들
SOLID_TILES = {"W"}

# 타일 글자 → 색상
TILE_COLORS = {
    "W": COLOR_WALL,
    "H": COLOR_HOUSE,
    "~": COLOR_WATER,
    ".": COLOR_GRASS,
    ",": COLOR_PATH,
    "=": COLOR_PATH,
    "P": COLOR_PATH,   # 시작 위치는 흙길로 표시
}

# 타일 글자 → 그림 파일 (assets/tiles/ 폴더, 32×32 PNG)
# 파일이 없으면 위의 색깔로 그립니다.
# 풀밭(.)과 흙길(, P)은 tiles.py가 여러 그림을 섞고 길 모양을 맞춰서 깝니다.
TILE_FILES = {
    "W": "tiles/wall.png",
    "H": "tiles/house.png",
    "~": "tiles/water.png",
}
PATH_TILES = {",", "=", "P"}   # 흙길로 취급하는 글자

# 치료소로 지정한 왼쪽 위 파란 물 구역: (왼쪽 열, 위 행, 너비 타일, 높이 타일)
CLINIC_SITE = (3, 9, 4, 2)
# 원본의 32px 중앙 출입문을 NPC 크기에 가까운 26px로 조금 줄인다.
CLINIC_DOOR_CENTER_X = 128
CLINIC_DOOR_WIDTH = 32
CLINIC_DOOR_TARGET = 26
WAREHOUSE_SITE = (33, 25, 4, 2)
WAREHOUSE_DRAW_WIDTH = 150
WAREHOUSE_OFFSET_X = -TILE_SIZE // 2

# 오래된 창고(24~27, 24~26)를 제외한 갈색 H 구역 8곳.
# 5종을 순서대로 쓰고 남은 세 곳은 1~3번을 반복한다.
HOUSE_SITES = [
    (3, 2, 4, 3, "buildings/blacksmith_sprite.png"),
    (10, 2, 4, 3, "buildings/house_5.png"),
    (24, 2, 5, 3, "buildings/house_1.png"),
    (31, 2, 4, 3, "buildings/inn_sprite.png"),
    (9, 9, 4, 3, "buildings/shop_sprite.png"),
    (25, 9, 4, 3, "buildings/house_1.png"),
    (23, 17, 4, 3, "buildings/house_2.png"),
    (4, 24, 4, 3, "buildings/lower_house_left_sprite.png"),
    # 남은 갈색 구역에는 기존 일반 주택 중 무작위로 고른 4번을 중복 배치한다.
    (24, 24, 4, 3, "buildings/lower_house_right_sprite.png"),
]
# 이미지별 (문 중심 x, 문턱 y, 화면 표시 너비).
# 특수 건물은 일반 주택보다 조금 크게 보이되 문은 길 입구 중앙에 맞춘다.
HOUSE_LAYOUT = {
    "buildings/house_1.png": (31, 56, 166),
    "buildings/house_2.png": (31, 55, 166),
    "buildings/house_3.png": (27, 56, 166),
    "buildings/house_4.png": (32, 56, 166),
    "buildings/house_5.png": (24, 56, 166),
    "buildings/shop_sprite.png": (390, 565, 170),
    "buildings/blacksmith_sprite.png": (368, 690, 170),
    "buildings/inn_sprite.png": (406, 652, 170),
    "buildings/archive_sprite.png": (355, 625, 170),
    "buildings/lower_house_left_sprite.png": (353, 681, 140),
    "buildings/lower_house_right_sprite.png": (414, 762, 140),
}
# 신부 베네딕트 뒤 주택은 시각적으로 오른쪽 반 칸 옮긴다.
HOUSE_POSITION_OFFSETS = {(25, 9): (TILE_SIZE // 2, 0)}

def building_footprints():
    """Return building ground areas at their actual rendered positions."""
    footprints = []
    for col, row, tile_w, tile_h, _path in HOUSE_SITES:
        offset_x, offset_y = HOUSE_POSITION_OFFSETS.get((col, row), (0, 0))
        footprints.append(pygame.Rect(
            col * TILE_SIZE + offset_x,
            row * TILE_SIZE + offset_y,
            tile_w * TILE_SIZE,
            tile_h * TILE_SIZE,
        ))

    col, row, tile_w, _tile_h = CLINIC_SITE
    footprints.append(pygame.Rect(
        col * TILE_SIZE, row * TILE_SIZE,
        tile_w * TILE_SIZE, 3 * TILE_SIZE,
    ))

    col, row, tile_w, _tile_h = WAREHOUSE_SITE
    footprints.append(pygame.Rect(
        col * TILE_SIZE + WAREHOUSE_OFFSET_X,
        row * TILE_SIZE,
        tile_w * TILE_SIZE,
        3 * TILE_SIZE,
    ))
    return footprints


class BuildingSprite:
    """A building image that participates in the world's Y-depth sorting."""

    def __init__(self, image, rect, depth_y):
        self.image = image
        self.rect = rect
        self.depth_y = depth_y

    def draw(self, surface, camera, time_sec=0.0):
        cam_x, cam_y = camera
        surface.blit(self.image, self.rect.move(-cam_x, -cam_y))


class World:
    """타일 맵을 읽어서 벽 목록을 만들고, 화면에 그려주는 클래스"""

    def __init__(self, map_data=VILLAGE_MAP):
        self.map_data = map_data
        self.rows = len(map_data)
        self.cols = len(map_data[0])
        # 맵 전체 크기(픽셀) - 카메라 계산에 사용
        self.pixel_width = self.cols * TILE_SIZE
        self.pixel_height = self.rows * TILE_SIZE

        self.walls = []                 # 충돌용 벽 사각형 목록
        self.player_start = (TILE_SIZE, TILE_SIZE)  # 기본 시작 위치
        self._load()
        self.buildings = []

        # 타일 그림 불러오기 (없는 것은 None → 색으로 그림)
        self.tile_images = {ch: load_image(path, (TILE_SIZE, TILE_SIZE))
                            for ch, path in TILE_FILES.items()}
        self.tileset = TileSet()
        # 맵은 바뀌지 않으므로 처음에 한 장의 큰 그림으로 미리 그려 둠 → 매 프레임 빠르게 그림
        self.image = pygame.Surface((self.pixel_width, self.pixel_height))
        # 1) 바닥(풀밭, 길 칸 포함)  2) 흙길 덮기  3) 집·담·물
        paths_drawn = False
        if self.tileset.has_grass():
            for row in range(self.rows):
                for col in range(self.cols):
                    self.image.blit(self.tileset.grass_for(col, row),
                                    (col * TILE_SIZE, row * TILE_SIZE))
            paths_drawn = self.tileset.draw_paths(self.image, self.map_data, PATH_TILES)
        for row in range(self.rows):
            for col in range(self.cols):
                ch = self.map_data[row][col]
                if ch in SOLID_TILES or not self.tileset.has_grass() or                         (ch in PATH_TILES and not paths_drawn):
                    self._draw_tile(self.image, col, row)
        self._load_houses()
        self._load_clinic()
        self._load_warehouse()

    def _load_houses(self):
        """이미지별 문 중심과 문턱을 길 입구에 맞춰 확대 배치한다."""
        for col, row, tile_w, tile_h, path in HOUSE_SITES:
            house = load_image(path)
            if house is None:
                continue
            area_w, area_h = tile_w * TILE_SIZE, tile_h * TILE_SIZE
            door_x, door_y, draw_width = HOUSE_LAYOUT[path]
            scale = draw_width / house.get_width()
            size = (draw_width, round(house.get_height() * scale))
            house = pygame.transform.scale(house, size)
            entrance_x = col * TILE_SIZE + area_w // 2
            entrance_y = row * TILE_SIZE + area_h
            x = entrance_x - round(door_x * scale)
            y = entrance_y - round(door_y * scale)
            offset_x, offset_y = HOUSE_POSITION_OFFSETS.get((col, row), (0, 0))
            x += offset_x
            y += offset_y
            self.buildings.append(BuildingSprite(
                house, house.get_rect(topleft=(x, y)), entrance_y + offset_y
            ))

    def _load_clinic(self):
        """파란 구역 중앙에 진료소 문을 맞추고, 문을 NPC와 비슷한 크기로 그린다."""
        clinic = load_image("buildings/clinic.png")
        if clinic is None:
            return
        col, row, tile_w, tile_h = CLINIC_SITE
        area_w, area_h = tile_w * TILE_SIZE, tile_h * TILE_SIZE
        scale = CLINIC_DOOR_TARGET / CLINIC_DOOR_WIDTH
        size = (max(1, round(clinic.get_width() * scale)),
                max(1, round(clinic.get_height() * scale)))
        clinic = pygame.transform.scale(clinic, size)
        entrance_x = col * TILE_SIZE + area_w // 2
        x = entrance_x - round(CLINIC_DOOR_CENTER_X * scale)
        # 루카스가 있는 위쪽 길목을 가리지 않도록 파란 구역에서 아래로 확장한다.
        y = row * TILE_SIZE
        rect = clinic.get_rect(topleft=(x, y))
        # The depth boundary is the building footprint's bottom edge, not the
        # bottom of the (often transparent) image.  A character above this
        # horizontal line is hidden by the building; one below it is drawn in
        # front.
        depth_y = (row + 3) * TILE_SIZE
        self.buildings.append(BuildingSprite(clinic, rect, depth_y))

    def _load_warehouse(self):
        """오른쪽 아래 파란 구역 중앙에 오래된 창고 이미지를 배치한다."""
        warehouse = load_image("buildings/warehouse_back_sprite.png")
        if warehouse is None:
            return
        col, row, tile_w, tile_h = WAREHOUSE_SITE
        scale = WAREHOUSE_DRAW_WIDTH / warehouse.get_width()
        warehouse_size = (WAREHOUSE_DRAW_WIDTH,
                          round(warehouse.get_height() * scale))
        warehouse = pygame.transform.scale(warehouse, warehouse_size)
        center_x = col * TILE_SIZE + tile_w * TILE_SIZE // 2 + WAREHOUSE_OFFSET_X
        center_y = row * TILE_SIZE + tile_h * TILE_SIZE // 2 - TILE_SIZE // 2
        rect = warehouse.get_rect(center=(center_x, center_y))
        depth_y = (row + 3) * TILE_SIZE
        self.buildings.append(BuildingSprite(warehouse, rect, depth_y))

    def _load(self):
        """맵 문자열을 한 칸씩 읽어서 벽과 시작 위치를 찾습니다."""
        for row, line in enumerate(self.map_data):
            for col, ch in enumerate(line):
                x, y = col * TILE_SIZE, row * TILE_SIZE
                if ch in SOLID_TILES:
                    self.walls.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                elif ch == "P":
                    # 타일의 가운데를 시작 위치로 사용
                    self.player_start = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)

        # Brown dirt is always walkable.  Carve each road (plus half a
        # character of clearance) out of building footprints.  The clearance
        # is necessary because collision uses the character's whole body
        # rectangle; without it a roof/footprint directly beside a road can
        # still catch the character while their centre remains on the road.
        for footprint in building_footprints():
            blocked_parts = [footprint]
            for tile_row, line in enumerate(self.map_data):
                for tile_col, ch in enumerate(line):
                    if ch not in PATH_TILES:
                        continue
                    road = pygame.Rect(tile_col * TILE_SIZE,
                                       tile_row * TILE_SIZE,
                                       TILE_SIZE, TILE_SIZE).inflate(
                                           PLAYER_SIZE, PLAYER_SIZE)
                    if not footprint.colliderect(road):
                        continue
                    next_parts = []
                    for part in blocked_parts:
                        cut = part.clip(road)
                        if not cut.width or not cut.height:
                            next_parts.append(part)
                            continue
                        if part.top < cut.top:
                            next_parts.append(pygame.Rect(
                                part.left, part.top, part.width,
                                cut.top - part.top))
                        if cut.bottom < part.bottom:
                            next_parts.append(pygame.Rect(
                                part.left, cut.bottom, part.width,
                                part.bottom - cut.bottom))
                        if part.left < cut.left:
                            next_parts.append(pygame.Rect(
                                part.left, cut.top,
                                cut.left - part.left, cut.height))
                        if cut.right < part.right:
                            next_parts.append(pygame.Rect(
                                cut.right, cut.top,
                                part.right - cut.right, cut.height))
                    blocked_parts = next_parts
            self.walls.extend(blocked_parts)

    def is_absolute_path(self, rect):
        """Whether a character stands on an always-walkable dirt path.

        This is checked during movement after the floor map has been split
        into path and non-path areas.  It deliberately takes priority over
        every building/object collision rectangle.
        """
        x, y = rect.center
        path_mask = getattr(self.tileset, "path_mask", None)
        if path_mask is not None and 0 <= x < self.pixel_width and 0 <= y < self.pixel_height:
            # Use the exact same rounded/wobbled brown area that was painted,
            # including visible dirt extending beyond the source map tile.
            return bool(path_mask.get_at((x, y)))

        col = x // TILE_SIZE
        row = y // TILE_SIZE
        return (0 <= row < self.rows and 0 <= col < self.cols and
                self.map_data[row][col] in PATH_TILES)

    def _draw_tile(self, surface, col, row):
        """타일 한 칸을 그림 또는 색깔로 그립니다. (그림이 없는 타일용)"""
        ch = self.map_data[row][col]
        rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        image = self.tile_images.get(ch)   # 집·담·물 그림 (없으면 색깔)
        if image:
            if ch == "W":
                # 돌담 가장자리의 어두운 외곽선이 타일마다 틈처럼 보이지 않게
                # 한 픽셀씩 포개어 그린다. 방향은 모든 구간에서 원본 그대로 유지한다.
                wall = pygame.transform.scale(image, (TILE_SIZE + 2, TILE_SIZE + 2))
                pygame.draw.rect(surface, COLOR_WALL, rect)
                surface.blit(wall, (rect.x - 1, rect.y - 1))
            else:
                surface.blit(image, rect)
            return
        color = TILE_COLORS.get(ch, COLOR_GRASS)
        pygame.draw.rect(surface, color, rect)
        # 벽 타일에는 테두리를 그려서 구분이 잘 되게 함
        if ch in SOLID_TILES:
            darker = tuple(max(0, c - 30) for c in color)
            pygame.draw.rect(surface, darker, rect, 2)

    def draw(self, surface, camera):
        """미리 그려 둔 맵 그림에서 화면에 보이는 부분만 옮겨 그립니다. camera = 카메라 왼쪽 위 좌표"""
        surface.fill(COLOR_BG)
        cam_x, cam_y = camera
        surface.blit(self.image, (-cam_x, -cam_y))
