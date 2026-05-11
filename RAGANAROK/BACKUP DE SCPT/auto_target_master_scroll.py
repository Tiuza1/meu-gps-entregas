import mss
import cv2
import numpy as np
import time
import ctypes
import pyautogui
import winsound

def is_active():
    # Retornado para SCROLL LOCK (0x91)
    return ctypes.windll.user32.GetKeyState(0x91) & 1

def executar(placa, stop_event):
    print(">>> [MECH] BOT CAÇADOR DE ÁRVORES 100% AUTOMÁTICO INICIADO")
    print(">>> ATIVAÇÃO: [SCROLL LOCK LIGADO]")
    winsound.Beep(1000, 200)
    winsound.Beep(1500, 200)

    # --- CONFIGURAÇÕES DE SCAN (ÁRVORE) ---
    monitor = {"top": 240, "left": 660, "width": 600, "height": 600}
    lower_green = np.array([30, 40, 30])
    upper_green = np.array([80, 200, 180])

    # --- CONFIGURAÇÕES DO SISTEMA ---
    hp_x, hp_y = 1490, 64
    item_x, item_y = 89, 201 
    r_vazio, g_vazio, b_vazio = 206, 214, 230 

    # --- MEMÓRIAS E CRONÔMETROS ---
    alvos_recentes = []
    tentativas_falhas = 0
    ultimo_alvo = None

    tempo_inicio = time.time()
    ultima_checagem_hp = tempo_inicio
    ultimo_buff = tempo_inicio - 60.0    # Para buffar imediatamente ao ligar
    ultimo_armazem = tempo_inicio        # Vai esperar 5 minutos para a primeira kafra

    with mss.mss() as sct:
        while not stop_event.is_set():
            if not is_active():
                time.sleep(0.1)
                tentativas_falhas = 0
                alvos_recentes.clear()
                continue

            try:
                tempo_atual = time.time()

                # --- PASSO 1: SISTEMA DE SEGURANÇA (HP) ---
                if tempo_atual - ultima_checagem_hp > 2.0:
                    ultima_checagem_hp = tempo_atual
                    r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)

                    if g_hp < 100: 
                        print(">>> [MORTE DETECTADA!] O personagem morreu. Aguardando 2s...")
                        for _ in range(3): winsound.Beep(500, 300)
                        time.sleep(2.0)

                        print(">>> Enviando Alt+6 (Resgate) e pausando bot...")
                        placa.write(b"X\n")
                        placa.flush()
                        time.sleep(1.0)

                        while True:
                            if stop_event.is_set(): break 
                            time.sleep(1)
                            try:
                                r_novo, g_novo, b_novo = pyautogui.pixel(hp_x, hp_y)
                            except:
                                continue
                            if g_novo >= 100 and is_active():
                                print(">>> [RETOMANDO] Personagem salvo! Voltando à caça...")
                                winsound.Beep(2000, 150)
                                winsound.Beep(2000, 150)
                                ultima_checagem_hp = time.time() 
                                break

                tempo_atual = time.time()

                # --- PASSO 2: SISTEMA DE BUFF (A cada 60s) ---
                if tempo_atual - ultimo_buff > 60.0:
                    print(">>> [BUFF] Parando tudo para castar o Buff...")
                    winsound.Beep(1200, 100)
                    winsound.Beep(1800, 100)

                    placa.write(b"B\n")
                    placa.flush()
                    time.sleep(0.5)

                    print(">>> [BUFF] Concluído!")
                    ultimo_buff = time.time()

                tempo_atual = time.time()

                # --- PASSO 3: SISTEMA DE KAFRA (A cada 5 Minutos = 300s) ---
                if tempo_atual - ultimo_armazem > 300.0:
                    print("\n>>> [KAFRA] Hora de guardar os Galhos Secos!")
                    winsound.Beep(600, 150)
                    winsound.Beep(600, 150)

                    placa.write(b"S\n")
                    placa.flush()
                    time.sleep(0.8) 

                    atual_x, atual_y = pyautogui.position()
                    delta_x = item_x - atual_x
                    delta_y = item_y - atual_y

                    placa.write(f"V{delta_x},{delta_y}\n".encode())
                    placa.flush()
                    time.sleep(0.5) 

                    for _ in range(15):
                        if not is_active() or stop_event.is_set(): break
                        try: 
                            r, g, b = pyautogui.pixel(item_x, item_y)
                            if abs(r - r_vazio) < 10 and abs(g - g_vazio) < 10 and abs(b - b_vazio) < 10:
                                print(">>> [KAFRA] Inventário Limpo! Todos os galhos foram guardados.")
                                break
                        except Exception as e:
                            break

                        placa.write(b"R\n")
                        placa.flush()
                        time.sleep(0.6) 

                    print(">>> [KAFRA] Retomando caça com Teleporte...")
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(1.0)

                    ultimo_armazem = time.time()

                # --- MULTIKILL TURBO (A CAÇA) ---
                alvos_recentes = [alvo for alvo in alvos_recentes if tempo_atual - alvo[2] < 1.5]

                img = np.array(sct.grab(monitor))
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                mask = cv2.inRange(hsv, lower_green, upper_green)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                arvore_encontrada = False

                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 100 and area < 4000:
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"]) + monitor["left"]
                            cy = int(M["m01"] / M["m00"]) + monitor["top"]

                            if abs(cx - 960) < 30 and abs(cy - 540) < 30:
                                continue

                            ignorar_alvo = False
                            for alvo in alvos_recentes:
                                if abs(cx - alvo[0]) < 40 and abs(cy - alvo[1]) < 40:
                                    ignorar_alvo = True
                                    break
                            if ignorar_alvo: continue 

                            atual_x, atual_y = pyautogui.position()
                            delta_x = cx - atual_x
                            delta_y = cy - atual_y

                            placa.write(f"V{delta_x},{delta_y}\n".encode())
                            placa.flush()
                            time.sleep(0.08) 

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
                                time.sleep(0.8)
                                break

                            placa.write(b"Q\n")
                            placa.flush()

                            alvos_recentes.append((cx, cy, tempo_atual))
                            arvore_encontrada = True
                            break 

                if not arvore_encontrada:
                    ultimo_alvo = None
                    tentativas_falhas = 0
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(0.4) 

            except Exception as e:
                time.sleep(0.5)

    print(">>> BOT FINALIZADO.")
