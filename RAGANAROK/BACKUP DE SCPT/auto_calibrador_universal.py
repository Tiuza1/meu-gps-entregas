import mss
import cv2
import numpy as np
import time
import ctypes
import pyautogui
import winsound
import random
import json
import os

# ==============================================================================
# SISTEMA DE CONFIGURAÇÃO UNIVERSAL (SEM CMD - Usa Janelas Nativas do Windows)
# Copie este bloco de funções para qualquer outro script para usar o mesmo padrão!
# ==============================================================================

ARQUIVO_CONFIG = "bot_configuracao_padrao.json"

def msg_box(titulo, texto, estilo=0):
    # Estilos: 0=OK, 4=Yes/No, 0x40=Aviso, 0x20=Pergunta
    return ctypes.windll.user32.MessageBoxW(0, texto, titulo, estilo)

def esperar_shift():
    # Espera soltar o SHIFT caso esteja pressionado
    while ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000:
        time.sleep(0.01)
    # Espera pressionar o SHIFT
    while True:
        if ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000:
            x, y = pyautogui.position()
            winsound.Beep(1000, 200)
            time.sleep(0.3)
            return x, y
        time.sleep(0.05)

def calibrar_novo_pc():
    msg_box("Calibração - Passo 1 (HP)", 
            "Mova o mouse para o final da BARRA DE HP (onde fica vazio se perder vida).\n\n"
            "Pressione a tecla SHIFT para salvar.", 0x40)
    hp_x, hp_y = esperar_shift()

    msg_box("Calibração - Passo 2 (Inventário)", 
            "Abra a Kafra/Inventário.\n"
            "Mova o mouse para o SLOT VAZIO (onde o item será guardado).\n\n"
            "Pressione a tecla SHIFT para salvar a posição e a cor.", 0x40)
    item_x, item_y = esperar_shift()
    r_v, g_v, b_v = pyautogui.pixel(item_x, item_y)

    msg_box("Calibração - Passo 3 (Área de Caça - Início)", 
            "Mova o mouse para o CANTO SUPERIOR ESQUERDO da área onde os monstros aparecem.\n\n"
            "Pressione a tecla SHIFT para salvar.", 0x40)
    tl_x, tl_y = esperar_shift()

    msg_box("Calibração - Passo 4 (Área de Caça - Fim)", 
            "Mova o mouse para o CANTO INFERIOR DIREITO da área de caça.\n\n"
            "Pressione a tecla SHIFT para salvar.", 0x40)
    br_x, br_y = esperar_shift()

    # FÓRMULA UNIVERSAL DO JSON - Use esse formato para todos os seus scripts
    config = {
        "hp": {"x": hp_x, "y": hp_y},
        "item": {"x": item_x, "y": item_y, "r": r_v, "g": g_v, "b": b_v},
        "scan": {"top": tl_y, "left": tl_x, "width": br_x - tl_x, "height": br_y - tl_y}
    }

    with open(ARQUIVO_CONFIG, 'w') as f:
        json.dump(config, f, indent=4)

    msg_box("Sucesso!", "Configuração salva com sucesso! O bot será iniciado agora.", 0x40)
    return config

def carregar_configuracao():
    if os.path.exists(ARQUIVO_CONFIG):
        # 4 = Yes/No, 0x20 = Question Icon -> 6 = Yes, 7 = No
        resposta = msg_box("Configuração Encontrada", 
                           f"Foi encontrada uma configuração salva neste PC.\n\n"
                           "Deseja usar as coordenadas salvas?\n\n"
                           "[SIM] - Para Iniciar o Bot\n"
                           "[NÃO] - Para Recalibrar o Mouse", 4 | 0x20)

        if resposta == 6: # Clicou em SIM
            try:
                with open(ARQUIVO_CONFIG, 'r') as f:
                    return json.load(f)
            except:
                msg_box("Erro", "Falha ao ler configuração. Recalibrando...", 0x30)
                return calibrar_novo_pc()
        else: # Clicou em NÃO
            return calibrar_novo_pc()
    else:
        msg_box("Bem-vindo!", "Nenhuma configuração encontrada. Vamos calibrar as coordenadas do jogo para este PC.", 0x40)
        return calibrar_novo_pc()

# ==============================================================================
# MOTOR DO BOT
# ==============================================================================

def is_active():
    return ctypes.windll.user32.GetKeyState(0x91) & 1

def executar(placa, stop_event):
    # CHAMA A INTERFACE ANTES DE RODAR O LOOP PESADO
    cfg = carregar_configuracao()

    # Aplica a "Fórmula" puxando as variáveis do dicionário
    hp_x, hp_y = cfg["hp"]["x"], cfg["hp"]["y"]
    item_x, item_y = cfg["item"]["x"], cfg["item"]["y"]
    r_vazio, g_vazio, b_vazio = cfg["item"]["r"], cfg["item"]["g"], cfg["item"]["b"]
    monitor = cfg["scan"]

    winsound.Beep(1000, 200)
    winsound.Beep(1500, 200)

    # --- CONFIGURAÇÕES DE CORES (Anjos - Brancos/Beges) ---
    lower_white = np.array([0, 0, 190])
    upper_white = np.array([179, 60, 255])

    alvos_recentes = []
    tentativas_falhas = 0
    ultimo_alvo = None

    tempo_inicio = time.time()
    ultima_checagem_hp = tempo_inicio

    limite_buff = random.uniform(58.0, 62.0)
    limite_armazem = random.uniform(295.0, 305.0)

    ultimo_buff = tempo_inicio - limite_buff    
    ultimo_armazem = tempo_inicio        

    with mss.mss() as sct:
        while not stop_event.is_set():
            if not is_active():
                time.sleep(random.uniform(0.08, 0.12))
                tentativas_falhas = 0
                alvos_recentes.clear()
                continue

            try:
                tempo_atual = time.time()

                # --- SISTEMA DE SEGURANÇA (HP) ---
                if tempo_atual - ultima_checagem_hp > 2.0:
                    ultima_checagem_hp = tempo_atual
                    r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)

                    # Pela lógica, se estiver verde, g_hp será > 100. Se morrer, g_hp cai (cinza/azulado escuro).
                    # Por isso não precisamos capturar a cor, apenas a posição!
                    if g_hp < 100: 
                        for _ in range(3): winsound.Beep(500, 300)
                        time.sleep(random.uniform(1.8, 2.2))

                        placa.write(b"X\n")
                        placa.flush()
                        time.sleep(random.uniform(0.9, 1.2))

                        while True:
                            if stop_event.is_set(): break 
                            time.sleep(random.uniform(0.8, 1.2))
                            try:
                                r_novo, g_novo, b_novo = pyautogui.pixel(hp_x, hp_y)
                            except:
                                continue
                            if g_novo >= 100 and is_active():
                                winsound.Beep(2000, 150)
                                winsound.Beep(2000, 150)
                                ultima_checagem_hp = time.time() 
                                break

                tempo_atual = time.time()

                # --- SISTEMA DE BUFF ---
                if tempo_atual - ultimo_buff > limite_buff:
                    placa.write(b"B\n")
                    placa.flush()
                    time.sleep(random.uniform(0.4, 0.6))
                    ultimo_buff = time.time()
                    limite_buff = random.uniform(58.0, 62.0)

                tempo_atual = time.time()

                # --- SISTEMA DE KAFRA ---
                if tempo_atual - ultimo_armazem > limite_armazem:
                    winsound.Beep(600, 150)
                    placa.write(b"P\n")
                    placa.flush()
                    time.sleep(random.uniform(0.4, 0.6))

                    placa.write(b"S\n")
                    placa.flush()
                    time.sleep(random.uniform(0.7, 0.9)) 

                    atual_x, atual_y = pyautogui.position()
                    delta_x = item_x - atual_x
                    delta_y = item_y - atual_y

                    placa.write(f"V{delta_x},{delta_y}\n".encode())
                    placa.flush()
                    time.sleep(random.uniform(0.4, 0.6)) 

                    for _ in range(15):
                        if not is_active() or stop_event.is_set(): break
                        try: 
                            r, g, b = pyautogui.pixel(item_x, item_y)
                            if abs(r - r_vazio) < 10 and abs(g - g_vazio) < 10 and abs(b - b_vazio) < 10:
                                break
                        except Exception as e:
                            break

                        placa.write(b"R\n")
                        placa.flush()
                        time.sleep(random.uniform(0.5, 0.7)) 

                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(random.uniform(0.9, 1.2))

                    ultimo_armazem = time.time()
                    limite_armazem = random.uniform(290.0, 310.0)

                # --- MULTIKILL TURBO: CAÇA ---
                alvos_recentes = [alvo for alvo in alvos_recentes if tempo_atual - alvo[2] < 1.5]

                img = np.array(sct.grab(monitor))
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, lower_white, upper_white)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                monstro_encontrado = False

                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 120 and area < 4000:
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"]) + monitor["left"]
                            cy = int(M["m01"] / M["m00"]) + monitor["top"]

                            centro_tela_x = monitor["left"] + (monitor["width"] // 2)
                            centro_tela_y = monitor["top"] + (monitor["height"] // 2)

                            if abs(cx - centro_tela_x) < 40 and abs(cy - centro_tela_y) < 40:
                                continue

                            ignorar_alvo = False
                            for alvo in alvos_recentes:
                                if abs(cx - alvo[0]) < 40 and abs(cy - alvo[1]) < 40:
                                    ignorar_alvo = True
                                    break
                            if ignorar_alvo: continue 

                            atual_x, atual_y = pyautogui.position()
                            delta_x = cx - atual_x
                            delta_y = cy - atual_y + 10

                            placa.write(f"V{delta_x},{delta_y}\n".encode())
                            placa.flush()
                            time.sleep(random.uniform(0.07, 0.10)) 

                            if ultimo_alvo and abs(cx - ultimo_alvo[0]) < 20 and abs(cy - ultimo_alvo[1]) < 20:
                                tentativas_falhas += 1
                            else:
                                tentativas_falhas = 1
                                ultimo_alvo = (cx, cy)

                            if tentativas_falhas >= 3:
                                ultimo_alvo = None
                                tentativas_falhas = 0
                                placa.write(b"T\n")
                                placa.flush()
                                time.sleep(random.uniform(0.7, 0.9))
                                break

                            placa.write(b"Q\n")
                            placa.flush()

                            alvos_recentes.append((cx, cy, tempo_atual))
                            monstro_encontrado = True
                            break 

                if not monstro_encontrado:
                    ultimo_alvo = None
                    tentativas_falhas = 0
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(random.uniform(0.35, 0.45)) 

            except Exception as e:
                time.sleep(random.uniform(0.4, 0.6))
