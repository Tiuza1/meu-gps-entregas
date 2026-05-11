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
# ⚙️ MODO HÍBRIDO - AUTOPOT INTENSO + AURA GARANTIDA
# ========================================================
# Tempo que o script espera DEPOIS que a vida encher antes de puxar a Aura.
# Ajuda a furar o delay pós-mortal do Ragnarok.
ESPERA_POS_CURA = 0.15

# Tempo de "respiro" pra animação da Aura terminar antes do script voltar a olhar a tela.
TEMPO_DA_AURA = 0.35  

NOME_ARQUIVO_CFG = "config_autopot_aura.json"

log_q = queue.Queue()

def log(msg):
    t = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_q.put(f"[{t}] {msg}")

def janela_logs_thread():
    root = tk.Tk()
    root.title("Ninja - Autopot Rápido + Aura Garantida")
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
            f"Configuração encontrada!\n\nDeseja carregar os dados e pular calibração?",
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
    log("SISTEMA HÍBRIDO - POT EXTREMO E AURA REFINADA")
    log("="*50)

    user32 = ctypes.windll.user32
    hdc = user32.GetDC(0)

    hp_caiu = False

    while not stop_event.is_set():
        try:
            hp_cheio, r, g, b = checar_hp_rapido(hdc, x_hp, y_hp, r_base, g_base, b_base)

            if not hp_cheio:
                # ==========================================
                # O POT CONTINUA NA VELOCIDADE MÁXIMA
                # ==========================================
                log(f">>> HP VAZIO! POTANDO (P) <<< RGB:({r},{g},{b})")
                try:
                    placa.write(b"P\n")
                    placa.flush()
                except:
                    pass
                
                hp_caiu = True
                # Respiro do Autopot que vc não quer mexer
                time.sleep(random.uniform(0.02, 0.05))
                
            else:
                if hp_caiu:
                    # ==========================================
                    # NOVO CÉREBRO DA AURA
                    # ==========================================
                    log(">>> HP RECUPERADO! Preparando Aura...")
                    
                    # 1. Espera o servidor destravar o boneco do ataque anterior
                    time.sleep(ESPERA_POS_CURA)
                    
                    # 2. Metralha a Aura 3x rápido pra garantir o hit no server
                    try:
                        for _ in range(1):
                            placa.write(b"A\n")
                            placa.flush()
                            time.sleep(0.01) # Intervalo entre cada A
                    except:
                        pass
                    
                    log(">>> AURA ENVIADA (3x) <<<")
                    
                    # 3. Respiro do Cast da Aura (Tempo da animação no jogo)
                    time.sleep(TEMPO_DA_AURA) 
                    
                    hp_caiu = False
                else:
                    time.sleep(0.001)

        except Exception as e:
            time.sleep(0.1)

    user32.ReleaseDC(0, hdc)
    log("SCRIPT FINALIZADO.")