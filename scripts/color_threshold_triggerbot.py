import cv2
import mss
import numpy as np
import time
import random
import threading
import win32api
import win32con

# Metadata obligatoria
NAME = "Triggerbot color"
DESCRIPTION = "Detecta color en el centro de la pantalla y dispara automáticamente."
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 16, "min": 8, "max": 64, "label": "ROI Size (px)"},
    {"key": "lower_h", "type": "int", "default": 20, "min": 0, "max": 179, "label": "Lower Hue"},
    {"key": "upper_h", "type": "int", "default": 40, "min": 0, "max": 179, "label": "Upper Hue"},
    {"key": "pixel_threshold", "type": "int", "default": 25, "min": 5, "max": 200, "label": "Pixel Threshold"},
    {"key": "enabled", "type": "bool", "default": True, "label": "Enable Shooting"}
]

# Variables internas
_running = False
_thread = None
_metrics = {"fps": 0, "detections": 0, "avg_loop_ms": 0}

def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)   # Left click DOWN
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP

def loop(config):
    global _metrics
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    img_temp = np.array(sct.grab(monitor_full))
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

    size = config["roi_size"]
    monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2,
               "width": size, "height": size}

    lower = np.array([config["lower_h"], 125, 150])
    upper = np.array([config["upper_h"], 255, 255])
    threshold = config["pixel_threshold"]

    last_time = time.time()
    frames = 0
    detections = 0

    while _running:
        start = time.time()
        img = np.array(sct.grab(monitor))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        pixels = cv2.countNonZero(mask)

        if pixels > threshold and config["enabled"]:
            disparar()
            detections += 1
            time.sleep(random.uniform(0.05, 0.1))

        frames += 1
        elapsed = time.time() - last_time
        if elapsed >= 1.0:
            _metrics = {
                "fps": frames,
                "detections": detections,
                "avg_loop_ms": round((elapsed/frames)*1000, 2)
            }
            frames = 0
            detections = 0
            last_time = time.time()

        loop_ms = (time.time() - start) * 1000
        _metrics["avg_loop_ms"] = loop_ms

def start(config: dict):
    global _running, _thread
    if _running: return
    _running = True
    _thread = threading.Thread(target=loop, args=(config,), daemon=True)
    _thread.start()

def stop():
    global _running, _thread
    _running = False
    if _thread:
        _thread.join(timeout=2)
        _thread = None

def get_metrics() -> dict:
    return _metrics