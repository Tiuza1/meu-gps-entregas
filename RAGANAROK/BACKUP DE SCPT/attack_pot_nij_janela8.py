import time
import ctypes
from datetime import datetime
import threading
import tkinter as tk
import queue

log_q = queue.Queue()

def log(msg):
    t = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_q.put(f"[{t}] {msg}")

def janela_logs_thread():
    root = tk.Tk()
    root.title("Metralhadora F4->F2->Click")
    root.geometry("550x350")
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

def executar(placa, stop_event):
    threading.Thread(target=janela_logs_thread, daemon=True).start()
    time.sleep(0.5)

    log("="*50)
    log("METRALHADORA LIGADA: F4 -> F2 -> Click")
    log("Aponte para o inimigo e LIGUE O CAPS LOCK.")
    log("="*50)

    user32 = ctypes.windll.user32
    estado_anterior = False 

    while not stop_event.is_set():
        try:
            # Verifica se o Caps Lock está LIGADO (1)
            caps_ligado = bool(user32.GetKeyState(0x14) & 1)

            if caps_ligado:
                if not estado_anterior:
                    log(">>> CAPS LIGADO! Iniciando spam de magias na Placa (M) <<<")
                    estado_anterior = True
                
                try:
                    # Grita M pra placa, e a placa cuida dos Delays (1.2s no total)
                    placa.write(b"M\n") 
                    placa.flush()
                except: pass
                
                # Aguarda o ciclo terminar na placa pra mandar de novo
                # F4(0.05 + 0.4) + F2(0.05 + 0.4) + Click(0.4) = ~1.3 segundos
                time.sleep(1.3) 
                
            else:
                if estado_anterior:
                    log("--- CAPS DESLIGADO! Pausando metralhadora ---")
                    estado_anterior = False
                time.sleep(0.05)

        except Exception as e:
            time.sleep(0.1)

    log("SCRIPT FINALIZADO.")