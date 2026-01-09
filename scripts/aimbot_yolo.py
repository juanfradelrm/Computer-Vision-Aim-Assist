import cv2
import mss
import numpy as np
import time
import threading
import win32api
import win32con
import tkinter as tk
from ultralytics import YOLO


NAME = "Aimbot YOLO + KCF Hybrid"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 320, "min": 100, "max": 640, "label": "ROI Size"},
    {"key": "smoothing", "type": "str", "default": "0.15", "label": "Smoothing"},
    {"key": "confidence", "type": "str", "default": "0.5", "label": "YOLO Confidence"},
    {"key": "show_visuals", "type": "bool", "default": True, "label": "Show Overlay"}
]

_running = False
_thread = None


def crear_tracker():
    if hasattr(cv2, 'TrackerKCF_create'):
        print("El metodo TrackerKCF_create se encuentra")
        return cv2.TrackerKCF_create()
    
    if hasattr(cv2, 'TrackerKCF'):
        print("El metodo TrackerKCF se encuentra")
        return cv2.TrackerKCF.create()
    
    if hasattr(cv2, 'legacy'):
        print("El metodo legacy.TrackerKCF_create se encuentra")
        return cv2.legacy.TrackerKCF_create()
        
    raise AttributeError("No se ha encontrado el módulo de Tracking. Reinstala opencv-contrib-python.")

class HybridOverlay:
    def __init__(self, size):
        self.root = tk.Tk()
        self.size = size
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True, "-transparentcolor", "black")
        self.root.config(bg='black')
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{size}x{size}+{(sw-size)//2}+{(sh-size)//2}")
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg='black', highlightthickness=0)
        self.canvas.pack()

    def update_view(self, bbox=None, mode="None"):
        self.canvas.delete("all")
        c = self.size // 2
        self.canvas.create_line(c-8, c, c+8, c, fill="white")
        self.canvas.create_line(c, c-8, c, c+8, fill="white")
        
        if bbox is not None:
            color = "#00FF00" if mode == "YOLO" else "#00BFFF"
            x, y, w, h = bbox
            self.canvas.create_rectangle(x, y, x+w, y+h, outline=color, width=2)
            self.canvas.create_text(x, y-10, text=f"MODE: {mode}", fill=color, anchor="sw")
        self.root.update()

    def close(self):
        try: self.root.destroy()
        except: pass

def init_kalman():
    kf = cv2.KalmanFilter(4, 2)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
    kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
    return kf

def loop(config):
    global _running
    size = config["roi_size"]
    smoothing = float(config.get("smoothing", 0.15))
    
    # Forzar uso de YOLOv8 (no permitir elección por parte del usuario)
    model = YOLO("yolov8n.pt")
    tracker = crear_tracker()
    kf = init_kalman()
    
    overlay = HybridOverlay(size) if config.get("show_visuals") else None
    sct = mss.mss()
    monitor = {
        "top": (sct.monitors[1]["height"] - size) // 2,
        "left": (sct.monitors[1]["width"] - size) // 2,
        "width": size, "height": size
    }
    
    tracking_active = False
    center = size // 2

    while _running:
        start_loop = time.time()
        img = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        current_bbox = None
        mode = "None"

        if not tracking_active:
            results = model.predict(img, conf=float(config["confidence"]), verbose=False, imgsz=size)
            for r in results:
                for box in r.boxes:
                    if int(box.cls) == 0:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        w, h = x2 - x1, y2 - y1
                        current_bbox = (int(x1), int(y1), int(w), int(h))
                        
                        
                        tracker = cv2.TrackerKCF_create()
                        tracker.init(img, current_bbox)
                        kf.statePost = np.array([x1+w/2, y1+h/2, 0, 0], np.float32)
                        
                        tracking_active = True
                        mode = "YOLO"
                        break
        else:
            
            success, bbox = tracker.update(img)
            if success:
                current_bbox = bbox
                mode = "KCF"
                
                
                target_x = bbox[0] + bbox[2] / 2
                target_y = bbox[1] + bbox[3] * 0.2 
                
                kf.predict()
                kf.correct(np.array([[np.float32(target_x)], [np.float32(target_y)]]))
                
                rel_x = int((target_x - center) * smoothing)
                rel_y = int((target_y - center) * smoothing)
                if rel_x != 0 or rel_y != 0:
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, rel_x, rel_y, 0, 0)
            else:
                tracking_active = False 

        if overlay:
            overlay.update_view(current_bbox, mode)

        # loop timing omitted (métricas eliminadas)

    if overlay: overlay.close()

def start(config):
    global _running, _thread
    if _running: return
    _running = True
    _thread = threading.Thread(target=loop, args=(config,), daemon=True)
    _thread.start()

def stop():
    global _running
    _running = False

# Métricas eliminadas: ya no se expone información de rendimiento