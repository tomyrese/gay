#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 4 Camera Controller
================================
Live camera preview with on-screen FPS / system info overlay.

Usage:
    python3 pi4_camera.py
    python3 pi4_camera.py --width 1920 --height 1080 --fps 30 --fullscreen

Controls (bam phim khi cua so preview dang mo):
    SPACE    : Bat / tat camera
    S        : Chup anh (luu thanh JPG)
    R        : Bat / tat quay video (luu thanh AVI)
    Q / ESC  : Thoat

Requirements (tren Raspberry Pi 4):
    pip3 install opencv-python-headless picamera2 numpy
    Chu y: picamera2 da co san trong Raspberry Pi OS Bookworm.
"""

import argparse
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2

# ============================================================
# Cau hinh mac dinh (co the ghi de bang tham so dong lenh)
# ============================================================
WIDTH = 1280
HEIGHT = 720
FPS = 30
SAVE_DIR = "captures"
FULLSCREEN = False


def read_cpu_temp():
    """Doc nhiet do CPU tu sysfs cua Raspberry Pi."""
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError, IOError):
        return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Raspberry Pi 4 camera controller with live FPS / info overlay."
    )
    parser.add_argument("--width", type=int, default=WIDTH, help="Capture width (default %(default)s)")
    parser.add_argument("--height", type=int, default=HEIGHT, help="Capture height (default %(default)s)")
    parser.add_argument("--fps", type=int, default=FPS, help="Camera framerate (default %(default)s)")
    parser.add_argument("--save-dir", default=SAVE_DIR, help="Folder for photos/videos (default %(default)s)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch fullscreen preview")
    return parser.parse_args()


def draw_status(overlay, lines, color=(0, 255, 255)):
    y = 30
    for line in lines:
        if line:
            cv2.putText(
                overlay, line, (12, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA,
            )
            y += 32


def main():
    args = parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"},
        controls={"FrameRate": args.fps},
    )
    picam2.configure(config)

    window = "Pi 4 Camera"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    if args.fullscreen:
        cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    camera_on = False
    recording = False
    writer = None
    fps = 0.0
    started_at = time.time()
    blank = np.zeros((args.height, args.width, 3), dtype=np.uint8)

    print("""
Pi 4 Camera Controller
======================
Controls:
  SPACE : camera on/off
  S     : take photo (JPG)
  R     : toggle video recording (AVI)
  Q/ESC : quit
""")

    while True:
        overlayed = None

        if camera_on:
            t0 = time.perf_counter()
            frame = picam2.capture_array()
            elapsed = time.perf_counter() - t0
            if elapsed > 0:
                instant = 1.0 / elapsed
                fps = instant if fps <= 0 else fps * 0.9 + instant * 0.1

            if recording:
                if writer is None:
                    path = save_dir / f"video_{datetime.now():%Y%m%d_%H%M%S}.avi"
                    writer = cv2.VideoWriter(
                        str(path),
                        cv2.VideoWriter_fourcc(*"MJPG"),
                        args.fps, (args.width, args.height),
                    )
                    print(f"[*] recording -> {path}")
                writer.write(frame)

            overlayed = frame.copy()
            temp = read_cpu_temp()
            temp_line = f"CPU Temp: {temp:.1f} C" if temp is not None else "CPU Temp: n/a"
            draw_status(overlayed, [
                f"FPS: {fps:6.1f}",
                f"Resolution: {args.width}x{args.height}",
                f"Date: {datetime.now():%Y-%m-%d %H:%M:%S}",
                f"Uptime: {int(time.time() - started_at)} s",
                temp_line,
                f"Recording: {'ON ' if recording else 'OFF'}",
            ])
        else:
            overlayed = blank.copy()
            draw_status(overlayed, [
                "CAMERA IS OFF",
                "Press SPACE to turn it on",
            ], color=(0, 0, 255))

        cv2.imshow(window, overlayed)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord(" "):
            if camera_on:
                picam2.stop()
                camera_on = False
                fps = 0.0
                print("[i] camera stopped")
            else:
                picam2.start()
                camera_on = True
                print("[i] camera started")
        elif key == ord("s") and camera_on:
            path = save_dir / f"photo_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            cv2.imwrite(str(path), frame)
            print(f"[+] photo saved -> {path}")
        elif key == ord("r"):
            recording = not recording
            if not recording and writer is not None:
                writer.release()
                writer = None
                print("[i] recording stopped")

    if writer is not None:
        writer.release()
    if camera_on:
        picam2.stop()
    cv2.destroyAllWindows()
    print("[i] bye")


if __name__ == "__main__":
    main()