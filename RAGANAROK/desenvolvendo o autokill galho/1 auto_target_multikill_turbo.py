import mss
import cv2
import numpy as np
import time
import ctypes
import pyautogui

def is_active():
    return ctypes.windll.user32.GetKeyState(0x91) & 1

def executar(placa, stop_event):
    print(">>> BOT DE CAÇA TURBO (TELEPORTE DO MOUSE) INICIADO")
    print(">>> ATIVAÇÃO: [SCROLL LOCK LIGADO]")

    monitor = {"top": 240, "left": 660, "width": 600, "height": 600}

    lower_green = np.array([30, 40, 30])
    upper_green = np.array([80, 200, 180])

    alvos_recentes = []
    tentativas_falhas = 0
    ultimo_alvo = None

    with mss.mss() as sct:
        while not stop_event.is_set():
            if not is_active():
                time.sleep(0.1)
                tentativas_falhas = 0
                alvos_recentes.clear()
                continue

            try:
                tempo_atual = time.time()
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

                            # --- O PULO DO GATO PARA VELOCIDADE ---
                            # Lemos a posição do seu mouse físico no Windows
                            atual_x, atual_y = pyautogui.position()

                            # Calculamos exatamente quantos pixels faltam para chegar na árvore
                            delta_x = cx - atual_x
                            delta_y = cy - atual_y

                            # Enviamos o comando 'V' (Viajar Relativo) para a placa
                            # Ao invés de zerar o mouse na ponta da tela e voltar, ele só dá o "pulinho" necessário
                            placa.write(f"V{delta_x},{delta_y}\n".encode())
                            placa.flush()

                            time.sleep(0.08) # Praticamente instantâneo agora

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
