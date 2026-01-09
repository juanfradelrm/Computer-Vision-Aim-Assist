import cv2
import mss
import numpy as np
import time
import random
import threading
import win32api
import win32con

# Configuración y parámetros
NAME = "Triggerbot Color Threshold"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 16, "min": 8, "max": 64, "label": "ROI Size (px)"},
    {"key": "lower_h", "type": "int", "default": 20, "min": 0, "max": 179, "label": "Lower Hue"},
    {"key": "upper_h", "type": "int", "default": 40, "min": 0, "max": 179, "label": "Upper Hue"},
    {"key": "pixel_threshold", "type": "int", "default": 25, "min": 5, "max": 200, "label": "Pixel Threshold"},
]

# --- [STATS] Diccionario completo para el nuevo motor ---
_running = False
_thread = None
_metrics = {
    "fps": 0, 
    "status": "Idle", 
    "avg_loop_ms": 0, 
    "detections": 0,
    "target_stability": 0 # <--- Nueva métrica universal
}

def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)

def loop(config):
    global _metrics, _running
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

    # --- [STATS] Control de métricas ---
    last_time = time.time()
    frames = 0
    detecciones_acumuladas = 0
    centro_previo = np.array([size//2, size//2]) # Centro del ROI por defecto
    estabilidad_acumulada = []

    while _running:
        start_ciclo = time.time()
        
        img = np.array(sct.grab(monitor))   
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  
        mask = cv2.inRange(hsv, lower, upper)
        
        # Calcular momentos para hallar el centro de los píxeles blancos
        M = cv2.moments(mask)
        pixels = int(M["m00"]) # Esto equivale a countNonZero pero más eficiente aquí

        if pixels > threshold:
            # --- [CALCULO ESTABILIDAD] ---
            # Hallamos el centro de masa de la detección
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            centro_actual = np.array([cX, cY])
            
            # Calculamos el desplazamiento (jitter) respecto al frame anterior
            desplazamiento = np.linalg.norm(centro_actual - centro_previo)
            estabilidad_acumulada.append(desplazamiento)
            centro_previo = centro_actual
            
            disparar()
            detecciones_acumuladas += 1
            _metrics["status"] = "Firing!"
            time.sleep(random.uniform(0.05, 0.1))
        else:
            _metrics["status"] = "Searching..."

        frames += 1
        curr_time = time.time()
        
        # --- [STATS] Publicación de datos al monitor ---
        if (curr_time - last_time) >= 1.0:
            _metrics["fps"] = frames
            _metrics["avg_loop_ms"] = round((time.time() - start_ciclo) * 1000, 2)
            _metrics["detections"] = detecciones_acumuladas
            
            # La estabilidad es el promedio de "temblor" de los píxeles (menor es mejor)
            if estabilidad_acumulada:
                _metrics["target_stability"] = round(np.mean(estabilidad_acumulada), 2)
            else:
                _metrics["target_stability"] = 0
            
            # Reset
            frames = 0
            detecciones_acumuladas = 0
            estabilidad_acumulada = []
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