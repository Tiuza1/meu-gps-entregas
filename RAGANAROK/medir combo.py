import time
import queue
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import keyboard
from pynput import mouse

# =========================================
# MEDIDOR DE COMBO LIVRE
# Grava qualquer tecla/clique na ordem que voce apertar.
# Mostra o delay em ms entre uma tecla e a proxima.
# =========================================

# Estado
log_q = queue.Queue()
eventos = []          # lista de (nome, tempo_ms)
gravando = False
mouse_listener = None

def agora_ms():
    return time.perf_counter() * 1000

def log(msg):
    t = time.strftime("%H:%M:%S")
    log_q.put(f"[{t}] {msg}")

def log_raw(msg):
    # log sem timestamp, pra deixar a tabela de resultado limpa
    log_q.put(msg)

def iniciar_gravacao():
    global eventos, gravando
    eventos = []
    gravando = True
    log("=" * 60)
    log("GRAVACAO INICIADA")
    log("Aperte qualquer tecla ou clique do mouse na ordem.")
    log("Clique em 'Parar' quando terminar o combo.")
    log("=" * 60)

def parar_gravacao():
    global gravando
    if not gravando and not eventos:
        log("Nada gravado ainda.")
        return
    gravando = False
    log("Gravacao parada.")
    exibir_resultado()

def registrar(nome):
    global gravando, eventos

    if not gravando:
        return

    t = agora_ms()
    eventos.append((nome, t))

    # Mostra ao vivo o delay desde a tecla anterior
    if len(eventos) == 1:
        log(f"[{len(eventos)}] {nome}  (inicio)")
    else:
        delta = eventos[-1][1] - eventos[-2][1]
        nome_ant = eventos[-2][0]
        log(f"[{len(eventos)}] {nome_ant} -> {nome}  =  {delta:.1f} ms")

def exibir_resultado():
    if len(eventos) == 0:
        log("Nenhum evento capturado.")
        return

    log_raw("")
    log_raw("=" * 60)
    log_raw("  RESUMO DOS DELAYS ENTRE TECLAS")
    log_raw("=" * 60)

    if len(eventos) == 1:
        log_raw(f"  Apenas 1 evento capturado: {eventos[0][0]}")
        log_raw(f"  Sem delay para calcular.")
        log_raw("=" * 60)
        return

    # Cabecalho da tabela
    log_raw(f"  {'#':>3}  {'DE':<14} -> {'PARA':<14} {'DELAY (ms)':>12}")
    log_raw("  " + "-" * 56)

    for i in range(1, len(eventos)):
        nome_a, t_a = eventos[i-1]
        nome_b, t_b = eventos[i]
        delta = t_b - t_a
        log_raw(f"  {i:>3}  {nome_a:<14} -> {nome_b:<14} {delta:>12.1f}")

    total = eventos[-1][1] - eventos[0][1]
    log_raw("  " + "-" * 56)
    log_raw(f"  Total de teclas capturadas: {len(eventos)}")
    log_raw(f"  Tempo total do combo: {total:.1f} ms ({total/1000:.3f} s)")
    log_raw("=" * 60)
    log_raw("")
    log("Use 'Copiar Tempos' para gerar os time.sleep() prontos.")
    log("Clique em 'Nova Medicao' para gravar outro combo.")

def on_click(x, y, button, pressed):
    if not pressed:
        return
    nome = f"mouse_{button.name}"  # mouse_left, mouse_right, mouse_middle
    registrar(nome)

def on_key(e):
    registrar(e.name)

def instalar_hooks():
    keyboard.on_press(on_key, suppress=False)

def processar_logs(txt, root):
    while not log_q.empty():
        msg = log_q.get()
        txt.configure(state="normal")
        txt.insert(tk.END, msg + "\n")
        txt.see(tk.END)
        txt.configure(state="disabled")
    root.after(50, processar_logs, txt, root)

def copiar_tempos():
    if len(eventos) < 2:
        log("Precisa de pelo menos 2 eventos para gerar delays.")
        return

    linhas = []
    linhas.append("# Combo gerado automaticamente")
    linhas.append("import time")
    linhas.append("")
    linhas.append(f"# 1. {eventos[0][0]}")
    linhas.append(f"# (acao do evento 1 aqui)")

    for i in range(1, len(eventos)):
        delta_ms = eventos[i][1] - eventos[i-1][1]
        delta_s = delta_ms / 1000.0
        linhas.append(f"time.sleep({delta_s:.3f})  # {delta_ms:.1f} ms")
        linhas.append(f"# {i+1}. {eventos[i][0]}")
        linhas.append(f"# (acao do evento {i+1} aqui)")

    texto = "\n".join(linhas)

    root.clipboard_clear()
    root.clipboard_append(texto)
    root.update()
    log("Tempos copiados para a area de transferencia.")

def limpar_log():
    txt.configure(state="normal")
    txt.delete("1.0", tk.END)
    txt.configure(state="disabled")

def fechar():
    try:
        if mouse_listener is not None:
            mouse_listener.stop()
    except:
        pass
    try:
        keyboard.unhook_all()
    except:
        pass
    root.destroy()

# =========================================
# JANELA
# =========================================
root = tk.Tk()
root.title("Medidor de Combo - Delay entre Teclas")
root.geometry("820x580")
root.configure(bg="#111111")
root.attributes("-topmost", True)

frame_top = tk.Frame(root, bg="#111111")
frame_top.pack(fill="x", padx=10, pady=10)

lbl = tk.Label(
    frame_top,
    text="Modo livre: aperta as teclas, clica em 'Parar' e ve o delay em ms entre cada uma.",
    fg="#00ff88",
    bg="#111111",
    font=("Consolas", 10, "bold")
)
lbl.pack(anchor="w")

frame_btn = tk.Frame(root, bg="#111111")
frame_btn.pack(fill="x", padx=10, pady=(0, 10))

btn1 = tk.Button(frame_btn, text="Nova Medicao", command=iniciar_gravacao,
                 bg="#1f1f1f", fg="white", width=18)
btn1.pack(side="left", padx=(0, 8))

btn2 = tk.Button(frame_btn, text="Parar", command=parar_gravacao,
                 bg="#aa2222", fg="white", width=12)
btn2.pack(side="left", padx=(0, 8))

btn3 = tk.Button(frame_btn, text="Copiar Tempos", command=copiar_tempos,
                 bg="#1f1f1f", fg="white", width=16)
btn3.pack(side="left", padx=(0, 8))

btn4 = tk.Button(frame_btn, text="Limpar Log", command=limpar_log,
                 bg="#1f1f1f", fg="white", width=12)
btn4.pack(side="left", padx=(0, 8))

btn5 = tk.Button(frame_btn, text="Fechar", command=fechar,
                 bg="#1f1f1f", fg="white", width=12)
btn5.pack(side="left")

txt = ScrolledText(root, bg="black", fg="#00ff88",
                   insertbackground="white", font=("Consolas", 10))
txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
txt.configure(state="disabled")

processar_logs(txt, root)

mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

instalar_hooks()

log("Janela iniciada.")
log("1. Clique em 'Nova Medicao'.")
log("2. Faca o combo. Cada tecla mostra o delay desde a anterior.")
log("3. Clique em 'Parar' para ver a tabela final com todos os delays.")

root.protocol("WM_DELETE_WINDOW", fechar)
root.mainloop()