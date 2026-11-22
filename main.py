# main.py
# 게임을 실행하는 시작 파일입니다.
#   PC에서 실행:   python main.py
#   웹으로 실행:   python -m pygbag .   (브라우저에서 http://localhost:8000 접속)
# 게임 상태 머신(TITLE → PROLOGUE → PLAYING ⇄ DIALOGUE ...)과 메인 루프를 담당합니다.

import asyncio
import traceback
import pygame

from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, TRAVEL_TIME, INTERACT_RANGE,
                      TOPBAR_HEIGHT,
                      YELLOW, LIGHT_RED,
                      STATE_TITLE, STATE_PROLOGUE, STATE_PLAYING, STATE_DIALOGUE,
                      STATE_MENU, STATE_ENDING, HIGH_SPREAD_THRESHOLD,
                      REMOVAL_FAILURE_THRESHOLD, REMOVAL_FAILURE_SPREAD_GAIN)
from world import World
from player import Player
from npc import create_npcs
from objects import create_objects
from quest import (CHAPTERS, QuestManager, PROLOGUE_DIALOGUE, SPREAD_WARNINGS,
                   ENDINGS, recovery_ending)
from stats import PlagueStats
from touch import TouchControls, is_portrait, draw_rotate_notice, web_screen_size, refit_canvas
import ui

TOAST_TIME = 2.5    # 퀘스트 진행 알림이 떠 있는 시간(초)
WARNING_TIME = 4.0  # 확산도 경고 알림이 떠 있는 시간(초)
ENDING_INPUT_DELAY = 3.5   # 엔딩 화면에서 이 시간이 지나야 터치로 다시 시작 (실수로 넘기지 않게)

# 대화를 넘기는 키 (E / Enter / 스페이스)
ADVANCE_KEYS = (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class Game:
    def __init__(self):
        # [순서도] Pygame 초기화 → 화면 생성 및 맵 불러오기 → 플레이어 생성
        pygame.init()
        pygame.display.set_caption(TITLE)
        # 웹(휴대폰)이면 화면 비율에 맞춘 크기, PC면 960×640
        size = web_screen_size() or (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.screen = pygame.display.set_mode(size)
        self.size_check_timer = 0.0   # 화면 크기가 바뀌었는지 확인하는 간격(초)
        self.clock = pygame.time.Clock()
        self.running = True
        self.time = 0.0               # 게임 시작 후 지난 시간(초)
        self.touch = TouchControls(size)  # 휴대폰 조작 (조이스틱 + 행동 버튼)
        self.portrait = False         # 휴대폰을 세로로 들고 있는지 (그동안 게임 일시정지)
        self.world = World()
        self.reset()

    def reset(self):
        """새 게임 준비 (처음 시작할 때, 엔딩 후 다시 시작할 때)"""
        self.state = STATE_TITLE      # 처음 상태는 타이틀 화면
        self.menu_page = "main"
        self.menu_buttons = {}
        self.menu_selected = 0
        self.menu_scroll = 0
        self.mode = "normal"
        self.title_mode_buttons = {}
        self.run_time = 0.0
        self.player = Player(*self.world.player_start)
        self.npcs = create_npcs()     # 마을 주민들
        self.objects = create_objects()   # 우물, 쓰레기, 쥐, 약초, 환자 (objects.py)
        self.inventory = {}           # 가방 {물건 이름: 개수}
        self.nearby = None            # 지금 E로 상호작용할 수 있는 대상 (없으면 None)
        self.camera = (0, 0)
        self.touch.release()

        self.stats = PlagueStats()    # 확산도·신뢰도·생존자 (0~100)
        self.quest = QuestManager()   # 챕터 진행 (0 = 프롤로그)
        self.investigation_reward_pending = False  # 실패하면 회수할 7부 조사 보상
        self.toast = None             # 알림 [글자, 남은 시간, 색] (없으면 None)

        self.dialogue = None          # 지금 열려 있는 대화창 (없으면 None)
        self.pending_dialogue_action = None  # 현재 대화가 끝난 직후 실행할 연출
        self.prologue_time = 0.0      # 프롤로그가 시작된 뒤 지난 시간
        self.ending = None            # 엔딩 화면 내용 (quest.ENDINGS 중 하나)
        self.ending_time = 0.0        # 엔딩이 시작된 뒤 지난 시간

    # ---------------- 상태 전환 ----------------
    def start_prologue(self, mode=None):
        """[순서도] 타이틀 → 프롤로그 (중세시대로 이동)"""
        if mode is not None:
            self.mode = mode
        self.run_time = 0.0
        self.state = STATE_PROLOGUE
        self.prologue_time = 0.0
        self.dialogue = None
        self.update_camera()

    def start_dialogue(self, lines):
        """대화창을 열고 DIALOGUE 상태로 바꿉니다. (STEP 3부터 NPC 대화에 사용)"""
        self.dialogue = ui.Dialogue(lines)
        self.state = STATE_DIALOGUE

    def advance_dialogue(self):
        """대화 넘기기. 대화가 끝나면 대화창을 닫고 알맞은 상태로 돌아갑니다."""
        self.dialogue.advance()
        self.close_dialogue_if_done()

    def choose(self, index):
        """대화 중 선택지 index번을 고릅니다. (5부 설득 등)"""
        self.dialogue.choose(self, index)
        self.close_dialogue_if_done()

    def close_dialogue_if_done(self):
        if not self.dialogue.finished:
            return
        self.dialogue = None
        pending_action = self.pending_dialogue_action
        self.pending_dialogue_action = None
        if pending_action:
            follow_lines = pending_action() or []
            if follow_lines:
                self.start_dialogue(follow_lines)
                return
        if self.state == STATE_PROLOGUE:
            # [순서도] 책의 요정 등장(목표 설명) → 1부 시작
            self.quest.start(1)
        self.state = STATE_PLAYING
        # [순서도] 퀘스트 → 완료 확인 (대화가 끝난 뒤에 확인해야 대사가 겹치지 않음)
        self.check_quest()

    # ---------------- 퀘스트 ----------------
    def check_quest(self):
        """챕터 목표를 다 채웠으면 보상을 주고, 완료 대사 → 다음 챕터로 넘어갑니다."""
        if self.state == STATE_ENDING:
            return
        if self.quest.index == 9:
            if self.stats.is_lost():
                self.start_ending("bad")
            elif self.quest.is_complete():
                ending = recovery_ending(self.stats)
                if ending:
                    self.start_ending(ending)
            return
        if not self.quest.is_complete():
            return
        completed = self.quest.index
        if completed == 8 and self.stats["spread"] >= REMOVAL_FAILURE_THRESHOLD:
            self.fail_infection_removal()
            return

        next_index = None
        if completed == 6:
            # 6부 보상까지 반영된, 실제 7부 진입 시점의 확산도로 분기한다.
            spread_reward = self.quest.chapter.get("reward", {}).get("spread", 0)
            entry_spread = max(0, min(100, self.stats["spread"] + spread_reward))
            next_index = 7 if entry_spread >= HIGH_SPREAD_THRESHOLD else 8
        elif completed == 8:
            next_index = 9
        reward, lines = self.quest.complete(next_index)
        if completed == 7:
            self.investigation_reward_pending = True
        elif completed == 8:
            self.investigation_reward_pending = False
        if completed == 6 and next_index == 8:
            lines.insert(0, ("책의 요정", "확산도가 아직 높지 않아. 감염원 조사는 생략하고 오래된 창고의 감염원을 바로 제거하자!"))
        for stat, amount in reward.items():
            self.stats.change(stat, amount)
        self.toast = None
        if lines:
            self.start_dialogue(lines)

    def reset_infection_source_state(self):
        """7~8부 재시도에 관련된 퀘스트와 월드 오브젝트 상태를 초기화한다."""
        for obj in self.objects:
            if hasattr(obj, "investigated"):
                obj.investigated = False
            if hasattr(obj, "discovered"):
                obj.discovered = False
            if hasattr(obj, "removed"):
                obj.removed = False
            if hasattr(obj, "cleaned"):
                obj.cleaned = False
        self.nearby = None

    def fail_infection_removal(self):
        """감염원 제거 실패를 처리하고 7부를 완전히 새로 시작한다."""
        before = self.stats["spread"]
        self.stats.change("spread", REMOVAL_FAILURE_SPREAD_GAIN)
        if self.investigation_reward_pending:
            investigation_reward = CHAPTERS[7].get("reward", {})
            for stat, amount in investigation_reward.items():
                self.stats.change(stat, -amount)
            self.investigation_reward_pending = False
        self.reset_infection_source_state()
        self.quest.go_to(7)
        if self.stats.is_lost():
            self.start_ending("bad")
            return
        self.toast = None
        self.start_dialogue([
            ("", f"감염원 제거에 실패했다! 확산도 {before} → {self.stats['spread']}"),
            ("책의 요정", "병이 크게 번졌어. 7부로 돌아가 감염원의 흔적부터 다시 조사하자!"),
        ])

    def notify_quest(self, target, event=None):
        """
        대상과 상호작용했다고 퀘스트에 알리고, 진행됐으면 알림을 띄웁니다.
        event = 알릴 행동 이름 (없으면 대상의 기본 행동 target.quest_event)
        """
        if self.quest.notify(event or target.quest_event, getattr(target, "id", None)):
            self.show_toast(f"목표 진행: {self.quest.progress_text()}")

    def show_toast(self, text, time=TOAST_TIME, color=YELLOW):
        """화면 위쪽에 잠깐 알림을 띄웁니다."""
        self.toast = [text, time, color]

    # ---------------- 엔딩 ----------------
    def start_ending(self, key):
        """[순서도] 결과 계산 → 엔딩. key = quest.ENDINGS의 이름 ("bad" 등)"""
        self.ending = ENDINGS[key]
        self.ending_time = 0.0
        self.dialogue = None
        self.toast = None
        self.touch.release()
        self.state = STATE_ENDING

    # ---------------- 입력 처리 ----------------
    def menu_action(self, action):
        """키보드와 포인터가 같은 메뉴 동작을 사용한다."""
        self.touch.release()
        self.menu_buttons = {}
        self.menu_selected = 0
        self.menu_scroll = 0
        if action == "resume":
            self.state = STATE_PLAYING
        else:
            self.menu_page = "main" if action == "back" else action

    def handle_events(self):
        """키/터치를 '누른 순간'에 반응하는 입력을 처리합니다."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # 터치(또는 마우스 클릭): 누른 순간이면 좌표가 돌아옴
            press = self.touch.handle_event(event)
            if press is not None and not self.portrait:
                self.on_press(press)

            self.handle_key(event)

        # 웹: 브라우저에서 직접 읽은 터치 (pygame 손가락 이벤트 대신 사용)
        for kind, pid, pos in self.touch.poll_web():
            press = self.touch.handle_pointer(kind, pid, pos)
            if press is not None and not self.portrait:
                self.on_press(press)

    def handle_key(self, event):
        """키보드 입력 (PC)"""
        if event.type == pygame.KEYDOWN:
            if self.state == STATE_TITLE:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                    self.mode = "time_attack" if self.mode == "normal" else "normal"
                # 타이틀 화면에서 Enter → 선택한 모드 시작
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.start_prologue()

            elif self.dialogue and self.dialogue.choosing:
                # 선택지: 숫자 키로 바로 고르기, 또는 위/아래로 움직이고 E/Enter로 고르기
                count = len(self.dialogue.item["choices"])
                if pygame.K_1 <= event.key < pygame.K_1 + count:
                    self.choose(event.key - pygame.K_1)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.dialogue.move_selection(-1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.dialogue.move_selection(1)
                elif event.key in ADVANCE_KEYS:
                    self.choose(self.dialogue.selected)

            elif self.state in (STATE_PROLOGUE, STATE_DIALOGUE):
                if event.key in ADVANCE_KEYS:
                    self.on_advance()

            elif self.state == STATE_MENU:
                if event.key == pygame.K_ESCAPE:
                    self.menu_action("resume" if self.menu_page == "main" else "back")
                elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                    step = -1 if event.key == pygame.K_UP else 1
                    if self.menu_page == "main":
                        self.menu_selected = (self.menu_selected + step) % 3
                    else:
                        self.menu_scroll = max(0, self.menu_scroll + step)
                elif event.key in ADVANCE_KEYS:
                    action = ("resume", "inventory", "settings")[self.menu_selected]
                    self.menu_action(action if self.menu_page == "main" else "back")
                elif event.key == pygame.K_i:
                    self.menu_action("inventory")
                elif event.key == pygame.K_s:
                    self.menu_action("settings")

            elif self.state == STATE_PLAYING:
                if event.key == pygame.K_ESCAPE:
                    self.touch.release()
                    self.menu_buttons = {}
                    self.menu_selected = 0
                    self.menu_scroll = 0
                    self.menu_page = "main"
                    self.state = STATE_MENU
                elif event.key == pygame.K_e:
                    self.on_action()

            elif self.state == STATE_ENDING:
                if event.key in ADVANCE_KEYS and self.ending_time > ENDING_INPUT_DELAY:
                    self.reset()

    def on_press(self, pos):
        """화면을 터치했을 때 (상태마다 하는 일이 다름)"""
        if self.state == STATE_TITLE:
            mode = next((key for key, rect in self.title_mode_buttons.items()
                         if rect.collidepoint(pos)), None)
            if mode:
                self.start_prologue(mode)
        elif self.dialogue and self.dialogue.choosing:
            index = self.dialogue.option_at(pos)  # 선택지 버튼을 눌렀을 때만 고름
            if index is not None:
                self.choose(index)
        elif self.state in (STATE_PROLOGUE, STATE_DIALOGUE):
            self.on_advance()                     # 아무 데나 터치 → 대화 넘기기
        elif self.state == STATE_MENU:
            action = next((name for name, rect in self.menu_buttons.items()
                           if rect.collidepoint(pos)), None)
            if action in ("resume", "inventory", "settings", "back"):
                self.menu_action(action)
            elif action == "scroll_up":
                self.menu_scroll = max(0, self.menu_scroll - 1)
            elif action == "scroll_down":
                self.menu_scroll += 1
            self.touch.release()
        elif self.state == STATE_PLAYING:
            if self.touch.hit_action_button(pos):
                self.on_action()                  # 행동 버튼 = E 키
        elif self.state == STATE_ENDING:
            if self.ending_time > ENDING_INPUT_DELAY:
                self.reset()                      # 처음부터 다시

    def on_advance(self):
        """E/Enter/터치로 '다음'을 눌렀을 때 (프롤로그, 대화 중)"""
        if self.state == STATE_PROLOGUE and self.dialogue is None:
            # 시간여행 연출 중에 누르면 연출 건너뛰기
            self.prologue_time = TRAVEL_TIME
        elif self.dialogue:
            self.advance_dialogue()

    def on_action(self):
        """[순서도] E(행동 버튼) → NPC/오브젝트 확인 → 상호작용 가능? → 대화/조사"""
        if self.state != STATE_PLAYING or not self.nearby:
            return
        if not self.nearby.visible(self) or not self.nearby.can_interact(self):
            self.nearby = None
            return
        # 퀘스트 진행은 각 대상의 interact()에서 notify_quest()로 알려줌
        lines = self.nearby.interact(self)
        self.nearby = None
        if lines:
            self.start_dialogue(lines)    # 대화가 끝나면 퀘스트 완료 확인
        else:
            self.check_quest()            # 대화 없는 행동(쓰레기, 쥐)은 바로 확인

    # ---------------- 카메라 ----------------
    def update_camera(self):
        """플레이어를 화면 가운데에 두되, 맵 바깥은 보이지 않게 합니다."""
        sw, sh = self.screen.get_size()
        cx = self.player.rect.centerx - sw // 2
        cy = self.player.rect.centery - sh // 2
        cx = max(0, min(cx, self.world.pixel_width - sw))
        # 위쪽은 상태바 높이만큼 더 올라갈 수 있게 함 → 맵 맨 위(북쪽 성문)가 상태바에 가려지지 않음
        cy = max(-TOPBAR_HEIGHT, min(cy, self.world.pixel_height - sh))
        self.camera = (cx, cy)

    # ---------------- 화면 크기 (웹) ----------------
    def check_screen_size(self, dt):
        """
        웹: 0.5초마다 브라우저 화면 비율을 확인해서, 바뀌었으면 게임 화면 크기를 맞춥니다.
        (전체 화면으로 바뀌거나, 주소창이 숨겨지거나, 휴대폰을 돌렸을 때)
        """
        self.size_check_timer -= dt
        if self.size_check_timer > 0:
            return
        self.size_check_timer = 0.5
        size = web_screen_size()
        if size and size != self.screen.get_size():
            self.screen = pygame.display.set_mode(size)
            refit_canvas()
            self.touch.set_size(size)
            self.update_camera()

    # ---------------- 상호작용 대상 찾기 ----------------
    def find_nearby(self):
        """플레이어와 가장 가까운 상호작용 대상(INTERACT_RANGE 안)을 찾습니다."""
        px, py = self.player.rect.center
        best, best_dist = None, INTERACT_RANGE
        for target in self.targets():
            if not target.can_interact(self):
                continue
            dist = ((target.rect.centerx - px) ** 2 + (target.rect.centery - py) ** 2) ** 0.5
            if dist <= best_dist:
                best, best_dist = target, dist
        return best

    # ---------------- 마을에 있는 것들 ----------------
    def targets(self):
        """지금 마을에 나와 있는 상호작용 대상 전부 (주민 + 보이는 오브젝트)"""
        return self.npcs + [obj for obj in self.objects if obj.visible(self)]

    def obstacles(self, *exclude):
        """지나갈 수 없는 사각형 목록: 벽 + 주민 + 단단한 오브젝트 (exclude는 제외)"""
        rects = [t.rect for t in self.targets() if t.solid and t not in exclude]
        return self.world.walls + rects

    # ---------------- 가방 ----------------
    def add_item(self, name, count=1):
        self.inventory[name] = self.inventory.get(name, 0) + count

    def has_item(self, name):
        return self.inventory.get(name, 0) > 0

    def use_item(self, name):
        """물건 하나를 씁니다. 다 쓰면 가방에서 사라짐"""
        if self.has_item(name):
            self.inventory[name] -= 1
            if self.inventory[name] == 0:
                del self.inventory[name]

    # ---------------- 상태 갱신 ----------------
    def update(self, dt):
        if self.state == STATE_MENU:
            return
        self.time += dt
        if getattr(self, "mode", "normal") == "time_attack" and self.state in (STATE_PLAYING, STATE_DIALOGUE):
            self.run_time += dt

        # 감염원 조사·제거 중에는 이동뿐 아니라 대화/결과 메시지 중에도 시간이 흐른다.
        infection_phase_active = self.quest.index in (7, 8)
        if infection_phase_active and self.state in (STATE_PLAYING, STATE_DIALOGUE):
            for level in self.stats.update(dt):
                self.show_toast(SPREAD_WARNINGS[level], WARNING_TIME, LIGHT_RED)
            if self.stats.is_lost():
                self.start_ending("bad")
                return

        if self.state == STATE_PROLOGUE:
            self.prologue_time += dt
            # 시간여행 연출이 끝나면 책의 요정 대사 시작
            if self.prologue_time >= TRAVEL_TIME and self.dialogue is None:
                self.dialogue = ui.Dialogue(PROLOGUE_DIALOGUE)

        elif self.state == STATE_PLAYING:
            # 회복 조건을 먼저 확인해 확산도 증가 직전에도 엔딩을 놓치지 않는다.
            self.check_quest()
            if self.state != STATE_PLAYING:
                return
            # [순서도] 플레이어 이동 (벽 + 주민 + 우물 등과 충돌)
            path_checker = getattr(self.world, "is_absolute_path", None)
            if path_checker is None:
                self.player.update(dt, self.obstacles(), self.touch.move_vector())
            else:
                self.player.update(dt, self.obstacles(),
                                   self.touch.move_vector(), path_checker)
            self.update_camera()
            # [순서도] NPC/오브젝트 상태 업데이트 (벽, 플레이어, 서로 부딪히지 않게)
            for npc in self.npcs:
                npc.update(dt, self.obstacles(npc) + [self.player.rect])
            for obj in self.objects:
                if obj.visible(self):
                    obj.update(dt, self.obstacles(obj))
            self.nearby = self.find_nearby()

            # [순서도] 마을 상태 업데이트 → 흑사병 수치 계산
            if not infection_phase_active:
                for level in self.stats.update(dt):
                    self.show_toast(SPREAD_WARNINGS[level], WARNING_TIME, LIGHT_RED)
            if self.stats.is_lost():
                self.start_ending("bad")

        elif self.state == STATE_ENDING:
            self.ending_time += dt

        if self.toast:
            self.toast[1] -= dt   # [글자, 남은 시간, 색]
            if self.toast[1] <= 0:
                self.toast = None

        # 대화창이 열려 있으면 글자를 한 글자씩 보여줌 (대화 중에는 플레이어가 멈춤)
        if self.dialogue:
            self.dialogue.update(dt)

    # ---------------- 화면 그리기 ----------------
    def draw_fairy_near_player(self):
        """플레이어 오른쪽 위에 책의 요정을 그립니다."""
        cam_x, cam_y = self.camera
        px, py = self.player.rect.center
        ui.draw_fairy(self.screen, (px - cam_x + 26, py - cam_y - 24), self.time)

    def label_pos(self, target, gap):
        """
        대상 머리 위 표시('!', [E] 안내)의 화면 위치.
        상태바에 가려지는 곳(북쪽 성문 등)이면 대상 아래쪽에 표시
        """
        cam_x, cam_y = self.camera
        x = target.rect.centerx - cam_x
        y = target.top - cam_y - gap
        if y < TOPBAR_HEIGHT + 30:
            y = target.rect.bottom - cam_y + 34 + gap
        return x, y

    def draw(self):
        if self.portrait:
            # 휴대폰이 세로면 게임 대신 '가로로 돌려주세요' 안내
            draw_rotate_notice(self.screen, self.time)
            pygame.display.flip()
            return

        if self.state == STATE_TITLE:
            self.title_mode_buttons = ui.draw_title_screen(self.screen, self.time, self.mode)

        elif self.state == STATE_PROLOGUE and self.prologue_time < TRAVEL_TIME:
            ui.draw_time_travel(self.screen, self.prologue_time, TRAVEL_TIME)

        else:
            # 마을 + 플레이어 + 요정 + 상단 상태바 (+ 대화창)
            self.world.draw(self.screen, self.camera)
            # 발밑(rect.bottom)이 위쪽인 캐릭터부터 그려야 앞뒤가 자연스럽게 겹침
            things = self.targets() + [self.player] + self.world.buildings
            for thing in sorted(things, key=lambda t: getattr(t, "depth_y", t.rect.bottom)):
                thing.draw(self.screen, self.camera, self.time)
            self.draw_fairy_near_player()
            # 퀘스트에 필요한 대상 머리 위에 '!' (가까이 가서 [E] 안내가 뜨면 '!'는 숨김)
            for target in self.targets():
                shown_hint = self.state == STATE_PLAYING and target is self.nearby
                wanted = any(self.quest.wants(e, target.id) for e in target.quest_events)
                if not shown_hint and wanted:
                    ui.draw_quest_marker(self.screen, self.label_pos(target, 0), self.time)
            # 상호작용 가능한 대상 머리 위에 [E] 안내
            if self.state == STATE_PLAYING and self.nearby:
                ui.draw_interact_hint(self.screen, self.label_pos(self.nearby, 4),
                                      self.nearby.interact_text(self),
                                      show_key=not self.touch.visible)
            ui.draw_top_bar(self.screen, self.quest.chapter["name"],
                            self.quest.objective_text(), self.stats, self.time)
            ui.draw_inventory(self.screen, self.inventory)
            if self.mode == "time_attack" and self.state != STATE_ENDING:
                ui.draw_stopwatch(self.screen, self.run_time)
            if self.toast:
                ui.draw_toast(self.screen, *self.toast)
            if self.dialogue:
                self.dialogue.draw(self.screen, self.time)
            elif self.state == STATE_PLAYING:
                # 휴대폰 조작 버튼 (대화창이 열려 있을 때는 숨김)
                label = self.nearby.button_label(self) if self.nearby else None
                self.touch.draw(self.screen, label)
            # 엔딩: 멈춘 마을 화면 위에 어두운 막 + 엔딩 글자
            if self.state == STATE_ENDING:
                final_time = self.run_time if self.mode == "time_attack" else None
                ui.draw_ending(self.screen, self.ending, self.stats, self.ending_time, final_time)
            if self.state == STATE_MENU:
                self.menu_buttons = ui.draw_menu_overlay(
                    self.screen, self.menu_page, self.inventory, self.stats,
                    self.menu_selected, self.menu_scroll)

        pygame.display.flip()

    # ---------------- 메인 루프 ----------------
    async def run(self):
        """
        async(비동기)로 만든 이유: 웹 브라우저에서 돌릴 때(pygbag)는 매 프레임마다
        await asyncio.sleep(0)으로 브라우저에게 잠깐 차례를 넘겨줘야 화면이 멈추지 않습니다.
        PC에서 실행할 때도 똑같이 동작합니다.
        """
        error = None   # 오류가 나면 내용을 저장해서 화면에 보여줌 (웹에서는 그냥 멈춘 것처럼 보이므로)
        while self.running:
            # dt = 지난 프레임부터 걸린 시간(초). 컴퓨터 속도와 상관없이 같은 속도로 움직이게 함
            # (탭 전환 등으로 오래 멈췄다 돌아와도 캐릭터가 순간이동하지 않게 최대 0.1초로 제한)
            dt = min(self.clock.tick(FPS) / 1000, 0.1)
            if error:
                error = self.run_error_screen(error)
            else:
                try:
                    self.portrait = is_portrait()
                    self.check_screen_size(dt)
                    self.handle_events()
                    if not self.portrait:          # 세로 화면이면 일시정지
                        self.update(dt)
                    self.draw()
                except Exception:
                    error = traceback.format_exc()
                    print(error)
            await asyncio.sleep(0)
        pygame.quit()

    def run_error_screen(self, error):
        """
        오류 화면 한 프레임. 화면을 캡처해서 보내면 원인을 찾을 수 있음.
        터치/Enter → 처음부터 다시 시작 (돌려주는 값이 None이면 오류 화면 끝)
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            pressed = (event.type == pygame.KEYDOWN and event.key in ADVANCE_KEYS) or                 event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN)
            if pressed:
                self.reset()
                return None
        if self.touch.poll_web():   # 휴대폰 터치
            self.reset()
            return None
        ui.draw_error(self.screen, error)
        pygame.display.flip()
        return error


if __name__ == "__main__":
    asyncio.run(Game().run())
