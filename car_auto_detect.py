#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""car_auto_detect.py

Xe chạy tự động kết hợp CAMERA (nhận diện người YOLO11n/HOG) + SIÊU ÂM HC-SR04.
- Có người phía trước (camera) hoặc vật gần < STOP_DISTANCE_CM  -> DỪNG xe.
- Đường thoáng (không có người + vật xa hơn SAFE_DISTANCE_CM)    -> xe chạy tiếp.
- Mỏ cửa sổ camera khi chạy để kiểm tra xem phần nhận diện có
  nhận diện được người hay không (nhìn box xanh + số Nguoi).

Chay:
    python3 car_auto_detect.py
    python3 car_auto_detect.py --fast

Controls:
    Q / ESC : thoat
    C       : bat / tat camera
"""

import argparse
import time

import cv2
from picamera2 import Picamera2

from pi4_camera import (
    CaptureThread,
    DetectorThread,
    draw_shadow,
    FAST_WIDTH,
    FAST_HEIGHT,
    FAST_FPS,
    FAST_DETECT_SCALE,
    FAST_YOLO_SIZE,
    WIDTH,
    HEIGHT,
    FPS,
    DETECT_SCALE,
    YOLO_SIZE,
)
from car_distance_stop import (
    tien,
    dung,
    do_khoang_cach,
    STBY_L,
    STBY_R,
    STOP_DISTANCE_CM,
    SAFE_DISTANCE_CM,
)

# ==================== LOGIC AN TOAN ====================
BLOCK_GRACE_S = 1.5      # sau khi sạch đường, giữ dừng thêm bao nhiêu giây
FRONT_BAND = 0.7         # dải ngang giữa khung hình coi là "phía trước xe"
MIN_AREA_RATIO = 0.004   # box người phải chiếm >= 0.4% diện tích ảnh mới tính
READ_INTERVAL = 0.05


def count_person_in_front(det, frame_w, frame_h):
    """Đếm box "người" nằm ở dải giữa (phía trước xe) và đủ lớn."""
    count = 0
    for label, color, x1, y1, x2, y2 in det.detections:
        if label != "nguoi":
            continue
        cx = (x1 + x2) / 2.0 / max(1, frame_w)
        if not (0.5 - FRONT_BAND / 2.0 <= cx <= 0.5 + FRONT_BAND / 2.0):
            continue
        area = (x2 - x1) * (y2 - y1)
        if area < MIN_AREA_RATIO * frame_w * frame_h:
            continue
        count += 1
    return count


def parse_args():
    parser = argparse.ArgumentParser(description="Xe tu dong: camera nhan dien nguoi + sieu am.")
    parser.add_argument("--fast", action="store_true", help="640x480 cho Pi 4")
    parser.add_argument("--conf", type=float, default=0.5, help="Nguong tin cay person")
    parser.add_argument("--detect-fps", type=float, default=8.0, help="Lan detect moi giay")
    return parser.parse_args()


def main():
    cv2.setUseOptimized(True)
    args = parse_args()

    width = FAST_WIDTH if args.fast else WIDTH
    height = FAST_HEIGHT if args.fast else HEIGHT
    fps = FAST_FPS if args.fast else FPS
    detect_scale = FAST_DETECT_SCALE if args.fast else DETECT_SCALE
    yolo_size = FAST_YOLO_SIZE if args.fast else YOLO_SIZE

    # ------ Camera ------
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(
        main={"size": (width, height), "format": "YUV420"},
        controls={"FrameRate": fps},
    ))

    capture = CaptureThread(picam2)
    capture.start()

    det = DetectorThread(work_width=detect_scale, yolo_size=yolo_size,
                         conf=args.conf, detect_fps=args.detect_fps)
    det.start()

    window = "Xe tu dong - Nhan dien nguoi"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    # ------ Xe ------
    STBY_L.on()
    STBY_R.on()
    print("TB6612 san sang. Nhan C de bat/tat camera, Q de thoat.")

    camera_on = False
    blocked_until = 0.0
    n_loop = 0
    last_distance = 999.0

    try:
        while True:
            frame = capture.latest() if camera_on else None

            if frame is not None:
                if det.loaded:
                    det.submit(frame)
                distance = do_khoang_cach() if n_loop % 2 == 0 else last_distance
                last_distance = distance
                n_loop += 1

                person = count_person_in_front(det, width, height)
                obstacle = distance < STOP_DISTANCE_CM

                now = time.time()
                if person > 0 or obstacle:
                    blocked_until = now + BLOCK_GRACE_S

                if now < blocked_until:
                    dung()
                    state = "DUNG (co nguoi/vat)"
                else:
                    tien()
                    state = "CHAY"

                # Ve box + thong tin len anh
                for label, color, x1, y1, x2, y2 in det.detections:
                    thickness = 2 if label == "nguoi" else 1
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                    draw_shadow(frame, label, (x1, max(y1 - 8, 20)), scale=0.55, color=color, thickness=1)

                draw_shadow(frame, state, (12, 30), scale=0.8,
                            color=(0, 0, 255) if now < blocked_until else (0, 255, 0))
                draw_shadow(frame, f"Nguoi truoc: {person}   Engine: {det.engine}",
                            (12, 62), scale=0.6)
                draw_shadow(frame, f"Khoang cach: {distance:6.1f} cm   (dung < {STOP_DISTANCE_CM:.0f})",
                            (12, 94), scale=0.6)
                draw_shadow(frame, f"Detect FPS: {det.detect_fps:5.1f}", (12, 126), scale=0.6)

            else:
                distance = do_khoang_cach()
                last_distance = distance
                n_loop += 1
                if distance < STOP_DISTANCE_CM:
                    dung()
                else:
                    tien()

            if frame is not None:
                cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("c"):
                if camera_on:
                    capture.set_running(False)
                    picam2.stop()
                    camera_on = False
                    print("[i] camera stopped")
                else:
                    picam2.start()
                    capture.set_running(True)
                    camera_on = True
                    print("[i] camera started")
            time.sleep(READ_INTERVAL)
    except KeyboardInterrupt:
        print("\nDung bang Ctrl+C.")
    finally:
        dung()
        if camera_on:
            capture.set_running(False)
            picam2.stop()
        STBY_L.off()
        STBY_R.off()
        cv2.destroyAllWindows()
        print("Hoan thanh.")


if __name__ == "__main__":
    main()