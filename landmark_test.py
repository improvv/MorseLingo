from pathlib import Path
import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from eye_metrics import RIGHT_EYE_INDICES, LEFT_EYE_INDICES, calculate_ear
from blink_tracker import BlinkTracker
from morse import duration_to_symbol, check_answer, encode_sentence
from sentence_overlay import SentenceOverlay


def request_sentence():
    # 카메라를 열기 전에 터미널에서 목표 문장을 받는다.
    # 잘못된 문자는 조용히 버리지 않고 사용자에게 다시 입력하도록 안내한다.
    while True:
        try:
            sentence = input("\n연습할 한글 문장 (종료: /q): ")
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return None
        if sentence.strip() == "/q":
            return None
        try:
            target = encode_sentence(sentence)
        except ValueError as error:
            print(error)
            continue
        print("문장:", target.text)
        print("모스부호:", target.display)
        print("구분: 자모 공백 / 글자 / / 단어 // (눈으로 구분자를 입력하지 않습니다)")
        return target


def practice_sentence(target, landmarker, overlay):
    # 함수가 다시 호출될 때 입력 상태도 새로 만들어진다.
    tracker = BlinkTracker()
    sequence = ""
    state = "READY"
    feedback = "눈을 뜨고 B를 눌러 시작하세요"
    previous_timestamp_ms = -1
    camera = cv2.VideoCapture(0)
    cv2.namedWindow("MorseLingo", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("MorseLingo", 1280, 1026)

    try:
        if not camera.isOpened():
            print("카메라를 열지 못했어요.")
            return False
        while True:
            success, frame = camera.read()
            if not success:
                print("프레임을 읽지 못했어요.")
                return False

            # 시간은 프레임 수가 아니라 단조 증가 시계로 측정한다.
            timestamp_ms = max(time.monotonic_ns() // 1_000_000, previous_timestamp_ms + 1)
            # 긴 영상 공백을 눈 감김 시간으로 계산하지 않는다.
            if previous_timestamp_ms >= 0 and timestamp_ms - previous_timestamp_ms > 1000:
                tracker.reset()
            previous_timestamp_ms = timestamp_ms
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            height, width = frame.shape[:2]
            eye_text = "얼굴 없음"

            if not result.face_landmarks:
                tracker.reset()
            for landmarks in result.face_landmarks:
                right_ear = calculate_ear(landmarks, RIGHT_EYE_INDICES, width, height)
                left_ear = calculate_ear(landmarks, LEFT_EYE_INDICES, width, height)
                if right_ear is None or left_ear is None:
                    tracker.reset()
                    eye_text = "눈 상태 확인 불가"
                    continue

                # 양눈이 모두 기준보다 작을 때 감김으로 판단한다.
                both_closed = right_ear < 0.15 and left_ear < 0.15
                eye_text = f"{'감김' if both_closed else '열림'} R {right_ear:.2f} / L {left_ear:.2f}"
                duration_ms = tracker.update(both_closed, timestamp_ms)
                if duration_ms is not None and state == "INPUT":
                    sequence += duration_to_symbol(duration_ms)
                    print(f"입력: {sequence} | 이번 감김: {duration_ms} ms")
                    # 목표 길이에 도달하면 멈춰 추가 자연 깜빡임이 섞이지 않게 한다.
                    if len(sequence) >= len(target.sequence):
                        state = "REVIEW"
                        feedback = "목표 길이 도달: S 제출 / X 수정 / C 다시 준비"

                # 영상에는 눈 점만 남기고 글씨는 위쪽 전용 패널에 표시한다.
                for landmark_index in RIGHT_EYE_INDICES + LEFT_EYE_INDICES:
                    point = landmarks[landmark_index]
                    cv2.circle(frame, (int(point.x * width), int(point.y * height)), 3, (0, 255, 0), -1)

            display = overlay.render(frame, target, sequence, state, feedback, eye_text)
            cv2.imshow("MorseLingo", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or cv2.getWindowProperty("MorseLingo", cv2.WND_PROP_VISIBLE) < 1:
                return False
            if key == ord("n"):
                # 카메라와 창을 정리한 뒤 터미널로 돌아가 새 문장을 받는다.
                return True
            if key == ord("b"):
                if state not in ("READY", "PAUSED"):
                    feedback = "C로 다시 준비하거나 X로 마지막 부호를 지우세요"
                elif not tracker.ready or tracker.was_closed:
                    feedback = "얼굴이 인식되고 눈을 뜬 상태에서 시작하세요"
                else:
                    state = "INPUT"
                    feedback = "입력 중: S 제출 / X 마지막 부호 지우기"
            elif key == ord("c"):
                sequence = ""
                state = "READY"
                tracker.reset()
                feedback = "초기화했어요. 눈을 뜨고 B로 시작하세요"
            elif key == ord("x"):
                # 삭제하는 동안 자연 깜빡임이 쌓이지 않도록 일시정지한다.
                sequence = sequence[:-1]
                tracker.reset()
                state = "PAUSED"
                feedback = "한 부호 삭제: X 추가 삭제 / B 이어 입력"
            elif key == ord("s"):
                if state not in ("INPUT", "REVIEW", "PAUSED"):
                    feedback = "먼저 B로 입력을 시작하세요"
                elif not tracker.ready or tracker.was_closed:
                    feedback = "얼굴이 인식되고 눈을 뜬 상태에서 제출하세요"
                elif not sequence:
                    feedback = "먼저 부호를 입력하세요"
                else:
                    state = "RESULT"
                    correct = check_answer(sequence, target.sequence)
                    feedback = "정답! N 새 문장 / C 다시 연습" if correct else "다시 해봐요. X 수정 / C 초기화"
                    print(feedback)
    finally:
        # 새 문장 입력이나 오류 발생 시에도 카메라 사용을 끝낸다.
        camera.release()
        cv2.destroyAllWindows()


def main():
    # 기존 카메라·EAR·시간 판정은 유지하고 목표만 터미널 입력으로 바꾼다.
    print("한글 문장 연습 모드 — 한글과 공백 지원, 최대 100자")
    print("보내주신 표 기준. 표에 없는 겹자모는 구성 자모로 나누는 앱 연습 규칙을 사용합니다.")
    print("목표의 글자 경계로 진행을 안내하며, 자유 문장을 해독하는 기능은 아닙니다.")
    target = request_sentence()
    if target is None:
        return
    model_path = Path(__file__).resolve().parent / "models" / "face_landmarker.task"
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )
    overlay = SentenceOverlay()
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        while target is not None:
            if not practice_sentence(target, landmarker, overlay):
                break
            target = request_sentence()


# 모듈을 가져오는 것만으로 카메라가 켜지지 않게 실행 진입점을 분리한다.
if __name__ == "__main__":
    main()
