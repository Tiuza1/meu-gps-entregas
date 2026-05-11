import os
import json
import time
import threading
import queue
import ctypes

import cv2
import mss
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

# ─── configurações ───────────────────────────────────────────────────────────
CONFIG_FILE          = 'config_ninja_buffs.json'
AURA_FILE            = 'aura.jpg'

MATCH_THRESHOLD_AURA = 0.48

# Aura AUSENTE -> envia FULL_COMBO: F1(28ms) + F2(28ms) + F3(50ms) = ~120ms
# Aura PRESENTE -> envia ATK: F3(50ms) = ~60ms
FULL_COMBO_EXEC  = 0.120
ATK_EXEC         = 0.060
POST_CMD_WAIT    = 0.030

POLL_INTERVAL_OFF = 0.05
STATUS_LOG_EVERY  = 10
# ─────────────────────────────────────────────────────────────────────────────

log_q           = queue.Queue()
serial_lock     = threading.Lock()
log_window_open = False
root_ref        = None


def log(msg):
    t = time.strftime('%H:%M:%S')
    log_q.put(f'[{t}] {msg}')


def caps_on():
    return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)


def carregar_template(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    return img


def detectar_template(gray_img, template, threshold):
    if gray_img.shape[0] < template.shape[0] or gray_img.shape[1] < template.shape[1]:
        return False, 0.0
    res = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold, float(max_val)


def esperar_tecla_espaco(mensagem):
    messagebox.showinfo('Calibracao', mensagem)
    log(mensagem.replace('\n', ' '))
    while True:
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            while ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
                time.sleep(0.03)
            x, y = pyautogui.position()
            log(f'Ponto capturado em x={x}, y={y}')
            time.sleep(0.2)
            return x, y
        time.sleep(0.02)


def calibrar_area():
    p1 = esperar_tecla_espaco(
        'Passo 1/2: leve o mouse ao canto SUPERIOR ESQUERDO do icone da aura e aperte ESPACO.')
    p2 = esperar_tecla_espaco(
        'Passo 2/2: leve o mouse ao canto INFERIOR DIREITO do icone da aura e aperte ESPACO.')
    cfg = {
        'left':   min(p1[0], p2[0]),
        'top':    min(p1[1], p2[1]),
        'width':  abs(p2[0] - p1[0]),
        'height': abs(p2[1] - p1[1]),
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    log(f"Area salva: left={cfg['left']} top={cfg['top']} w={cfg['width']} h={cfg['height']}")
    messagebox.showinfo('Calibracao', 'Area salva com sucesso.')
    return cfg


def escolher_area_inicial():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            resposta = messagebox.askyesnocancel(
                'Area do icone da aura',
                'Sim  = usar a ultima area salva\n'
                'Nao  = redefinir agora\n'
                'Cancelar = fechar\n\n'
                f"left={cfg['left']}  top={cfg['top']}  "
                f"w={cfg['width']}  h={cfg['height']}"
            )
            if resposta is None:
                log('Abertura cancelada pelo usuario.')
                return None
            if resposta:
                log('Usando ultima area salva.')
                return cfg
            log('Usuario escolheu redefinir a area.')
            return calibrar_area()
        except Exception as e:
            log(f'Falha ao ler config antiga: {e}')
            return calibrar_area()
    log('Nenhuma configuracao encontrada, iniciando calibracao.')
    return calibrar_area()


def enviar_comando(placa, comando):
    if not placa:
        return False
    try:
        with serial_lock:
            placa.write((comando + '\n').encode('utf-8'))
            placa.flush()
        return True
    except Exception as e:
        log(f'Erro ao enviar {comando}: {e}')
        return False


def atualizar_logs_widget(txt, root):
    while not log_q.empty():
        txt.configure(state='normal')
        txt.insert(tk.END, log_q.get() + '\n')
        txt.see(tk.END)
        txt.configure(state='disabled')
    root.after(50, atualizar_logs_widget, txt, root)


def iniciar_janela_logs(stop_event, area_holder):
    global root_ref, log_window_open
    root = tk.Tk()
    root_ref = root
    root.title('Ninja Combo Manager v4')
    root.geometry('860x540')
    root.configure(bg='#111111')
    root.attributes('-topmost', True)

    top = tk.Frame(root, bg='#111111')
    top.pack(fill='x', padx=10, pady=(10, 0))

    tk.Label(
        top,
        text='CAPS ON -> aura? -> F1+F2+F3 (ausente) / F3 (presente) | sem click',
        bg='#111111', fg='#00ccff', font=('Consolas', 10, 'bold')
    ).pack(side='left')

    def redefinir():
        root.attributes('-topmost', False)
        area_holder['value'] = calibrar_area()
        root.attributes('-topmost', True)

    tk.Button(top, text='Redefinir area', command=redefinir,
              bg='#222222', fg='white').pack(side='right')

    txt = ScrolledText(root, bg='black', fg='#00ccff',
                       insertbackground='white', font=('Consolas', 10))
    txt.pack(fill='both', expand=True, padx=10, pady=10)
    txt.configure(state='disabled')

    def on_close():
        stop_event.set()
        log_window_open = False
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_close)
    atualizar_logs_widget(txt, root)
    root.mainloop()
    log_window_open = False


def executar(placa, stop_event):
    global log_window_open

    area_holder = {'value': None}

    if not log_window_open:
        log_window_open = True
        threading.Thread(target=iniciar_janela_logs,
                         args=(stop_event, area_holder), daemon=True).start()
        time.sleep(0.6)

    log('Script v4 iniciado [apenas teclas, zero click].')
    log(f'Ciclo ATK~{(ATK_EXEC+POST_CMD_WAIT)*1000:.0f}ms  FULL_COMBO~{(FULL_COMBO_EXEC+POST_CMD_WAIT)*1000:.0f}ms')
    log(f'Pasta atual: {os.getcwd()}')

    if not os.path.exists(AURA_FILE):
        log(f'ERRO: arquivo nao encontrado -> {AURA_FILE}')
        return

    try:
        aura_tpl = carregar_template(AURA_FILE)
        log(f'Template da aura carregado: {aura_tpl.shape}')
    except Exception as e:
        log(f'ERRO ao carregar template: {e}')
        return

    if root_ref:
        root_ref.attributes('-topmost', False)
    area = escolher_area_inicial()
    if root_ref:
        root_ref.attributes('-topmost', True)

    if area is None:
        log('Execucao cancelada antes de iniciar.')
        return

    area_holder['value'] = area
    log(f"Area ativa: left={area['left']} top={area['top']} "
        f"w={area['width']} h={area['height']}")
    log('Aguardando CAPS LOCK...')

    last_caps  = None
    iter_count = 0

    try:
        with mss.mss() as sct:
            while not stop_event.is_set():
                caps = caps_on()

                if caps != last_caps:
                    last_caps = caps
                    if caps:
                        log('CAPS LIGADO -> loop ativo')
                        iter_count = 0
                    else:
                        log('CAPS DESLIGADO -> pausado')

                if not caps:
                    time.sleep(POLL_INTERVAL_OFF)
                    continue

                area = area_holder['value']
                shot = np.array(sct.grab(area))
                gray = cv2.cvtColor(shot, cv2.COLOR_BGRA2GRAY)
                tem_aura, score_aura = detectar_template(gray, aura_tpl, MATCH_THRESHOLD_AURA)

                if tem_aura:
                    enviar_comando(placa, 'ATK')
                    wait = ATK_EXEC + POST_CMD_WAIT
                    if iter_count % STATUS_LOG_EVERY == 0:
                        log(f'[{iter_count}] Aura OK ({score_aura:.2f}) -> F3 | {wait*1000:.0f}ms')
                    time.sleep(wait)
                else:
                    enviar_comando(placa, 'FULL_COMBO')
                    wait = FULL_COMBO_EXEC + POST_CMD_WAIT
                    if iter_count % STATUS_LOG_EVERY == 0:
                        log(f'[{iter_count}] Aura AUSENTE ({score_aura:.2f}) -> F1+F2+F3 | {wait*1000:.0f}ms')
                    time.sleep(wait)

                iter_count += 1

    except Exception as e:
        log(f'ERRO no loop: {e}')
