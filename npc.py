# npc.py
# 마을 주민(NPC)을 담당하는 파일입니다.
# 주민 정보는 아래 NPC_DATA 목록(데이터)에 적고, NPC 클래스가 그 데이터로 주민을 만듭니다.
# (우물, 쓰레기, 쥐 같은 상호작용 오브젝트는 STEP 6에서 추가합니다)

import math
import random
from settings import (TILE_SIZE, NPC_SPEED, NPC_WANDER_RADIUS,
                      PERSUADE_TRUST, PERSUADE_TRUST_GAIN, PERSUADE_WRONG_SPREAD)
from character import Character
from quest import FAIRY, PERSUASIONS

# ---------------- 주민 데이터 ----------------
#   id     : 고유 이름 (퀘스트에서 누구와 대화했는지 셀 때도 사용)
#            4×4 걷기 시트 assets/characters/<id>.png가 있으면 그 그림을 먼저 씀
#   sprite : 시트가 없을 때 쓰는 정면 그림 1장 (assets 폴더 기준 경로)
#   name   : 화면에 보이는 이름
#   tile   : 처음 서 있는 위치 (열, 행) - world.py 맵 기준
#   color  : 그림이 없을 때 쓰는 색
#   lines  : E로 말을 걸었을 때 하는 대사 (순서대로)
#   wander : True면 집 근처를 어슬렁거림
NPC_DATA = [
    {"id": "hans", "name": "대장장이 한스", "tile": (5, 5), "sprite": "characters/trimmed/npc_06_r2_c2.png", "color": (150, 100, 70),
     "wander": True,
     "lines": ["요즘 쥐가 부쩍 늘었어. 대장간 구석구석에 쥐똥 천지야.",
               "고양이라도 한 마리 있으면 좋겠는데 말이지."]},
    {"id": "marta", "name": "빵집 마르타", "tile": (12, 5), "sprite": "characters/trimmed/npc_02_r1_c2.png", "color": (220, 150, 160),
     "wander": True,
     "lines": ["어서 와요, 여행자님. 처음 보는 얼굴이네요.",
               "그런데 요즘 우물물 냄새가 이상해요. 그래도 다들 그냥 마시지만요..."]},
    {"id": "klaus", "name": "촌장 클라우스", "tile": (26, 5), "sprite": "characters/trimmed/npc_03_r1_c3.png", "color": (170, 140, 200),
     "wander": False,
     "lines": ["흠, 외지인인가. 요즘 같은 때에 마을을 돌아다니다니 용감하군.",
               "옆 마을에서 사람들이 열병으로 쓰러지고 있다는 소문이 돌고 있네.",
               "부디 우리 마을만은 무사해야 할 텐데..."]},
    {"id": "benedikt", "name": "신부 베네딕트", "tile": (27, 12), "sprite": "characters/trimmed/npc_10_r3_c2.png", "color": (60, 60, 70),
     "wander": False,
     "lines": ["어린 양이여, 이 병은 하늘이 내린 벌이라고들 하지요.",
               "기도로 이겨낼 수 있을 겁니다... 아마도요."]},
    {"id": "otto", "name": "경비병 오토", "tile": (9, 18), "sprite": "characters/trimmed/npc_05_r2_c1.png", "color": (130, 130, 150),
     "wander": True,
     "lines": ["멈추시오! ...아, 그냥 지나가는 사람이군.",
               "요즘 외지 상인들이 성문으로 계속 들어오고 있소. 짐에서 쥐가 튀어나오기도 하더군."]},
    {"id": "elsa", "name": "약초꾼 엘자", "tile": (30, 26), "sprite": "characters/trimmed/npc_09_r3_c1.png", "color": (90, 160, 90),
     "wander": True,
     "lines": ["마을 가장자리 풀숲에 쓸 만한 약초가 자라요.",
               "열을 내리는 데 좋은 풀도 있죠. 필요하면 언제든 물어보세요."]},
]


class NPC(Character):
    def __init__(self, data):
        col, row = data["tile"]
        # 타일 번호 → 타일 가운데 픽셀 좌표
        x = col * TILE_SIZE + TILE_SIZE // 2
        y = row * TILE_SIZE + TILE_SIZE // 2
        super().__init__(x, y, data["color"], f"characters/{data['id']}.png", data.get("sprite"))

        self.id = data["id"]
        self.name = data["name"]
        self.lines = data["lines"]
        self.wanders = data.get("wander", False)
        self.home = (x, y)          # 어슬렁거릴 때 기준 위치
        self.quest_event = "talk"   # 퀘스트에 알릴 행동 이름 (quest.py 챕터 목표의 "event")
        self.quest_events = ("talk", "persuade")   # 이 주민과 관련된 퀘스트 행동들 ('!' 표시용)
        self.persuaded = False      # 5부에서 설득했는지

        # 어슬렁거리기: 잠깐 걷고 → 잠깐 쉬고를 반복
        self.walk_dir = (0, 0)
        self.timer = random.uniform(1.0, 3.0)

    # ---------------- 상호작용 ----------------
    # objects.py의 오브젝트들과 같은 형식의 메서드를 가집니다. (main.py가 똑같이 처리)
    solid = True          # 플레이어가 주민을 통과할 수 없음

    def visible(self, game):
        return True

    def can_interact(self, game):
        return True

    def can_persuade(self, game):
        """지금 이 주민을 설득해야 하는지 (설득 대사가 있는 주민만)"""
        return self.id in PERSUASIONS and game.quest.wants("persuade", self.id)

    def interact_text(self, game):
        """머리 위 [E] 안내에 보여줄 글자"""
        if self.can_persuade(game):
            return f"{self.name}: 설득하기"
        return f"{self.name}: 대화하기"

    def button_label(self, game):
        """휴대폰 행동 버튼에 보여줄 글자"""
        return "설득" if self.can_persuade(game) else "대화"

    def interact(self, game):
        """
        E를 눌렀을 때 호출됩니다. 플레이어를 바라보고, 퀘스트에 알리고, 대사 목록을 돌려줍니다.
        돌려주는 형식: [(말하는 사람, 대사), ...]  → ui.Dialogue에 그대로 넣음
        """
        self.face_towards(game.player.rect)
        self.walk_dir = (0, 0)
        if self.can_persuade(game):
            return self.persuade(game)
        if self.persuaded:
            return [(self.name, PERSUASIONS[self.id]["after"])]
        game.notify_quest(self)
        if self.id == "elsa":
            lukas = next((obj for obj in game.objects
                          if getattr(obj, "id", None) == "lukas"), None)
            if lukas is not None and getattr(lukas, "healed", False):
                return [(self.name, "루카스는 지금 치료소에 있어요. 안정을 취하면 곧 나아질 거예요.")]
        return [(self.name, line) for line in self.lines]

    # ---------------- 5부: 설득 ----------------
    def persuade(self, game):
        """설득 대화: 주민의 말 → 선택지 (신뢰도가 부족하면 거절)"""
        data = PERSUASIONS[self.id]
        if game.stats["trust"] < PERSUADE_TRUST:
            return [(self.name, data["refuse"]),
                    (FAIRY, f"신뢰도가 {PERSUADE_TRUST} 이상이어야 내 말을 들어줄 거야. "
                            "마을 사람들을 더 도와서 믿음을 얻자!")]
        choice = {"speaker": "나", "text": "뭐라고 설득할까?",
                  "choices": [option["text"] for option in data["options"]],
                  "on_choose": self.on_persuade_choice}
        return [(self.name, line) for line in data["before"]] + [choice]

    def on_persuade_choice(self, game, index):
        """선택지를 골랐을 때: 맞으면 설득 성공, 틀리면 확산도가 오르고 다시 시도"""
        data = PERSUASIONS[self.id]
        option = data["options"][index]
        if option["correct"]:
            self.persuaded = True
            game.stats.change("trust", PERSUADE_TRUST_GAIN)
            game.notify_quest(self, "persuade")
            return [(self.name, line) for line in data["success"]] +                    [("", f"{self.name}을(를) 설득했다! (신뢰도 +{PERSUADE_TRUST_GAIN})")]
        game.stats.change("spread", PERSUADE_WRONG_SPREAD)
        return [(self.name, option["reply"]),
                ("", f"설득에 실패했다... 시간이 흘러 병이 조금 더 퍼졌다. (확산도 +{PERSUADE_WRONG_SPREAD})"),
                (FAIRY, "다시 말을 걸어서 다른 말로 설득해 보자. 병이 진짜로 어떻게 퍼지는지 떠올려 봐!")]

    # ---------------- 매 프레임 갱신 ----------------
    def update(self, dt, obstacles):
        """어슬렁거리기: 걷는 시간과 쉬는 시간을 번갈아 가며, 집에서 너무 멀어지지 않게 합니다."""
        if not self.wanders:
            return

        self.timer -= dt
        if self.timer <= 0:
            if self.walk_dir != (0, 0):
                # 걷다가 → 쉬기
                self.walk_dir = (0, 0)
                self.timer = random.uniform(1.5, 4.0)
            else:
                # 쉬다가 → 걷기 (집에서 멀면 집 쪽으로, 아니면 아무 방향)
                self.walk_dir = self._choose_direction()
                self.timer = random.uniform(0.4, 1.2)

        moved = False
        if self.walk_dir != (0, 0):
            self.facing = self.walk_dir
            moved = self.move(*self.walk_dir, NPC_SPEED, dt, obstacles)
            if not moved:
                self.walk_dir = (0, 0)   # 벽에 막히면 그 자리에서 멈춤
        self.moving = moved
        self.anim.update(dt, moved, self.facing)

    def _choose_direction(self):
        dx = self.home[0] - self.rect.centerx
        dy = self.home[1] - self.rect.centery
        if math.hypot(dx, dy) > NPC_WANDER_RADIUS:
            # 너무 멀리 왔으면 집 쪽으로
            if abs(dx) > abs(dy):
                return (1 if dx > 0 else -1, 0)
            return (0, 1 if dy > 0 else -1)
        return random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])


def create_npcs():
    """NPC_DATA로 주민 목록을 만듭니다."""
    return [NPC(data) for data in NPC_DATA]
