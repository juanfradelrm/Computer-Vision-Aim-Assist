import cv2
import mss
import numpy as np
import time
import random

LOWER_YELLOW = np.array([20, 125, 150])  
UPPER_YELLOW = np.array([40, 255, 255])
PIXEL_THRESHOLD = 25

print("Calibracion")
with mss.mss() as sct:
    monitor_full = sct.monitors[1]
    img_temp = np.array(sct.grab(monitor_full))
    screen_w, screen_h = img_temp.shape[1], img_temp.shape[0]

size = 16
monitor = {"top": (screen_h-size)//2, "left": (screen_w-size)//2, "width": size, "height": size}
print(f"Res: {screen_w}x{screen_h} | ROI centro: {size}x{size}")

sct = mss.mss()

cv2.namedWindow("MASK (blanco=dispara)", cv2.WINDOW_NORMAL)
cv2.namedWindow("CENTRO (pixeles)", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("MASK (blanco=dispara)", cv2.WND_PROP_TOPMOST, 1)
cv2.setWindowProperty("CENTRO (pixeles)", cv2.WND_PROP_TOPMOST, 1)
cv2.resizeWindow("MASK (blanco=dispara)", 320, 320)
cv2.resizeWindow("CENTRO (pixeles)", 320, 320)
cv2.moveWindow("MASK (blanco=dispara)", screen_w-350, 50)
cv2.moveWindow("CENTRO (pixeles)", screen_w-350, 400)


shooting = True
print("Triggerbot listo!")
print("0.5 segundos y empieza...")
time.sleep(5)

import win32api
import win32con

def disparar():
    #win32api.keybd_event(win32con.VK_LMENU, 0, 0, 0)        # Alt izq DOWN (solo para forzar foco)
    win32api.keybd_event(0x01, 0, 0, 0)                    # Left click DOWN  (0x01 = WM_LBUTTONDOWN)
    win32api.keybd_event(0x01, 0, win32con.KEYEVENTF_KEYUP, 0)  # Left click UP
    win32api.keybd_event(win32con.VK_LMENU, 0, win32con.KEYEVENTF_KEYUP, 0)

while True:
    img = np.array(sct.grab(monitor))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)
    pixels = cv2.countNonZero(mask)

    h, w = img.shape[:2]
    #cv2.putText(img, f"Pix: {pixels} | Thr: {PIXEL_THRESHOLD} | {'ON' if shooting else 'OFF'}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.imshow("MASK (blanco=dispara)", mask)
    cv2.imshow("CENTRO (pixeles)", img)

    print(f"Pixels: {pixels} | Thr: {PIXEL_THRESHOLD} | Shooting: {'SI' if shooting else 'NO'}", end="\r")

    if pixels > PIXEL_THRESHOLD and shooting:
        print(f"\nDISPARANDO! ({pixels} px)")
        disparar()                                             
        time.sleep(random.uniform(0.05, 0.1))

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('t'): shooting = not shooting; print(f"\nShooting: {'ON' if shooting else 'OFF'}")
    elif key == ord('-'): PIXEL_THRESHOLD = max(PIXEL_THRESHOLD-5, 5); print(f"\nThr: {PIXEL_THRESHOLD}")
    elif key == ord('+'): PIXEL_THRESHOLD += 5; print(f"\nThr: {PIXEL_THRESHOLD}")

cv2.destroyAllWindows()
print("\nApagado")