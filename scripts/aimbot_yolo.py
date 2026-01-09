import cv2
import mss
import numpy as np
import time
import threading
import win32api
import win32con
import tkinter as tk    # Para la interfaz del overlay
from ultralytics import YOLO


NAME = "Aimbot YOLO + KCF Hybrid"
PARAMS = [
    {"key": "roi_size", "type": "int", "default": 320, "min": 100, "max": 640, "label": "ROI Size"},
    {"key": "smoothing", "type": "str", "default": "0.15", "label": "Smoothing"},   # suavizado del movimiento del raton
    {"key": "confidence", "type": "str", "default": "0.5", "label": "YOLO Confidence"},
    {"key": "show_visuals", "type": "bool", "default": True, "label": "Show Overlay"}
]

_running = False
_thread = None

# Funcion para crear el tracker KCF (intenta con distintas versiones de OpenCV)
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

# Función para mostrar el overlay con el tracking en pantalla
class HybridOverlay:
    def __init__(self, size):
        self.root = tk.Tk()
        self.size = size
        self.root.overrideredirect(True)    # para quitar bordes y barra de titulo
        self.root.attributes("-topmost", True, "-transparentcolor", "black")    # ventana siempre encima y transparente
        self.root.config(bg='black')

        # centrar ventana en la pantalla
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{size}x{size}+{(sw-size)//2}+{(sh-size)//2}")

        # canvas para dibujar
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg='black', highlightthickness=0)
        self.canvas.pack()

    #para actualizar la vista del overlay
    def update_view(self, bbox=None, mode="None"):
        self.canvas.delete("all")
        c = self.size // 2

        #dibujamos una mira en el centro (una cruz)
        self.canvas.create_line(c-8, c, c+8, c, fill="white")
        self.canvas.create_line(c, c-8, c, c+8, fill="white")
        
        # si se detecta un objetivo lo dibujamos
        if bbox is not None:
            color = "#00FF00" if mode == "YOLO" else "#00BFFF"  # verde para YOLO, azul para KCF
            x, y, w, h = bbox
            self.canvas.create_rectangle(x, y, x+w, y+h, outline=color, width=2)
            self.canvas.create_text(x, y-10, text=f"MODE: {mode}", fill=color, anchor="sw")
        self.root.update()

    def close(self):
        try: self.root.destroy()
        except: pass

# inicialización del filtro de kalman, que predice la posicion del objetivo en base a movimientos previos
def init_kalman():
    kf = cv2.KalmanFilter(4, 2) # 4 variables de estado (x, y, vx, vy), 2 mediciones (x, y)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32) # Mapea estado a medición
    kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32) # Modelo de movimiento
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03 # Incertidumbre del modelo de movimiento (suavidad vs reacción)
    return kf

# LOOP PRINCIPAL DEL SCRIPT
def loop(config):
    global _running
    size = config["roi_size"]   # tamaño de la region
    smoothing = float(config.get("smoothing", 0.15))    #factor de suavizado del movimiento
    
    # inicializar yolov8 nano, el tracker kcf y el filtro de kalman
    model = YOLO("yolov8n.pt")
    tracker = crear_tracker()
    kf = init_kalman()
    
    overlay = HybridOverlay(size) if config.get("show_visuals") else None

    # configuracion de mss para las capturas de pantalla
    sct = mss.mss()
    monitor = {
        "top": (sct.monitors[1]["height"] - size) // 2,
        "left": (sct.monitors[1]["width"] - size) // 2,
        "width": size, "height": size
    }
    
    tracking_active = False # para indicar si se esta trackeando un objetivo
    center = size // 2  # centro de la regiopn de interes

    while _running:
        start_loop = time.time()

        # captura de pantalla
        img = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        current_bbox = None
        mode = "None"

        # MODO YOLO
        # si no se está trackeando, usamos YOLO para detectar el objetivo
        if not tracking_active:
            results = model.predict(img, conf=float(config["confidence"]), verbose=False, imgsz=size)
            for r in results:
                for box in r.boxes:
                    if int(box.cls) == 0:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy() # coordenadas de la caja
                        w, h = x2 - x1, y2 - y1
                        current_bbox = (int(x1), int(y1), int(w), int(h))
                        
                        # inicializamos el tracker con esa caja detectada
                        tracker = cv2.TrackerKCF_create()
                        tracker.init(img, current_bbox)

                        # inicializamos el filtro de kalman con la posición del objetivo
                        kf.statePost = np.array([x1+w/2, y1+h/2, 0, 0], np.float32)
                        
                        tracking_active = True
                        mode = "YOLO"
                        break
        else:
            # MODO KCF
            # si ya se está trackeando, usamos KCF para seguir el objetivo
            success, bbox = tracker.update(img)
            if success:
                current_bbox = bbox
                mode = "KCF"
                
                # calculamos el centro del objetivo (un 20% más arriba para apuntar a la cabeza)
                target_x = bbox[0] + bbox[2] / 2
                target_y = bbox[1] + bbox[3] * 0.2 
                
                # actualizar el filtro de kalman
                kf.predict()
                kf.correct(np.array([[np.float32(target_x)], [np.float32(target_y)]]))

                # calcular el movimiento relativo del raton
                rel_x = int((target_x - center) * smoothing)
                rel_y = int((target_y - center) * smoothing)

                # mover el raton
                if rel_x != 0 or rel_y != 0:
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, rel_x, rel_y, 0, 0)
            else:
                # si falla el tracking volvemos a modo YOLO
                tracking_active = False 

        # actualizar el overlay si está activo
        if overlay:
            overlay.update_view(current_bbox, mode)
    # cerrar el overlay al salir del loop
    if overlay: overlay.close()

def start(config):
    # iniciamos el aimbot en un hilo separado
    global _running, _thread
    if _running: return
    _running = True
    _thread = threading.Thread(target=loop, args=(config,), daemon=True)
    _thread.start()

def stop():
    global _running
    _running = False