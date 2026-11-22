# settings.py
# 게임 전체에서 공통으로 쓰는 설정값(상수)을 모아두는 파일입니다.

# ---------------- 화면 설정 ----------------
SCREEN_WIDTH = 960          # 창 가로 크기(픽셀) - PC 기준
SCREEN_HEIGHT = 640         # 창 세로 크기(픽셀) - PC 기준
# 웹(휴대폰)에서는 화면 비율에 맞춰 가로 크기를 자동으로 바꿉니다. (touch.web_screen_size)
PHONE_SCREEN_HEIGHT = 480   # 휴대폰에서는 세로를 줄여서 글자와 캐릭터가 더 크게 보이게 함
MIN_ASPECT = 4 / 3          # 화면 비율(가로÷세로) 최소값
MAX_ASPECT = 2.4            # 화면 비율 최대값 (이보다 길쭉한 화면은 양옆에 여백)
FPS = 60                    # 초당 프레임 수
TITLE = "흑사병의 마을 - 시간여행자와 책의 요정"

# ---------------- 타일 설정 ----------------
TILE_SIZE = 32              # 타일 한 칸의 크기(픽셀)

# ---------------- 플레이어 설정 ----------------
PLAYER_SPEED = 180          # 초당 이동 픽셀 수
PLAYER_SIZE = 24            # 플레이어 사각형 크기(타일보다 조금 작게 해야 길을 잘 지나감)

# ---------------- 캐릭터 그림 / NPC ----------------
SPRITE_SIZE = 32            # 캐릭터 그림 한 칸 크기 (충돌 사각형 24px보다 조금 큼)
ANIM_FPS = 8                # 걷기 애니메이션: 초당 프레임 수
NPC_SPEED = 45              # NPC가 어슬렁거리는 속도
NPC_WANDER_RADIUS = 64      # NPC가 집(처음 위치)에서 벗어날 수 있는 거리(픽셀)
INTERACT_RANGE = 48         # 이 거리(픽셀) 안에 있으면 E로 상호작용 가능
RAT_SPEED = 75              # 쥐가 달리는 속도 (플레이어 180보다 느리게 해야 잡을 수 있음)
RAT_WANDER_RADIUS = 96      # 쥐가 처음 위치에서 벗어날 수 있는 거리(픽셀)

# ---------------- 색상 (R, G, B) ----------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (120, 120, 120)
DARK_GRAY = (50, 50, 50)
RED = (200, 50, 50)
LIGHT_RED = (255, 110, 100)
YELLOW = (240, 210, 80)

COLOR_BG = (20, 18, 25)          # 배경색
COLOR_GRASS = (70, 110, 60)      # 풀밭(바닥)
COLOR_PATH = (150, 125, 90)      # 흙길
COLOR_WALL = (90, 80, 75)        # 돌담(벽)
COLOR_HOUSE = (120, 70, 50)      # 집(벽 취급)
COLOR_WATER = (50, 90, 160)      # 물(벽 취급 - 못 지나감)
COLOR_PLAYER = (80, 160, 230)    # 플레이어(시간여행자)
COLOR_FAIRY = (255, 230, 140)    # 책의 요정(빛나는 노란색)
COLOR_FAIRY_WING = (190, 230, 255)

# UI 색상
COLOR_UI_BG = (15, 12, 20)           # 상태바/대화창 배경
COLOR_UI_BORDER = (200, 170, 110)    # 테두리(낡은 금색)
COLOR_BAR_EMPTY = (60, 55, 65)       # 수치 막대의 빈 부분
COLOR_SPREAD = (210, 60, 60)         # 확산도(빨강)
COLOR_TRUST = (80, 170, 230)         # 신뢰도(파랑)
COLOR_SURVIVORS = (110, 200, 110)    # 생존자(초록)

# ---------------- UI 크기 ----------------
TOPBAR_HEIGHT = 64           # 상단 상태바 높이
DIALOGUE_HEIGHT = 150        # 하단 대화창 높이
DIALOGUE_SPEED = 40          # 대화 글자가 초당 몇 글자씩 나오는지 (타자기 효과)
TRAVEL_TIME = 3.0            # 프롤로그 시간여행 연출 시간(초)

# ---------------- 모바일 터치 조작 ----------------
# 위치는 화면 크기가 바뀌어도 맞도록 '왼쪽 아래 / 오른쪽 아래 모서리에서 떨어진 거리'로 적습니다.
JOYSTICK_RADIUS = 70                 # 가상 조이스틱 크기(반지름)
JOYSTICK_MARGIN = 130                # 손을 떼고 있을 때 조이스틱 가운데 ↔ 왼쪽 아래 모서리 거리
ACTION_BUTTON_MARGIN = 110           # 행동(대화/조사) 버튼 가운데 ↔ 오른쪽 아래 모서리 거리
ACTION_BUTTON_RADIUS = 56

# ---------------- 수치 (0~100) ----------------
# 게임 시작 시 수치. 시간에 따라 바뀌는 규칙은 stats.py에 있습니다.
START_SPREAD = 30            # 확산도: 100이 되면 배드 엔딩
START_TRUST = 20             # 신뢰도: 임무를 하거나 주민을 도우면 오름
START_SURVIVORS = 100        # 생존자: 0이 되면 배드 엔딩

SPREAD_INTERVAL = 7.0        # 플레이 중 이 시간(초)마다 확산도 +1 (대화 중에는 멈춤)
# 확산도가 높으면 생존자가 줄어듦: (확산도 이상, 생존자 1명이 줄어드는 간격(초))
# 높은 단계부터 적어야 함. 이 단계를 처음 넘을 때 경고 알림도 뜸
SURVIVOR_LOSS_LEVELS = [(90, 3.0), (70, 6.0), (50, 10.0)]

# 5부 주민 설득
PERSUADE_TRUST = 50          # 신뢰도가 이 값 이상이어야 주민이 설득을 들어줌
PERSUADE_TRUST_GAIN = 5      # 설득에 성공하면 신뢰도 +
PERSUADE_WRONG_SPREAD = 2    # 틀린 말을 고르면 확산도 + (시간을 버린 셈)

# 7~8부 감염원 처리
HIGH_SPREAD_THRESHOLD = 70           # 7부 진입 시 조사 단계를 진행하는 기준
REMOVAL_FAILURE_THRESHOLD = 75       # 이 확산도 이상에서 제거를 마치면 실패
REMOVAL_FAILURE_SPREAD_GAIN = 20     # 제거 실패 시 확산도 증가량

# ---------------- 게임 상태 (상태 머신) ----------------
# 게임은 항상 이 중 하나의 상태에 있습니다.
STATE_TITLE = "TITLE"          # 타이틀 화면
STATE_PROLOGUE = "PROLOGUE"    # 프롤로그 (중세시대로 이동, 책의 요정 등장)
STATE_PLAYING = "PLAYING"      # 실제 플레이 중
STATE_DIALOGUE = "DIALOGUE"    # 대화창이 열린 상태
STATE_MENU = "MENU"            # ESC 메뉴 (설정/인벤토리)
STATE_ENDING = "ENDING"        # 엔딩 화면

# ---------------- 한글 폰트 ----------------
# pygame 기본 폰트는 한글이 깨지므로 윈도우의 '맑은 고딕'을 우선 사용합니다.
FONT_NAMES = ["malgungothic", "applegothic", "nanumgothic", "notosanscjkkr"]
