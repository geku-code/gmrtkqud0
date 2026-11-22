# touch.py
# 휴대폰(터치) 조작을 담당하는 파일입니다.
#   - 화면 왼쪽 절반: 누른 곳에 가상 조이스틱이 생기고, 드래그한 방향으로 이동
#   - 오른쪽 아래 원형 버튼: 행동(대화/조사) = PC의 E 키
#   - 그 밖의 터치: 대화 넘기기, 타이틀에서 시작하기 등 (main.py에서 처리)
# PC 마우스로 클릭해도 똑같이 동작하므로 컴퓨터에서도 테스트할 수 있습니다.
#
# 웹(휴대폰)에서는 pygame의 손가락 이벤트 대신 브라우저의 터치를 직접 읽습니다. (TOUCH_JS)
#   - 손가락 위치를 '게임 화면(캔버스)' 기준으로 계산 → 카카오톡, 크롬 등 어디서나 같은 위치
#   - 드래그를 브라우저가 '페이지 스크롤/새로고침'으로 가져가지 못하게 막음
#     (막지 않으면 손가락을 움직이는 도중 터치가 끊겨서 조이스틱이 멈춤)

import json
import math
import sys
import pygame
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, PHONE_SCREEN_HEIGHT, MIN_ASPECT, MAX_ASPECT,
                      TOPBAR_HEIGHT, WHITE, YELLOW, JOYSTICK_RADIUS, JOYSTICK_MARGIN,
                      ACTION_BUTTON_MARGIN, ACTION_BUTTON_RADIUS)
import ui

MOUSE_ID = "mouse"   # 마우스를 손가락 하나처럼 취급할 때 쓰는 번호
IS_WEB = sys.platform == "emscripten"   # emscripten = 웹(pygbag)에서 실행 중이라는 뜻

# 브라우저에서 실행하는 자바스크립트: 터치를 모아 두었다가 파이썬이 매 프레임 꺼내 감
#   한 개의 터치 = [종류, 손가락 번호, x 비율(0~1), y 비율(0~1)]  ← 캔버스 기준
TOUCH_JS = r"""
(function () {
  if (window.__touchq) return;
  const q = window.__touchq = [];
  const canvas = document.getElementById('canvas');
  for (const el of [document.documentElement, document.body, canvas]) {
    el.style.touchAction = 'none';          // 브라우저의 스크롤/확대 동작 끄기
    el.style.overscrollBehavior = 'none';   // 당겨서 새로고침 끄기
  }
  const push = (kind) => (e) => {
    const r = canvas.getBoundingClientRect();
    for (const t of e.changedTouches) {
      q.push([kind, t.identifier, (t.clientX - r.left) / r.width, (t.clientY - r.top) / r.height]);
    }
    if (e.cancelable) e.preventDefault();
  };
  const opt = {passive: false, capture: true};
  window.addEventListener('touchstart', push('down'), opt);
  window.addEventListener('touchmove', push('move'), opt);
  window.addEventListener('touchend', push('up'), opt);
  window.addEventListener('touchcancel', push('up'), opt);
  // 처음 터치할 때 전체 화면으로 (주소창 숨기기). 지원하지 않는 앱이면 그냥 넘어감
  window.addEventListener('touchend', () => {
    const d = document.documentElement;
    if (!document.fullscreenElement && d.requestFullscreen) {
      d.requestFullscreen({navigationUI: 'hide'}).catch(() => {});
    }
  }, {capture: true});
})();
"""


def _js_window():
    """웹에서 브라우저의 window 객체 (PC에서는 None)"""
    if not IS_WEB:
        return None
    try:
        import platform
        return platform.window
    except Exception:
        return None


class TouchControls:
    def __init__(self, size=(SCREEN_WIDTH, SCREEN_HEIGHT)):
        self.visible = False       # 한 번이라도 터치/클릭하면 화면에 버튼을 보여줌
        self.got_finger = False    # 진짜 손가락 터치를 받은 적이 있는지
        self.joy_id = None         # 조이스틱을 잡고 있는 손가락 번호 (없으면 None)
        self.size = size
        self.joy_origin = self.joy_home   # 조이스틱 가운데
        self.joy_pos = self.joy_home      # 손가락 위치

        # 웹이면 브라우저 터치 읽기 시작
        self.web = False
        window = _js_window()
        if window is not None:
            try:
                window.eval(TOUCH_JS)
                self.web = True
            except Exception as e:
                print("touch bridge failed:", e)

    # ---------------- 화면 크기에 따라 바뀌는 위치 ----------------
    @property
    def joy_home(self):
        """손을 떼고 있을 때 조이스틱 위치 (왼쪽 아래)"""
        return (JOYSTICK_MARGIN, self.size[1] - JOYSTICK_MARGIN)

    @property
    def button_pos(self):
        """행동 버튼 위치 (오른쪽 아래)"""
        return (self.size[0] - ACTION_BUTTON_MARGIN, self.size[1] - ACTION_BUTTON_MARGIN)

    def set_size(self, size):
        """게임 화면 크기가 바뀌었을 때 호출 (휴대폰 회전, 전체 화면 전환 등)"""
        self.size = size
        self.release()

    # ---------------- 입력 읽기 ----------------
    def poll_web(self):
        """
        웹: 브라우저가 모아 둔 터치를 꺼내 옵니다.
        돌려주는 값: [("down"/"move"/"up", 손가락 번호, (x, y)), ...]
        """
        if not self.web:
            return []
        try:
            raw = _js_window().eval("JSON.stringify(window.__touchq.splice(0))")
            touches = json.loads(str(raw))
        except Exception:
            return []
        if touches:
            self.got_finger = True
        w, h = self.size
        return [(kind, tid, (fx * w, fy * h)) for kind, tid, fx, fy in touches]

    def _to_pointer(self, event):
        """
        손가락 이벤트와 마우스 이벤트를 같은 형식으로 바꿉니다.
        돌려주는 값: ("down"/"move"/"up", 손가락 번호, (x, y))  또는 None
        """
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            if self.web:
                return None   # 웹에서는 poll_web()으로 따로 읽음
            self.got_finger = True
            # 손가락 좌표는 0~1 비율로 오므로 화면 크기를 곱해서 픽셀로 바꿈
            pos = (event.x * self.size[0], event.y * self.size[1])
            kind = {pygame.FINGERDOWN: "down", pygame.FINGERMOTION: "move",
                    pygame.FINGERUP: "up"}[event.type]
            return kind, event.finger_id, pos

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            # 휴대폰에서는 터치 한 번에 '가짜 마우스 이벤트'도 같이 오므로 중복 처리하지 않음
            if getattr(event, "touch", False) and (self.got_finger or self.web):
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                return "down", MOUSE_ID, event.pos
            if event.type == pygame.MOUSEMOTION and event.buttons[0]:
                return "move", MOUSE_ID, event.pos
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                return "up", MOUSE_ID, event.pos
        return None

    def handle_event(self, event):
        """pygame 이벤트 하나를 처리합니다. 화면을 '누른 순간'이면 좌표, 아니면 None"""
        pointer = self._to_pointer(event)
        if pointer is None:
            return None
        return self.handle_pointer(*pointer)

    def handle_pointer(self, kind, pid, pos):
        """
        터치/클릭 하나를 처리합니다.
        화면을 '누른 순간'이면 그 좌표를 돌려주고, 아니면 None을 돌려줍니다.
        """
        w, h = self.size
        if kind == "down":
            self.visible = True
            # 왼쪽 절반(상단바 아래)을 누르면 그 자리에 조이스틱 생성
            if self.joy_id is None and pos[0] < w / 2 and pos[1] > TOPBAR_HEIGHT:
                self.joy_id = pid
                # 조이스틱이 화면 밖으로 잘리지 않게 위치 조정
                r = JOYSTICK_RADIUS
                self.joy_origin = (max(r, min(pos[0], w - r)),
                                   max(r, min(pos[1], h - r)))
                self.joy_pos = pos
            return pos

        if pid == self.joy_id:
            if kind == "move":
                self.joy_pos = pos
            elif kind == "up":
                self.release()
        return None

    def release(self):
        """조이스틱에서 손을 뗀 상태로 되돌립니다."""
        self.joy_id = None
        self.joy_origin = self.joy_home
        self.joy_pos = self.joy_home

    # ---------------- 조이스틱 방향 ----------------
    def move_vector(self):
        """
        조이스틱이 가리키는 방향 (dx, dy). 길이는 0~1
        (조금만 당기면 천천히, 반지름의 60% 이상 당기면 최고 속도)
        """
        if self.joy_id is None:
            return 0.0, 0.0
        ox = self.joy_pos[0] - self.joy_origin[0]
        oy = self.joy_pos[1] - self.joy_origin[1]
        length = math.hypot(ox, oy)
        if length < 10:                 # 손가락 떨림은 무시 (데드존)
            return 0.0, 0.0
        power = min(1.0, length / (JOYSTICK_RADIUS * 0.6))
        return ox / length * power, oy / length * power

    def hit_action_button(self, pos):
        """좌표가 행동 버튼 안인지 (손가락이 두꺼우니 조금 넉넉하게 판정)"""
        bx, by = self.button_pos
        return math.hypot(pos[0] - bx, pos[1] - by) <= ACTION_BUTTON_RADIUS + 16

    # ---------------- 그리기 ----------------
    def draw(self, surface, action_label):
        """
        조이스틱과 행동 버튼을 그립니다.
        action_label = 버튼에 쓸 글자 (가까이에 대상이 없으면 None → 흐리게 표시)
        """
        if not self.visible:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # 조이스틱: 바깥 원(받침) + 안쪽 원(손잡이)
        r = JOYSTICK_RADIUS
        ox, oy = self.joy_origin
        dx, dy = self.joy_pos[0] - ox, self.joy_pos[1] - oy
        dist = math.hypot(dx, dy)
        if dist > r:                    # 손잡이는 받침 밖으로 못 나감
            dx, dy = dx / dist * r, dy / dist * r
        active = self.joy_id is not None
        pygame.draw.circle(overlay, (255, 255, 255, 50 if active else 30), (ox, oy), r)
        pygame.draw.circle(overlay, (255, 255, 255, 110 if active else 60), (ox, oy), r, 3)
        pygame.draw.circle(overlay, (255, 255, 255, 160 if active else 80),
                           (ox + dx, oy + dy), r * 0.42)

        # 행동 버튼
        bx, by = self.button_pos
        br = ACTION_BUTTON_RADIUS
        if action_label:
            pygame.draw.circle(overlay, (240, 210, 80, 170), (bx, by), br)
            pygame.draw.circle(overlay, (255, 245, 200, 230), (bx, by), br, 3)
        else:
            pygame.draw.circle(overlay, (255, 255, 255, 35), (bx, by), br)
            pygame.draw.circle(overlay, (255, 255, 255, 70), (bx, by), br, 3)
        surface.blit(overlay, (0, 0))

        if action_label:
            ui.draw_text(surface, action_label, 22, (40, 30, 10), (bx, by))
        else:
            ui.draw_text(surface, "행동", 20, (190, 190, 190), (bx, by))


# ======================================================================
# 웹 화면 크기 / 휴대폰 세로 화면 확인
# ======================================================================
def web_screen_size():
    """
    웹: 브라우저 화면 비율에 맞는 게임 화면 크기 (가로, 세로).
    세로 길이는 고정하고, 가로 길이를 화면 비율에 맞춰 늘리거나 줄입니다.
    → 휴대폰마다 화면 비율이 달라도 양옆에 빈 여백이 생기지 않음
    PC(파이썬으로 직접 실행)이거나 휴대폰이 세로면 None
    """
    window = _js_window()
    if window is None:
        return None
    try:
        iw, ih = float(window.innerWidth), float(window.innerHeight)
    except Exception:
        return None
    if iw <= 0 or ih <= 0 or ih > iw:
        return None
    # 휴대폰처럼 작은 화면은 세로를 줄여서 글자/캐릭터를 크게 보여줌
    height = PHONE_SCREEN_HEIGHT if ih < 600 else SCREEN_HEIGHT
    aspect = max(MIN_ASPECT, min(MAX_ASPECT, iw / ih))
    return int(height * aspect) // 2 * 2, height


def refit_canvas():
    """웹: 게임 화면 크기를 바꾼 뒤, 브라우저 화면에 꽉 차게 다시 배치 (pygbag 기능 호출)"""
    window = _js_window()
    if window is None:
        return
    try:
        window.window_resize()
    except Exception:
        pass


def is_portrait():
    """
    웹 브라우저에서 휴대폰을 세로로 들고 있으면 True.
    PC(파이썬으로 직접 실행)에서는 항상 False.
    """
    window = _js_window()
    if window is None:
        return False
    try:
        return window.innerHeight > window.innerWidth
    except Exception:
        return False


def draw_rotate_notice(surface, time_sec):
    """'가로로 돌려주세요' 안내 화면"""
    surface.fill((10, 8, 14))
    w, h = surface.get_size()
    # 휴대폰 모양 사각형이 세로 ↔ 가로로 기울어지는 그림
    angle = 0 if int(time_sec) % 2 == 0 else -90
    phone = pygame.Surface((90, 160), pygame.SRCALPHA)
    pygame.draw.rect(phone, WHITE, phone.get_rect(), 6, border_radius=14)
    phone = pygame.transform.rotate(phone, angle)
    surface.blit(phone, phone.get_rect(center=(w // 2, h // 2 - 70)))
    ui.draw_text(surface, "휴대폰을 가로로 돌려주세요", 40, YELLOW, (w // 2, h // 2 + 80))
    ui.draw_text(surface, "이 게임은 가로 화면에서 플레이합니다", 24, WHITE, (w // 2, h // 2 + 135))
