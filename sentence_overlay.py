import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from morse import completed_text, matching_prefix


class SentenceOverlay:
    def __init__(self):
        # macOS의 한글 글꼴을 사용한다. 글꼴은 프레임마다 다시 읽지 않는다.
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        self.font = ImageFont.truetype(font_path, 23)
        self.symbol_font = ImageFont.truetype(font_path, 32)
        self.small_font = ImageFont.truetype(font_path, 19)

    def render(self, frame, target, sequence, state, feedback, eye_text):
        # 패널을 영상 위에 덮지 않고 별도 영역으로 붙여 눈을 가리지 않는다.
        width = min(1280, frame.shape[1])
        if frame.shape[1] != width:
            frame = cv2.resize(frame, (width, round(frame.shape[0] * width / frame.shape[1])))
        panel = Image.new("RGB", (width, 306), (15, 18, 24))
        draw = ImageDraw.Draw(panel)
        white, muted = (245, 247, 250), (170, 181, 197)

        def text_line(position, text, font=self.font, color=white):
            # 긴 문장이 패널 밖으로 잘리지 않도록 말줄임 처리한다.
            available = width - position[0] - 20
            if draw.textlength(text, font=font) > available:
                while text and draw.textlength(text + "…", font=font) > available:
                    text = text[:-1]
                text += "…"
            draw.text(position, text, font=font, fill=color)

        matched = matching_prefix(sequence, target.sequence)
        total = len(target.sequence)
        # 긴 부호열은 입력 커서가 속한 페이지를 자동으로 보여준다.
        cell_width = 21
        columns = max(1, (width - 130) // cell_width)
        cursor = min(len(sequence), total - 1)
        display_cursor = 0
        symbol_index = 0
        for display_index, symbol in enumerate(target.display):
            if symbol in ".-":
                if symbol_index == cursor:
                    display_cursor = display_index
                    break
                symbol_index += 1
        start = (display_cursor // columns) * columns
        segment = target.display[start:start + columns]
        symbol_index = sum(symbol in ".-" for symbol in target.display[:start])

        text_line((20, 10), f"문장: {target.text}")
        draw.text((20, 52), "목표", font=self.font, fill=white)
        draw.text((20, 97), "내 입력", font=self.font, fill=white)
        for column, expected in enumerate(segment):
            position_x = 115 + column * cell_width
            draw.text((position_x, 45), expected, font=self.symbol_font, fill=white)
            if expected in ".-":
                actual = sequence[symbol_index] if symbol_index < len(sequence) else "_"
                color = muted if actual == "_" else ((100, 238, 174) if actual == expected else (255, 115, 130))
                draw.text((position_x, 90), actual, font=self.symbol_font, fill=color)
                if symbol_index == len(sequence):
                    draw.line((position_x, 132, position_x + 15, 132), fill=white, width=3)
                symbol_index += 1
            else:
                # 자모·글자·단어 구분자는 목표를 기준으로 자동 표시한다.
                draw.text((position_x, 90), expected, font=self.symbol_font, fill=muted)

        pages = max(1, math.ceil(len(target.display) / columns))
        text_line((20, 140), f"입력 {len(sequence)}/{total}개 | 처음부터 일치 {matched}/{total}개 | 표시 {start // columns + 1}/{pages}", self.small_font)
        done = completed_text(target, matched) or "아직 없음"
        text_line((20, 167), f"목표 기준 완료: {done}", self.small_font)
        next_unit = next((unit for unit in target.units if unit.end > matched), None)
        if matched < min(len(sequence), total):
            guide = f"{matched + 1}번째 부호가 달라요. X로 뒤에서부터 지우거나 C로 다시 준비하세요."
        elif next_unit:
            guide = f"다음: '{next_unit.character}'의 {next_unit.jamo} ({next_unit.code})"
        else:
            guide = "목표 부호 입력 완료! S로 제출하세요."
        text_line((20, 194), guide, self.small_font)
        text_line((20, 221), f"{state} | {feedback} | {eye_text}", self.small_font)
        text_line((20, 251), "B 시작 · S 제출 · X 한 부호 지우기 · C 초기화 · N 새 문장 · Q 종료", self.small_font)
        text_line((20, 276), "구분: 자모 사이 공백 / 글자 사이 / / 단어 사이 // (구분자는 자동 표시)", self.small_font, muted)

        # Pillow는 RGB, OpenCV는 BGR을 사용하므로 변환 후 세로로 합친다.
        return np.vstack((cv2.cvtColor(np.asarray(panel), cv2.COLOR_RGB2BGR), frame))
