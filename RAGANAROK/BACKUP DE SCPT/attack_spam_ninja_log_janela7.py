import pyautogui
import time
import random
import ctypes
from datetime import datetime
import threading
import tkinter as tk
import queue
import json
import os

# ========================================================
# ⚙️ MODO HÍBRIDO - AUTOPOT + AURA INSTANTÂNEA
# ========================================================
TEMPO_DA_AURA = 0.40  
NOME_ARQUIVO_CFG = "config_autopot_aura.json"

log_q = queue.Queue()

def log(msg):
    t = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_q.put(f"[{t}] {msg}")

def janela_logs_thread():
    root = tk.Tk()
    root.title("Ninja - Autopot + Aura")
    root.geometry("550x400")
    root.attributes("-topmost", True)
    txt = tk.Text(root, bg="black", fg="lime", font=("Consolas", 10))
    txt.pack(expand=True, fill="both")
    def atualizar_logs():
        while not log_q.empty():
            txt.insert(tk.END, log_q.get() + "\n")
            txt.see(tk.END)
        root.after(50, atualizar_logs)
    root.after(50, atualizar_logs)
    root.mainloop()

# ========================================================
# MEMÓRIA
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
            except:
                pass

    dados = funcao_calibrar(stop_event)
    if dados is not None:
        with open(nome_arquivo, 'w') as f:
            json.dump(dados, f, indent=4)
    return dados

def calibrar_hp(stop_event):
    msg = (
        "NINJA - AUTOPOT + AURA\n\n"
        "1. Deixe o HP CHEIO.\n"
        "2. Mova o mouse para 10% da barra verde (Local de cura).\n"
        "3. Aperte ESPAÇO para salvar."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "Calibração", 0x40 | 0x40000)

    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            r, g, b = pyautogui.pixel(x, y)
            ctypes.windll.user32.MessageBoxW(0, "Pronto! Salvo com sucesso.", "OK", 0x40 | 0x40000)
            time.sleep(1.0)
            return {"x": x, "y": y, "r": r, "g": g, "b": b}
        time.sleep(0.05)
    return None

def checar_hp_rapido(hdc, x_hp, y_hp, r_base, g_base, b_base):
    color = ctypes.windll.gdi32.GetPixel(hdc, x_hp, y_hp)
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    # Se a cor do pixel for muito diferente da barra verde, o HP não está cheio
    cheio = abs(r - r_base) < 30 and abs(g - g_base) < 30 and abs(b - b_base) < 30
    return cheio, r, g, b

def executar(placa, stop_event):
    threading.Thread(target=janela_logs_thread, daemon=True).start()
    time.sleep(0.5)

    cfg = carregar_ou_calibrar(NOME_ARQUIVO_CFG, calibrar_hp, stop_event)
    if cfg is None: return

    x_hp, y_hp = cfg["x"], cfg["y"]
    r_base, g_base, b_base = cfg["r"], cfg["g"], cfg["b"]

    log("="*50)
    log("SISTEMA HÍBRIDO (AUTOPOT + AURA) INICIADO!")
    log("="*50)

    user32 = ctypes.windll.user32
    hdc = user32.GetDC(0)

    hp_caiu = False

    while not stop_event.is_set():
        try:
            hp_cheio, r, g, b = checar_hp_rapido(hdc, x_hp, y_hp, r_base, g_base, b_base)

            if not hp_cheio:
                # SE O HP NÃO TÁ CHEIO, A PRIORIDADE MÁXIMA É POTAR
                log(f">>> HP VAZIO! POTANDO (P) <<< RGB:({r},{g},{b})")
                try:
                    placa.write(b"P\n")
                    placa.flush()
                except:
                    pass
                
                hp_caiu = True
                # Espera a poção fazer efeito antes de tentar olhar de novo
                time.sleep(random.uniform(0.03, 0.06))
                
            else:
                # SE O HP TÁ CHEIO, E ELE TINHA CAIDO, ENTÃO É A HORA DA AURA
                if hp_caiu:
                    log(">>> HP RECUPERADO! AURA ENVIADA (A) <<<")
                    try:
                        placa.write(b"A\n")
                        placa.flush()
                    except:
                        pass
                    
                    time.sleep(TEMPO_DA_AURA) 
                    hp_caiu = False
                else:
                    time.sleep(0.001)

        except Exception as e:
            time.sleep(0.1)

    user32.ReleaseDC(0, hdc)
    log("SCRIPT FINALIZADO.")