import os
import json
import time
import threading
import ctypes

import cv2
import mss
import numpy as np
import pyautogui

# ─── caminhos ────────────────────────────────────────────────────────────────
_DIR          = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(_DIR, 'config_troca_pele.json')
TEMPLATE_FILE = os.path.join(_DIR, 'troca_de_pele.png')
LOG_FILE      = os.path.join(_DIR, 'log_troca_pele.txt')

# ─── configurações ───────────────────────────────────────────────────────────
MATCH_THRESHOLD = 0.72   # score >= este valor → ícone presente (buff ativo)
POLL_MS         = 0.025  # 25ms entre scans (40 checks/s)
COOLDOWN_CAST   = 0.400  # aguarda após enviar F5 antes de checar novamente
# ─────────────────────────────────────────────────────────────────────────────

serial_lock = threading.Lock()


def log(msg):
    t = time.strftime('%H:%M:%S')
    linha = f'[{t}] [PELE] {msg}'
    print(linha)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(linha + '\n')
    except Exception:
        pass


def _msgbox(titulo, msg, flags=0x40):
    return ctypes.windll.user32.MessageBoxW(0, msg, titulo, flags | 0x40000)


def _msgbox_sim_nao_cancelar(titulo, msg):
    return ctypes.windll.user32.MessageBoxW(0, msg, titulo, 0x03 | 0x20 | 0x40000)


def carregar_template(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    return img


def detectar(gray_img, template):
    if gray_img.shape[0] < template.shape[0] or gray_img.shape[1] < template.shape[1]:
        return False, 0.0
    res = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= MATCH_THRESHOLD, float(max_val)


def esperar_espaco(mensagem):
    _msgbox('Calibração', mensagem)
    while True:
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            while ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
                time.sleep(0.03)
            x, y = pyautogui.position()
            time.sleep(0.15)
            return x, y
        time.sleep(0.02)


def calibrar():
    p1 = esperar_espaco(
        'Passo 1/2\n\nLeve o mouse ao canto SUPERIOR ESQUERDO\n'
        'do ícone na barra de skill e aperte ESPAÇO.')
    p2 = esperar_espaco(
        'Passo 2/2\n\nLeve o mouse ao canto INFERIOR DIREITO\n'
        'do ícone na barra de skill e aperte ESPAÇO.')
    cfg = {
        'left':   min(p1[0], p2[0]),
        'top':    min(p1[1], p2[1]),
        'width':  abs(p2[0] - p1[0]),
        'height': abs(p2[1] - p1[1]),
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    log(f"Área calibrada: left={cfg['left']} top={cfg['top']} "
        f"w={cfg['width']} h={cfg['height']}")
    _msgbox('Calibração OK', 'Área salva com sucesso!')
    return cfg


def escolher_area():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            r = _msgbox_sim_nao_cancelar(
                'Área do ícone — Troca de Pele',
                f"left={cfg['left']}  top={cfg['top']}  "
                f"w={cfg['width']}  h={cfg['height']}\n\n"
                'Sim       = usar área salva\n'
                'Não       = recalibrar\n'
                'Cancelar = sair'
            )
            if r == 2:
                return None
            if r == 6:
                log(f"Área carregada: left={cfg['left']} top={cfg['top']} "
                    f"w={cfg['width']} h={cfg['height']}")
                return cfg
            return calibrar()
        except Exception as e:
            log(f'Config inválida: {e} → recalibrando')
            return calibrar()
    log('Sem configuração → iniciando calibração.')
    return calibrar()


def enviar(placa, cmd):
    try:
        with serial_lock:
            placa.write((cmd + '\n').encode())
            placa.flush()
        return True
    except Exception as e:
        log(f'Erro serial [{cmd}]: {e}')
        return False


def executar(placa, stop_event):
    # Limpa log anterior ao iniciar
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f'=== Troca de Pele v1 — {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n')
    except Exception:
        pass

    log('Script iniciado. Ativo assim que ON no painel.')
    log(f'Template : {TEMPLATE_FILE}')

    # ── verifica template ──────────────────────────────────────────────────
    if not os.path.exists(TEMPLATE_FILE):
        log(f'ERRO: template não encontrado → {TEMPLATE_FILE}')
        _msgbox('Erro', f'Arquivo não encontrado:\n{TEMPLATE_FILE}', 0x10)
        return

    try:
        tpl = carregar_template(TEMPLATE_FILE)
        log(f'Template: {tpl.shape[1]}x{tpl.shape[0]}px')
    except Exception as e:
        log(f'ERRO ao carregar template: {e}')
        _msgbox('Erro', f'Falha ao carregar template:\n{e}', 0x10)
        return

    # ── área de scan ──────────────────────────────────────────────────────
    area = escolher_area()
    if area is None:
        log('Cancelado.')
        return

    # Avisa se área menor que template (matching impossível)
    if area['width'] < tpl.shape[1] or area['height'] < tpl.shape[0]:
        log(f'AVISO: área ({area["width"]}x{area["height"]}) '
            f'menor que template ({tpl.shape[1]}x{tpl.shape[0]}). Recalibre!')
        _msgbox('Aviso',
                f'Área capturada ({area["width"]}x{area["height"]}px) é menor '
                f'que o template ({tpl.shape[1]}x{tpl.shape[0]}px).\n\n'
                'Recalibre selecionando uma área maior.',
                0x30)
        return

    log(f'Threshold={MATCH_THRESHOLD} | Scan={POLL_MS*1000:.0f}ms | '
        f'Cooldown={COOLDOWN_CAST*1000:.0f}ms')
    log('Monitorando — ativo direto (sem tecla de toggle).')

    ultimo_cast = 0.0
    cast_count  = 0
    miss_seq    = 0   # misses consecutivos antes de disparar (evita falso-positivo)

    with mss.mss() as sct:
        while not stop_event.is_set():

            # ── cooldown pós-cast ──────────────────────────────────────────
            if (time.time() - ultimo_cast) < COOLDOWN_CAST:
                time.sleep(POLL_MS)
                continue

            # ── captura e detecta ──────────────────────────────────────────
            try:
                frame = np.array(sct.grab(area))
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                encontrou, score = detectar(gray, tpl)
            except Exception as e:
                log(f'Erro no scan: {e}')
                time.sleep(POLL_MS)
                continue

            if not encontrou:
                miss_seq += 1
                # 2 misses consecutivos (50ms) antes de disparar — evita frame de transição
                if miss_seq >= 2:
                    cast_count += 1
                    log(f'Buff sumiu (score={score:.3f}) → SKIN (F5)  #{cast_count}')
                    enviar(placa, 'SKIN')
                    ultimo_cast = time.time()
                    miss_seq = 0
            else:
                miss_seq = 0

            time.sleep(POLL_MS)

    log(f'Script finalizado. Total casts: {cast_count}')
    log(f'Log salvo em: {LOG_FILE}')
