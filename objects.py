# objects.py
# 마을에 놓인 상호작용 오브젝트(우물, 쓰레기 더미, 쥐, 약초, 환자)를 담당하는 파일입니다.
# 위치와 종류는 아래 OBJECT_DATA 목록(데이터)에 적고, create_objects()가 오브젝트를 만듭니다.
#
# 모든 상호작용 대상(NPC 포함)은 아래 메서드를 가집니다. (main.py가 이것만 보고 처리)
#   visible(game)       : 지금 마을에 나와 있는지 (예: 쥐는 3부에만, 약초는 4부부터)
#   can_interact(game)  : 지금 E(행동 버튼)로 상호작용할 수 있는지
#   interact_text(game) : 머리 위 [E] 안내 글자
#   button_label(game)  : 휴대폰 행동 버튼 글자
#   interact(game)      : 실제 행동. 퀘스트 진행은 여기서 game.notify_quest(self)로 알림
#                         대화창에 보여줄 대사 목록을 돌려줌 (빈 목록이면 대화창 없이 알림만)
#
# 그림: assets/objects/<kind>.png 가 있으면 그 그림, 없으면 도형으로 그립니다.

import math
import random
import pygame
from settings import TILE_SIZE, RAT_SPEED, RAT_WANDER_RADIUS
from assets import load_image
from npc import NPC
from quest import FAIRY
from settings import HIGH_SPREAD_THRESHOLD

# ---------------- 오브젝트 데이터 ----------------
#   kind : 종류 (well / trash / rat / herb / patient)
#   id   : 고유 이름 (퀘스트에서 같은 대상을 두 번 세지 않도록 사용)
#   tile : 놓이는 위치 (열, 행) - world.py 맵 기준, 풀밭(.) 칸이어야 함
OBJECT_DATA = [
    # 2부: 우물 3곳
    {"kind": "well", "id": "well_west", "tile": (14, 10)},
    {"kind": "well", "id": "well_center", "tile": (22, 10)},
    {"kind": "well", "id": "well_south", "tile": (12, 26)},
    # 2부: 쓰레기 더미 5개
    {"kind": "trash", "id": "trash_1", "tile": (8, 3)},
    {"kind": "trash", "id": "trash_2", "tile": (22, 8)},
    {"kind": "trash", "id": "trash_3", "tile": (37, 11)},
    {"kind": "trash", "id": "trash_4", "tile": (3, 19)},
    {"kind": "trash", "id": "trash_5", "tile": (30, 18)},
    # 3부: 성문을 조사하면 조사한 문에서 한꺼번에 쏟아져 나온다.
    # 아래 위치는 생성용 임시값이며, 실제 등장 위치는 Gate.interact()가 정한다.
    {"kind": "rat", "id": "rat_1", "tile": (18, 1)},
    {"kind": "rat", "id": "rat_2", "tile": (18, 1)},
    {"kind": "rat", "id": "rat_3", "tile": (18, 1)},
    {"kind": "rat", "id": "rat_4", "tile": (18, 1)},
    {"kind": "rat", "id": "rat_5", "tile": (18, 1)},
    {"kind": "rat", "id": "rat_6", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_1", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_2", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_3", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_4", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_5", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_6", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_7", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_8", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_9", "tile": (18, 1)},
    {"kind": "flea", "id": "flea_10", "tile": (18, 1)},
    # 6부: 성문 3곳 (큰길 끝이 마을 담에 닿는 곳. orient: h = 가로로 긴 문, v = 세로로 긴 문)
    {"kind": "gate", "id": "gate_north", "tile": (18, 0), "orient": "h", "name": "북쪽 성문"},
    {"kind": "gate", "id": "gate_west", "tile": (0, 14), "orient": "v", "name": "서쪽 성문"},
    {"kind": "gate", "id": "gate_east", "tile": (39, 14), "orient": "v", "name": "동쪽 성문"},
    # 4부: 약초 (약초꾼 엘자 근처, 마을 동쪽 아래 풀숲) / 아픈 소년 (마을 진료소 앞)
    {"kind": "herb", "id": "herb", "tile": (37, 27)},
    # 왼쪽 위의 두 건물 사이 길목 중, 아래쪽 치료소에 가까운 위치
    {"kind": "patient", "id": "lukas", "tile": (6, 12)},
]

# 아픈 소년 (NPC와 같은 형식의 데이터 - npc.py 참고)
PATIENT_DATA = {"id": "lukas", "name": "아픈 소년 루카스", "color": (150, 120, 90),
                "sprite": "characters/trimmed/npc_08_r2_c4.png", "wander": False, "lines": []}


def tile_center(tile):
    """타일 번호 (열, 행) → 타일 가운데 픽셀 좌표"""
    col, row = tile
    return col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2


# ======================================================================
# 기본 오브젝트
# ======================================================================
class WorldObject:
    kind = "object"
    name = "물건"
    solid = False          # True면 플레이어가 지나갈 수 없음
    size = (28, 28)        # 충돌/상호작용 사각형 크기

    def __init__(self, data):
        self.id = data["id"]
        cx, cy = tile_center(data["tile"])
        self.rect = pygame.Rect(0, 0, *self.size)
        self.rect.center = (cx, cy)
        self.quest_event = self.kind
        self.quest_events = (self.kind,)   # 이 오브젝트와 관련된 퀘스트 행동들 ('!' 표시용)
        self.image = load_image(f"objects/{self.kind}.png")   # 없으면 None

    @property
    def top(self):
        """머리 위 표시('!', [E] 안내) 위치 - 맵 기준 y좌표"""
        return self.rect.top

    def visible(self, game):
        return True

    def can_interact(self, game):
        return self.visible(game)

    def interact_text(self, game):
        return f"{self.name}: 살펴보기"

    def button_label(self, game):
        return "조사"

    def interact(self, game):
        return []

    def update(self, dt, obstacles):
        pass

    def draw(self, surface, camera, time_sec):
        cam_x, cam_y = camera
        r = self.rect.move(-cam_x, -cam_y)
        if self.image:
            surface.blit(self.image, self.image.get_rect(midbottom=r.midbottom))
        else:
            self.draw_shape(surface, r, time_sec)

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.rect(surface, (200, 200, 200), r)


# ======================================================================
# 2부: 우물
# ======================================================================
class Well(WorldObject):
    kind = "well"
    name = "우물"
    solid = True
    size = (30, 30)

    def __init__(self, data):
        super().__init__(data)
        self.clean = False
        self.dirty_image = load_image("objects/well_dirty.png", (64, 64))
        self.clean_image = load_image("objects/well_clean.png", (64, 64))

    def can_interact(self, game):
        return not self.clean   # 청소가 끝난 우물은 더 할 일이 없음

    def interact_text(self, game):
        if game.quest.wants("well", self.id):
            return "우물: 청소하기"
        return "우물: 살펴보기"

    def button_label(self, game):
        return "청소" if game.quest.wants("well", self.id) else "조사"

    def interact(self, game):
        if not game.quest.wants("well", self.id):
            # 2부 전에는 살펴보기만 (단서)
            return [("", "물이 뿌옇고 고약한 냄새가 난다... 이 물을 마셔도 괜찮은 걸까?")]
        self.clean = True
        game.notify_quest(self)
        return [("", "고인 물을 퍼내고, 우물 주변의 오물을 깨끗이 치웠다."),
                (FAIRY, "좋아! 이제 이 우물은 안심하고 쓸 수 있어.")]

    def draw(self, surface, camera, time_sec):
        """청소 전에는 오염된 우물, 청소 후에는 깨끗한 우물 이미지를 표시한다."""
        image = self.clean_image if self.clean else self.dirty_image
        if image is None:
            super().draw(surface, camera, time_sec)
            return
        cam_x, cam_y = camera
        center = (self.rect.centerx - cam_x, self.rect.centery - cam_y)
        surface.blit(image, image.get_rect(center=center))

    def draw_shape(self, surface, r, time_sec):
        # 돌로 쌓은 둥근 우물 + 안쪽 물 (더러우면 탁한 초록, 깨끗하면 파랑)
        center = r.center
        pygame.draw.circle(surface, (95, 90, 90), center, 16)
        pygame.draw.circle(surface, (140, 135, 130), center, 16, 4)
        water = (60, 120, 200) if self.clean else (90, 100, 50)
        pygame.draw.circle(surface, water, center, 10)
        if self.clean:   # 반짝임
            if int(time_sec * 2) % 2 == 0:
                pygame.draw.circle(surface, (200, 230, 255), (center[0] - 3, center[1] - 3), 2)
        else:            # 떠다니는 거품
            bob = int(math.sin(time_sec * 3) * 2)
            pygame.draw.circle(surface, (130, 140, 70), (center[0] + 3, center[1] + bob), 2)
        # 두레박 기둥
        pygame.draw.line(surface, (110, 75, 45), (r.left + 2, r.top - 6), (r.left + 2, r.centery), 3)
        pygame.draw.line(surface, (110, 75, 45), (r.right - 2, r.top - 6), (r.right - 2, r.centery), 3)
        pygame.draw.line(surface, (110, 75, 45), (r.left, r.top - 6), (r.right, r.top - 6), 3)


# ======================================================================
# 2부: 쓰레기 더미
# ======================================================================
class Trash(WorldObject):
    kind = "trash"
    name = "쓰레기 더미"

    def __init__(self, data):
        super().__init__(data)
        self.removed = False

    def visible(self, game):
        return not self.removed

    def interact_text(self, game):
        if game.quest.wants("trash", self.id):
            return "쓰레기 더미: 치우기"
        return "쓰레기 더미: 살펴보기"

    def button_label(self, game):
        return "치우기" if game.quest.wants("trash", self.id) else "조사"

    def interact(self, game):
        if not game.quest.wants("trash", self.id):
            return [("", "썩은 음식 찌꺼기가 쌓여 있다. 쥐들이 아주 좋아하겠는걸...")]
        # 여러 번 반복하는 일이라 대화창 없이 알림만 (휴대폰에서 편하게)
        self.removed = True
        game.notify_quest(self)
        return []

    def draw_shape(self, surface, r, time_sec):
        # 갈색·초록 덩어리들 + 주위를 맴도는 파리
        x, y = r.centerx, r.bottom - 6
        pygame.draw.ellipse(surface, (90, 70, 45), (x - 14, y - 10, 28, 14))
        pygame.draw.ellipse(surface, (110, 120, 60), (x - 9, y - 16, 14, 10))
        pygame.draw.ellipse(surface, (120, 90, 55), (x - 1, y - 14, 12, 9))
        for i in range(3):
            a = time_sec * 4 + i * 2.1
            fx = x + math.cos(a) * 12
            fy = y - 20 + math.sin(a * 1.3) * 5
            pygame.draw.circle(surface, (20, 20, 20), (int(fx), int(fy)), 1)


# ======================================================================
# 3부: 쥐
# ======================================================================
class Rat(WorldObject):
    kind = "rat"
    name = "쥐"
    size = (18, 14)

    def __init__(self, data):
        super().__init__(data)
        self.caught = False
        self.released = False
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.home = self.rect.center
        self.walk_dir = (0, 0)
        self.facing = (1, 0)
        self.timer = random.uniform(0.2, 1.0)

    def visible(self, game):
        return game.quest.index == 3 and self.released and not self.caught

    def release_from(self, origin, inward, order, total):
        """성문 안쪽에서 서로 겹치지 않게 부채꼴로 흩어져 나오게 한다."""
        lateral = (-inward[1], inward[0])
        column = order % 8
        row = order // 8
        spread = (column - 3.5) * 12
        forward = row * 22 + (column % 2) * 7
        center = (
            origin[0] + inward[0] * forward + lateral[0] * spread,
            origin[1] + inward[1] * forward + lateral[1] * spread,
        )
        self.rect.center = (round(center[0]), round(center[1]))
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.home = self.rect.center
        # 양옆으로 향하는 힘을 충분히 주어 등장 직후에도 한 덩어리로 보이지 않게 한다.
        fan = (column - 3.5) / 3.5
        jitter = fan * 0.85 + random.uniform(-0.12, 0.12)
        direction = (inward[0] + lateral[0] * jitter,
                     inward[1] + lateral[1] * jitter)
        length = math.hypot(*direction)
        self.walk_dir = (direction[0] / length, direction[1] / length)
        self.facing = self.walk_dir
        self.timer = random.uniform(0.7, 1.3)
        self.released = True

    def interact_text(self, game):
        return "쥐: 잡기"

    def button_label(self, game):
        return "잡기"

    def interact(self, game):
        self.caught = True
        game.notify_quest(self)
        return []

    def update(self, dt, obstacles):
        """잠깐 멈췄다가 휙 달리기를 반복. 처음 위치에서 너무 멀어지지 않음"""
        self.timer -= dt
        if self.timer <= 0:
            if self.walk_dir != (0, 0):
                self.walk_dir = (0, 0)
                self.timer = random.uniform(0.6, 1.8)
            else:
                dx = self.home[0] - self.rect.centerx
                dy = self.home[1] - self.rect.centery
                if math.hypot(dx, dy) > RAT_WANDER_RADIUS:
                    length = math.hypot(dx, dy)
                    self.walk_dir = (dx / length, dy / length)
                else:
                    a = random.uniform(0, math.tau)
                    self.walk_dir = (math.cos(a), math.sin(a))
                self.facing = self.walk_dir
                self.timer = random.uniform(0.3, 0.9)

        if self.walk_dir == (0, 0):
            return
        # 가로/세로를 따로 움직여서 벽에 부딪히면 그 방향만 멈춤
        for axis in (0, 1):
            step = self.walk_dir[axis] * RAT_SPEED * dt
            if axis == 0:
                self.x += step
                self.rect.x = round(self.x)
            else:
                self.y += step
                self.rect.y = round(self.y)
            if self.rect.collidelist(obstacles) != -1:
                if axis == 0:
                    self.x -= step
                    self.rect.x = round(self.x)
                else:
                    self.y -= step
                    self.rect.y = round(self.y)
                self.walk_dir = (0, 0)
                self.timer = random.uniform(0.2, 0.6)
                return

    def draw_shape(self, surface, r, time_sec):
        # 회갈색 몸통 + 머리 + 귀 + 꼬리 (바라보는 방향으로)
        side = 1 if self.facing[0] >= 0 else -1
        cx, cy = r.center
        body = (110, 100, 95)
        pygame.draw.ellipse(surface, body, (cx - 9, cy - 5, 18, 11))
        hx = cx + side * 9
        pygame.draw.circle(surface, body, (hx, cy - 1), 5)
        pygame.draw.circle(surface, (210, 150, 150), (hx - side * 2, cy - 6), 3)   # 귀
        pygame.draw.circle(surface, (20, 20, 20), (hx + side * 2, cy - 2), 1)      # 눈
        wiggle = math.sin(time_sec * 12) * 2
        tail_end = (cx - side * 17, cy + 2 + wiggle)
        pygame.draw.line(surface, (190, 140, 140), (cx - side * 8, cy + 1), tail_end, 2)


class Flea(Rat):
    """쥐와 별개로 좁은 범위를 뛰어다니는 작은 벼룩."""
    kind = "flea"
    name = "벼룩"
    size = (9, 7)

    def __init__(self, data):
        super().__init__(data)
        self.image = load_image("objects/flea.png", self.size)
        self.timer = random.uniform(0.1, 0.6)

    def interact_text(self, game):
        return "벼룩: 잡기"

    def update(self, dt, obstacles):
        # 벼룩은 쥐보다 짧게 멈추고 자주 방향을 바꾸며 톡톡 뛴다.
        super().update(dt * 1.25, obstacles)


# ======================================================================
# 4부: 약초
# ======================================================================
class Herb(WorldObject):
    kind = "herb"
    name = "약초"

    def __init__(self, data):
        super().__init__(data)
        self.picked = False

    def visible(self, game):
        return game.quest.index >= 4 and not self.picked

    def interact_text(self, game):
        return "약초: 캐기"

    def button_label(self, game):
        return "캐기"

    def interact(self, game):
        self.picked = True
        game.add_item("약초")
        game.notify_quest(self)
        return [("", "열을 내리는 약초를 캤다! (가방에 넣었다)"),
                (FAIRY, "이제 이 약초를 아픈 루카스에게 가져가자. 마을 왼쪽 위 치료소 앞에 있어!")]

    def draw_shape(self, surface, r, time_sec):
        # 초록 잎사귀 몇 장 + 반짝임
        x, y = r.centerx, r.bottom - 4
        for dx, h in ((-6, 12), (0, 16), (6, 12)):
            pygame.draw.ellipse(surface, (70, 170, 80), (x + dx - 3, y - h, 7, h))
        pygame.draw.circle(surface, (230, 240, 120), (x, y - 17), 2)
        if int(time_sec * 3) % 2 == 0:
            pygame.draw.circle(surface, (255, 255, 200), (x + 9, y - 18), 2)


# ======================================================================
# 6부: 성문 (큰길 끝, 마을 담에 붙어 있음. 성문 자리는 맵에서 담(W)이라 원래 못 지나감)
# ======================================================================
class Gate(WorldObject):
    kind = "gate"
    solid = False   # 충돌은 맵의 담이 이미 담당

    def __init__(self, data):
        self.orient = data["orient"]
        # 큰길 폭(3칸)만큼 긴 문
        self.size = (TILE_SIZE * 3, TILE_SIZE) if self.orient == "h" else (TILE_SIZE, TILE_SIZE * 3)
        super().__init__(data)
        self.name = data["name"]
        self.closed = False
        if self.image and self.orient == "v":
            self.image = pygame.transform.rotate(self.image, 90)   # 그림은 가로 문 기준

    @property
    def top(self):
        return self.rect.top if self.orient == "v" else self.rect.top - 8

    def can_interact(self, game):
        if self.closed:
            return False
        if game.quest.index == 3:
            return not any(getattr(obj, "released", False)
                           for obj in game.objects if obj.kind in ("rat", "flea"))
        return True

    def interact_text(self, game):
        if game.quest.wants("gate", self.id):
            return f"{self.name}: 닫기"
        if game.quest.index == 3:
            return f"{self.name}: 꾸물거리는 짐 조사하기"
        return f"{self.name}: 살펴보기"

    def button_label(self, game):
        return "닫기" if game.quest.wants("gate", self.id) else "조사"

    def interact(self, game):
        if game.quest.index == 3:
            animals = [obj for obj in game.objects if obj.kind in ("rat", "flea")]
            if any(animal.released for animal in animals):
                return []
            game.pending_dialogue_action = lambda: self.release_animals(game)
            return [("", "수레에 실린 짐을 확인해 본다."),
                    ("", "......"),
                    ("", "포대 안쪽에서 무언가 빠르게 움직이는 소리가 난다...")]
        if not game.quest.wants("gate", self.id):
            return [("", "외지 상인들의 수레가 쉴 새 없이 드나드는 성문이다. 짐 사이로 뭔가 꼬물거린다...")]
        self.closed = True
        game.notify_quest(self)
        return [("", f"무거운 빗장을 걸어 {self.name}을 닫았다.")]

    def release_animals(self, game):
        """조사 대사가 끝난 뒤 쥐와 벼룩을 실제로 등장시킨다."""
        animals = [obj for obj in game.objects if obj.kind in ("rat", "flea")]
        if any(animal.released for animal in animals):
            return []
        inward_by_gate = {
            "gate_north": (0, 1),
            "gate_west": (1, 0),
            "gate_east": (-1, 0),
        }
        inward = inward_by_gate[self.id]
        # 담 한 칸을 지나 마을 안쪽에서 등장시켜 벽 충돌 없이 쏟아져 나오게 한다.
        origin = (self.rect.centerx + inward[0] * TILE_SIZE * 1.5,
                  self.rect.centery + inward[1] * TILE_SIZE * 1.5)
        for order, animal in enumerate(animals):
            animal.release_from(origin, inward, order, len(animals))
        return [("", "포대를 들추자 숨어 있던 쥐와 벼룩이 성문 안쪽으로 와르르 쏟아져 나왔다!"),
                (FAIRY, "쥐 6마리와 벼룩 10마리야! 마을로 흩어지기 전에 모두 잡자!")]

    def draw(self, surface, camera, time_sec):
        cam_x, cam_y = camera
        r = self.rect.move(-cam_x, -cam_y)
        if self.image and self.closed:
            surface.blit(self.image, r)
            return
        wood, dark, iron = (125, 85, 50), (70, 45, 25), (60, 60, 65)
        if self.closed:
            # 닫힌 문: 나무판 + 가운데 빗장
            pygame.draw.rect(surface, wood, r)
            step = TILE_SIZE // 4
            if self.orient == "h":
                for x in range(r.left + step, r.right, step):
                    pygame.draw.line(surface, dark, (x, r.top), (x, r.bottom), 2)
                pygame.draw.rect(surface, iron, (r.left + 6, r.centery - 3, r.width - 12, 6))
            else:
                for y in range(r.top + step, r.bottom, step):
                    pygame.draw.line(surface, dark, (r.left, y), (r.right, y), 2)
                pygame.draw.rect(surface, iron, (r.centerx - 3, r.top + 6, 6, r.height - 12))
            pygame.draw.rect(surface, dark, r, 3)
        else:
            # 열린 문: 어두운 문간 + 양쪽으로 젖혀진 문짝
            pygame.draw.rect(surface, (35, 30, 30), r)
            if self.orient == "h":
                pygame.draw.rect(surface, wood, (r.left, r.top, 10, r.height))
                pygame.draw.rect(surface, wood, (r.right - 10, r.top, 10, r.height))
            else:
                pygame.draw.rect(surface, wood, (r.left, r.top, r.width, 10))
                pygame.draw.rect(surface, wood, (r.left, r.bottom - 10, r.width, 10))
            pygame.draw.rect(surface, dark, r, 3)


# ======================================================================
# 4부: 아픈 소년 (NPC처럼 생겼지만 대화 내용이 퀘스트에 따라 바뀜)
# ======================================================================
class Patient(NPC):
    kind = "patient"
    solid = True

    def __init__(self, data):
        super().__init__({**PATIENT_DATA, "tile": data["tile"]})
        self.quest_event = "patient"
        self.quest_events = ("patient",)
        self.healed = False

    def visible(self, game):
        return game.quest.index >= 4

    def can_interact(self, game):
        return True

    def interact_text(self, game):
        return f"{self.name}: {'약초 주기' if self.ready(game) else '대화하기'}"

    def button_label(self, game):
        return "치료" if self.ready(game) else "대화"

    def ready(self, game):
        """약초를 가지고 있고, 아직 치료 전인지"""
        return not self.healed and game.has_item("약초") and game.quest.wants("patient", self.id)

    def interact(self, game):
        self.face_towards(game.player.rect)
        if self.healed:
            return [("루카스", "덕분에 살았어요! 이제 물도 꼭 끓여서 마실게요.")]
        if not self.ready(game):
            return [("루카스", "콜록콜록... 몸이 불덩이 같아요..."),
                    (FAIRY, "열을 내리는 약초가 필요해. 약초꾼 엘자 말로는 마을 동쪽 아래 풀숲에 있대!")]
        game.use_item("약초")
        self.healed = True
        self.name = "루카스"
        game.notify_quest(self)
        return [("", "약초를 달여 루카스에게 먹였다. 이마의 열이 조금씩 내려간다..."),
                ("루카스", "고마워요... 숨쉬기가 한결 편해졌어요.")]

    def update(self, dt, obstacles):
        self.anim.update(dt, False, self.facing)

    def draw(self, surface, camera, time_sec=0.0):
        super().draw(surface, camera)
        if not self.healed:
            # 열이 나는 표시: 머리 옆에 땀방울
            cam_x, cam_y = camera
            x = self.rect.centerx - cam_x + 12
            y = self.top - cam_y + 10 + int(math.sin(time_sec * 4) * 2)
            pygame.draw.circle(surface, (120, 190, 255), (x, y), 3)


# ---------------- 만들기 ----------------
OBJECT_CLASSES = {"well": Well, "trash": Trash, "rat": Rat, "flea": Flea,
                  "herb": Herb, "patient": Patient,
                  "gate": Gate}


def create_objects():
    """OBJECT_DATA로 오브젝트 목록을 만듭니다."""
    return [OBJECT_CLASSES[data["kind"]](data) for data in OBJECT_DATA]


# ======================================================================
# 7부 / 8부: 감염원 조사와 오래된 창고 (프롤로그 포함 index 7 / 8)
# ======================================================================
class InfectionClue(WorldObject):
    kind = "investigate"
    name = "감염원의 흔적"
    size = (28, 24)

    def __init__(self, data):
        super().__init__(data)
        self.image = None
        self.investigated = False

    def visible(self, game):
        return (game.quest.index == 7 and game.stats["spread"] >= HIGH_SPREAD_THRESHOLD
                and not self.investigated)

    def can_interact(self, game):
        return self.visible(game) and game.quest.wants(self.quest_event, self.id)

    def interact_text(self, game):
        return f"{self.name}: 조사하기"

    def button_label(self, game):
        return "조사"

    def interact(self, game):
        if not self.can_interact(game):
            return []
        self.investigated = True
        game.notify_quest(self)
        return [("", "찢어진 포대와 쥐의 발자국이 동쪽으로 이어진다."),
                (FAIRY, "마지막 감염원은 오래된 창고에 있어! 마을 남동쪽 약초꾼 옆 창고를 찾아 조사해 보자.")]

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.ellipse(surface, (76, 66, 48), r)
        pygame.draw.polygon(surface, (184, 155, 98),
                            [(r.left + 3, r.top + 4), (r.right - 4, r.top + 2),
                             (r.right - 1, r.bottom - 5), (r.left + 7, r.bottom - 2)])
        for dx, dy in ((8, 7), (16, 11), (10, 17)):
            pygame.draw.circle(surface, (46, 39, 31), (r.left + dx, r.top + dy), 2)
        pulse = int(2 * math.sin(time_sec * 3))
        pygame.draw.circle(surface, (139, 177, 67),
                           (r.right - 5, r.top + 5), 3 + pulse)


class ContaminatedGrain(WorldObject):
    kind = "grain"
    name = "오염된 곡물 자루"
    size = (26, 28)

    def __init__(self, data):
        super().__init__(data)
        self.image = None
        self.removed = False

    def visible(self, game):
        return (game.quest.index == 8 and not self.removed
                and not game.quest.wants("warehouse", "old_warehouse_part8"))

    def can_interact(self, game):
        return self.visible(game) and game.quest.wants(self.quest_event, self.id)

    def interact_text(self, game):
        return f"{self.name}: 치우기"

    def button_label(self, game):
        return "치우기"

    def interact(self, game):
        if not self.can_interact(game):
            return []
        self.removed = True
        game.notify_quest(self)
        return []

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.ellipse(surface, (153, 118, 65),
                            (r.left, r.top + 5, r.width, r.height - 5))
        pygame.draw.ellipse(surface, (83, 64, 39),
                            (r.left, r.top + 5, r.width, r.height - 5), 2)
        pygame.draw.polygon(surface, (185, 147, 85),
                            [(r.centerx - 5, r.top), (r.centerx + 5, r.top),
                             (r.centerx + 3, r.top + 8), (r.centerx - 3, r.top + 8)])
        pygame.draw.line(surface, (73, 51, 30),
                         (r.centerx - 5, r.top + 6), (r.centerx + 5, r.top + 6), 2)
        for dx, dy in ((7, 15), (17, 19), (11, 23)):
            pygame.draw.circle(surface, (93, 114, 48), (r.left + dx, r.top + dy), 3)


# 단서는 큰길 옆, 곡물은 약초꾼 옆 창고 앞의 통행 가능한 바닥에 배치한다.
OBJECT_DATA.extend([
    {"kind": "investigate", "id": "infection_clue_part7", "tile": (15, 17)},
    {"kind": "grain", "id": "warehouse_grain_part8", "tile": (34, 28)},
])
OBJECT_CLASSES.update({"investigate": InfectionClue, "grain": ContaminatedGrain})


class RecoveryClinic(WorldObject):
    kind = "recovery"
    name = "마을 진료소"
    size = (44, 36)

    def __init__(self, data):
        super().__init__(data)
        self.image = None
        self.finished = False

    def visible(self, game):
        return game.quest.index == 9 and not self.finished

    def can_interact(self, game):
        from settings import STATE_PLAYING
        return (self.visible(game) and game.state == STATE_PLAYING
                and game.dialogue is None)

    def interact_text(self, game):
        return "마을 진료소: 환자 돌보기"

    def button_label(self, game):
        return "치료"

    def interact(self, game):
        if not self.can_interact(game):
            return []

        spread_before = game.stats["spread"]
        # 이미 확산도가 10 이하인 채로 9부에 진입한 경우에도 이 행동으로
        # 회복 목표를 완료할 수 있어야 한다.
        if spread_before > 10:
            game.stats.change("spread", -10)
        spread_after = game.stats["spread"]

        if spread_after <= 10:
            self.finished = True
            game.notify_quest(self)
            game.check_quest()
            return []

        return [(FAIRY, "진료소에서 환자들을 돌보고 위생 수칙을 안내했어."),
                ("", f"확산도 {spread_before} → {spread_after}. 계속 치료하자!")]

    def draw(self, surface, camera, time_sec):
        """월드에 항상 그려진 진료소 이미지와 겹치지 않게 상호작용 도형은 숨긴다."""
        pass

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.polygon(surface, (126, 91, 73),
                            [(r.left, r.top + 13), (r.centerx, r.top),
                             (r.right, r.top + 13)])
        pygame.draw.rect(surface, (225, 219, 190),
                         (r.left + 4, r.top + 12, r.width - 8, r.height - 12))
        pygame.draw.rect(surface, (104, 76, 57),
                         (r.centerx - 5, r.bottom - 17, 10, 17))
        pygame.draw.rect(surface, (175, 65, 57),
                         (r.centerx - 2, r.top + 15, 4, 12))
        pygame.draw.rect(surface, (175, 65, 57),
                         (r.centerx - 6, r.top + 19, 12, 4))


OBJECT_DATA.append(
    # 왼쪽 위 파란 구역에 놓인 진료소의 문 앞
    {"kind": "recovery", "id": "village_clinic_part9", "tile": (5, 12)}
)
OBJECT_CLASSES.update({"recovery": RecoveryClinic})


class OldWarehouse(WorldObject):
    kind = "warehouse"
    name = "오래된 창고"
    size = (112, 64)

    def __init__(self, data):
        super().__init__(data)
        self.image = None
        self.discovered = False

    def visible(self, game):
        return game.quest.index == 8

    def can_interact(self, game):
        return (self.visible(game) and not self.discovered
                and game.quest.wants(self.quest_event, self.id))

    def interact_text(self, game):
        return "오래된 창고: 조사하기"

    def interact(self, game):
        if not self.can_interact(game):
            return []
        self.discovered = True
        game.notify_quest(self)
        return [(FAIRY, "이곳이 마지막 감염원이야! 창고 앞의 오염된 곡물 자루를 먼저 치우고, 창고를 청소하자.")]

    def draw(self, surface, camera, time_sec):
        """월드에 그려진 창고 이미지와 겹치지 않게 임시 도형은 숨긴다."""
        pass

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.polygon(surface, (91, 67, 49),
                            [(r.left, r.top + 19), (r.centerx, r.top),
                             (r.right, r.top + 19)])
        pygame.draw.rect(surface, (145, 119, 78),
                         (r.left + 5, r.top + 18, r.width - 10, r.height - 18))
        pygame.draw.rect(surface, (76, 57, 42),
                         (r.centerx - 11, r.bottom - 34, 22, 34))
        pygame.draw.rect(surface, (83, 68, 51), (r.left + 14, r.top + 29, 18, 15))
        pygame.draw.rect(surface, (83, 68, 51), (r.right - 32, r.top + 29, 18, 15))


class WarehouseCleanup(WorldObject):
    kind = "warehouse_clean"
    name = "창고 청소"
    size = (30, 24)

    def __init__(self, data):
        super().__init__(data)
        self.image = None
        self.cleaned = False

    def visible(self, game):
        return (game.quest.index == 8 and not self.cleaned
                and not game.quest.wants("grain", "warehouse_grain_part8"))

    def can_interact(self, game):
        return self.visible(game) and game.quest.wants(self.quest_event, self.id)

    def interact_text(self, game):
        return "창고: 청소하기"

    def button_label(self, game):
        return "청소"

    def interact(self, game):
        if not self.can_interact(game):
            return []
        self.cleaned = True
        game.notify_quest(self)
        return [("", "오염된 곡물 자루를 치우고 창고 안을 깨끗이 쓸었다."),
                (FAIRY, "제거 작업은 끝났어. 확산 상태를 확인해 보자.")]

    def draw_shape(self, surface, r, time_sec):
        pygame.draw.line(surface, (112, 78, 48),
                         (r.left + 7, r.top + 3), (r.centerx + 3, r.bottom - 7), 4)
        pygame.draw.line(surface, (190, 151, 83),
                         (r.centerx + 3, r.bottom - 10), (r.right - 2, r.bottom - 10), 4)
        pygame.draw.circle(surface, (224, 207, 135), (r.left + 5, r.top + 5), 2)


OBJECT_DATA.extend([
    # 약초꾼 엘자 옆의 오른쪽 아래 파란 구역과 그 정면
    {"kind": "warehouse", "id": "old_warehouse_part8", "tile": (35, 25)},
    {"kind": "warehouse_clean", "id": "warehouse_clean_part8", "tile": (36, 28)},
])
OBJECT_CLASSES.update({"warehouse": OldWarehouse, "warehouse_clean": WarehouseCleanup})
