import pyautogui
import time
import ctypes
from datetime import datetime
import threading
import tkinter as tk
import queue

# ========================================================
# ⚙️ MODO TURBO - CONFIGURAÇÕES DE DELAY (AJUSTE AQUI)
# ========================================================
# Ritmo de checagem contínua da vida. Padrão era 0.12.
INTERVALO_ATAQUE = 0.12

# Tempo de "respiro" APÓS o HP encher antes de mandar a Aura.
COOLDOWN_DO_ATAQUE = 0.43  

# Tempo para a Aura carregar antes de voltar a vigiar.
TEMPO_DA_AURA = 0.40  

# ========================================================
# SISTEMA DE LOGS
# ========================================================
log_q = queue.Queue()

def log(msg):
    t = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_q.put(f"[{t}] {msg}")

def janela_logs_thread():
    root = tk.Tk()
    root.title("Ninja - Vigia de Aura (Sem F3)")
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
def macro_ataque_ativo():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def calibrar_hp(stop_event):
    msg = (
        "NINJA MORTAL - SOMENTE AURA\n\n"
        "1. Deixe o HP CHEIO.\n"
        "2. Mova o mouse para 10% da barra verde.\n"
        "3. Aperte ESPAÇO para salvar."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "Calibração", 0x40 | 0x0)

    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            r, g, b = pyautogui.pixel(x, y)
            conf = f"HP Salvo!\nX: {x} | Y: {y}\nCor: RGB({r}, {g}, {b})"
            ctypes.windll.user32.MessageBoxW(0, conf, "Pronto!", 0x40 | 0x0)
            time.sleep(1.0)
            return x, y, (r, g, b)
        time.sleep(0.05)
    return None, None, None

def checar_hp(hdc, x_hp, y_hp, r_base, g_base, b_base):
    color = ctypes.windll.gdi32.GetPixel(hdc, x_hp, y_hp)
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    cheio = abs(r - r_base) < 30 and abs(g - g_base) < 30 and abs(b - b_base) < 30
    return cheio, (r, g, b)

def sleep_and_poll(delay_sec, hdc, x, y, r_b, g_b, b_b):
    start = time.perf_counter()
    caiu_alguma_vez = False
    rgb_da_queda = (0,0,0)
    
    while time.perf_counter() - start < delay_sec:
        cheio, rgb = checar_hp(hdc, x, y, r_b, g_b, b_b)
        if not cheio:
            caiu_alguma_vez = True
            rgb_da_queda = rgb
        time.sleep(0.005)
    return caiu_alguma_vez, rgb_da_queda

def executar(placa, stop_event):
    threading.Thread(target=janela_logs_thread, daemon=True).start()
    time.sleep(0.5)

    x_hp, y_hp, cor_base = calibrar_hp(stop_event)
    if x_hp is None: return

    r_base, g_base, b_base = cor_base
    log("="*50)
    log(f"VIGIA DE AURA ATIVADO!")
    log(f"Respiro Pré-Aura: {COOLDOWN_DO_ATAQUE}s | Cast Aura: {TEMPO_DA_AURA}s")
    log("="*50)

    user32 = ctypes.windll.user32
    hdc = user32.GetDC(0)

    hp_precisa_f4 = False
    estado_anterior = False

    while not stop_event.is_set():
        caps_on = macro_ataque_ativo()

        if not caps_on:
            if estado_anterior:
                log("CAPS LOCK DESLIGADO -> PAUSANDO VIGIA")
                estado_anterior = False
            hp_precisa_f4 = False
            time.sleep(0.05)
            continue

        if not estado_anterior:
            log("CAPS LOCK LIGADO -> VIGIANDO O HP")
            estado_anterior = True

        try:
            hp_cheio, rgb_atual = checar_hp(hdc, x_hp, y_hp, r_base, g_base, b_base)

            if not hp_cheio:
                if not hp_precisa_f4:
                    log(f"HP CAIU! Marcando F4 na fila.")
                    hp_precisa_f4 = True
                
                # Apenas espera (O Q foi removido)
                time.sleep(INTERVALO_ATAQUE)
                
            else:
                if hp_precisa_f4:
                    log(f"HP RECUPEROU! Pausando {COOLDOWN_DO_ATAQUE}s (Respiro)...")
                    
                    time.sleep(COOLDOWN_DO_ATAQUE) 
                    
                    log(">>> ENVIANDO F4 (AURA) PARA A PLACA <<<")
                    placa.write(b"A\n")
                    placa.flush()
                    
                    time.sleep(TEMPO_DA_AURA) 
                    
                    log(">>> AURA PRONTA <<<")
                    hp_precisa_f4 = False
                else:
                    # Apenas vigia o HP (O Q foi removido)
                    caiu_no_delay, rgb_queda = sleep_and_poll(INTERVALO_ATAQUE, hdc, x_hp, y_hp, r_base, g_base, b_base)
                    
                    if caiu_no_delay:
                        hp_precisa_f4 = True

        except Exception as e:
            log(f"Erro no loop: {e}")
            time.sleep(0.5)

    user32.ReleaseDC(0, hdc)