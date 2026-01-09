import cv2
import mss
import numpy as np
import time
import random
import threading
import win32api
import win32con

# Configuración y parámetros
NAME = "Triggerbot Canny Contours"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 64, "min": 16, "max": 256, "label": "ROI Size (px)"},
    {"key": "canny_t1", "type": "int", "default": 50, "min": 1, "max": 500, "label": "Canny Threshold1"},
    {"key": "canny_t2", "type": "int", "default": 150, "min": 1, "max": 500, "label": "Canny Threshold2"},
    {"key": "blur_ksize", "type": "int", "default": 5, "min": 1, "max": 31, "label": "Gaussian Blur Kernel (odd)"},
    {"key": "min_contour_area", "type": "int", "default": 200, "min": 10, "max": 10000, "label": "Min Contour Area"},
]

# --- [STATS] Diccionario de métricas ---
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

def _ensure_odd(x):
    x = int(x)
    return x if x % 2 == 1 else max(1, x - 1)

def loop(config):
    global _metrics, _running
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    
    img_temp = np.array(sct.grab(monitor_full))
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

    size = int(config.get("roi_size", 64))
    monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2,
               "width": size, "height": size}

    t1 = int(config.get("canny_t1", 50))
    t2 = int(config.get("canny_t2", 150))
    blur_k = _ensure_odd(config.get("blur_ksize", 5))
    min_area = int(config.get("min_contour_area", 200))

    # --- [STATS] Variables de control ---
    last_time = time.time()
    frames = 0
    detecciones_acumuladas = 0
    areas_history = [] 

    while _running:
        start_ciclo = time.time() # [STATS] Inicio medida latencia
        
        img = np.array(sct.grab(monitor))
        if img is None: continue

        frame = img[:, :, :3]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if blur_k > 1:
            gray = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

        # Canny Edge Detection
        edges = cv2.Canny(gray, t1, t2)

        contours_info = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

        trigger = False
        cx_center, cy_center = size // 2, size // 2
        proximity_thresh = size * 0.45

        current_frame_areas = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area: continue
            
            current_frame_areas.append(area)

            M = cv2.moments(cnt)
            if M.get('m00', 0) == 0: continue
            
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])

            dist = ((cx - cx_center)**2 + (cy - cy_center)**2)**0.5
            if dist <= proximity_thresh:
                trigger = True
                break

        if trigger:
            disparar()
            detecciones_acumuladas += 1
            _metrics["status"] = "Firing!"
            # Guardamos el área que activó el trigger para medir estabilidad
            areas_history.append(area) 
            time.sleep(random.uniform(0.05, 0.12))
        else:
            _metrics["status"] = "Scanning..."

        # --- [STATS] Actualización ---
        frames += 1
        curr_time = time.time()
        if (curr_time - last_time) >= 1.0:
            _metrics["fps"] = frames
            _metrics["avg_loop_ms"] = round((time.time() - start_ciclo) * 1000, 2)
            _metrics["detections"] = detecciones_acumuladas
            
            # Estabilidad basada en la consistencia del tamaño del objetivo
            # Si el área es siempre similar, la estabilidad es alta (valor bajo de Desviación Estándar)
            if len(areas_history) > 1:
                _metrics["target_stability"] = round(np.std(areas_history), 2)
            else:
                _metrics["target_stability"] = 0
            
            frames = 0
            detecciones_acumuladas = 0
            areas_history = []
            last_time = curr_time

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