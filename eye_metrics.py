import math

# 각 눈의 양 끝점, 위쪽 눈꺼풀, 아래쪽 눈꺼풀에 해당하는 번호다.
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


def calculate_ear(face_landmarks, eye_indices, width, height):
    # 정규화 좌표를 픽셀 좌표로 변환한다.
    # 가로·세로에 각각 영상 너비·높이를 적용해야 거리가 올바르게 계산된다.
    points = [
        (
            face_landmarks[index].x * width,
            face_landmarks[index].y * height,
        )
        for index in eye_indices
    ]

    # 눈 양 끝점 사이의 가로 길이다.
    horizontal = math.dist(points[0], points[3])

    # 위·아래 눈꺼풀의 세로 간격을 두 곳에서 측정한다.
    vertical_first = math.dist(points[1], points[5])
    vertical_second = math.dist(points[2], points[4])

    # 가로 길이가 거의 0이면 유효한 비율을 구할 수 없다.
    if horizontal < 1e-6:
        return None

    # 세로 간격의 평균을 가로 길이로 나눈다.
    return (vertical_first + vertical_second) / (2.0 * horizontal)