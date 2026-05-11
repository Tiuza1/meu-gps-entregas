import tkinter as tk
from tkinter import filedialog, messagebox
import serial
import serial.tools.list_ports
from threading import Thread, Event
import importlib.util
import os
import time
import ctypes
import pygame

# --- CONFIGURAÇÕES DE SISTEMA ---
def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

class MacroManager:
    def __init__(self, root):
        self.root = root
        self.root.title("RAGBRAZIL - TOTAL INPUT MANAGER")
        self.root.geometry("550x650")
        self.root.configure(bg="#121212")
        self.root.attributes("-topmost", True)

        # Inicializa Pygame para Joystick (Arcade)
        pygame.init()
        pygame.joystick.init()
        self.conectar_joystick()

        self.placa = None
        self.scripts_carregados = {}
        self.gravando_para = None 

        porta = encontrar_placa()
        try:
            self.placa = serial.Serial(porta, 9600, timeout=0)
            status_txt = f"PLACA: {porta} | JOYSTICK: {'OK' if pygame.joystick.get_count() > 0 else 'N/D'}"
            status_color = "#00ff00"
        except:
            status_txt = "PLACA NÃO ENCONTRADA"
            status_color = "#ff0000"

        tk.Label(root, text="GERENCIADOR DE MACROS", bg="#121212", fg="#00ffff", font=("Consolas", 16, "bold")).pack(pady=15)
        self.lbl_status = tk.Label(root, text=status_txt, bg="#121212", fg=status_color, font=("Consolas", 10))
        self.lbl_status.pack()

        self.frame_lista = tk.Frame(root, bg="#121212")
        self.frame_lista.pack(fill="both", expand=True, padx=15, pady=10)

        tk.Button(root, text="+ IMPORTAR SCRIPT", command=self.importar_script, bg="#333", fg="white", font=("Arial", 10, "bold")).pack(side="bottom", fill="x", padx=30, pady=20)

    def conectar_joystick(self):
        """ Inicializa todos os joysticks conectados """
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()

    def importar_script(self):
        caminho = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if not caminho: return
        
        nome = os.path.basename(caminho)
        frame = tk.Frame(self.frame_lista, bg="#1e1e1e", pady=10)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=nome, bg="#1e1e1e", fg="white", width=15, anchor="w").pack(side="left", padx=10)

        btn_key = tk.Button(frame, text="CLIQUE P/ DEFINIR", width=15, bg="#444", fg="#00ffff", 
                            command=lambda n=nome: self.iniciar_gravacao(n))
        btn_key.pack(side="left", padx=10)

        btn_onoff = tk.Button(frame, text="OFF", width=8, bg="#555", fg="white", font=("Arial", 9, "bold"),
                             command=lambda n=nome: self.toggle_script(n))
        btn_onoff.pack(side="right", padx=10)

        self.scripts_carregados[nome] = {
            'caminho': caminho, 'btn_onoff': btn_onoff, 'btn_key': btn_key,
            'status': False, 'stop_event': None, 'tipo_input': None, 'id_input': None
        }
        Thread(target=self.monitor_execucao, args=(nome,), daemon=True).start()

    def iniciar_gravacao(self, nome):
        self.gravando_para = nome
        self.scripts_carregados[nome]['btn_key'].config(text="PRESSIONE ALGO...", bg="#ff8800", fg="black")
        Thread(target=self.capturar_proximo_input, args=(nome,), daemon=True).start()

    def capturar_proximo_input(self, nome):
        detectado = False
        while self.gravando_para == nome:
            # 1. Checa Teclado e MOUSE (0x01 a 0x06 são botões do mouse)
            # 0x01: Esquerdo, 0x02: Direito, 0x04: Meio, 0x05: Lateral 1, 0x06: Lateral 2
            for i in range(0x01, 0xFF):
                if ctypes.windll.user32.GetAsyncKeyState(i) & 0x8000:
                    nome_tecla = {0x05: "Mouse Lateral 1", 0x06: "Mouse Lateral 2"}.get(i, f"Tecla: {hex(i)}")
                    self.scripts_carregados[nome]['tipo_input'] = 'teclado_mouse'
                    self.scripts_carregados[nome]['id_input'] = i
                    self.root.after(0, self.finalizar_gravacao, nome, nome_tecla)
                    detectado = True
                    break
            
            # 2. Checa Arcade/Joystick
            if not detectado:
                pygame.event.pump()
                for j_idx, joy in enumerate(self.joysticks):
                    for b in range(joy.get_numbuttons()):
                        if joy.get_button(b):
                            self.scripts_carregados[nome]['tipo_input'] = 'joystick'
                            self.scripts_carregados[nome]['id_input'] = (j_idx, b)
                            self.root.after(0, self.finalizar_gravacao, nome, f"Arcade Btn: {b}")
                            detectado = True
                            break
            
            if detectado: break
            time.sleep(0.05)

    def finalizar_gravacao(self, nome, texto):
        self.gravando_para = None
        self.scripts_carregados[nome]['btn_key'].config(text=texto, bg="#222", fg="#00ff00")

    def monitor_execucao(self, nome):
        while True:
            script = self.scripts_carregados.get(nome)
            if not script or script['id_input'] is None or self.gravando_para == nome:
                time.sleep(0.1); continue

            ativou = False
            if script['tipo_input'] == 'teclado_mouse':
                if ctypes.windll.user32.GetAsyncKeyState(script['id_input']) & 0x8000:
                    ativou = True
            elif script['tipo_input'] == 'joystick':
                pygame.event.pump()
                j_idx, b_idx = script['id_input']
                if self.joysticks[j_idx].get_button(b_idx):
                    ativou = True

            if ativou:
                self.root.after(0, self.toggle_script, nome)
                while True: # Debounce (espera soltar)
                    time.sleep(0.1)
                    if script['tipo_input'] == 'teclado_mouse':
                        if not (ctypes.windll.user32.GetAsyncKeyState(script['id_input']) & 0x8000): break
                    else:
                        pygame.event.pump()
                        if not self.joysticks[j_idx].get_button(b_idx): break
            time.sleep(0.05)

    def toggle_script(self, nome):
        script = self.scripts_carregados[nome]
        if not script['status']:
            if not self.placa: return
            try:
                spec = importlib.util.spec_from_file_location("mod", script['caminho'])
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                script['status'] = True
                script['btn_onoff'].config(text="ON", bg="#006600")
                script['stop_event'] = Event()
                Thread(target=modulo.executar, args=(self.placa, script['stop_event']), daemon=True).start()
            except Exception as e: print(f"Erro: {e}")
        else:
            script['status'] = False
            script['btn_onoff'].config(text="OFF", bg="#555")
            if script['stop_event']: script['stop_event'].set()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroManager(root)
    root.mainloop()