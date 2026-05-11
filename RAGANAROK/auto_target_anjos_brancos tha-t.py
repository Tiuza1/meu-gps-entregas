import mss
import cv2
import numpy as np
import time
import ctypes
import pyautogui
import winsound
import random

def is_active():
    return ctypes.windll.user32.GetKeyState(0x91) & 1

def executar(placa, stop_event):
    print(">>> [MECH] BOT ARENA (CAÇADOR DE ANJOS) INICIADO")
    print(">>> ATIVAÇÃO: [SCROLL LOCK LIGADO]")
    winsound.Beep(1000, 200)
    winsound.Beep(1500, 200)

    # --- CONFIGURAÇÕES DE SCAN (ASAS BRANCAS/BEGES) ---
    monitor = {"top": 240, "left": 660, "width": 600, "height": 600}

    # Paleta HSV para tons muito claros/brancos/bege (Asas dos anjos)
    # H pode ser qualquer coisa (0-179)
    # S deve ser baixo (pouca cor, mais branco/cinza) (0-60)
    # V deve ser MUITO ALTO (muito brilho, destaca do chão cinza) (200-255)
    lower_white = np.array([0, 0, 190])
    upper_white = np.array([179, 60, 255])

    # --- CONFIGURAÇÕES DO SISTEMA ---
    hp_x, hp_y = 1490, 64
    item_x, item_y = 89, 201 
    r_vazio, g_vazio, b_vazio = 206, 214, 230 

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

                    if g_hp < 100: 
                        print(">>> [MORTE DETECTADA!] Aguardando...")
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

                # --- MULTIKILL TURBO: CAÇA AOS ANJOS ---
                alvos_recentes = [alvo for alvo in alvos_recentes if tempo_atual - alvo[2] < 1.5]

                img = np.array(sct.grab(monitor))
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                mask = cv2.inRange(hsv, lower_white, upper_white)

                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                monstro_encontrado = False

                for contour in contours:
                    area = cv2.contourArea(contour)
                    # Aumentamos a área MÍNIMA para ignorar itens pequenos no chão e pegar só as asas/corpo grandes
                    if area > 120 and area < 4000:
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"]) + monitor["left"]
                            cy = int(M["m01"] / M["m00"]) + monitor["top"]

                            # Ignora o centro da tela (o próprio personagem)
                            if abs(cx - 960) < 40 and abs(cy - 540) < 40:
                                continue

                            ignorar_alvo = False
                            for alvo in alvos_recentes:
                                if abs(cx - alvo[0]) < 40 and abs(cy - alvo[1]) < 40:
                                    ignorar_alvo = True
                                    break
                            if ignorar_alvo: continue 

                            atual_x, atual_y = pyautogui.position()
                            delta_x = cx - atual_x
                            # Clica no centro de gravidade das asas (que fica um pouco pra cima no sprite)
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

    print(">>> BOT FINALIZADO.")
