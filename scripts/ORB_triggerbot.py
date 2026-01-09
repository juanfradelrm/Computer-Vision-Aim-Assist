import cv2
import mss
import numpy as np
import time
import random
import threading
import win32api
import win32con

# Configuración
NAME = "Triggerbot ORB Density"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 128, "min": 64, "max": 256, "label": "ROI Size (px)"},
    {"key": "orb_features", "type": "int", "default": 100, "min": 50, "max": 500, "label": "Max ORB Features"},
    {"key": "keypoint_threshold", "type": "int", "default": 65, "min": 30, "max": 100, "label": "Min Keypoints to Shoot"},
    {"key": "debug_window", "type": "bool", "default": False, "label": "Show Debug Window"},
]

# --- [STATS] Diccionario de métricas universales ---
_running = False
_thread = None
_metrics = {
    "fps": 0, 
    "status": "Idle", 
    "avg_loop_ms": 0, 
    "detections": 0,
    "target_stability": 0 
}

def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)

def loop(config):
    global _metrics, _running
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    
    # Captura inicial para dimensiones
    img_temp = np.array(sct.grab(monitor_full)) 
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

    size = int(config.get("roi_size", 128))
    monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2, 
               "width": size, "height": size}

    n_features = int(config.get("orb_features", 100))
    orb = cv2.ORB_create(nfeatures=n_features, scoreType=cv2.ORB_HARRIS_SCORE)
    
    keypoint_thresh = int(config.get("keypoint_threshold", 15))
    show_debug = config.get("debug_window", False)

    # --- [STATS] Variables de control ---
    last_time = time.time()
    frames = 0
    detecciones_acumuladas = 0
    kp_counts_history = [] # Para medir estabilidad de la detección

    if show_debug:
        cv2.namedWindow("Debug ORB View", cv2.WINDOW_NORMAL)

    try:
        while _running:
            start_ciclo = time.time() # [STATS] Inicio medida latencia
            
            img = np.array(sct.grab(monitor))
            if img is None: continue

            frame = img[:, :, :3]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Inferencia ORB
            keypoints = orb.detect(gray, None)
            kp_counts_history.append(len(keypoints))
            
            trigger = False
            cx_center, cy_center = size // 2, size // 2
            proximity_thresh = size * 0.3
            
            central_keypoints = [kp for kp in keypoints if np.linalg.norm(np.array(kp.pt) - [cx_center, cy_center]) <= proximity_thresh]
            count_central = len(central_keypoints)
            
            if len(keypoints) >= keypoint_thresh and count_central >= (keypoint_thresh // 2):
                trigger = True

            if trigger:
                disparar()
                detecciones_acumuladas += 1
                _metrics["status"] = "Firing!"
                time.sleep(random.uniform(0.05, 0.12))
            else:
                _metrics["status"] = "Scanning..."

            # Visualización Debug
            if show_debug:
                debug_frame = cv2.drawKeypoints(frame, keypoints, None, color=(0, 255, 0))
                cv2.imshow("Debug ORB View", debug_frame)
                cv2.waitKey(1)

            # --- [STATS] Actualización de métricas ---
            frames += 1
            curr_time = time.time()
            if (curr_time - last_time) >= 1.0:
                _metrics["fps"] = frames
                _metrics["avg_loop_ms"] = round((time.time() - start_ciclo) * 1000, 2)
                _metrics["detections"] = detecciones_acumuladas
                
                # Estabilidad: Desviación estándar del número de puntos encontrados
                # Si la desviación es alta, la detección es "ruidosa" o inestable
                if len(kp_counts_history) > 1:
                    _metrics["target_stability"] = round(np.std(kp_counts_history), 2)
                
                # Reset
                frames = 0
                detecciones_acumuladas = 0
                kp_counts_history = []
                last_time = curr_time

    finally:
        if show_debug: cv2.destroyAllWindows()

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