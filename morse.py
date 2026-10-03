import unicodedata
from dataclasses import dataclass

# 0.3초 미만은 점, 0.3초 이상은 선으로 판정한다.
# 342ms처럼 비교적 짧게 감아도 선을 입력할 수 있도록 낮춘 기준이다.
DOT_DASH_THRESHOLD_MS = 300

# 사용자가 제공한 한글 부호표를 옮긴 것이다. 국제 영문 부호표와 다르다.
HANGUL_MORSE = {
    "ㄱ": ".-..", "ㄴ": "..-.", "ㄷ": "-...", "ㄹ": "...-",
    "ㅁ": "--", "ㅂ": ".--", "ㅅ": "--.", "ㅇ": "-.-",
    "ㅈ": ".--.", "ㅊ": "-.-.", "ㅋ": "-..-", "ㅌ": "--..",
    "ㅍ": "---", "ㅎ": ".---",
    "ㅏ": ".", "ㅑ": "..", "ㅓ": "-", "ㅕ": "...", "ㅗ": ".-",
    "ㅛ": "-.", "ㅜ": "....", "ㅠ": ".-.", "ㅡ": "-..", "ㅣ": "..-",
    "ㅐ": "--.-", "ㅔ": "-.--", "ㅚ": ".-..-", "ㅟ": "....-", "ㅢ": "-...-",
}

# 표에 없는 겹자모는 아래 구성 자모 순서로 연습한다.
# 이것은 앱의 명시적인 확장 규칙이며 별도의 표준 송신 규칙 주장이 아니다.
COMPOUND_JAMO = {
    "ㄲ": "ㄱㄱ", "ㄸ": "ㄷㄷ", "ㅃ": "ㅂㅂ", "ㅆ": "ㅅㅅ", "ㅉ": "ㅈㅈ",
    "ㄳ": "ㄱㅅ", "ㄵ": "ㄴㅈ", "ㄶ": "ㄴㅎ", "ㄺ": "ㄹㄱ", "ㄻ": "ㄹㅁ",
    "ㄼ": "ㄹㅂ", "ㄽ": "ㄹㅅ", "ㄾ": "ㄹㅌ", "ㄿ": "ㄹㅍ", "ㅀ": "ㄹㅎ",
    "ㅄ": "ㅂㅅ", "ㅒ": "ㅑㅣ", "ㅖ": "ㅕㅣ", "ㅘ": "ㅗㅏ", "ㅙ": "ㅗㅐ",
    "ㅝ": "ㅜㅓ", "ㅞ": "ㅜㅔ",
}
INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
FINALS = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")


@dataclass(frozen=True)
class MorseUnit:
    # 원문 글자와 자모, 해당 자모의 부호 범위를 함께 보관한다.
    source_index: int
    character: str
    jamo: str
    code: str
    start: int
    end: int


@dataclass(frozen=True)
class MorseTarget:
    text: str
    units: tuple[MorseUnit, ...]
    sequence: str
    display: str


def duration_to_symbol(duration_ms):
    return "." if duration_ms < DOT_DASH_THRESHOLD_MS else "-"


def check_answer(sequence, target):
    return sequence == target


def split_character(character):
    # 유니코드 완성형 한글을 초성·중성·종성으로 분해한다.
    offset = ord(character) - ord("가")
    if 0 <= offset < 11172:
        return INITIALS[offset // 588] + VOWELS[(offset % 588) // 28] + FINALS[offset % 28]
    if character in HANGUL_MORSE or character in COMPOUND_JAMO:
        return character
    raise ValueError(f"지원하지 않는 문자: {character!r}. 현재 한글과 공백만 입력할 수 있어요.")


def encode_sentence(text):
    # 분해형 한글도 정규화하고 연속 공백은 한 칸으로 통일한다.
    text = " ".join(unicodedata.normalize("NFC", text).split())
    if not text:
        raise ValueError("한글 문장을 입력해주세요.")
    if len(text) > 100:
        raise ValueError("한 번에 100자 이하로 입력해주세요.")

    units = []
    offset = 0
    display_parts = []
    separator = ""
    for source_index, character in enumerate(text):
        if character == " ":
            separator = " // "
            continue
        codes = []
        for jamo in split_character(character):
            for basic_jamo in COMPOUND_JAMO.get(jamo, jamo):
                code = HANGUL_MORSE[basic_jamo]
                units.append(MorseUnit(source_index, character, basic_jamo, code, offset, offset + len(code)))
                offset += len(code)
                codes.append(code)
        display_parts.append(separator + " ".join(codes))
        separator = " / "

    return MorseTarget(text, tuple(units), "".join(unit.code for unit in units), "".join(display_parts))


def matching_prefix(sequence, target):
    # 입력 개수와 실제로 처음부터 맞춘 길이를 구분한다.
    matched = 0
    for actual, expected in zip(sequence, target):
        if actual != expected:
            break
        matched += 1
    return matched


def completed_text(target, matched):
    # 정답 접두부가 한 글자의 모든 자모를 덮었을 때만 완료된 글자로 센다.
    completed_end = 0
    for unit_index, unit in enumerate(target.units):
        last_in_character = (
            unit_index + 1 == len(target.units)
            or target.units[unit_index + 1].source_index != unit.source_index
        )
        if last_in_character and unit.end <= matched:
            completed_end = unit.source_index + 1
    return target.text[:completed_end]
