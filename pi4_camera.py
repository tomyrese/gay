#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 4 Camera Controller - Turbo v7 (toc do hoa)
========================================================
Live preview with FPS overlay + detection:
    - NGUOI      (full body)   -> YOLO11n (ONNX, OpenCV DNN)
    - THAN TREN  (upper body)  -> nua tren box nguoi
    - THAN DUOI  (lower body)  -> nua duoi box nguoi
    - MAT        (face)        -> Haar cascade (co san trong OpenCV)

Khac phuc "treo" va toi uu toc do:
  * Model YOLO tai NEN (background) - khong bao gio chan khoi dong.
    He thong chay HOG ngay lap tuc, tu nang cap len YOLO khi tai xong.
  * YOLO input mac dinh 320 (nhanh cho Pi 4), dung --yolo-size 640 neu can chu xac.
  * Capture YUV420 + capture thread + detection thread => display FPS con cao.
  * Nen khong lay duoc model (mang cham) thi van chay duoc voi HOG.

Cai dat tren Raspberry Pi 4 (lam 1 lan):
    pip3 install --upgrade opencv-python-headless picamera2 numpy

Usage (kHUYEN DUNG cho Pi 4):
    python3 pi4_camera.py --fast
    python3 pi4_camera.py                              # mac dinh
    python3 pi4_camera.py --yolo-size 640 --conf 0.4   # chat luong cao hon

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
DETECT_SCALE = 480    # do rong anh dung cho face / hog fallback
YOLO_SIZE = 320       # YOLO input: 320 nhanh (Pi4), 640 chinh xac hon
YOLO_CONF = 0.5       # nguong tin cay person
YOLO_CLASSES = 80     # COCO80
PERSON_CLASS = 0      # COCO80: 0 = "person"

# preset --fast
FAST_WIDTH = 640
FAST_HEIGHT = 480
FAST_FPS = 60
FAST_DETECT_SCALE = 480
FAST_YOLO_SIZE = 320

GREEN = (0, 255, 0)
ORANGE = (0, 165, 255)
BLUE = (255, 0, 0)
CYAN = (255, 255, 0)

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR / "models"
YOLO_ONNX = MODEL_DIR / "yolo11n.onnx"
YOLO_ONNX_LOCAL = SCRIPT_DIR / "yolo11n.onnx"   # manh de dat model ngay canh script
YOLO_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.onnx"
MIN_YOLO_BYTES = 5_000_000


def ensure_model():
    """Tim model co san (models/ hoac canh script); chi tai mang neu chua co.
    Tra ve path hop le hoac None."""
    for p in (YOLO_ONNX, YOLO_ONNX_LOCAL):
        if p.exists() and p.stat().st_size > MIN_YOLO_BYTES:
            return p

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not _download(YOLO_URL, YOLO_ONNX, needs_bytes=MIN_YOLO_BYTES):
        return None
    return YOLO_ONNX


def read_cpu_temp():
    """Doc nhiet do CPU tu sysfs cua Raspberry Pi."""
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError, IOError):
        return None


def _download(url, dest, needs_bytes=0):
    for attempt in range(1, 4):
        try:
            print(f"[*] tai {os.path.basename(str(dest))} (lan {attempt}/3) ...")
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.1"})
            with urllib.request.urlopen(req, timeout=90) as resp, open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            size = dest.stat().st_size
            if size > needs_bytes:
                print(f"[+] xong: {size // 1024 // 1024} MB")
                return True
            print("[!] file khong hop le (qua nho) -> xoa, thu lai")
            dest.unlink(missing_ok=True)
        except Exception as exc:
            print(f"[!] loi download: {exc}")
    return False


def load_yolo():
    """Tra ve (net, meta) hoac raise khi khong dung duoc."""
    model = ensure_model()
    if model is None:
        raise RuntimeError("Khong tai duoc model YOLO11n")
    net = cv2.dnn.readNetFromONNX(str(model))
    return net, {"classes": YOLO_CLASSES, "person": PERSON_CLASS}


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
    """Detection chay song song; tai YOLO nen khong chong khoi dong."""

    def __init__(self, work_width=DETECT_SCALE, yolo_size=YOLO_SIZE, conf=YOLO_CONF):
        super().__init__(daemon=True)
        self.work_width = max(work_width, 320)
        self.yolo_size = max(yolo_size, 288)
        self.confidence = conf
        self._frame = None
        self._new = threading.Event()
        self._lock = threading.Lock()
        self.detections = []  # list of (label, color, x1, y1, x2, y2)
        self.detect_fps = 0.0
        self.loaded = False
        self.error = None
        self.yolo = None       # (net, meta) khi YOLO san sang
        self.hog = None
        self.person_cascade = None
        self.face = None
        self.engine = "loading"
        self.once_warned = False

    def submit(self, frame):
        with self._lock:
            self._frame = frame
        self._new.set()

    def run(self):
        # --- Face cascade (co san trong OpenCV) ---
        path = find_cascade("haarcascade_frontalface_default.xml")
        if path:
            fc = cv2.CascadeClassifier(path)
            if not fc.empty():
                self.face = fc
                print("[*] face cascade: OK")
        else:
            print("[w] khong tim thay face cascade: bo qua mat")

        # --- HOG fallback (built-in) dung ngay lap tuc ---
        try:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.engine = "hog"
            print("[i] engine tam thoi: HOG")
        except Exception as exc:
            print(f"[i] HOG khong co (OpenCV 5+ bo HOG?) -> dung Haar person: {exc}")
            for cfile in ("haarcascade_fullbody.xml", "haarcascade_upperbody.xml"):
                cpath = find_cascade(cfile)
                if cpath:
                    pc = cv2.CascadeClassifier(cpath)
                    if not pc.empty():
                        self.person_cascade = pc
                        self.engine = "haar_person"
                        print(f"[i] engine tam thoi: Haar ({cfile})")
                        break

        # --- Tai YOLO11n tren nen (KHONG chan nha) ---
        model_available = any(
            p.exists() and p.stat().st_size > MIN_YOLO_BYTES
            for p in (YOLO_ONNX, YOLO_ONNX_LOCAL)
        )
        if model_available:
            print("[i] model YOLO11n co san -> dang nap engine...")
        else:
            print("[i] model YOLO11n chua co -> tai nen (xem log), van chay fallback...")
        loader = threading.Thread(target=self._load_yolo_bg, daemon=True)
        loader.start()

        if self.face is None and self.hog is None and self.person_cascade is None:
            self.error = "Khong co engine nhan dien nao hoat dong"
            print(f"[!] {self.error}")
            return

        self.loaded = True

        while True:
            self._new.wait()
            self._new.clear()
            with self._lock:
                frame = self._frame
            if frame is None:
                continue
            t0 = time.perf_counter()
            try:
                self.detections = self._detect(frame)
            except Exception as exc:
                if not self.once_warned:
                    self.once_warned = True
                    print(f"[w] loi detection (bo qua 1 khung): {exc}")
            self.detect_fps = self._ema(time.perf_counter() - t0)

    def _load_yolo_bg(self):
        try:
            yolo = load_yolo()
            self.yolo = yolo
            self.engine = "yolo11n"
            print("[*] YOLO11n san sang (engine da nang cap)")
        except Exception as exc:
            print(f"[!] khong dung duoc YOLO11n, giu engine hien tai: {exc}")

    # ----------------------------------------------------------
    # Main detect: person -> upper/lower -> face
    # ----------------------------------------------------------
    def _detect(self, frame):
        results = []

        if self.yolo is not None:
            person_boxes = self._yolo_person(frame, self.yolo)
        elif self.hog is not None:
            person_boxes = self._hog_person(frame, self.hog)
        elif self.person_cascade is not None:
            person_boxes = self._cascade_person(frame, self.person_cascade)
        else:
            person_boxes = []

        person_boxes = self._nms(person_boxes)

        # NGUOI + THAN TREN + THAN DUOI (chia hinh hoc tu box nguoi)
        for (x, y, bw, bh) in person_boxes:
            results.append(("nguoi", GREEN, x, y, x + bw, y + bh))
            mid = y + int(bh * 0.5)
            results.append(("than_tren", ORANGE, x, y, x + bw, mid))
            results.append(("than_duoi", BLUE, x, mid, x + bw, y + bh))

        # MAT (Haar frontface), chay tren anh thu nho cho nhanh
        if self.face is not None:
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            scale = self.work_width / float(w)
            if scale < 1.0:
                small = cv2.resize(gray, (self.work_width, max(1, int(h * scale))),
                                   interpolation=cv2.INTER_AREA)
            else:
                scale = 1.0
                small = gray
            small = cv2.equalizeHist(small)
            inv = 1.0 / scale
            faces = self.face.detectMultiScale(small, scaleFactor=1.1, minNeighbors=6,
                                               minSize=(24, 24))
            for (x, y, bw, bh) in faces:
                results.append(("mat", CYAN, int(x * inv), int(y * inv),
                                int((x + bw) * inv), int((y + bh) * inv)))

        return results

    @staticmethod
    def _letterbox(img, size):
        h, w = img.shape[:2]
        r = min(size / h, size / w)
        nw, nh = max(1, round(w * r)), max(1, round(h * r))
        resized = cv2.resize(img, (nw, nh))
        canvas = np.full((size, size, 3), 114, np.uint8)
        px, py = (size - nw) // 2, (size - nh) // 2
        canvas[py:py + nh, px:px + nw] = resized
        return canvas, r, px, py

    def _yolo_person(self, frame, yolo):
        net, meta = yolo
        n_classes = meta["classes"]
        person_class = meta["person"]
        h0, w0 = frame.shape[:2]

        canvas, r, px, py = self._letterbox(frame, self.yolo_size)
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 255.0, (self.yolo_size, self.yolo_size),
                                     swapRB=True, crop=False)
        net.setInput(blob)
        out = net.forward()[0]
        if out.shape[0] == n_classes + 4:
            out = out.T
        out = out.reshape(-1, n_classes + 4)

        scores = out[:, 4:]
        class_ids = scores.argmax(1)
        confs = scores[np.arange(len(class_ids)), class_ids]
        sel = np.where((class_ids == person_class) & (confs > self.confidence))[0]

        rects, box_conf = [], []
        for i in sel:
            cx, cy, bw, bh = out[i, :4]
            x1 = (cx - bw / 2.0 - px) / r
            y1 = (cy - bh / 2.0 - py) / r
            x2 = (cx + bw / 2.0 - px) / r
            y2 = (cy + bh / 2.0 - py) / r
            x1 = max(0, min(x1, w0)); y1 = max(0, min(y1, h0))
            x2 = max(0, min(x2, w0)); y2 = max(0, min(y2, h0))
            rects.append([int(x1), int(y1), int(max(1, x2 - x1)), int(max(1, y2 - y1))])
            box_conf.append(float(confs[i]))

        if not rects:
            return []
        keep = cv2.dnn.NMSBoxes(rects, box_conf, self.confidence, 0.45)
        keep = np.array(keep).reshape(-1).tolist() if keep is not None else []
        return [(rects[i][0], rects[i][1], rects[i][2], rects[i][3]) for i in keep]

    def _hog_person(self, frame, hog):
        h, w = frame.shape[:2]
        scale = self.work_width / float(w)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if scale < 1.0:
            small = cv2.resize(gray, (self.work_width, max(1, int(h * scale))),
                               interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            small = gray
        inv = 1.0 / scale
        rects, _ = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
        out = []
        for (x, y, bw, bh) in rects:
            out.append((int(x * inv), int(y * inv), int(bw * inv), int(bh * inv)))
        return out

    def _cascade_person(self, frame, cascade):
        h, w = frame.shape[:2]
        scale = self.work_width / float(w)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if scale < 1.0:
            small = cv2.resize(gray, (self.work_width, max(1, int(h * scale))),
                               interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            small = gray
        inv = 1.0 / scale
        rects = cascade.detectMultiScale(small, scaleFactor=1.05, minNeighbors=3, minSize=(48, 96))
        out = []
        for (x, y, bw, bh) in rects:
            out.append((int(x * inv), int(y * inv), int(bw * inv), int(bh * inv)))
        return out

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
    parser.add_argument("--fast", action="store_true",
                        help="Preset toc do cao cho Pi 4: %(default)s")
    parser.add_argument("--width", type=int, default=None, help="Capture width (default thay doi theo preset)")
    parser.add_argument("--height", type=int, default=None, help="Capture height (default thay doi theo preset)")
    parser.add_argument("--fps", type=int, default=None, help="Desired camera framerate (default thay doi theo preset)")
    parser.add_argument("--save-dir", default=SAVE_DIR, help="Folder for photos/videos (default %(default)s)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch fullscreen preview")
    parser.add_argument("--detect-scale", type=int, default=None,
                        help="Working width for face/hog detection (default thay doi theo preset)")
    parser.add_argument("--yolo-size", type=int, default=None,
                        help="YOLO input size; 320 fast / 640 accurate (default thay doi theo preset)")
    parser.add_argument("--conf", type=float, default=YOLO_CONF,
                        help="Person confidence threshold (default %(default)s)")
    parser.add_argument("--detect", dest="detect", action="store_true", default=True, help="Enable detection (default)")
    parser.add_argument("--no-detect", dest="detect", action="store_false", help="Disable detection")
    return parser.parse_args()


def main():
    cv2.setUseOptimized(True)

    args = parse_args()

    fast = args.fast
    width = args.width if args.width is not None else (FAST_WIDTH if fast else WIDTH)
    height = args.height if args.height is not None else (FAST_HEIGHT if fast else HEIGHT)
    fps = args.fps if args.fps is not None else (FAST_FPS if fast else FPS)
    detect_scale = args.detect_scale if args.detect_scale is not None else (
        FAST_DETECT_SCALE if fast else DETECT_SCALE)
    yolo_size = args.yolo_size if args.yolo_size is not None else (
        FAST_YOLO_SIZE if fast else YOLO_SIZE)

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (width, height), "format": "YUV420"},
        controls={"FrameRate": fps},
    )
    picam2.configure(config)

    capture = CaptureThread(picam2)
    capture.start()

    det = DetectorThread(work_width=detect_scale, yolo_size=yolo_size, conf=args.conf)
    det.start()

    window = "Pi 4 Camera"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    if args.fullscreen:
        cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    camera_on = False
    detect_on = args.detect
    recording = False
    writer = None
    fps_disp = 0.0
    started_at = time.time()
    blank = np.zeros((height, width, 3), dtype=np.uint8)

    print(f"""
Pi 4 Camera Controller (Turbo v7)
=================================
Mode     : {'FAST (640x480, yolo 320)' if fast else 'default (1280x720, yolo 320)'}
Controls:
  SPACE : camera on/off         D : toggle detection
  S     : take photo (JPG)      R : toggle video recording
  Q/ESC : quit
Detection colors:
  green=nguoi  orange=than_tren  blue=than_duoi  cyan=mat
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
                        fps, (width, height),
                    )
                    print(f"[*] recording -> {path}")
                writer.write(overlay)

            temp = read_cpu_temp()
            temp_line = f"CPU Temp: {temp:.1f} C" if temp is not None else "CPU Temp: n/a"
            draw_shadow(overlay, f"FPS: {fps_disp:6.1f}", (12, 30))
            draw_shadow(overlay, f"Detect FPS: {det.detect_fps:5.1f}  Engine: {det.engine}", (12, 62))
            draw_shadow(overlay, f"Res: {width}x{height}  Rec: {'ON ' if recording else 'OFF'}", (12, 94))
            draw_shadow(overlay, f"{datetime.now():%Y-%m-%d %H:%M:%S}  Uptime: {int(time.time() - started_at)}s", (12, 126))
            draw_shadow(overlay, temp_line, (12, 158))

            if detect_on:
                if det.loaded:
                    if det.yolo is None and det.engine not in ("loading",):
                        draw_shadow(overlay, "dang tai YOLO ... (fallback tam thoi)", (12, 190),
                                    scale=0.55, color=(0, 165, 255))
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
                fps_disp = 0.0
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
            fps_disp = instant if fps_disp <= 0 else fps_disp * 0.9 + instant * 0.1
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