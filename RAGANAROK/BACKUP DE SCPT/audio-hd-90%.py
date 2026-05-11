import mss
import numpy as np
import time
import serial
import serial.tools.list_ports
import random
import tkinter as tk
from threading import Thread, Lock

# --- CONFIGURAÇÕES CALIBRADAS (45% HP - BARRA VERDE) ---
X_HP, Y_HP = 1532, 64
LIMITE_VERDE = 150 # Abaixo de 150 (estava 238 cheio) = POTA
# ------------------------------------------------------

serial_lock = Lock()

def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

class RagBot45Pct:
    def __init__(self, root):
        self.root = root
        # Mudei o título da janela para algo discreto (Segurança contra Anti-cheat)
        self.root.title("System Sound Controller") 
        self.root.geometry("200x180")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        
        self.ligado = False
        self.placa = None

        tk.Label(root, text="MODO ECONÔMICO (45%)", bg="#1e1e1e", fg="lightgreen", font=("Arial", 9, "bold")).pack(pady=5)
        
        self.lbl_hw = tk.Label(root, text="STATUS: INICIANDO...", bg="#1e1e1e", fg="white", font=("Arial", 8))
        self.lbl_hw.pack()
        
        self.btn = tk.Button(root, text="OFF", command=self.toggle, width=12, height=2, bg="#333", fg="white")
        self.btn.pack(pady=10)
        
        self.lbl_debug = tk.Label(root, text="Verde: --", bg="#1e1e1e", fg="yellow", font=("Arial", 10, "bold"))
        self.lbl_debug.pack()

        self.conectar()
        Thread(target=self.loop_visao, daemon=True).start()

    def conectar(self):
        porta = encontrar_placa()
        if porta:
            try:
                self.placa = serial.Serial(porta, 9600, timeout=0)
                self.lbl_hw.config(text=f"CONECTADO: {porta}", fg="green")
            except:
                self.lbl_hw.config(text="ERRO: PORTA OCUPADA", fg="red")
        else:
            self.lbl_hw.config(text="PLACA NÃO ENCONTRADA", fg="red")

    def toggle(self):
        self.ligado = not self.ligado
        self.btn.config(text="ON" if self.ligado else "OFF", bg="#008000" if self.ligado else "#333")

    def loop_visao(self):
        with mss.mss() as sct:
            monitor = {"top": Y_HP, "left": X_HP, "width": 1, "height": 1}
            while True:
                if self.ligado and self.placa:
                    img = sct.grab(monitor)
                    px = img.pixel(0, 0)
                    
                    # px[1] é o canal VERDE (RGB: R=0, G=1, B=2)
                    verde_atual = px[1]
                    
                    try: self.lbl_debug.config(text=f"Verde: {verde_atual}")
                    except: pass

                    if verde_atual < LIMITE_VERDE:
                        with serial_lock:
                            try:
                                self.placa.write(b'P')
                                self.placa.flush()
                                # Delay humano rítmico
                                time.sleep(random.uniform(0.08, 0.14))
                            except: pass
                    else:
                        time.sleep(0.005)
                else:
                    time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = RagBot45Pct(root)
    root.mainloop()