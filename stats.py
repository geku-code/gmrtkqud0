# stats.py
# 마을 상태 수치(확산도, 신뢰도, 생존자)와 시간이 지나면 바뀌는 규칙을 담당하는 파일입니다.
# [순서도] 마을 상태 업데이트 → 흑사병 수치 계산
#
# 규칙 (숫자는 settings.py에서 바꿀 수 있음)
#   - 확산도: 플레이 중 SPREAD_INTERVAL초마다 +1 (대화 중에는 멈춤)
#   - 생존자: 확산도가 50 / 70 / 90 이상이면 각각 정해진 간격마다 -1 (확산도가 높을수록 빨리 줄어듦)
#   - 확산도가 50 / 70 / 90을 처음 넘으면 경고 (main.py에서 알림 표시)
#   - 확산도 100 또는 생존자 0 → 배드 엔딩

from settings import (START_SPREAD, START_TRUST, START_SURVIVORS,
                      SPREAD_INTERVAL, SURVIVOR_LOSS_LEVELS)


class PlagueStats:
    def __init__(self):
        self.values = {"spread": START_SPREAD,
                       "trust": START_TRUST,
                       "survivors": START_SURVIVORS}
        self.spread_timer = 0.0     # 다음 확산도 +1까지 쌓인 시간
        self.loss_timer = 0.0       # 다음 생존자 -1까지 쌓인 시간
        self.warned = set()         # 이미 경고한 확산도 단계 (같은 경고는 한 번만)

    # ui.draw_top_bar가 stats["spread"]처럼 읽을 수 있게 함
    def __getitem__(self, name):
        return self.values[name]

    def change(self, name, amount):
        """수치를 바꿉니다. 항상 0~100 사이로 유지"""
        self.values[name] = max(0, min(100, self.values[name] + amount))

    def loss_interval(self):
        """지금 확산도에서 생존자가 1명 줄어드는 간격(초). 줄지 않으면 None"""
        for level, interval in SURVIVOR_LOSS_LEVELS:   # 높은 단계부터 확인
            if self.values["spread"] >= level:
                return interval
        return None

    def update(self, dt):
        """
        플레이 중 매 프레임 호출합니다.
        확산도가 경고 단계(50/70/90)를 처음 넘으면 그 단계 숫자들을 목록으로 돌려줍니다.
        """
        # 1) 확산도: 일정 시간마다 +1
        self.spread_timer += dt
        while self.spread_timer >= SPREAD_INTERVAL:
            self.spread_timer -= SPREAD_INTERVAL
            self.change("spread", 1)

        # 2) 생존자: 확산도가 높으면 일정 시간마다 -1
        interval = self.loss_interval()
        if interval is None:
            self.loss_timer = 0.0
        else:
            self.loss_timer += dt
            while self.loss_timer >= interval:
                self.loss_timer -= interval
                self.change("survivors", -1)

        # 3) 경고 단계를 처음 넘었는지
        new_levels = []
        for level, _ in SURVIVOR_LOSS_LEVELS:
            if self.values["spread"] >= level and level not in self.warned:
                self.warned.add(level)
                new_levels.append(level)
        return sorted(new_levels)

    def is_lost(self):
        """배드 엔딩 조건: 확산도 100 또는 생존자 0"""
        return self.values["spread"] >= 100 or self.values["survivors"] <= 0
