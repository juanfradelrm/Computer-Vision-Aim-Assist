import cv2
import mss
import numpy as np
import time
import threading
import win32api
import win32con
from ultralytics import YOLO

NAME = "YOLO11 Triggerbot"
DESCRIPTION = "Triggerbot híbrido con lógica de Kill-check y filtros de imagen."
PARAMS = [
    {"key": "model_name", "type": "str", "default": "best.pt", "label": "Modelo (.pt)"},
    {"key": "roi_size", "type": "int", "default": 320, "min": 100, "max": 640, "label": "Tamaño ROI"},
    {"key": "confidence", "type": "str", "default": "0.5", "label": "Confianza (0.1-0.9)"},
    {"key": "use_filters", "type": "bool", "default": True, "label": "Activar Filtros CV"},
    {"key": "enabled", "type": "bool", "default": True, "label": "Disparo Activo"}
]

_running = False
_thread = None
_metrics = {"fps": 0, "status": "Idle", "avg_loop_ms": 0}

def disparar():
     win32api.keybd_event(0x01, 0, 0, 0)   # Left click DOWN
     win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP
     print("Disparo!")

def loop(config):
    global _metrics, _running
    
    conf_threshold = float(config.get("confidence", 0.5))
    model_path = config.get("model_name", "best.pt")
    size = config["roi_size"]

    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
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
    
    sharpen_kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    last_time = time.time()
    frames = 0

    while _running:
        start_time = time.time()
        
        
        img = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if config.get("use_filters", True):
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_enhanced = clahe.apply(l)
            img = cv2.merge((l_enhanced, a, b))
            img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
            img = cv2.filter2D(img, -1, sharpen_kernel)

        
        results = model.predict(img, conf=conf_threshold, verbose=False, imgsz=size)

        kill_detected = False
        shot_fired = False

        for r in results:
            
            for box in r.boxes:
                if int(box.cls) == 1:
                    kill_detected = True
                    _metrics["status"] = "Kill Detected"
                    break
            
            if kill_detected: break

           
            for box in r.boxes:
                if int(box.cls) == 0: 
                    b = box.xyxy[0].cpu().numpy()
                    
                    
                    if b[0] <= crosshair_pos <= b[2] and b[1] <= crosshair_pos <= b[3]:
                        if config["enabled"]:
                            disparar()
                            shot_fired = True
                            _metrics["status"] = "Firing!"
                            time.sleep(0.05) 
                            break
            
            if shot_fired: break
        
        if not shot_fired and not kill_detected:
            _metrics["status"] = "Searching..."

        
        frames += 1
        curr_time = time.time()
        if (curr_time - last_time) >= 1.0:
            _metrics["fps"] = frames
            _metrics["avg_loop_ms"] = round((curr_time - start_time) * 1000, 2)
            frames = 0
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