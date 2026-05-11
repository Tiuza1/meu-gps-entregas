import time
import random
import ctypes
import pyautogui

def macro_autorizado():
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def executar(placa, stop_event):
    print(">>>[SISTEMA V12 - 2X SPEED + 20 TELEPORTES] - POSIÇÃO FIXA 841, 599")

    mira_x, mira_y = 841, 599
    ygg_x, ygg_y = 53, 201
    hp_x, hp_y = 1490, 64
    r_vazio, g_vazio, b_vazio = 206, 214, 230

    contador = 0
    ultimo_foco = None
    focos_recentes = []

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(random.uniform(0.05, 0.08))
            focos_recentes.clear()
            continue

        try:
            r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)
            if g_hp < 100:
                print(">>> [MORTE DETECTADA!] Aguardando o jogo processar...")
                time.sleep(random.uniform(1.2, 1.5))
                print(">>> Enviando Alt+6 e pausando bot...")
                placa.write(b"X\n")
                placa.flush()
                time.sleep(random.uniform(0.6, 0.8))
                print(">>> Aguardando reviver e Num Lock ativado...")
                while True:
                    if stop_event.is_set():
                        break
                    time.sleep(random.uniform(0.5, 0.8))
                    try:
                        r_hp_novo, g_hp_novo, b_hp_novo = pyautogui.pixel(hp_x, hp_y)
                    except:
                        continue
                    if g_hp_novo >= 100 and macro_autorizado():
                        print(">>> [RETOMANDO] Personagem vivo. Voltando ao ciclo...")
                        break

            if contador == 0:
                atual_x, atual_y = pyautogui.position()
                delta_x = mira_x - atual_x
                delta_y = mira_y - atual_y
                placa.write(f"V{delta_x},{delta_y}\n".encode())
                placa.flush()
                time.sleep(random.uniform(0.04, 0.06))
                placa.write(b"L\n")
                placa.flush()
                time.sleep(random.uniform(0.12, 0.18))

            print(f"Farmando... Ciclo: {contador + 1}/20")

            placa.write(b"T\n")
            placa.flush()
            time.sleep(random.uniform(0.8, 1.0))

            atual_x, atual_y = pyautogui.position()
            delta_x = mira_x - atual_x
            delta_y = mira_y - atual_y
            placa.write(f"V{delta_x},{delta_y}\n".encode())
            placa.flush()
            time.sleep(random.uniform(0.05, 0.07))

            placa.write(b"Q\n")
            placa.flush()
            focos_recentes.append((mira_x, mira_y, time.time()))
            focos_recentes = [f for f in focos_recentes if time.time() - f[2] < 1.0]
            time.sleep(random.uniform(0.45, 0.55))
            contador += 1

            if contador >= 20:
                print(">>>[SEGURANÇA] Pressionando F1 antes da Kafra...")
                placa.write(b"P\n")
                placa.flush()
                time.sleep(random.uniform(0.18, 0.28))

                r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)
                if g_hp < 100:
                    print(">>> [MORTE DETECTADA na KAFRA!] Aguardando processamento...")
                    time.sleep(random.uniform(1.2, 1.5))
                    placa.write(b"X\n")
                    placa.flush()
                    time.sleep(random.uniform(0.6, 0.8))
                    while True:
                        if stop_event.is_set():
                            break
                        time.sleep(random.uniform(0.5, 0.8))
                        try:
                            r_hp_novo, g_hp_novo, b_hp_novo = pyautogui.pixel(hp_x, hp_y)
                        except:
                            continue
                        if g_hp_novo >= 100 and macro_autorizado():
                            print(">>> [RETOMANDO] Vivo novamente após Kafra.")
                            break

                print(">>> [KAFRA] Iniciando limpeza...")
                placa.write(b"S\n")
                placa.flush()
                time.sleep(random.uniform(0.8, 1.1))

                for volta in range(12):
                    if not macro_autorizado() or stop_event.is_set():
                        break
                    atual_x, atual_y = pyautogui.position()
                    delta_x = ygg_x - atual_x
                    delta_y = ygg_y - atual_y
                    placa.write(f"V{delta_x},{delta_y}\n".encode())
                    placa.flush()
                    time.sleep(random.uniform(0.35, 0.55))
                    try:
                        r, g, b = pyautogui.pixel(ygg_x, ygg_y)
                        if abs(r - r_vazio) < 10 and abs(g - g_vazio) < 10 and abs(b - b_vazio) < 10:
                            print(">>> [KAFRA] Inventário limpo.")
                            break
                    except:
                        break
                    placa.write(b"R\n")
                    placa.flush()
                    time.sleep(random.uniform(0.35, 0.55))

                print(">>> [RESET] Retornando ao chão e limpando foco...")
                atual_x, atual_y = pyautogui.position()
                delta_x = mira_x - atual_x
                delta_y = mira_y - atual_y
                placa.write(f"V{delta_x},{delta_y}\n".encode())
                placa.flush()
                time.sleep(random.uniform(0.12, 0.20))
                placa.write(b"L\n")
                placa.flush()
                time.sleep(random.uniform(0.12, 0.20))
                for _ in range(3):
                    placa.write(b"\x1b")
                    placa.flush()
                    time.sleep(random.uniform(0.08, 0.12))
                print(">>> [RESET] Teleporte de limpeza...")
                for i in range(2):
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(random.uniform(0.7, 0.9))

                contador = 0
                ultimo_foco = None
                focos_recentes.clear()
                print(">>>[PRONTO] Script reiniciado com foco no chão.")

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(random.uniform(0.2, 0.4))

    print(">>> MACRO FINALIZADO.")
