import cv2
import mss
import numpy as np
import time
import threading
import win32api
import win32con
from ultralytics import YOLO

# --- Metadata compatible con UILauncher ---
NAME = "YOLO v8 Trigger"
DESCRIPTION = "Detección de objetos en tiempo real para disparo automático."
PARAMS = [
    {"key": "model_name", "type": "str", "default": "yolov8n.pt", "label": "Modelo (yolov8n.pt)"},
    {"key": "roi_size", "type": "int", "default": 320, "min": 100, "max": 640, "label": "Tamaño Captura (px)"},
    {"key": "confidence", "type": "str", "default": "0.5", "label": "Confianza (0.1 - 0.9)"},
    {"key": "target_id", "type": "int", "default": 0, "label": "ID Clase (0=persona)"},
    {"key": "enabled", "type": "bool", "default": True, "label": "Disparo Activo"}
]

# Variables de control interno
_running = False
_thread = None
_metrics = {"fps": 0, "detections": 0, "avg_loop_ms": 0}

def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)   # Click Izquierdo Presionar
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Click Izquierdo Soltar

def loop(config):
    global _metrics, _running
    
    # Pre-procesamiento de parámetros del Launcher
    # (El launcher pasa floats como strings si no son ints)
    conf_threshold = float(config.get("confidence", 0.5))
    model_path = config.get("model_name", "yolov8n.pt")
    size = config["roi_size"]
    target_class = config["target_id"]

    # Inicializar YOLO (se recomienda descargar el .pt en la carpeta raíz)
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        _running = False
        return

    sct = mss.mss()
    monitor_full = sct.monitors[1]
    
    # Calcular centro de pantalla para el ROI
    center_x = monitor_full["width"] // 2
    center_y = monitor_full["height"] // 2
    
    monitor = {
        "top": center_y - (size // 2),
        "left": center_x - (size // 2),
        "width": size,
        "height": size
    }

    # El punto de mira en coordenadas relativas al ROI
    crosshair_pos = size // 2 

    last_time = time.time()
    frames = 0

    while _running:
        start_time = time.time()
        
        # 1. Captura rápida de pantalla
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 2. Inferencia (Solo en el ROI seleccionado)
        # device='0' para GPU NVIDIA, device='cpu' para procesador
        results = model.predict(img, conf=conf_threshold, verbose=False, device='cpu')

        shot_fired = False
        for r in results:
            for box in r.boxes:
                # Verificar clase
                if int(box.cls) == target_class:
                    print("Disparo detectado")
                    # Coordenadas: x1, y1 (top-left), x2, y2 (bottom-right)
                    b = box.xyxy[0].cpu().numpy()
                    
                    # Lógica de Trigger: ¿El centro de la captura cae dentro de la caja?
                    if b[0] <= crosshair_pos <= b[2] and b[1] <= crosshair_pos <= b[3]:
                        if config["enabled"]:
                            disparar()
                            shot_fired = True
                            break
            if shot_fired: break

        # 3. Cálculo de métricas para la UI
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