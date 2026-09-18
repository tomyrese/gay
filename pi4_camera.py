#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 4 Camera Controller - Turbo Edition
================================================
Live preview with FPS overlay + real-time person detection
(MobileNet-SSD chay tren OpenCV DNN).

Toi uu tang FPS:
  * Capture native YUV420 -> chuyen doi BGR bang OpenCV (nhanh hon RGB888)
  * Thread rieng doc frame tu camera (vong display khong cho sensor)
  * Person detection chay trong thread rieng -> KHONG lam giam FPS hien thi
  * Detection chi tinh tren blob 300x300, chi ve hop len man hinh

Usage:
    python3 pi4_camera.py
    python3 pi4_camera.py --width 640 --height 480 --fps 90 --fullscreen
    python3 pi4_camera.py --fps 90 --detect-threshold 0.4

Controls (bam phim khi cua so preview dang mo):
    SPACE  : Bat / tat camera
    D      : Bat / tat person detection
    S      : Chup anh (luu thanh JPG)
    R      : Bat / tat quay video (luu thanh AVI)
    Q/ESC  : Thoat

Model (tu dong tai ve lan dau vao thu muc models/ ~23 MB):
    MobileNetSSD_deploy.prototxt + MobileNetSSD_deploy.caffemodel

Requirements (tren Raspberry Pi 4):
    pip3 install opencv-python-headless picamera2 numpy
    Chu y: picamera2 da co san trong Raspberry Pi OS Bookworm.
"""

import argparse
import shutil
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2

# ============================================================
# Cau hinh mac dinh
# ============================================================
WIDTH = 1280
HEIGHT = 720
FPS = 60
SAVE_DIR = "captures"
FULLSCREEN = False
DETECT_THRESHOLD = 0.45
PERSON_CLASS_ID = 15  # COCO / VOC: person

MODEL_DIR = Path(__file__).resolve().parent / "models"
PROTO = MODEL_DIR / "MobileNetSSD_deploy.prototxt"
CAFFE = MODEL_DIR / "MobileNetSSD_deploy.caffemodel"

PROTO_URLS = [
    "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/MobileNetSSD_deploy.prototxt",
    "https://raw.githubusercontent.com/djmv/MobilNet_SSD_opencv/master/MobileNetSSD_deploy.prototxt",
]
CAFFE_URLS = [
    "https://github.com/chuanqi305/MobileNet-SSD/raw/master/VGG/VOC0712/MobileNetSSD_deploy.caffemodel",
    "https://github.com/djmv/MobilNet_SSD_opencv/raw/master/MobileNetSSD_deploy.caffemodel",
]


def read_cpu_temp():
    """Doc nhiet do CPU tu sysfs cua Raspberry Pi."""
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError, IOError):
        return None


def _download(url, dest):
    print(f"[*] downloading {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.1"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)
        return dest.stat().st_size > 1000
    except Exception as exc:
        print(f"[!] download failed: {exc}")
        return False


def ensure_model():
    """Tai model MobileNet-SSD ve neu chua co."""
    if PROTO.exists() and CAFFE.exists() and CAFFE.stat().st_size > 1_500_000:
        return PROTO, CAFFE
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not PROTO.exists():
        for url in PROTO_URLS:
            if _download(url, PROTO):
                break
    if not CAFFE.exists():
        for url in CAFFE_URLS:
            if _download(url, CAFFE):
                break
    if not (PROTO.exists() and CAFFE.exists()):
        raise RuntimeError("Khong tai duoc model MobileNet-SSD, dung --no-detect de tat.")
    return PROTO, CAFFE


class CaptureThread(threading.Thread):
    """Doc frame lien tuc tu camera, vong display khong bao gio cho sensor."""

    def __init__(self, picam2):
        super().__init__(daemon=True)
        self.picam2 = picam2
        self._frame = None
        self._lock = threading.Lock()
        self.active = False

    def run(self):
        while True:
            if not self.active:
                time.sleep(0.005)
                continue
            try:
                yuv = self.picam2.capture_array()
                bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            except Exception:
                time.sleep(0.005)
                continue
            with self._lock:
                self._frame = bgr

    def latest(self):
        with self._lock:
            return self._frame

    def set_running(self, on):
        self.active = on
        if not on:
            with self._lock:
                self._frame = None


class DetectorThread(threading.Thread):
    """Nhan dien nguoi chay nend song song, khong chan vong display."""

    def __init__(self, confidence=DETECT_THRESHOLD):
        super().__init__(daemon=True)
        self.confidence = confidence
        self._frame = None
        self._new = threading.Event()
        self._lock = threading.Lock()
        self.detections = []
        self.detect_fps = 0.0
        self.loaded = False
        self.error = None

    def submit(self, frame):
        with self._lock:
            self._frame = frame
        self._new.set()

    def run(self):
        try:
            proto, caffemodel = ensure_model()
            net = cv2.dnn.readNetFromCaffe(str(proto), str(caffemodel))
            self.loaded = True
            print("[*] person detector ready (MobileNet-SSD)")
        except Exception as exc:
            self.error = str(exc)
            print(f"[!] detector unavailable: {exc}")
            return

        while True:
            self._new.wait()
            self._new.clear()
            with self._lock:
                frame = self._frame
            if frame is None:
                continue
            h, w = frame.shape[:2]
            if h == 0 or w == 0:
                continue

            t0 = time.perf_counter()
            blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
            net.setInput(blob)
            out = net.forward()

            rects, scores, found = [], [], []
            for i in range(out.shape[2]):
                conf = float(out[0, 0, i, 2])
                if conf < self.confidence:
                    continue
                if int(out[0, 0, i, 1]) != PERSON_CLASS_ID:
                    continue
                x1 = int(np.clip(out[0, 0, i, 3] * w, 0, w))
                y1 = int(np.clip(out[0, 0, i, 4] * h, 0, h))
                x2 = int(np.clip(out[0, 0, i, 5] * w, 0, w))
                y2 = int(np.clip(out[0, 0, i, 6] * h, 0, h))
                rects.append([x1, y1, x2 - x1, y2 - y1])
                scores.append(conf)
                found.append(("person", conf, x1, y1, x2, y2))

            keep = cv2.dnn.NMSBoxes(rects, scores, self.confidence, 0.4)
            keep = np.array(keep).reshape(-1).tolist() if keep is not None else []
            self.detections = [found[i] for i in keep]
            self.detect_fps = self._ema(time.perf_counter() - t0)

    def _ema(self, elapsed):
        instant = 1.0 / elapsed if elapsed > 0 else 0.0
        return instant if self.detect_fps <= 0 else self.detect_fps * 0.9 + instant * 0.1


def draw_shadow(overlay, text, pos, scale=0.6, color=(0, 255, 255), thickness=2):
    x, y = pos
    cv2.putText(overlay, text, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(overlay, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def parse_args():
    parser = argparse.ArgumentParser(description="Pi 4 camera + person detection + FPS overlay.")
    parser.add_argument("--width", type=int, default=WIDTH, help="Capture width (default %(default)s)")
    parser.add_argument("--height", type=int, default=HEIGHT, help="Capture height (default %(default)s)")
    parser.add_argument("--fps", type=int, default=FPS, help="Desired camera framerate (default %(default)s)")
    parser.add_argument("--save-dir", default=SAVE_DIR, help="Folder for photos/videos (default %(default)s)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch fullscreen preview")
    parser.add_argument("--detect", dest="detect", action="store_true", default=True, help="Enable person detection (default)")
    parser.add_argument("--no-detect", dest="detect", action="store_false", help="Disable person detection")
    parser.add_argument("--detect-threshold", type=float, default=DETECT_THRESHOLD,
                        help="Detection confidence threshold (default %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (args.width, args.height), "format": "YUV420"},
        controls={"FrameRate": args.fps},
    )
    picam2.configure(config)

    capture = CaptureThread(picam2)
    capture.start()

    det = DetectorThread(confidence=args.detect_threshold)
    det.start()

    window = "Pi 4 Camera"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    if args.fullscreen:
        cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    camera_on = False
    detect_on = args.detect
    recording = False
    writer = None
    fps = 0.0
    started_at = time.time()
    blank = np.zeros((args.height, args.width, 3), dtype=np.uint8)

    print("""
Pi 4 Camera Controller (Turbo)
==============================
Controls:
  SPACE : camera on/off         D : toggle person detection
  S     : take photo (JPG)      R : toggle video recording
  Q/ESC : quit
""")

    loop_t = time.perf_counter()

    while True:
        overlay = capture.latest() if camera_on else None

        if overlay is None:
            overlay = blank.copy()
            draw_shadow(overlay, "CAMERA IS OFF - press SPACE", (12, 40), scale=0.9, color=(0, 0, 255))
        else:
            if detect_on and det.loaded:
                det.submit(overlay)

            # Ghi hinh (truoc khi ve overlay de video sach)
            if recording:
                if writer is None:
                    path = save_dir / f"video_{datetime.now():%Y%m%d_%H%M%S}.avi"
                    writer = cv2.VideoWriter(
                        str(path),
                        cv2.VideoWriter_fourcc(*"MJPG"),
                        args.fps, (args.width, args.height),
                    )
                    print(f"[*] recording -> {path}")
                writer.write(overlay)

            temp = read_cpu_temp()
            temp_line = f"CPU Temp: {temp:.1f} C" if temp is not None else "CPU Temp: n/a"
            draw_shadow(overlay, f"FPS: {fps:6.1f}", (12, 30))
            draw_shadow(overlay, f"Detect FPS: {det.detect_fps:5.1f}", (12, 62))
            draw_shadow(overlay, f"Res: {args.width}x{args.height}  Rec: {'ON ' if recording else 'OFF'}", (12, 94))
            draw_shadow(overlay, f"{datetime.now():%Y-%m-%d %H:%M:%S}  Uptime: {int(time.time() - started_at)}s", (12, 126))
            draw_shadow(overlay, temp_line, (12, 158))

            if detect_on:
                if det.loaded:
                    for label, conf, x1, y1, x2, y2 in det.detections:
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        draw_shadow(overlay, f"{label} {conf:.2f}", (x1, max(y1 - 8, 20)),
                                    scale=0.55, color=(0, 255, 0), thickness=1)
                elif det.error:
                    draw_shadow(overlay, "Detector: unavailable", (12, 190), color=(0, 0, 255))
            else:
                draw_shadow(overlay, "Detection OFF", (12, 190), scale=0.55, color=(0, 165, 255))

        cv2.imshow(window, overlay)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord(" "):
            if camera_on:
                capture.set_running(False)
                picam2.stop()
                camera_on = False
                fps = 0.0
                print("[i] camera stopped")
            else:
                picam2.start()
                capture.set_running(True)
                camera_on = True
                print("[i] camera started")
        elif key == ord("d"):
            detect_on = not detect_on
            print(f"[i] person detection: {'ON' if detect_on else 'OFF'}")
        elif key == ord("s") and camera_on:
            path = save_dir / f"photo_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            cv2.imwrite(str(path), capture.latest())
            print(f"[+] photo saved -> {path}")
        elif key == ord("r"):
            recording = not recording
            if not recording and writer is not None:
                writer.release()
                writer = None
                print("[i] recording stopped")

        # FPS tinh theo toc do vong lap hien thi (EMA)
        elapsed = time.perf_counter() - loop_t
        if elapsed > 0:
            instant = 1.0 / elapsed
            fps = instant if fps <= 0 else fps * 0.9 + instant * 0.1
        loop_t = time.perf_counter()

    if writer is not None:
        writer.release()
    if camera_on:
        capture.set_running(False)
        picam2.stop()
    cv2.destroyAllWindows()
    print("[i] bye")


if __name__ == "__main__":
    main()