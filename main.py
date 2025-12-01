import keyboard
from overlay.ui import UILauncher


if __name__ == "__main__":
    print("Iniciando UILauncher...")
    app = UILauncher()
    app.load_scripts()
    keyboard.add_hotkey("ctrl+alt+a", app.toggle_panel)
    app.mainloop()