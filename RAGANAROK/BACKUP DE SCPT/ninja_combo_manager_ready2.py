import os
import json
import time
import threading
import ctypes

import cv2
import mss
import numpy as np
import pyautogui

# ─── configurações ───────────────────────────────────────────────────────────
_DIR        = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_DIR, 'config_ninja_buffs.json')
AURA_FILE   = os.path.join(_DIR, 'aura.jpg')

MATCH_THRESHOLD_AURA = 0.48
AURA_RETRY_COOLDOWN  = 0.01   # tempo mínimo entre ativações de AURA_YGG (F2+F1)
SPAM_INTERVAL        = 0.12   # intervalo entre cada Q (F3+click)
POLL_INTERVAL_ON     = 0.005  # frequência do loop com CAPS ligado
POLL_INTERVAL_OFF    = 0.05   # frequência do loop com CAPS desligado
STATUS_INTERVAL      = 0.1    # intervalo entre logs de status
# ─────────────────────────────────────────────────────────────────────────────

serial_lock = threading.Lock()


def log(msg):
    t = time.strftime('%H:%M:%S')
    print(f'[{t}] [NINJA] {msg}')


def _msgbox(titulo, msg, flags=0x40):
    """Caixa de mensagem Win32 — funciona de qualquer thread."""
    return ctypes.windll.user32.MessageBoxW(0, msg, titulo, flags | 0x40000)


def _msgbox_sim_nao_cancelar(titulo, msg):
    """Retorna: 6=Sim, 7=Não, 2=Cancelar."""
    return ctypes.windll.user32.MessageBoxW(0, msg, titulo, 0x03 | 0x20 | 0x40000)


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
    _msgbox('Calibração', mensagem)
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
    _msgbox('Calibração', 'Área salva com sucesso.')
    return cfg


def escolher_area_inicial():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            resposta = _msgbox_sim_nao_cancelar(
                'Área do ícone da aura',
                'Sim  = usar a última área salva\n'
                'Não  = redefinir agora\n'
                'Cancelar = fechar\n\n'
                f"left={cfg['left']}  top={cfg['top']}  "
                f"w={cfg['width']}  h={cfg['height']}"
            )
            if resposta == 2:   # Cancelar
                log('Abertura cancelada pelo usuario.')
                return None
            if resposta == 6:   # Sim
                log('Usando ultima area salva.')
                return cfg
            # Não → redefinir
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


def executar(placa, stop_event):
    log('Script iniciado.')
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

    area = escolher_area_inicial()
    if area is None:
        log('Execucao cancelada antes de iniciar.')
        return

    log(f"Area ativa: left={area['left']} top={area['top']} "
        f"w={area['width']} h={area['height']}")
    log('Aguardando CAPS LOCK...')

    last_aura_cmd = 0.0
    last_spam     = 0.0
    last_status   = 0.0
    last_caps     = None

    try:
        with mss.mss() as sct:
            while not stop_event.is_set():
                agora = time.perf_counter()
                caps  = caps_on()

                if caps != last_caps:
                    last_caps = caps
                    if caps:
                        log('CAPS LIGADO -> verificando aura + spam ativo')
                        last_spam     = 0.0
                        last_aura_cmd = 0.0
                    else:
                        log('CAPS DESLIGADO -> pausado')

                if not caps:
                    time.sleep(POLL_INTERVAL_OFF)
                    continue

                shot = np.array(sct.grab(area))
                gray = cv2.cvtColor(shot, cv2.COLOR_BGRA2GRAY)
                tem_aura, score_aura = detectar_template(gray, aura_tpl, MATCH_THRESHOLD_AURA)

                if not tem_aura and (agora - last_aura_cmd) >= AURA_RETRY_COOLDOWN:
                    last_aura_cmd = agora
                    log(f'Aura AUSENTE ({score_aura:.2f}) -> AURA_YGG (F2+F1)')
                    enviar_comando(placa, 'AURA_YGG')

                if (agora - last_spam) >= SPAM_INTERVAL:
                    last_spam = agora
                    enviar_comando(placa, 'Q')

                if (agora - last_status) >= STATUS_INTERVAL:
                    last_status = agora
                    estado = 'OK' if tem_aura else 'AUSENTE'
                    log(f'Status | Aura={estado} ({score_aura:.2f})')

                time.sleep(POLL_INTERVAL_ON)

    except Exception as e:
        log(f'ERRO no loop: {e}')
