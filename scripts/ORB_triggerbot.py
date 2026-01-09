import cv2
import mss
import numpy as np
import time
import random
import threading
import win32api
import win32con

# Metadata
NAME = "Triggerbot ORB Density"
DESCRIPTION = "Detecta enemigos usando características ORB (Oriented FAST and Rotated BRIEF) comparando keypoints en la ROI central."
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 128, "min": 64, "max": 256, "label": "ROI Size (px)"},
    {"key": "orb_features", "type": "int", "default": 100, "min": 50, "max": 500, "label": "Max ORB Features"},
    {"key": "keypoint_threshold", "type": "int", "default": 65, "min": 30, "max": 100, "label": "Min Keypoints to Shoot"},
    {"key": "debug_window", "type": "bool", "default": False, "label": "Show Debug Window"},
    {"key": "enabled", "type": "bool", "default": True, "label": "Enable Shooting"}
]

# Internal state
_running = False
_thread = None
_metrics = {"fps": 0, "detections": 0, "avg_loop_ms": 0, "keypoints": 0}

def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)   # Left click DOWN
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP


def loop(config):
    global _metrics
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    img_temp = np.array(sct.grab(monitor_full))
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

    size = int(config.get("roi_size", 128))
    monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2, 
               "width": size, "height": size}

    n_features = int(config.get("orb_features", 100))
    orb = cv2.ORB_create(nfeatures=n_features, scoreType=cv2.ORB_HARRIS_SCORE)
    
    keypoint_thresh = int(config.get("keypoint_threshold", 15))
    show_debug = config.get("debug_window", False)

    last_time = time.time()
    frames = 0
    detections = 0

    if show_debug:
        cv2.namedWindow("Debug ORB View", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Debug ORB View", 256, 256)

    try:
        while _running:
            start = time.time()
            img = np.array(sct.grab(monitor))
            if img is None: continue

            frame = img[:, :, :3]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detectar keypoints
            keypoints = orb.detect(gray, None)
            
            trigger = False
            cx_center = size // 2
            cy_center = size // 2
            proximity_thresh = size * 0.3
            
            # Contar keypoints centrales
            central_keypoints_list = []
            outer_keypoints_list = []

            for kp in keypoints:
                kx, ky = kp.pt
                dist = ((kx - cx_center)**2 + (ky - cy_center)**2)**0.5
                if dist <= proximity_thresh:
                    central_keypoints_list.append(kp)
                else:
                    outer_keypoints_list.append(kp)
            
            count_central = len(central_keypoints_list)
            
            # Condición de disparo: suficientes puntos totales Y suficientes en el centro
            if len(keypoints) >= keypoint_thresh and count_central >= (keypoint_thresh // 2):
                trigger = True

            # --- DEBUG VISUALIZACIÓN ---
            if show_debug:
                debug_frame = frame.copy()
                
                # Dibujar zona letal (círculo azul)
                cv2.circle(debug_frame, (cx_center, cy_center), int(proximity_thresh), (255, 255, 0), 1)
                
                # Dibujar keypoints LEJOS (rojos pequeños)
                cv2.drawKeypoints(debug_frame, outer_keypoints_list, debug_frame, color=(0, 0, 255), flags=0)
                
                # Dibujar keypoints CENTRALES (verdes grandes) que causan el disparo
                # flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS dibuja el tamaño del keypoint
                cv2.drawKeypoints(debug_frame, central_keypoints_list, debug_frame, color=(0, 255, 0), flags=0)

                # Texto de estado
                status_text = f"KP: {count_central}/{len(keypoints)}" 
                trigger_text = "SHOOT!" if trigger else "SCANNING"
                color_text = (0, 255, 0) if trigger else (200, 200, 200)
                
                cv2.putText(debug_frame, status_text, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(debug_frame, trigger_text, (5, size - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_text, 1)

                cv2.imshow("Debug ORB View", debug_frame)
                cv2.waitKey(1)
            # ---------------------------

            if trigger and config.get("enabled", True):
                disparar()
                detections += 1
                time.sleep(random.uniform(0.05, 0.12))

            # Métricas
            frames += 1
            elapsed = time.time() - last_time
            if elapsed >= 1.0:
                _metrics = {
                    "fps": frames,
                    "detections": detections,
                    "avg_loop_ms": round(((time.time() - start) * 1000), 2),
                    "keypoints": len(keypoints)
                }
                frames = 0
                detections = 0
                last_time = time.time()

    finally:
        if show_debug:
            cv2.destroyAllWindows()


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
