# Computer Vision Aim Assist & Analysis System

Academic research project focused on the **comparative evaluation of computer vision techniques** applied to real-time target detection and tracking in dynamic environments. The system integrates classical image processing methods, deep learning–based object detection, predictive filtering, a graphical overlay UI, and a statistics engine for quantitative analysis.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)
![YOLO](https://img.shields.io/badge/YOLO-v8-darkgreen)
![License](https://img.shields.io/badge/License-Academic-orange)

---

## Academic Disclaimer

**This project is developed strictly for academic and educational purposes.**

It is part of the *Computer Vision* course at the **University of Las Palmas de Gran Canaria (ULPGC)** and aims to analyze the behavior of different detection approaches under real-time, high-demand visual conditions.

The authors **do not support or encourage** the use of this software in online competitive environments or in violation of third-party terms of service.  
All responsibility derived from the use of this software lies solely with the user.

---

## Executive Summary

This project explores the application of computer vision techniques in fast-paced and visually complex environments, such as first-person shooter scenarios. It compares **classical methods** (color thresholding, contour detection, ORB features) against **deep learning approaches** (YOLO pretrained and fine-tuned models) under real-time constraints.

The main contribution is a **modular and extensible architecture** that allows:
- Runtime switching between detection techniques
- Objective performance evaluation through metrics
- Visual feedback via overlay UI
- Predictive tracking using Kalman filtering

---

## Objectives

### General Objective
Design and implement a modular real-time vision system capable of detecting and tracking targets using multiple computer vision techniques, enabling comparative performance analysis.

### Specific Objectives
- Efficient real-time screen capture
- Implementation of multiple detection algorithms
- Modular and interchangeable architecture
- Automated trigger and aim assistance logic
- Overlay-based graphical interface
- Training and evaluation of a custom YOLO model
- Quantitative comparison using performance metrics

---
## Detection Techniques Implemented

### 1. Color Thresholding
- HSV-based segmentation
- Pixel-count activation logic
- Extremely low latency
- Sensitive to lighting and scene color composition

### 2. Contour Detection (Canny)
- Edge detection with contour extraction
- Shape and centroid proximity analysis
- More robust than color-based detection
- Prone to jitter in complex backgrounds

### 3. ORB Feature Density
- FAST keypoint detection with BRIEF descriptors
- Density and spatial distribution analysis
- Independent of color information
- Medium computational cost

### 4. YOLO Base Model
- YOLOv8n pretrained on COCO
- Detection filtered to `person` class
- Bounding-box intersection logic
- High robustness with increased latency

### 5. YOLO Trained Model (Headshot Detection)
- Fine-tuned YOLO model trained on Valorant-specific dataset
- Head-level precision
- Kill-confirmation filtering to prevent over-triggering
- Best accuracy at the cost of GPU usage

### 6. Predictive Aimbot with Kalman Filter
- Target centroid tracking
- Motion prediction and smoothing
- Latency compensation
- Decoupled from detection stage

---

## User Interface (Overlay)

The overlay UI allows:
- Runtime selection of detection method
- Parameter tuning (thresholds, confidence levels, ROI size)
- Visualization of detections, bounding boxes, contours, and keypoints
- Monitoring of system state and metrics

---

## Statistics & Evaluation Engine

The integrated **Stats Engine** measures:

- End-to-end latency (ms)
- Frames per second (FPS)
- Detection confidence stability
- Target jitter and tracking error
- Efficiency Score (accuracy vs computational cost)

All metrics are logged for offline analysis and comparison.

---

## Comparative Results (Summary)

| Method           | FPS     | Latency | Stability | Precision | Compute Load |
|------------------|---------|---------|-----------|-----------|--------------|
| Color Threshold  | 144+    | 1–3 ms  | Medium    | Low       | Very Low     |
| Canny Contours   | 90–110  | 5–8 ms  | Low       | Medium    | Medium       |
| ORB Density      | 60–80   | 12–18 ms| Medium    | Medium    | Medium       |
| YOLO Base        | 10–35   | 25–40 ms| High      | High      | High (GPU)   |
| YOLO Trained     | 10–30   | 30–45 ms| High      | Very High | High (GPU)   |

---
## Installation & Environment Setup

Recommended setup using **Conda**:

```bash
conda create trbajo_final python=3.10
conda activate trabajo_final

pip install torch torchvision torchaudio
pip install ultralytics opencv-python numpy mss dxcam pillow
pip install pyautogui pywin32 matplotlib pandas
```
---
## Educational Value

- Real-time computer vision system design  
- Classical vs deep learning performance trade-offs  
- Modular software architecture  
- Tracking and prediction algorithms  
- Experimental evaluation and benchmarking  

---

## Authors

- Eduardo Gainza Koller  
- Mario García Abellán  
- Juan Francisco del Rosario Machín  

---

## External Resources

- **YOLO Models:** https://docs.ultralytics.com/  
- **Dataset:** [https://universe.roboflow.com/hans-industries/valorant-bot-model/  ](https://universe.roboflow.com/hans-industries/valorant-bot-model/dataset/4) 

**Universidad de Las Palmas de Gran Canaria** *Grado en Ingeniería Informática | Visión por Computador 2025-2026*
