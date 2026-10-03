import cv2

camera = cv2.VideoCapture(0)

try:
    if not camera.isOpened():
        print("카메라를 열지 못했어요.")
    else:
        first_frame = True

        while True:
            success, frame = camera.read()

            if not success:     #읽기 실패 시 종료
                print("프레임을 읽지 못했어요.")
                break

            if first_frame:     #성공한 첫 프레임의 정보 출력
                print("프레임 크기:", frame.shape)
                print("자료형:", frame.dtype)
                first_frame = False

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cv2.imshow("Original Camera", frame)
            cv2.imshow("Gray Camera", gray)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
finally:
    camera.release()
    cv2.destroyAllWindows()