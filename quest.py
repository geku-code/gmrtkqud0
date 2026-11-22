# quest.py
# 프롤로그와 1부~9부 챕터(퀘스트)를 데이터(리스트/딕셔너리)로 관리하는 파일입니다.
# if문을 길게 쓰는 대신, 챕터 정보를 아래 목록에 적어두고 번호로 꺼내 씁니다.
# 퀘스트 진행(몇 개 했는지, 다 했는지, 보상)은 아래쪽 QuestManager가 담당합니다.

# ---------------- 챕터 목록 ----------------
# 리스트의 순서 = 챕터 번호 (0번 = 프롤로그)
#   name           : 상태바에 보이는 챕터 이름
#   objective      : 상태바에 보이는 목표 (뒤에 진행도가 자동으로 붙음)
#   goals          : 완료 조건 목록. 모두 채우면 챕터 완료
#       event  : 어떤 행동을 셀지 ("talk" = 주민과 대화. 우물/쥐 등은 STEP 6~8에서 추가)
#       count  : 몇 번 해야 하는지
#       label  : 목표가 여러 개일 때 진행도 앞에 붙는 짧은 이름
#       targets: (선택) 이 대상들만 셈. 없으면 같은 행동을 하는 누구든 셈
#       같은 대상(예: 같은 주민)은 한 번만 셉니다.
#   reward         : 완료하면 바뀌는 수치 {"trust": +10, "spread": -5 ...}
#   complete_lines : 완료했을 때 나오는 대사
#   intro_lines    : 이 챕터가 시작될 때 나오는 대사 (앞 챕터 완료 대사 바로 뒤에 이어짐)
FAIRY = "책의 요정"

CHAPTERS = [
    {"name": "프롤로그", "objective": "책의 요정의 이야기를 듣자", "goals": []},

    {"name": "1부: 마을 조사", "objective": "마을 주민 5명과 이야기하기",
     "goals": [{"event": "talk", "count": 5}],
     "reward": {"trust": 10},
     "complete_lines": [
         (FAIRY, "잘했어! 이제 마을에 무슨 일이 일어나고 있는지 조금 알겠지?"),
         (FAIRY, "쥐가 늘었고, 우물물 냄새가 이상하고, 외지 상인들이 짐을 들고 성문으로 들어오고 있어."),
         (FAIRY, "모두 흑사병이 퍼지기 딱 좋은 조건이야. 주민들도 너를 조금씩 믿기 시작했어."),
     ]},

    {"name": "2부: 위생 관리", "objective": "우물 3곳 청소, 쓰레기 더미 5개 치우기",
     "goals": [{"event": "well", "count": 3, "label": "우물"},
               {"event": "trash", "count": 5, "label": "쓰레기"}],
     "reward": {"trust": 10, "spread": -5},
     "intro_lines": [
         (FAIRY, "먼저 마을을 깨끗하게 만들자. 더러운 물과 쓰레기는 쥐와 병을 불러 모아."),
         (FAIRY, "우물 3곳을 청소하고, 쓰레기 더미 5개를 치워 줘!"),
     ],
     "complete_lines": [(FAIRY, "마을이 한결 깨끗해졌어! 쥐들이 숨을 곳이 줄었을 거야.")]},

    {"name": "3부: 쥐와 벼룩 관리", "objective": "성문을 조사해 쥐 6마리와 벼룩 10마리 잡기",
     "goals": [{"event": "rat", "count": 6, "label": "쥐"},
               {"event": "flea", "count": 10, "label": "벼룩"}],
     "reward": {"trust": 5, "spread": -10},
     "intro_lines": [
         (FAIRY, "흑사병균을 가진 쥐의 피를 벼룩이 빨면, 그 벼룩도 병균을 품게 돼."),
         (FAIRY, "감염된 쥐가 죽으면 굶주린 벼룩은 새로운 숙주를 찾아 사람에게 뛰어들고, 물어서 병을 옮길 수 있어."),
         (FAIRY, "아까 성문 짐 사이에서 뭔가 꾸물거렸지? 성문 하나를 골라 수레의 짐을 조사해 보자!"),
         (FAIRY, "숨어 있는 쥐와 벼룩이 나오면 마을로 흩어지기 전에 모두 잡아 줘!"),
     ],
     "complete_lines": [(FAIRY, "쥐와 벼룩을 모두 줄였어! 병이 사람에게 옮겨 갈 길도 크게 줄었을 거야.")]},

    {"name": "4부: 첫 환자", "objective": "약초를 찾아 아픈 주민에게 가져가기",
     "goals": [{"event": "herb", "count": 1, "label": "약초"},
               {"event": "patient", "count": 1, "label": "환자"}],
     "reward": {"trust": 15},
     "intro_lines": [(FAIRY, "큰일이야, 첫 환자가 생겼어! 마을 왼쪽 위 진료소 앞의 루카스가 열이 펄펄 끓고 있어."),
                     (FAIRY, "약초꾼 엘자가 말한 약초를 찾아서 가져다주자. 마을 동쪽 아래 풀숲을 찾아봐!")],
     "complete_lines": [(FAIRY, "열이 조금 내렸어. 네가 사람을 살렸다는 소문이 퍼지고 있어!")]},

    {"name": "5부: 주민 설득", "objective": "주민 3명 설득하기 (신뢰도 50 이상 필요)",
     "goals": [{"event": "persuade", "count": 3, "targets": ["benedikt", "klaus", "marta"]}],
     "reward": {"trust": 10, "spread": -5},
     "intro_lines": [(FAIRY, "아직도 병의 진짜 원인을 모르는 사람들이 있어. 이대로면 병이 계속 퍼질 거야."),
                     (FAIRY, "신부 베네딕트, 촌장 클라우스, 빵집 마르타를 찾아가서 설득해 줘!"),
                     (FAIRY, "무슨 말을 하느냐가 중요해. 네가 아는 미래의 지식을 떠올려 봐.")],
     "complete_lines": [(FAIRY, "주민들이 네 말을 따르기 시작했어!")]},

    {"name": "6부: 마을 봉쇄", "objective": "마을 성문 3곳 닫기",
     "goals": [{"event": "gate", "count": 3}],
     "reward": {"spread": -10},
     "intro_lines": [(FAIRY, "촌장님이 허락했어! 외지 상인들의 짐에 숨은 쥐가 더 들어오지 못하게 하자."),
                     (FAIRY, "큰길 끝 북쪽, 서쪽, 동쪽에 성문이 있어. 3곳을 모두 닫아 줘!")],
     "complete_lines": [(FAIRY, "성문을 모두 닫았어. 이제 밖에서 들어오는 병은 막았어!")]},

    {"name": "7부: 최악의 날", "objective": "감염원의 흔적 조사하기",
     "goals": [{"event": "investigate", "count": 1}],
     "reward": {"trust": 5},
     "intro_lines": [(FAIRY, "성문을 닫았는데도 환자가 늘고 있어... 마을 안 어딘가에 감염원이 남아 있는 게 틀림없어!")],
     "complete_lines": [(FAIRY, "찾았어! 단서가 오래된 창고를 가리키고 있어.")]},

    {"name": "8부: 마지막 감염원", "objective": "오래된 창고의 감염원 제거하기",
     "goals": [{"event": "grain", "count": 1}],
     "reward": {"spread": -15},
     "intro_lines": [(FAIRY, "오래된 창고를 찾아 오염된 곡물 자루를 치우고 내부까지 깨끗이 청소하자!")],
     "complete_lines": [(FAIRY, "마지막 감염원을 없앴어! 이제 남은 환자들만 돌보면 돼.")]},

    # 진료소에서 확산도를 10 이하로 낮춰 회복 목표를 완료해야 결과를 계산합니다.
    {"name": "9부: 마을 회복", "objective": "남은 환자 치료하기 (확산도 10 이하)",
     "goals": [{"event": "recovery", "count": 1}],
     "intro_lines": [(FAIRY, "마지막이야. 남은 환자들을 치료해서 확산도를 10 이하로 낮추자!")]},
]

# ---------------- 확산도 경고 ----------------
# 확산도가 이 숫자를 처음 넘으면 화면 위에 빨간 경고가 뜹니다. (규칙은 stats.py)
SPREAD_WARNINGS = {
    50: "확산도 50! 마을에 환자가 생기기 시작했어. 생존자가 줄어들고 있어!",
    70: "확산도 70! 병이 빠르게 번지고 있어. 서둘러!",
    90: "확산도 90! 이대로면 마을이 무너져. 지금 바로 막아야 해!",
}

# ---------------- 엔딩 ----------------
# 엔딩 화면에 보여줄 내용. (좋은 엔딩들은 STEP 9에서 추가합니다)
#   title : 큰 제목 / color : 제목 색 (R, G, B) / lines : 설명 문장들
ENDINGS = {
    "bad": {
        "title": "배드 엔딩: 검은 죽음",
        "color": (210, 60, 60),
        "lines": [
            "흑사병이 마을 전체를 덮쳤다.",
            "역사책에 적힌 그대로, 마을은 텅 비어 버렸다.",
            "책의 요정: \"괜찮아... 다시 해 보자. 이번엔 더 빨리 움직이는 거야!\"",
        ],
    },
}

# ---------------- 5부: 주민 설득 ----------------
# 주민 id → 설득 내용. 말을 걸면 before 대사 → 선택지 → 고른 답에 따라 결과
#   options: 고를 수 있는 말 3개. correct=True가 정답, reply = 틀렸을 때 주민의 대답
#   success: 설득에 성공했을 때 대사 / after: 설득한 뒤 다시 말을 걸면 하는 말
#   refuse : 신뢰도가 부족할 때 하는 말
PERSUASIONS = {
    "benedikt": {
        "before": ["이 병은 죄 많은 우리에게 내린 하늘의 벌입니다.",
                   "모두 성당에 모여 함께 기도해야 해요. 아픈 이들도 빠짐없이요."],
        "options": [
            {"text": "향을 더 많이 피우면 나쁜 공기가 물러갈 거예요.", "correct": False,
             "reply": "향은 이미 충분히 피우고 있습니다... 그런데도 사람들이 쓰러지는군요."},
            {"text": "병은 쥐와 벼룩이 옮겨요. 사람이 모이면 더 빨리 번지니, 아픈 분들은 따로 돌봐 주세요.",
             "correct": True},
            {"text": "기도는 아무 소용 없어요! 신부님 말씀은 다 틀렸어요.", "correct": False,
             "reply": "무례하군요! 그런 말을 하는 사람의 이야기는 듣고 싶지 않습니다."},
        ],
        "success": ["쥐와 벼룩이라... 그러고 보니 쓰러진 이들의 집엔 쥐가 들끓었지요.",
                    "알겠습니다. 당분간 큰 모임은 줄이고, 아픈 이들은 따로 모셔 돌보겠습니다."],
        "after": "아픈 이들은 성당 뒤뜰에서 따로 돌보고 있습니다. 함께 기도는 하되, 떨어져서요.",
        "refuse": "외지인의 말을 어찌 믿겠습니까... 조금 더 지켜보지요.",
    },
    "klaus": {
        "before": ["곧 장날이라 외지 상인들이 몰려올 걸세.",
                   "장사를 막으면 마을이 굶어. 촌장으로서 그럴 순 없네."],
        "options": [
            {"text": "상인들을 모두 쫓아내고 다시는 못 오게 해요.", "correct": False,
             "reply": "그러면 겨울을 어떻게 나란 말인가! 말도 안 되는 소리일세."},
            {"text": "병은 나쁜 공기 탓이니 바람이 바뀔 때까지 기다리면 돼요.", "correct": False,
             "reply": "바람이라... 그걸 기다리는 사이에 옆 마을은 이미 무너졌다네."},
            {"text": "상인들 짐 속의 쥐와 벼룩이 병을 옮겨요. 잠시만 성문을 닫고, 물건은 성문 밖에서 받아요.",
             "correct": True},
        ],
        "success": ["짐 속의 쥐라... 옆 마을도 장이 선 뒤에 병이 돌았다고 했지.",
                    "좋네. 병이 잦아들 때까지 성문을 닫도록 하지. 장은 성문 밖에서 열고."],
        "after": "성문 일은 자네에게 맡기겠네. 마을을 부탁하네.",
        "refuse": "자네를 아직 잘 모르겠네. 마을을 위해 무얼 했는지 먼저 보여 주게.",
    },
    "marta": {
        "before": ["우물물이 좀 탁해도 다들 그냥 마셔요. 빵 반죽에도 쓰고요.",
                   "물을 버리면 어디서 새로 길어 오겠어요?"],
        "options": [
            {"text": "물은 꼭 끓여서 쓰고, 빵을 만들기 전엔 손을 깨끗이 씻어 주세요.", "correct": True},
            {"text": "물은 괜찮아요. 신경 쓰지 마세요.", "correct": False,
             "reply": "그렇죠? 그런데 왜 손님들이 하나둘 안 보이는 걸까요..."},
            {"text": "물에 장미 꽃잎을 띄우면 깨끗해진대요.", "correct": False,
             "reply": "꽃잎이요? 향은 좋겠지만... 그걸로 될까요?"},
        ],
        "success": ["끓이고, 손 씻기... 생각보다 어렵지 않네요!",
                    "손님들에게도 꼭 알려 줄게요. 고마워요, 여행자님."],
        "after": "물은 꼭 끓여서 쓰고 있어요. 빵 맛도 그대로랍니다!",
        "refuse": "음... 처음 보는 분 말만 듣고 바꾸기는 좀 그렇네요.",
    },
}

# 수치 이름 (보상 안내 문구에 사용)
STAT_NAMES = {"spread": "확산도", "trust": "신뢰도", "survivors": "생존자"}

# ---------------- 프롤로그 대사 ----------------
# (말하는 사람, 대사) 순서대로 나옵니다. 말하는 사람이 ""이면 해설(내레이션)입니다.
PROLOGUE_DIALOGUE = [
    ("", "...눈을 떠 보니 낯선 흙냄새와 연기 냄새가 났다."),
    ("???", "일어났구나! 여기야, 여기!"),
    ("책의 요정", "나는 '책의 요정'이야. 네가 펼친 역사책 속에 살고 있지."),
    ("책의 요정", "여기는 1347년, 중세 유럽의 작은 마을이야."),
    ("책의 요정", "곧 이 마을에 흑사병이 퍼지기 시작해. 역사책에는 마을 사람 대부분이 쓰러졌다고 적혀 있어."),
    ("책의 요정", "하지만 너는 미래에서 왔잖아. 병이 쥐와 벼룩, 더러운 환경 때문에 퍼진다는 걸 알고 있지."),
    ("책의 요정", "그 지식으로 9개의 장을 하나씩 해결해서, 이 마을의 역사를 바꿔 줘!"),
    ("책의 요정", "화면 위의 막대를 잘 봐. 빨간 막대는 '확산도'야. 100이 되면... 모든 게 끝이야."),
    ("책의 요정", "파란 막대는 주민들이 너를 믿는 '신뢰도', 초록 막대는 살아남은 '생존자'야."),
    ("책의 요정", "W A S D(또는 방향키)로 움직이고, E 키로 주민과 이야기하거나 물건을 조사할 수 있어."),
    ("책의 요정", "먼저 마을을 둘러보며 주민들과 이야기해 보자. 무슨 일이 일어나고 있는지 알아야 하니까!"),
]


# ======================================================================
# 퀘스트 진행 관리
# ======================================================================
class QuestManager:
    """
    지금 챕터의 목표 진행도를 세고, 다 채웠는지 확인하는 클래스입니다.
    게임 쪽에서는 행동할 때마다 notify("talk", "hans")처럼 알려주기만 하면 됩니다.
    """

    def __init__(self):
        self.index = 0          # 지금 챕터 번호 (0 = 프롤로그)
        self.counts = []        # 목표마다 지금까지 한 횟수
        self.done = set()       # 이미 센 (event, 대상) 묶음 → 같은 대상은 한 번만 셈
        self.start(0)

    @property
    def chapter(self):
        return CHAPTERS[self.index]

    @property
    def goals(self):
        return self.chapter.get("goals", [])

    def start(self, index):
        """index번 챕터를 시작합니다. (진행도 초기화)"""
        self.index = index
        self.counts = [0] * len(self.goals)
        self.done = set()

    def go_to(self, index):
        """원하는 챕터로 이동하며 그 챕터의 진행도를 새로 시작한다."""
        self.start(index)

    def restart(self):
        """현재 챕터의 진행도를 초기화하고 다시 시작한다."""
        self.start(self.index)

    def wants(self, event, target=None):
        """이 행동(대상)이 지금 챕터 목표에 아직 필요한지 → NPC 머리 위 '!' 표시에 사용"""
        if (event, target) in self.done:
            return False
        return any(self._matches(g, event, target) and self.counts[i] < g["count"]
                   for i, g in enumerate(self.goals))

    @staticmethod
    def _matches(goal, event, target):
        """이 목표가 이 행동(대상)을 세는지"""
        if goal["event"] != event:
            return False
        return "targets" not in goal or target in goal["targets"]

    def notify(self, event, target=None):
        """
        행동을 했다고 알려줍니다. 목표에 해당하면 1 올리고 True를 돌려줍니다.
        target = 대상 이름 (같은 대상은 한 번만 셈. None이면 매번 셈)
        """
        if not self.wants(event, target):
            return False
        for i, g in enumerate(self.goals):
            if self._matches(g, event, target) and self.counts[i] < g["count"]:
                self.counts[i] += 1
                if target is not None:
                    self.done.add((event, target))
                return True
        return False

    def is_complete(self):
        """목표가 있고, 모두 채웠는지"""
        return bool(self.goals) and all(
            c >= g["count"] for c, g in zip(self.counts, self.goals))

    def progress_text(self):
        """진행도 글자. 예) 2/5  또는  우물 1/3, 쓰레기 0/5  (목표가 없으면 "")"""
        if len(self.goals) == 1:
            return f"{self.counts[0]}/{self.goals[0]['count']}"
        return ", ".join(f"{g['label']} {c}/{g['count']}" for c, g in zip(self.counts, self.goals))

    def objective_text(self):
        """상태바에 보여줄 목표 + 진행도. 예) 마을 주민 5명과 이야기하기 (2/5)"""
        progress = self.progress_text()
        return self.chapter["objective"] + (f" ({progress})" if progress else "")

    def complete(self, next_index=None):
        """
        챕터를 완료하고 다음 챕터로 넘어갑니다.
        돌려주는 값: (보상 dict, 보여줄 대사 목록)
        """
        reward = self.chapter.get("reward", {})
        lines = list(self.chapter.get("complete_lines", []))
        if reward:
            changes = ", ".join(f"{STAT_NAMES[k]} {v:+d}" for k, v in reward.items())
            lines.append(("", f"{self.chapter['name']} 완료! ({changes})"))
        destination = self.index + 1 if next_index is None else next_index
        if destination < len(CHAPTERS):
            self.go_to(destination)
            lines += self.chapter.get("intro_lines", [])
        return reward, lines


ENDINGS.update({
    "perfect": {
        "title": "완벽한 방어",
        "color": (75, 160, 105),
        "lines": [
            "확산도를 낮추고 마을 사람들의 믿음과 생존자도 지켜 냈다.",
            "이 마을은 흑사병의 참혹한 역사를 바꾸어 냈다.",
            "책의 요정: \"네가 이 마을의 미래를 완전히 바꿨어!\"",
        ],
    },
    "friend": {
        "title": "마을의 친구",
        "color": (80, 145, 190),
        "lines": [
            "주민들은 네가 알려 준 지식을 믿고 함께 병을 이겨 냈다.",
            "마을 사람들은 너를 오래도록 기억할 것이다.",
            "책의 요정: \"네가 심은 지식이 이 마을을 지켜 냈어.\"",
        ],
    },
    "return": {
        "title": "일반 귀환",
        "color": (150, 155, 125),
        "lines": [
            "확산도가 낮아지자 마을은 조금씩 안정을 되찾았다.",
            "모든 것을 구할 수는 없었지만, 너의 노력은 사람들을 살렸다.",
            "책의 요정: \"이제 안심하고 돌아가도 돼. 정말 수고했어.\"",
        ],
    },
})


CHAPTERS[7]["objective"] = "감염원의 흔적을 따라 오래된 창고 찾기"
CHAPTERS[8]["objective"] = "약초꾼 옆 창고 발견 → 곡물 제거 → 창고 청소"
CHAPTERS[8]["goals"][0]["label"] = "곡물"
CHAPTERS[8]["goals"].insert(0, {"event": "warehouse", "count": 1, "label": "발견"})
CHAPTERS[8]["goals"].append({"event": "warehouse_clean", "count": 1, "label": "창고"})


def recovery_ending(stats):
    """회복 완료 시 좋은 엔딩을 높은 조건부터 하나만 선택한다."""
    if stats["spread"] > 10 or stats.is_lost():
        return None
    if stats["trust"] >= 80 and stats["survivors"] >= 90:
        return "perfect"
    if stats["trust"] >= 70:
        return "friend"
    return "return"
