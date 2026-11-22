# ui.py
# 글자 출력, 타이틀 화면, 상단 상태바, 대화창 등 화면 UI를 그리는 파일입니다.

import math
import os
import pygame
from settings import (FONT_NAMES, WHITE, YELLOW, GRAY, BLACK, LIGHT_RED, COLOR_BG,
                      COLOR_UI_BG, COLOR_UI_BORDER, COLOR_BAR_EMPTY,
                      COLOR_SPREAD, COLOR_TRUST, COLOR_SURVIVORS,
                      COLOR_FAIRY, COLOR_FAIRY_WING,
                      TOPBAR_HEIGHT, DIALOGUE_HEIGHT, DIALOGUE_SPEED, ANIM_FPS)
from assets import load_sheet, ASSET_DIR

_font_cache = {}


# 게임에 함께 들어 있는 한글 폰트 (웹/휴대폰에는 윈도우 폰트가 없으므로 꼭 필요)
BUNDLED_FONT = os.path.join(ASSET_DIR, "fonts", "NanumGothic.ttf")


def get_font(size):
    """한글이 나오는 폰트를 크기별로 만들어서 재사용합니다."""
    if size not in _font_cache:
        font_path = BUNDLED_FONT if os.path.exists(BUNDLED_FONT) else None
        # 들어 있는 폰트가 없으면 컴퓨터에 설치된 한글 폰트를 찾음
        for name in ([] if font_path else FONT_NAMES):
            font_path = pygame.font.match_font(name)
            if font_path:
                break
        # 한글 폰트를 못 찾으면 기본 폰트 사용 (이 경우 한글이 깨질 수 있음)
        _font_cache[size] = pygame.font.Font(font_path, size)
    return _font_cache[size]


def draw_text(surface, text, size, color, center):
    """글자를 지정한 중심 위치에 그립니다."""
    img = get_font(size).render(text, True, color)
    rect = img.get_rect(center=center)
    surface.blit(img, rect)


def draw_text_left(surface, text, size, color, topleft):
    """글자를 왼쪽 위 기준으로 그립니다."""
    img = get_font(size).render(text, True, color)
    surface.blit(img, topleft)


def wrap_text(text, size, max_width):
    """
    긴 문장을 max_width(픽셀)에 맞게 여러 줄로 나눕니다.
    띄어쓰기 단위로 나누고, 단어 하나가 너무 길면 글자 단위로 자릅니다.
    """
    font = get_font(size)
    lines, current = [], ""
    for word in text.split(" "):
        test = word if current == "" else current + " " + word
        if font.size(test)[0] <= max_width:
            current = test
            continue
        if current:
            lines.append(current)
        # 단어 자체가 한 줄보다 길면 글자 단위로 자르기
        current = ""
        for ch in word:
            if font.size(current + ch)[0] > max_width:
                lines.append(current)
                current = ""
            current += ch
    if current:
        lines.append(current)
    return lines


def draw_panel(surface, rect, alpha=230):
    """반투명한 어두운 상자 + 금색 테두리 (상태바, 대화창 공통)"""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*COLOR_UI_BG, alpha))
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, COLOR_UI_BORDER, rect, 2, border_radius=6)


# ======================================================================
# 타이틀 화면
# ======================================================================
def draw_title_screen(surface, time_sec, selected_mode="normal"):
    """타이틀 화면을 그립니다. time_sec는 깜빡임 효과에 사용합니다."""
    surface.fill(COLOR_BG)
    w, h = surface.get_size()

    draw_text(surface, "흑사병의 마을", 64, YELLOW, (w // 2, h // 2 - 90))
    draw_text(surface, "시간여행자와 책의 요정", 28, WHITE, (w // 2, h // 2 - 30))

    mode_buttons = {}
    modes = (("normal", "일반 모드", "이야기를 따라 천천히 플레이"),
             ("time_attack", "타임어택", "최대한 빠르게 마을을 구하기"))
    button_w, button_h = min(330, w // 2 - 24), 72
    start_x = w // 2 - button_w - 10
    for index, (key, title, description) in enumerate(modes):
        rect = pygame.Rect(start_x + index * (button_w + 20), h // 2 + 22,
                           button_w, button_h)
        mode_buttons[key] = rect
        draw_panel(surface, rect, alpha=245 if key == selected_mode else 190)
        if key == selected_mode:
            pygame.draw.rect(surface, YELLOW, rect, 3, border_radius=6)
        draw_text(surface, title, 24, YELLOW if key == selected_mode else WHITE,
                  (rect.centerx, rect.y + 23))
        draw_text(surface, description, 14, GRAY, (rect.centerx, rect.y + 51))

    # 0.5초마다 깜빡이는 안내 문구
    if int(time_sec * 2) % 2 == 0:
        draw_text(surface, "모드를 선택해서 시작", 22, WHITE, (w // 2, h // 2 + 125))

    draw_text(surface, "이동: 화면 왼쪽을 누른 채 드래그    대화·조사: 오른쪽 아래 버튼",
              18, GRAY, (w // 2, h - 60))
    draw_text(surface, "(PC: ← → 모드 선택 / Enter 시작 / WASD 이동 / E 대화·조사)",
              15, GRAY, (w // 2, h - 32))
    return mode_buttons


def format_time(seconds):
    """초 단위 기록을 MM:SS.d 형식으로 표시한다."""
    total_tenths = max(0, int(seconds * 10))
    minutes, remainder = divmod(total_tenths, 600)
    secs, tenths = divmod(remainder, 10)
    return f"{minutes:02d}:{secs:02d}.{tenths}"


def draw_stopwatch(surface, elapsed):
    """타임어택 플레이 중 상단 상태바 아래에 스톱워치를 표시한다."""
    label = f"⏱ {format_time(elapsed)}"
    font = get_font(21)
    rendered = font.render(label, True, YELLOW)
    box = pygame.Rect(0, TOPBAR_HEIGHT + 7, rendered.get_width() + 24, 36)
    box.right = surface.get_width() - 8
    draw_panel(surface, box, alpha=220)
    surface.blit(rendered, rendered.get_rect(center=box.center))


# ======================================================================
# 프롤로그: 시간여행 연출
# ======================================================================
def draw_time_travel(surface, t, duration):
    """
    중세로 이동하는 연출. 가운데서 퍼져 나가는 빛의 고리를 그립니다.
    t = 연출이 시작된 뒤 지난 시간(초), duration = 연출 전체 길이
    """
    surface.fill(BLACK)
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2

    # 고리 8개가 시간에 따라 바깥으로 퍼져 나감
    for i in range(8):
        r = (t * 220 + i * 70) % 560
        brightness = max(0, 255 - int(r / 560 * 255))
        color = (brightness, int(brightness * 0.8), int(brightness * 0.4))
        pygame.draw.circle(surface, color, (cx, cy), int(r) + 2, 3)

    # 글자는 서서히 나타남 (0 → 1)
    fade = min(1.0, t / (duration * 0.6))
    c = int(255 * fade)
    draw_text(surface, "1347년, 유럽 어딘가...", 32, (c, c, c), (cx, cy))
    draw_text(surface, "터치: 건너뛰기", 16, GRAY, (w - 70, h - 22))


# ======================================================================
# 책의 요정
# ======================================================================
def draw_fairy(surface, pos, time_sec):
    """책의 요정을 그립니다. pos = 화면 좌표, 위아래로 둥실둥실 움직입니다."""
    x = pos[0]
    y = pos[1] + math.sin(time_sec * 3) * 4   # 둥실둥실

    # 그림(assets/characters/fairy.png)이 있으면: 1줄의 4칸을 계속 반복 (날갯짓)
    frames = load_sheet("characters/fairy.png")
    if frames:
        image = frames[0][int(time_sec * ANIM_FPS) % len(frames[0])]
        surface.blit(image, image.get_rect(center=(x, y)))
        return

    # 은은한 빛 (반투명 원)
    glow = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*COLOR_FAIRY, 60), (24, 24), 22)
    surface.blit(glow, (x - 24, y - 24))

    # 날개 (파닥파닥: 날개 폭이 시간에 따라 바뀜)
    flap = 6 + abs(math.sin(time_sec * 12)) * 4
    pygame.draw.ellipse(surface, COLOR_FAIRY_WING,
                        pygame.Rect(x - 6 - flap, y - 10, flap, 12))
    pygame.draw.ellipse(surface, COLOR_FAIRY_WING,
                        pygame.Rect(x + 6, y - 10, flap, 12))
    # 몸
    pygame.draw.circle(surface, COLOR_FAIRY, (int(x), int(y)), 7)


# ======================================================================
# 상단 상태바
# ======================================================================
def _draw_stat_bar(surface, x, y, label, value, color, flash=False):
    """수치 막대 하나: [이름] [■■■■□□□] [숫자]   flash=True면 이름이 빨갛게 깜빡임 (위험)"""
    bar_w, bar_h = 150, 12
    draw_text_left(surface, label, 14, LIGHT_RED if flash else WHITE, (x, y - 3))
    bar = pygame.Rect(x + 56, y, bar_w, bar_h)
    pygame.draw.rect(surface, COLOR_BAR_EMPTY, bar, border_radius=3)
    filled = bar.copy()
    filled.width = int(bar_w * max(0, min(100, value)) / 100)
    if filled.width > 0:
        pygame.draw.rect(surface, color, filled, border_radius=3)
    draw_text_left(surface, str(int(value)), 14, WHITE, (bar.right + 8, y - 3))


def draw_top_bar(surface, chapter_name, objective, stats, time_sec=0.0):
    """
    화면 위쪽 상태바.
    왼쪽: 챕터 이름 + 현재 목표 / 오른쪽: 확산도·신뢰도·생존자 막대
    stats = {"spread": .., "trust": .., "survivors": ..}
    확산도가 70 이상이면 '확산도' 글자가 빨갛게 깜빡입니다.
    """
    blink = int(time_sec * 3) % 2 == 0
    w = surface.get_width()
    draw_panel(surface, pygame.Rect(4, 4, w - 8, TOPBAR_HEIGHT - 8))

    draw_text_left(surface, chapter_name, 20, YELLOW, (18, 10))
    draw_text_left(surface, "목표: " + objective, 15, WHITE, (18, 36))

    x = w - 270
    _draw_stat_bar(surface, x, 12, "확산도", stats["spread"], COLOR_SPREAD,
                   flash=stats["spread"] >= 70 and blink)
    _draw_stat_bar(surface, x, 28, "신뢰도", stats["trust"], COLOR_TRUST)
    _draw_stat_bar(surface, x, 44, "생존자", stats["survivors"], COLOR_SURVIVORS)


# ======================================================================
# "E 누르기" 안내
# ======================================================================
def draw_interact_hint(surface, pos, text="조사하기", show_key=True):
    """
    상호작용할 수 있는 대상 위에 [E] 안내를 띄웁니다.
    pos = 대상의 화면 좌표(머리 위쪽)
    show_key = False면 [E] 표시 없이 글자만 (휴대폰에서는 행동 버튼을 누르므로)
    """
    label = get_font(15).render(text, True, WHITE)
    key_w = 24 if show_key else 0
    box = pygame.Rect(0, 0, label.get_width() + key_w + 14, 26)
    box.midbottom = pos
    draw_panel(surface, box, alpha=210)
    if show_key:
        key = pygame.Rect(box.x + 5, box.y + 4, 18, 18)
        pygame.draw.rect(surface, YELLOW, key, border_radius=3)
        draw_text(surface, "E", 13, BLACK, key.center)
    surface.blit(label, (box.x + 7 + key_w, box.y + 4))


# ======================================================================
# 퀘스트 표시: 머리 위 '!' / 진행 알림
# ======================================================================
def draw_quest_marker(surface, pos, time_sec):
    """퀘스트에 필요한 대상 머리 위에 노란 '!'를 둥실둥실 띄웁니다. pos = 머리 위 화면 좌표"""
    x = pos[0]
    y = pos[1] - 12 + math.sin(time_sec * 4) * 3
    pygame.draw.circle(surface, BLACK, (int(x), int(y)), 11)
    pygame.draw.circle(surface, YELLOW, (int(x), int(y)), 9)
    draw_text(surface, "!", 16, BLACK, (x, y))


def draw_toast(surface, text, time_left, color=YELLOW):
    """상태바 아래 가운데에 잠깐 떴다 사라지는 알림 (마지막 0.5초 동안 흐려짐)"""
    alpha = int(255 * max(0.0, min(1.0, time_left / 0.5)))
    label = get_font(18).render(text, True, color)
    box = pygame.Rect(0, 0, label.get_width() + 32, 36)
    box.midtop = (surface.get_width() // 2, TOPBAR_HEIGHT + 8)
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    draw_panel(layer, box, alpha=230)
    layer.blit(label, (box.x + 16, box.y + 7))
    layer.set_alpha(alpha)
    surface.blit(layer, (0, 0))


# ======================================================================
# 가방 (가지고 있는 물건)
# ======================================================================
def draw_inventory(surface, inventory):
    """상태바 바로 아래 왼쪽에 가진 물건을 작게 보여줍니다. 예) 가방: 약초 1 (없으면 안 그림)"""
    if not inventory:
        return
    text = "가방: " + ", ".join(f"{name} {count}" for name, count in inventory.items())
    label = get_font(15).render(text, True, WHITE)
    box = pygame.Rect(8, TOPBAR_HEIGHT + 2, label.get_width() + 20, 26)
    draw_panel(surface, box, alpha=200)
    surface.blit(label, (box.x + 10, box.y + 4))


# ======================================================================
# 엔딩 화면
# ======================================================================
def draw_ending(surface, ending, stats, t, final_time=None):
    """
    엔딩 화면. ending = quest.ENDINGS의 항목, t = 엔딩이 시작된 뒤 지난 시간(초)
    화면이 천천히 어두워진 뒤 제목 → 설명 → 최종 수치 → 다시 하기 안내 순서로 나타납니다.
    """
    w, h = surface.get_size()
    # 1) 1.5초 동안 화면을 점점 어둡게 (마지막 게임 화면 위에 덮음)
    dark = pygame.Surface((w, h), pygame.SRCALPHA)
    dark.fill((8, 6, 10, int(255 * min(1.0, t / 1.5))))
    surface.blit(dark, (0, 0))
    if t < 1.0:
        return

    draw_text(surface, ending["title"], 44, ending["color"], (w // 2, h // 2 - 140))
    for i, line in enumerate(ending["lines"]):
        if t > 1.5 + i * 0.6:   # 한 줄씩 차례로 나타남
            draw_text(surface, line, 20, WHITE, (w // 2, h // 2 - 70 + i * 34))

    if t > 3.0:
        result = (f"최종 확산도 {stats['spread']}   신뢰도 {stats['trust']}   "
                  f"생존자 {stats['survivors']}")
        draw_text(surface, result, 18, GRAY, (w // 2, h // 2 + 60))
        if final_time is not None:
            draw_text(surface, f"최종 시간  {format_time(final_time)}", 25, YELLOW,
                      (w // 2, h // 2 + 96))
    if t > 3.5 and int(t * 2) % 2 == 0:
        draw_text(surface, "터치(PC: Enter)하면 처음부터 다시 시작", 22, YELLOW,
                  (w // 2, h // 2 + 145))


# ======================================================================
# 오류 화면
# ======================================================================
def draw_error(surface, error):
    """게임 도중 오류가 났을 때 보여주는 화면 (오류 내용 마지막 몇 줄 표시)"""
    surface.fill((25, 10, 15))
    w, h = surface.get_size()
    draw_text(surface, "오류가 발생했어요", 32, LIGHT_RED, (w // 2, 50))
    draw_text(surface, "이 화면을 캡처해서 보내 주세요. 터치(PC: Enter)하면 처음부터 다시 시작해요.",
              16, WHITE, (w // 2, 92))
    lines = [line for line in error.strip().splitlines() if line.strip()][-12:]
    y = 130
    for line in lines:
        for part in wrap_text(line.strip(), 14, w - 60):
            if y > h - 20:
                return
            draw_text_left(surface, part, 14, (220, 200, 200), (30, y))
            y += 22


# ======================================================================
# 대화창
# ======================================================================
class Dialogue:
    """
    화면 아래쪽 대화창.
    lines = [(말하는 사람, 대사), ...]  말하는 사람이 ""이면 해설(내레이션)
    글자가 한 글자씩 나오는 '타자기 효과'가 있습니다.

    선택지: 대사 대신 아래 형식의 딕셔너리를 넣으면, 대사가 다 나온 뒤 버튼이 나타납니다.
      {"speaker": "나", "text": "뭐라고 말할까?", "choices": ["답 1", "답 2", ...],
       "on_choose": 함수(game, 고른 번호) → 이어서 보여줄 대사 목록}
    """

    def __init__(self, lines):
        self.lines = list(lines)
        self.index = 0          # 지금 보여주는 대사 번호
        self.shown = 0.0        # 지금 대사에서 보여준 글자 수
        self.finished = False   # 모든 대사를 다 봤는지
        self.selected = 0       # 선택지에서 지금 고른 번호 (키보드용)
        self.option_rects = []  # 화면에 그린 선택지 버튼 위치 (터치 판정용)

    @property
    def item(self):
        """지금 대사 원본 (튜플 또는 선택지 딕셔너리)"""
        return self.lines[self.index]

    @property
    def current(self):
        """(말하는 사람, 대사)"""
        item = self.item
        if isinstance(item, dict):
            return item["speaker"], item["text"]
        return item

    def line_done(self):
        """지금 대사가 끝까지 다 나왔는지"""
        return self.shown >= len(self.current[1])

    @property
    def choosing(self):
        """선택지 버튼이 나와 있어서 답을 골라야 하는지"""
        return isinstance(self.item, dict) and self.line_done() and not self.finished

    def update(self, dt):
        if not self.finished:
            self.shown = min(len(self.current[1]), self.shown + DIALOGUE_SPEED * dt)

    def advance(self):
        """
        E/Enter를 눌렀을 때:
        글자가 아직 나오는 중이면 → 한 번에 다 보여주기
        선택지가 나와 있으면 → 아무 일도 안 함 (답을 골라야 넘어감)
        다 나왔으면 → 다음 대사로 (마지막이면 finished = True)
        """
        if not self.line_done():
            self.shown = len(self.current[1])
            return
        if self.choosing:
            return
        self._next()

    def _next(self):
        self.index += 1
        self.shown = 0.0
        self.selected = 0
        self.option_rects = []
        if self.index >= len(self.lines):
            self.index = len(self.lines) - 1
            self.finished = True

    def move_selection(self, step):
        """키보드 위/아래로 선택지 고르기"""
        if self.choosing:
            self.selected = (self.selected + step) % len(self.item["choices"])

    def option_at(self, pos):
        """터치한 좌표에 있는 선택지 번호 (없으면 None)"""
        for i, rect in enumerate(self.option_rects):
            if rect.collidepoint(pos):
                return i
        return None

    def choose(self, game, index):
        """선택지 index번을 고릅니다. 결과 대사를 바로 뒤에 끼워 넣고 다음으로 넘어감"""
        if not self.choosing:
            return
        follow = self.item["on_choose"](game, index) or []
        self.lines[self.index + 1:self.index + 1] = follow
        self._next()

    def draw(self, surface, time_sec):
        w, h = surface.get_size()
        box = pygame.Rect(16, h - DIALOGUE_HEIGHT - 16, w - 32, DIALOGUE_HEIGHT)
        draw_panel(surface, box, alpha=235)

        speaker, text = self.current
        text_x, text_y = box.x + 22, box.y + 18

        # 말하는 사람 이름표
        if speaker:
            name = get_font(18).render(speaker, True, YELLOW)
            tag = pygame.Rect(box.x + 14, box.y - 16, name.get_width() + 24, 30)
            draw_panel(surface, tag, alpha=255)
            surface.blit(name, (tag.x + 12, tag.y + 4))
            text_y += 8
            color = WHITE
        else:
            color = (200, 200, 210)   # 해설은 살짝 흐린 색

        # 전체 문장을 먼저 줄바꿈한 뒤, 지금까지 나온 글자 수만큼만 출력
        # (이렇게 해야 글자가 나오는 도중에 단어가 다음 줄로 튀지 않음)
        remaining = int(self.shown)
        for i, line in enumerate(wrap_text(text, 20, box.width - 44)):
            if remaining <= 0:
                break
            draw_text_left(surface, line[:remaining], 20, color, (text_x, text_y + i * 30))
            remaining -= len(line) + 1   # +1 = 줄바꿈으로 사라진 띄어쓰기

        if self.choosing:
            self._draw_choices(surface, box, time_sec)
        elif self.line_done() and int(time_sec * 2) % 2 == 0:
            # 대사가 다 나오면 오른쪽 아래에 ▼ 표시 깜빡임
            ax, ay = box.right - 28, box.bottom - 24
            pygame.draw.polygon(surface, YELLOW,
                                [(ax, ay), (ax + 12, ay), (ax + 6, ay + 8)])

    def _draw_choices(self, surface, box, time_sec):
        """대화창 위쪽에 선택지 버튼을 아래에서 위로 쌓아 그립니다. (휴대폰에서 누르기 쉽게 크게)"""
        size, line_h, pad, gap = 18, 26, 10, 8
        width = box.width - 32
        wrapped = [wrap_text(f"{i + 1}. {c}", size, width - 2 * pad - 4)
                   for i, c in enumerate(self.item["choices"])]
        heights = [max(44, len(lines) * line_h + 2 * pad) for lines in wrapped]
        y = box.top - 26 - sum(heights) - gap * (len(heights) - 1)
        self.option_rects = []
        for i, (lines, height) in enumerate(zip(wrapped, heights)):
            rect = pygame.Rect(box.x + 16, y, width, height)
            self.option_rects.append(rect)
            draw_panel(surface, rect, alpha=240)
            if i == self.selected:
                pygame.draw.rect(surface, YELLOW, rect, 3, border_radius=6)
            for j, line in enumerate(lines):
                color = YELLOW if i == self.selected else WHITE
                draw_text_left(surface, line, size, color,
                               (rect.x + pad + 4, rect.y + (height - len(lines) * line_h) // 2 + j * line_h))
            y += height + gap


def draw_menu_overlay(surface, page, inventory, stats, selected=0, scroll=0):
    """게임을 멈춘 상태에서 계속하기, 가방, 설정을 보여주는 메뉴."""
    width, height = surface.get_size()
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 155))
    surface.blit(shade, (0, 0))

    if page == "inventory":
        title = "가방"
        details = [f"{name}  x{count}" for name, count in inventory.items()]
        if not details:
            details = ["가방이 비어 있습니다."]
        details.append(f"확산도 {stats['spread']}   신뢰도 {stats['trust']}   생존자 {stats['survivors']}")
        actions = [("back", "메뉴로 돌아가기")]
    elif page == "settings":
        title = "설정"
        details = [
            "이동: W A S D 또는 방향키",
            "대화·조사: E    대화 넘기기: Enter",
            "메뉴 열기·닫기: ESC",
            "메뉴 선택: ↑ ↓ Tab / Enter    가방: I    설정: S",
            f"화면 크기: {width} x {height}",
        ]
        actions = [("back", "메뉴로 돌아가기")]
    else:
        title = "메뉴"
        details = []
        actions = [
            ("resume", "계속하기"),
            ("inventory", "가방"),
            ("settings", "설정"),
        ]

    panel_width = min(420, width - 32)
    wrapped_details = [line for detail in details
                       for line in wrap_text(detail, 16, panel_width - 36)]
    button_gap = 8
    button_height = min(48, max(20, (height - 100) // len(actions) - button_gap))
    detail_height = 22
    actions_height = len(actions) * button_height + (len(actions) - 1) * button_gap
    detail_space = max(0, height - 24 - 78 - actions_height)
    scrolling = len(wrapped_details) * detail_height > detail_space
    scroll_height = 28 if scrolling else 0
    capacity = max(0, (detail_space - scroll_height) // detail_height)
    max_scroll = max(0, len(wrapped_details) - capacity)
    scroll = max(0, min(scroll, max_scroll))
    visible_details = wrapped_details[scroll:scroll + capacity]
    panel_height = 78 + len(visible_details) * detail_height + scroll_height + actions_height
    panel_height = min(panel_height, height - 24)
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (width // 2, height // 2)
    draw_panel(surface, panel, alpha=245)
    draw_text(surface, title, 30, YELLOW, (panel.centerx, panel.top + 34))

    y = panel.top + 62
    for line in visible_details:
        draw_text(surface, line, 16, WHITE, (panel.centerx, y + 10))
        y += detail_height

    y += 6
    buttons = {}
    button_width = panel.width - 36
    if scrolling:
        for action, label, offset in (("scroll_up", "↑", 0), ("scroll_down", "↓", 1)):
            button = pygame.Rect(panel.left + 18 + offset * (button_width // 2 + 2),
                                 y, button_width // 2 - 2, scroll_height - 4)
            draw_panel(surface, button, alpha=225)
            draw_text(surface, label, 16, WHITE, button.center)
            if (action == "scroll_up" and scroll > 0) or (action == "scroll_down" and scroll < max_scroll):
                buttons[action] = button
        y += scroll_height
    for i, (action, label) in enumerate(actions):
        button = pygame.Rect(0, 0, button_width, button_height)
        button.centerx = panel.centerx
        button.top = y
        draw_panel(surface, button, alpha=225)
        if i == selected:
            pygame.draw.rect(surface, YELLOW, button, 2, border_radius=6)
        draw_text(surface, label, 18, WHITE, button.center)
        buttons[action] = button
        y += button_height + button_gap
    return buttons
