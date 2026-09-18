#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 4 Camera Controller - Turbo Edition v3
===================================================
Live preview with FPS overlay + multi-class detection:
    - NGUOI      (full body, engine: HOG + Haar fullbody)
    - THAN TREN  (upper body, Haar)
    - THAN DUOI  (lower body, Haar)
    - MAT        (face, Haar)

Detection dung phan mem CO SAN trong OpenCV (khong tai model):
  * HOG people detector      -> bat nguoi chinh xac
  * Haar cascades (cv2.data) -> than tren / than duoi / mat
  * Cascade path co fallback nhieu duong dan, khong crash khi thieu file
  * equalizeHist giup Haar nhan dien tot ca khi thieu sang

Toi uu FPS:
  * Capture native YUV420 -> chuyen doi BGR nhanh
  * Capture thread + detection thread -> vong display khong bi chan
  * Detection tinh tren anh thu nho (--detect-scale) roi scale box ve man hinh

Usage:
    python3 pi4_camera.py
    python3 pi4_camera.py --width 640 --height 480 --fps 90 --fullscreen
    python3 pi4_camera.py --detect-scale 480

Controls:
    SPACE  : Bat / tat camera
    D      : Bat / tat detection
    S      : Chup anh (JPG)
    R      : Bat / tat quay video (AVI)
    Q/ESC  : Thoat
"""

import argparse
import os
import threading
import time
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
DETECT_SCALE = 640  # do rong anh dung de detect (nho = nhanh hon)

# (file cascade, mau BGR, minSize tren anh detect, minNeighbors)
CASCADES = {
    "person": ("haarcascade_fullbody.xml", (0, 255, 0), (40, 80), 4),
    "upper": ("haarcascade_upperbody.xml", (0, 165, 255), (40, 50), 4),
    "lower": ("haarcascade_lowerbody.xml", (255, 0, 0), (40, 50), 4),
    "face": ("haarcascade_frontalface_default.xml", (255, 255, 0), (22, 22), 5),
}

# Ten hien thi cho tung lop
LABELS = {
    "person": "nguoi",
    "upper": "than_tren",
    "lower": "than_duoi",
    "face": "mat",
}


def read_cpu_temp():
    """Doc nhiet do CPU tu sysfs cua Raspberry Pi."""
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError, IOError):
        return None


def cascade_candidates():
    """Gom cac duong dan toi thu muc haarcascades co the co."""
    dirs = []
    try:
        dirs.append(cv2.data.haarcascades)
    except AttributeError:
        pass
    for path in (
        "/usr/share/opencv4/haarcascades/",
        "/usr/share/opencv/haarcascades/",
        "/usr/local/share/opencv4/haarcascades/",
        "/usr/local/share/opencv/haarcascades/",
    ):
        dirs.append(path)
    return dirs


def find_cascade(fname):
    """Tra ve duong dan cascade ton tai, else None."""
    for d in cascade_candidates():
        path = os.path.join(d, fname)
        if os.path.isfile(path):
            return path
    return None


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
    """Detect nguoi / than tren / than duoi / mat chay song song."""

    def __init__(self, work_width=DETECT_SCALE):
        super().__init__(daemon=True)
        self.work_width = max(work_width, 320)
        self._frame = None
        self._new = threading.Event()
        self._lock = threading.Lock()
        self.detections = []  # list of (label, color, x1, y1, x2, y2)
        self.detect_fps = 0.0
        self.loaded = False
        self.error = None
        self._warned = False

    def submit(self, frame):
        with self._lock:
            self._frame = frame
        self._new.set()

    def run(self):
        cascades = {}
        for label, (fname, color, minsize, minn) in CASCADES.items():
            path = find_cascade(fname)
            if path is None:
                print(f"[w] cascade khong tim thay: {fname} -> bo qua lop '{label}'")
                continue
            cascade = cv2.CascadeClassifier(path)
            if cascade.empty():
                print(f"[w] cascade loi: {path} -> bo qua lop '{label}'")
                continue
            cascades[label] = (cascade, color, minsize, minn)

        if not cascades:
            self.error = "Khong co cascade nao tai duoc"
            print(f"[!] {self.error}")
            return

        # HOG people detector duoc tich hop san trong OpenCV
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self.loaded = True
        names = ", ".join(LABELS[k] for k in cascades)
        print(f"[*] detector ready: {names} + person(HOG)")

        while True:
            self._new.wait()
            self._new.clear()
            with self._lock:
                frame = self._frame
            if frame is None:
                continue
            t0 = time.perf_counter()
            try:
                self.detections = self._detect(frame, cascades, hog)
            except Exception as exc:
                if not self._warned:
                    self._warned = True
                    print(f"[w] loi detection (bo qua): {exc}")
            self.detect_fps = self._ema(time.perf_counter() - t0)

    def _detect(self, frame, cascades, hog):
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = self.work_width / float(w)
        if scale < 1.0:
            small = cv2.resize(
                gray, (self.work_width, max(1, int(h * scale))),
                interpolation=cv2.INTER_AREA,
            )
        else:
            scale = 1.0
            small = gray

        # Tang tuong phan giup Haar nhan dien tot khi thieu sang
        small_eq = cv2.equalizeHist(small)
        inv = 1.0 / scale
        results = []
        persons = []

        # Haar: than tren / than duoi / mat + fullbody
        for label, (cascade, color, minsize, minn) in cascades.items():
            rects = cascade.detectMultiScale(
                small_eq, scaleFactor=1.05, minNeighbors=minn, minSize=minsize,
            )
            if len(rects) == 0:
                continue
            for (x, y, bw, bh) in rects:
                x1, y1 = int(x * inv), int(y * inv)
                x2, y2 = int((x + bw) * inv), int((y + bh) * inv)
                if label == "person":
                    persons.append((x1, y1, x2 - x1, y2 - y1))
                else:
                    results.append((LABELS[label], color, x1, y1, x2, y2))

        # Neu Haar fullbody chua thay nguoi -> chay HOG people detector
        if not persons:
            rects, _ = hog.detectMultiScale(
                small, winStride=(8, 8), padding=(8, 8), scale=1.05,
            )
            if len(rects) > 0:
                for (x, y, bw, bh) in rects:
                    x1, y1 = int(x * inv), int(y * inv)
                    x2, y2 = int((x + bw) * inv), int((y + bh) * inv)
                    persons.append((x1, y1, x2 - x1, y2 - y1))

        # Gom cac box nguoi trung nhau
        for (x, y, bw, bh) in self._nms(persons):
            results.append(("nguoi", (0, 255, 0), x, y, x + bw, y + bh))

        return results

    @staticmethod
    def _iou(a, b):
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[0] + a[2], b[0] + b[2])
        y2 = min(a[1] + a[3], b[1] + b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter <= 0:
            return 0.0
        union = a[2] * a[3] + b[2] * b[3] - inter
        return inter / union if union > 0 else 0.0

    def _nms(self, boxes, thresh=0.4):
        boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
        keep = []
        for b in boxes:
            if all(self._iou(b, k) < thresh for k in keep):
                keep.append(b)
        return keep

    def _ema(self, elapsed):
        instant = 1.0 / elapsed if elapsed > 0 else 0.0
        return instant if self.detect_fps <= 0 else self.detect_fps * 0.9 + instant * 0.1


def draw_shadow(overlay, text, pos, scale=0.6, color=(0, 255, 255), thickness=2):
    x, y = pos
    cv2.putText(overlay, text, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(overlay, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def parse_args():
    parser = argparse.ArgumentParser(description="Pi 4 camera + person/upper/lower/face detection + FPS overlay.")
    parser.add_argument("--width", type=int, default=WIDTH, help="Capture width (default %(default)s)")
    parser.add_argument("--height", type=int, default=HEIGHT, help="Capture height (default %(default)s)")
    parser.add_argument("--fps", type=int, default=FPS, help="Desired camera framerate (default %(default)s)")
    parser.add_argument("--save-dir", default=SAVE_DIR, help="Folder for photos/videos (default %(default)s)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch fullscreen preview")
    parser.add_argument("--detect-scale", type=int, default=DETECT_SCALE,
                        help="Detection working width; smaller = faster (default %(default)s)")
    parser.add_argument("--detect", dest="detect", action="store_true", default=True, help="Enable detection (default)")
    parser.add_argument("--no-detect", dest="detect", action="store_false", help="Disable detection")
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

    det = DetectorThread(work_width=args.detect_scale)
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
Pi 4 Camera Controller (Turbo v3)
=================================
Controls:
  SPACE : camera on/off         D : toggle detection
  S     : take photo (JPG)      R : toggle video recording
  Q/ESC : quit

Detection colors:
  green  = nguoi       orange = than_tren
  blue   = than_duoi   cyan   = mat
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
                    for label, color, x1, y1, x2, y2 in det.detections:
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
                        draw_shadow(overlay, label, (x1, max(y1 - 8, 20)),
                                    scale=0.55, color=color, thickness=1)
                elif det.error:
                    draw_shadow(overlay, f"Detector: {det.error}", (12, 190), color=(0, 0, 255))
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
            print(f"[i] detection: {'ON' if detect_on else 'OFF'}")
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