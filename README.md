# Computer Vision Trigger Prototype

A Python script demonstrating real-time screen capture and object detection using computer vision techniques (`OpenCV` and `mss`) to automate an action based on pixel color within a defined region of interest (ROI).

![Python](https://img.shields.io/badge/Python-3.x-blue) ![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red) ![License](https://img.shields.io/badge/License-Academic-orange)

## Academic Disclaimer and Responsibility

**This project is for educational and academic purposes only.**

We do not condone, promote, or encourage the use of this code for any malicious, illegal, or unfair competitive purposes, especially in online multiplayer environments. The primary objective of this repository is to demonstrate:

* **Computer Vision Fundamentals:** Real-time screen capture, color space conversion (BGR to HSV), and masking.
* **System Interaction:** How Python libraries can interface with the operating system to simulate input.

**By downloading or using this code, you agree that you are solely responsible for any consequences related to its use. The authors and contributors shall not be held liable for any misuse, damage, or violation of any third-party terms of service.**

---

## How It Works

This script monitors a small, defined area at the absolute center of the user's screen (the **Region of Interest** or **ROI**).

1.  **Screen Capture:** Uses the `mss` library to grab the central ROI in real-time.
2.  **Color Detection:** Converts the image to the **HSV color space** and applies a mask to detect pixels within the target color range (yellow in the default configuration).
3.  **Trigger:** If the number of detected pixels exceeds a set threshold (`PIXEL_THRESHOLD`), the script simulates a left mouse click using `win32api`.

---

## Prerequisites

You need Python 3.x installed along with the following libraries:

```bash
pip install opencv-python mss numpy pywin32
```

## Authors
Juan Francisco del Rosario Machín
Eduardo Gainza Koller
Mario García Abellán
