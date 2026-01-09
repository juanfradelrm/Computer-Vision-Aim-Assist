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

# variables para controlar la ejecución
_running = False
_thread = None

# simula un click izquierdo
def disparar():
    win32api.keybd_event(0x01, 0, 0, 0)   # Left click DOWN
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP

# asegura que el kernel del blur gaussiano sea impar
def _ensure_odd(x):
    x = int(x)
    return x if x % 2 == 1 else max(1, x - 1)

# el loop principal
def loop(config):
    # captura de pantalla
    sct = mss.mss()
    monitor_full = sct.monitors[1]
    img_temp = np.array(sct.grab(monitor_full))
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

    #configurar la región de interés en el centro
    size = int(config.get("roi_size", 64))
    monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2,
               "width": size, "height": size}

    # obtenemos los parametros de configuracion
    t1 = int(config.get("canny_t1", 50))
    t2 = int(config.get("canny_t2", 150))
    blur_k = _ensure_odd(config.get("blur_ksize", 5))
    min_area = int(config.get("min_contour_area", 200))

    # loop principal de la detección
    while _running:
        # captura la region de interes
        img = np.array(sct.grab(monitor))
        if img is None:
            continue

        # mss devuelve BGRA, convertimos a BGR
        frame = img[:, :, :3]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # convertimos a grises

        # aplicamos gaussian blur para evitar ruido
        if blur_k > 1:
            gray = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

        # APLICAMOS CANNY para detectar bordes
        edges = cv2.Canny(gray, t1, t2) # t1 y t2 son los umbrales

        # buscamos contornos en la imagen de bordes
        # retr_external para obtener solo contornos externos
        # chain_approx_simple para comprimir los contornos
        contours_info = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

        # comprobamos si algun contorno está cerca del centro
        trigger = False
        cx_center = size // 2
        cy_center = size // 2
        proximity_thresh = size * 0.45

        for cnt in contours:
            # si el contorno es muy pequeño lo ignoramos
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            # calculamos el centro del contorno
            M = cv2.moments(cnt)
            if M.get('m00', 0) == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])

            dist = ((cx - cx_center)**2 + (cy - cy_center)**2)**0.5 # distancia euclidiana al centro
            # si la distancia es menor que el umbral, disparamos
            if dist <= proximity_thresh:
                trigger = True
                break

        if trigger:
            disparar()  # pium
            time.sleep(random.uniform(0.05, 0.12))  # retraso aleatorio

def start(config: dict):
    # inicia la ejecucion
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=loop, args=(config,), daemon=True)
    _thread.start()


def stop():
    global _running, _thread
    _running = False
    if _thread:
        _thread.join(timeout=2)
        _thread = None



