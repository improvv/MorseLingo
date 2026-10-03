class BlinkTracker:
    # 객체를 만들 때 측정 상태를 초기화한다.
    def __init__(self):
        self.reset()

    def reset(self):
        # 처음 시작하거나 추적이 끊기면 이전 상태를 버린다.
        self.was_closed = False
        self.closed_start_ms = None

        # 먼저 눈을 뜬 상태를 확인해야 측정을 시작한다.
        # 이미 감긴 눈을 발견했을 때 중간부터 시간을 재는 것을 막는다.
        self.ready = False

    def update(self, is_closed, timestamp_ms):
        # 눈 상태를 알 수 없으면 진행 중인 측정을 취소한다.
        if is_closed is None:
            self.reset()
            return None

        # 시작·초기화 후에는 눈을 뜬 상태가 관찰될 때까지 기다린다.
        if not self.ready:
            if not is_closed:
                self.ready = True
            return None

        # 기본적으로는 완료된 감김 동작이 없다.
        duration_ms = None

        if is_closed and not self.was_closed:
            # 열림 → 감김: 시작 시간을 기록한다.
            self.closed_start_ms = timestamp_ms

        elif not is_closed and self.was_closed:
            # 감김 → 열림: 완료된 동작의 지속 시간을 계산한다.
            if self.closed_start_ms is not None:
                duration_ms = timestamp_ms - self.closed_start_ms

            self.closed_start_ms = None

        # 다음 프레임과 비교하기 위해 현재 상태를 저장한다.
        self.was_closed = is_closed

        # 다시 뜬 순간에만 시간을 반환하고, 나머지는 None을 반환한다.
        return duration_ms