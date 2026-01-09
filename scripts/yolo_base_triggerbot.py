import cv2
import mss
import numpy as np
import time
import threading
import win32api
import win32con
from ultralytics import YOLO

NAME = "Triggerbot YOLO Base"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 320, "min": 100, "max": 640, "label": "ROI Size"},
    {"key": "confidence", "type": "str", "default": "0.5", "label": "Confidence (0.1-0.9)"},
    {"key": "target_id", "type": "int", "default": 0, "label": "Class ID (0=person)"},
    {"key": "use_filters", "type": "bool", "default": True, "label": "Enable CV Filters"},
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

def loop(config):
    global _running, _metrics
    
    conf_threshold = float(config.get("confidence", 0.5))
    model_path = "yolov8n.pt" # Puedes cambiar a yolov11n.pt
    size = config["roi_size"]
    target_class = config["target_id"]

    try:
        # Cargar en GPU si está disponible para mejorar la métrica de latencia
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error: {e}")
        _running = False
        return

    sct = mss.mss()
    monitor_full = sct.monitors[1]
    monitor = {
        "top": (monitor_full["height"] - size) // 2,
        "left": (monitor_full["width"] - size) // 2,
        "width": size,
        "height": size
    }

    crosshair_pos = size // 2
    
    # Pre-cálculo de filtros
    sharpen_kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    # --- [STATS] Variables de control ---
    last_time = time.time()
    frames = 0
    detecciones_acumuladas = 0
    conf_scores_history = []

    while _running:
        start_ciclo = time.time() # [STATS] Inicio medida latencia
        
        img_raw = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGRA2BGR)

        if config.get("use_filters", True):
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_enhanced = clahe.apply(l)
            img = cv2.merge((l_enhanced, a, b))
            img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
            img = cv2.filter2D(img, -1, sharpen_kernel)

        # Inferencia
        results = model.predict(img, conf=conf_threshold, verbose=False, imgsz=size)

        shot_fired = False
        _metrics["status"] = "Scanning..."
        
        for r in results:
            for box in r.boxes:
                if int(box.cls) == target_class:
                    conf = float(box.conf[0])
                    conf_scores_history.append(conf) # [STATS] Guardar confianza
                    
                    b = box.xyxy[0].cpu().numpy()
                    
                    if b[0] <= crosshair_pos <= b[2] and b[1] <= crosshair_pos <= b[3]:
                        disparar()
                        detecciones_acumuladas += 1
                        _metrics["status"] = "Firing!"
                        shot_fired = True
                        time.sleep(0.05)
                        break
            if shot_fired: break

        # --- [STATS] Actualización ---
        frames += 1
        curr_time = time.time()
        if (curr_time - last_time) >= 1.0:
            _metrics["fps"] = frames
            # La latencia en YOLO incluye Captura + Filtros + Inferencia
            _metrics["avg_loop_ms"] = round((time.time() - start_ciclo) * 1000, 2)
            _metrics["detections"] = detecciones_acumuladas
            
            # Estabilidad basada en la desviación de la confianza
            # Un valor bajo significa que el modelo está muy seguro de lo que ve
            if len(conf_scores_history) > 1:
                _metrics["target_stability"] = round(np.std(conf_scores_history) * 100, 2)
            
            frames = 0
            detecciones_acumuladas = 0
            conf_scores_history = []
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