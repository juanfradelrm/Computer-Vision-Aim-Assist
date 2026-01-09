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

_running = False
_thread = None

# simular click para disparar
def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)   # Left click DOWN
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP

# LOOP PRINCIPAL
def loop(config):
    global _running
    
    # obtener parametros
    conf_threshold = float(config.get("confidence", 0.5))
    model_path = "yolov8n.pt"
    size = config["roi_size"]
    target_class = config["target_id"] # clase objetivo para disparar

    # cargar el modelo YOLO
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error: {e}")
        _running = False
        return

    # configuración de la captura de pantalla
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    monitor = {
        "top": (monitor_full["height"] - size) // 2,
        "left": (monitor_full["width"] - size) // 2,
        "width": size,
        "height": size
    }   # calcular ROI centrada

    crosshair_pos = size // 2   # centro para la mira
    
    # CONFIGURACION DE FILTROS
    # kernel y filtro para realzar bordes y que el modelo funcione mejor
    sharpen_kernel = np.array([[-1,-1,-1], 
                               [-1, 9,-1], 
                               [-1,-1,-1]]) # resta los bordes y multiplica el centro por 9
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    while _running:
        # capturar la region de interes
        img = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # si se selecciona, aplicar filtros
        if config.get("use_filters", True):
           # Convierte a LAB y aplica CLAHE solo al canal de luminancia
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_enhanced = clahe.apply(l)
            img = cv2.merge((l_enhanced, a, b))
            img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
            
            # sharpen para realzar detalles
            img = cv2.filter2D(img, -1, sharpen_kernel)

        # hacemos la predicción con el modelo
        results = model.predict(img, conf=conf_threshold, verbose=False, imgsz=size, device='cpu')

        # DETECCION Y DISPARO
        shot_fired = False
        for r in results:
            for box in r.boxes:
                # verficar si la clase detectada es la objetivo
                if int(box.cls) == target_class:
                    b = box.xyxy[0].cpu().numpy()   # obtener coordenadas de la caja
                    
                    # comprueba si la mira esta sobre la caja
                    if b[0] <= crosshair_pos <= b[2] and b[1] <= crosshair_pos <= b[3]:
                        disparar()
                        shot_fired = True
                        time.sleep(0.05)
                        break
            if shot_fired: break  
        

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

