import pyautogui
import time
import ctypes
from datetime import datetime
import threading
import tkinter as tk
import queue
import json
import os

# ========================================================
# ⚙️ MODO EXTREMO - CONFIGURAÇÕES DE DELAY
# ========================================================
# TEMPO DE ESPERA DEPOIS DE MANDAR A AURA (Para não floodar a placa)
# Só depois desse tempo ele volta a vigiar o HP
TEMPO_DA_AURA = 0.40  
NOME_ARQUIVO_CFG = "config_aura_extrema.json"

# ========================================================
# SISTEMA DE MEMÓRIA (CARREGAR / SALVAR)
# ========================================================
def carregar_ou_calibrar(nome_arquivo, funcao_calibrar, stop_event):
    if os.path.exists(nome_arquivo):
        resposta = ctypes.windll.user32.MessageBoxW(
            0,
            f"Configuração '{nome_arquivo}' encontrada!\n\nDeseja carregar os dados salvos e pular a calibração?",
            "Aproveitar Configuração?",
            0x04 | 0x20 | 0x40000
        )
        if resposta == 6: # SIM
            try:
                with open(nome_arquivo, 'r') as f:
                    return json.load(f)
            except Exception as e:
                ctypes.windll.user32.MessageBoxW(0, f"Erro ao ler arquivo. Recalibrando...", "Erro", 0x10 | 0x40000)

    dados = funcao_calibrar(stop_event)

    if dados is not None:
        with open(nome_arquivo, 'w') as f:
            json.dump(dados, f, indent=4)

    return dados

# ========================================================
# SISTEMA DE LOGS
# ========================================================
log_q = queue.Queue()

def log(msg):
    t = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_q.put(f"[{t}] {msg}")

def janela_logs_thread():
    root = tk.Tk()
    root.title("Ninja - Vigia de Aura (Modo Extremo + Memória)")
    root.geometry("550x400")
    root.attributes("-topmost", True)
    
    txt = tk.Text(root, bg="black", fg="lime", font=("Consolas", 10))
    txt.pack(expand=True, fill="both")
    
    def atualizar_logs():
        while not log_q.empty():
            msg = log_q.get()
            txt.insert(tk.END, msg + "\n")
            txt.see(tk.END)
        root.after(50, atualizar_logs)
        
    root.after(50, atualizar_logs)
    root.mainloop()

# ========================================================
# CÓDIGO DO MACRO
# ========================================================
def calibrar_hp(stop_event):
    msg = (
        "NINJA MORTAL - REAÇÃO INSTANTÂNEA\n\n"
        "1. Deixe o HP CHEIO.\n"
        "2. Mova o mouse para 10% da barra verde.\n"
        "3. Aperte ESPAÇO para salvar."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "Calibração", 0x40 | 0x40000)

    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            r, g, b = pyautogui.pixel(x, y)
            conf = f"HP Salvo!\nX: {x} | Y: {y}\nCor: RGB({r}, {g}, {b})"
            ctypes.windll.user32.MessageBoxW(0, conf, "Pronto!", 0x40 | 0x40000)
            time.sleep(1.0)
            return {"x": x, "y": y, "r": r, "g": g, "b": b}
        time.sleep(0.05)
    return None

def checar_hp_rapido(hdc, x_hp, y_hp, r_base, g_base, b_base):
    color = ctypes.windll.gdi32.GetPixel(hdc, x_hp, y_hp)
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    return abs(r - r_base) < 30 and abs(g - g_base) < 30 and abs(b - b_base) < 30

def executar(placa, stop_event):
    threading.Thread(target=janela_logs_thread, daemon=True).start()
    time.sleep(0.5)

    # Chama o sistema inteligente que lê do JSON ou mapeia novo
    cfg = carregar_ou_calibrar(NOME_ARQUIVO_CFG, calibrar_hp, stop_event)
    if cfg is None: return

    x_hp, y_hp = cfg["x"], cfg["y"]
    r_base, g_base, b_base = cfg["r"], cfg["g"], cfg["b"]

    log("="*50)
    log("VIGIA MODO EXTREMO (0 DELAY) ATIVADO COM MEMÓRIA!")
    log("="*50)

    user32 = ctypes.windll.user32
    hdc = user32.GetDC(0)

    hp_caiu = False

    while not stop_event.is_set():
        try:
            hp_cheio = checar_hp_rapido(hdc, x_hp, y_hp, r_base, g_base, b_base)

            if not hp_cheio:
                if not hp_caiu:
                    log("HP CAIU! Gatilho armado.")
                    hp_caiu = True
                
                time.sleep(0.001) 
                
            else:
                if hp_caiu:
                    log("HP ENCHEU! >>> AURA ENVIADA INSTANTANEAMENTE <<<")
                    
                    try:
                        placa.write(b"A\n")
                        placa.flush()
                    except Exception:
                        pass
                    
                    time.sleep(TEMPO_DA_AURA) 
                    
                    log("--- PRONTO PARA O PRÓXIMO CICLO ---")
                    hp_caiu = False
                else:
                    time.sleep(0.001)

        except Exception as e:
            time.sleep(0.1)

    user32.ReleaseDC(0, hdc)
    log("SCRIPT FINALIZADO.")