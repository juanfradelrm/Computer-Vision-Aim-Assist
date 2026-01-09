import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import os

class ScriptMonitor:
    def __init__(self):
        self.raw_data = []
        self.session_start = datetime.now()
        self.script_name = "Desconocido"
        # Crear carpetas necesarias
        for folder in ["reports", "logs"]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def registrar_metrica(self, script_name, metrics):
        """Registra métricas universales aplicables a cualquier método"""
        self.script_name = script_name
        registro = {
            "timestamp": datetime.now(),
            "fps": metrics.get("fps", 0),
            "latency_ms": metrics.get("avg_loop_ms", 0),
            "detections": metrics.get("detections", 0),
            # Métricas avanzadas para comparar calidad
            "stability": metrics.get("target_stability", 0), # Variación en px del objetivo
            "status": metrics.get("status", "Running")
        }
        self.raw_data.append(registro)

    def guardar_en_historial(self, resumen):
        """Guarda un resumen de la sesión en un CSV global para comparativas"""
        history_file = "logs/comparativa_metodos.csv"
        resumen['script'] = self.script_name
        resumen['fecha'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        df_history = pd.DataFrame([resumen])
        header = not os.path.exists(history_file)
        df_history.to_csv(history_file, mode='a', header=header, index=False)

    def generar_graficos(self):
        if len(self.raw_data) < 5:
            print("Datos insuficientes para el análisis.")
            return

        df = pd.DataFrame(self.raw_data)
        
        # --- CÁLCULOS AVANZADOS ---
        avg_fps = df['fps'].mean()
        avg_lat = df['latency_ms'].mean()
        total_det = df['detections'].sum()
        # Eficiencia: Detecciones por segundo ajustadas por el lag (ms)
        # Un score alto significa: "Detecta mucho consumiendo poco"
        efficiency_score = (total_det / (df['latency_ms'].sum() + 1)) * 1000

        # --- DISEÑO DEL DASHBOARD ---
        plt.style.use('dark_background')
        fig, axes = plt.subplots(3, 1, figsize=(12, 12))
        fig.suptitle(f"ANÁLISIS TÉCNICO: {self.script_name}", fontsize=18, color='#E52525', fontweight='bold')

        # 1. ESTABILIDAD DE FPS (Rendimiento del PC)
        axes[0].plot(df['timestamp'], df['fps'], color='#00FF00', label='FPS Actual')
        axes[0].axhline(avg_fps, color='white', linestyle='--', label=f'Avg: {avg_fps:.1f}')
        axes[0].set_ylabel("FPS")
        axes[0].legend(loc='upper right')
        axes[0].grid(alpha=0.1)

        # 2. COSTO DE PROCESAMIENTO (Latencia End-to-End)
        axes[1].fill_between(df['timestamp'], df['latency_ms'], color='#FF0000', alpha=0.3)
        axes[1].plot(df['timestamp'], df['latency_ms'], color='#FF0000', label='Latencia (ms)')
        axes[1].set_ylabel("ms")
        axes[1].legend(loc='upper right')

        # 4. MÉTRICA COMPARATIVA (Efficiency Score)
        # Esto permite comparar un Trigger de Color vs YOLO
        df['eff_running'] = (df['detections'] / (df['latency_ms'] + 0.1)) * 10
        axes[2].plot(df['timestamp'], df['eff_running'], color='#FFD700', label='Efficiency Score (Potencia/Lag)')
        axes[2].set_ylabel("Score")
        axes[2].set_xlabel("Tiempo de Sesión")
        axes[2].legend(loc='upper right')

        # --- RESUMEN FINAL ---
        resumen = {
            "avg_fps": round(avg_fps, 2),
            "avg_latency": round(avg_lat, 2),
            "total_detections": total_det,
            "efficiency_score": round(efficiency_score, 4)
        }
        
        info_box = (
            f"--- RESUMEN DE MÉTODO ---\n"
            f"FPS Promedio: {resumen['avg_fps']}\n"
            f"Latencia Media: {resumen['avg_latency']}ms\n"
            f"Detecciones: {resumen['total_detections']}\n"
            f"EFFICIENCY SCORE: {resumen['efficiency_score']}"
        )
        plt.figtext(0.15, 0.01, info_box, fontsize=11, bbox=dict(facecolor='#333333', alpha=0.9), color='white')

        # Guardar resultados
        ts = int(time.time())
        plt.tight_layout(rect=[0, 0.08, 1, 0.95])
        plt.savefig(f"reports/reporte_{self.script_name}_{ts}.png")
        self.guardar_en_historial(resumen)
        
        print(f"\n[SISTEMA] Reporte generado y guardado en historial.")
        plt.show()