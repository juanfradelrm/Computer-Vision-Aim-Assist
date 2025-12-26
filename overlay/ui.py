import importlib
import importlib.util
import os
import threading
import time
import customtkinter as ctk
from PIL import Image


# Launcher de la UI del overlay que hereda de tkinter
class UILauncher(ctk.CTk):

    #constructor
    def __init__(self):
        super().__init__()
        # Título de la ventana
        self.title("Aim-Assist Launcher")
        # Siempre en primer plano
        self.attributes("-topmost", True)
        # Pantalla completa de alto
        self.screen_h = self.winfo_screenheight()
        # Panel de un tercio del ancho de la pantalla
        self.panel_w =  self.winfo_screenwidth() / 3
        # Posiciones en x de manera oculta y + 30 para mostrar el borde
        self.hidden_x = -self.panel_w + 30  
        # Posición visible en x
        self.visible_x = 0
        # Estado inicial del panel
        self.is_visible = True
        self.target_x = self.visible_x
        self._current_x = self.visible_x
        # Configurar ventana inicial
        self.geometry(f"{int(self.panel_w)}x{self.screen_h}+{int(self._current_x)}+0")
        # Ventana sin bordes
        self.overrideredirect(True)
        # Color de fondo oscuro
        self.configure(fg_color = "#2e2e2e")
        # Trasparencia del 70%
        self.attributes("-alpha", 0.80)
        # Variables para scripts
        self.scripts = {}
        self.active_script = None
        self.script_thread = None
        self.running = False
        self.param_vars = {}   

        # Construir la UI
        self.build_ui()


    # Bucle de animación para mover la ventana entre posiciones
    def animate_loop(self):
        step = 20  
        if self._current_x < self.target_x:
            self._current_x += step
            if self._current_x > self.target_x:
                self._current_x = self.target_x
        elif self._current_x > self.target_x:
            self._current_x -= step
            if self._current_x < self.target_x:
                self._current_x = self.target_x

        # Actualizar la posición de la ventana
        self.geometry(f"{int(self.panel_w)}x{self.screen_h}+{int(self._current_x)}+0")
        # Llamar a esta función nuevamente después de 10 ms
        self.after(10, self.animate_loop)


    # Metodo para cambiar entre visible y oculta la ventana
    def toggle_panel(self):
        self.is_visible = not self.is_visible
        self.target_x = self.visible_x if self.is_visible else self.hidden_x
        self.animate_loop()


    # Metodo para cargar los scripts disponibles
    def load_scripts(self):
        scripts_dir = "scripts"
        self.scripts = {}
        #Recorrer archivos en el directorio de scripts
        for fname in os.listdir(scripts_dir):
            ## Recorremos los archivos; solo procesamos .py que no sean __init__.py
            if fname.endswith(".py") and fname != "__init__.py":
                # Construimos la ruta completa al archivo dentro de la carpeta scripts
                path = os.path.join(scripts_dir, fname)
                # Creamos la especificación (spec) para cargar el módulo desde un archivo concreto
                # fname[:-3] quita la extensión ".py" para usar el nombre del módulo
                spec = importlib.util.spec_from_file_location(fname[:-3], path)
                # Creamos un objeto módulo vacío a partir de la especificación
                module = importlib.util.module_from_spec(spec)
                # Ejecutamos el archivo .py dentro del objeto módulo (lo carga dinámicamente)
                spec.loader.exec_module(module)

                # Validar plantilla mínima
                if hasattr(module, "NAME") and hasattr(module, "PARAMS") and hasattr(module, "start") and hasattr(module, "stop"):
                    self.scripts[module.NAME] = module
   
        # Actualizar el selector de scripts en la UI
        names = list(self.scripts.keys())
        self.script_selector.configure(values=names)
        # Seleccionar el primer script por defecto
        if names:
            self.script_selector.set(names[0])
            self.load_params_ui()  



    # Metodo para cargar la UI de parámetros del script seleccionado
    def load_params_ui(self, selected=None):
        print("Cargando parámetros UI...")
        # Limpiar frame
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        # Cargar script seleccionado
        script_name = self.script_selector.get()
        script = self.scripts.get(script_name)
        if not script: return
        # Crear variables para cada parámetro
        self.param_vars = {}
        for param in script.PARAMS:
            label = ctk.CTkLabel(self.params_frame, text=param["label"], text_color="#FFFFFF")
            label.pack(anchor="w")
            # Si el parametro es int creamos un entry
            if param["type"] == "int":
                var = ctk.StringVar(value=str(param["default"]))
                entry = ctk.CTkEntry(self.params_frame, textvariable=var)
                entry.pack(fill="x", pady=5)
                self.param_vars[param["key"]] = var
            # Si el parametro es bool creamos un checkbox
            elif param["type"] == "bool":
                var = ctk.BooleanVar(value=param["default"])
                chk = ctk.CTkCheckBox(self.params_frame, text="", variable=var)
                chk.pack(pady=5)
                self.param_vars[param["key"]] = var
            # Si el parametro es string creamos un entry
            else:
                var = ctk.StringVar(value=str(param["default"]))
                entry = ctk.CTkEntry(self.params_frame, textvariable=var)
                entry.pack(fill="x", pady=5)
                self.param_vars[param["key"]] = var    


    # Metodo para lanzar el script seleccionado en un hilo
    def start_script(self):
        # Obtener script seleccionado
        script_name = self.script_selector.get()
        script = self.scripts.get(script_name)
        if not script: return
        # Construir configuración desde variables
        config = {}
        for k, v in self.param_vars.items():
            raw = v.get()
            try:
                # Si el valor parece un entero, lo convertimos
                config[k] = int(raw)
            except ValueError:
                # Si no se puede convertir, lo dejamos como está (bool o string)
                config[k] = raw if not isinstance(raw, str) else raw.strip()
        # Guardar referencia al script activo
        self.active_script = script
        self.running = True
        self.status_label.configure(text=f"Running → {script_name}")
        # Hilo para ejecutar el script
        def run():
            script.start(config)
            while self.running:
                if hasattr(script, "get_metrics"):
                    metrics = script.get_metrics()
                    self.metrics_label.configure(text=f"Metrics: {metrics}")
                time.sleep(0.5)
        # Iniciar hilo
        self.script_thread = threading.Thread(target=run, daemon=True)
        self.script_thread.start()


    # Metodo para detener el script activo
    def stop_script(self):
        if self.active_script:
            self.running = False
            self.active_script.stop()
            self.status_label.configure(text="Inactive")
            self.active_script = None


    # Metodo para construir la UI
    def build_ui(self):
        # Creación del frame principal con borde rojo
        main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1A1A1A", border_width=2, border_color="#E52525")
        # Main frame ocupando toda la ventana
        main_frame.pack(fill="both", expand=True) 
        # Título  principal
        title = ctk.CTkLabel(main_frame, text="Aim-Assist", font=("Consolas", 42, "bold"), text_color="#E52525")
        title.pack(pady=(50, 10))
        # Subtítulo
        subtitle = ctk.CTkLabel(main_frame, text="CV LAUNCHER", font=("Arial", 16), text_color="#FFFFFF")
        subtitle.pack(pady=(0, 20))
        # Logo
        logo_img = ctk.CTkImage(Image.open("overlay/whiteLogo2.png"), size=(200, 200))
        logo_label = ctk.CTkLabel(main_frame, image=logo_img, text="")
        logo_label.pack(pady=(0, 40))
        # Selector de scripts
        self.script_selector = ctk.CTkComboBox(
            main_frame,
            values=[],
            command=self.load_params_ui
        )
        self.script_selector.pack(pady=(10,20))
        # Estado del script
        self.status_label = ctk.CTkLabel(main_frame, text="Inactive", font=("Arial", 14), text_color="#FFFFFF")
        self.status_label.pack(pady=10)
        # Frame para parámetros
        self.params_frame = ctk.CTkScrollableFrame(main_frame, fg_color="#2e2e2e", height=int(self.screen_h * 0.4))
        self.params_frame.pack(padx=100, pady=10, fill="both", expand=False)
        # Boton de inicio del script
        start_btn = ctk.CTkButton(main_frame, text="START", command=self.start_script,
                          fg_color="#28a745", font=("Arial", 18, "bold"))
        start_btn.pack(pady=10)
        # Boton de parada del script
        stop_btn = ctk.CTkButton(main_frame, text="STOP", command=self.stop_script,
                         fg_color="#dc3545", font=("Arial", 18, "bold"))
        stop_btn.pack(pady=10)
        # Métricas en vivo
        self.metrics_label = ctk.CTkLabel(main_frame, text="Metrics: -", font=("Arial", 12), text_color="#AAAAAA")
        self.metrics_label.pack(pady=10)
