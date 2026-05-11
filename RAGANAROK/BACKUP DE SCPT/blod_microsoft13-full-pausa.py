import time
import random
import ctypes
import pyautogui

def macro_autorizado():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>>[SISTEMA V10 - CORREÇÃO DEFINITIVA COM SEGURANÇA] - POSIÇÃO FIXA 841, 599")

    # --- COORDENADAS FIXAS ---
    mira_x, mira_y = 841, 599  
    ygg_x, ygg_y = 53, 201     
    hp_x, hp_y = 1490, 64      

    contador = 0

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(0.5)
            continue 

        try:
            # --- 1. CHECAGEM DE VIDA (SEGURANÇA INICIAL) ---
            r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)
            if g_hp < 100: 
                print(">>> [MORTE DETECTADA!] Bot pausado. Reviva o personagem e ative o Caps Lock para continuar.")
                # Fica preso neste loop enquanto a vida estiver baixa
                while True:
                    # Se você desligar no painel geral, ele obedece e fecha
                    if stop_event.is_set(): 
                        break 

                    time.sleep(1)

                    # Checa a vida novamente
                    try:
                        r_hp_novo, g_hp_novo, b_hp_novo = pyautogui.pixel(hp_x, hp_y)
                    except:
                        continue

                    # Se a vida voltou (verde alto) e o Caps Lock está LIGADO, ele retoma o farm
                    if g_hp_novo >= 100 and macro_autorizado():
                        print(">>> [RETOMANDO] Personagem vivo e Caps Lock ativado. Voltando ao trabalho...")
                        break

            # --- 1. CICLO DE FARM ---
            if contador == 0:
                placa.write(f"M{mira_x},{mira_y}\n".encode())
                placa.write(b"L\n") # CLIQUE DE FOCO
                placa.flush()
                time.sleep(0.3)

            print(f"Farmando... Ciclo: {contador + 1}/15")

            # Teleporte
            placa.write(b"T\n")
            placa.flush()
            time.sleep(1.2) # Delay para carregar o mapa

            # Sequência de Ataque
            for _ in range(3):
                placa.write(b"A\n") # Tecla da Magia
                placa.flush()
                time.sleep(0.15)
                placa.write(b"L\n") # Clique no chão para confirmar magia
                placa.flush()
                time.sleep(0.15)

            time.sleep(0.8) # Delay essencial após magia

            contador += 1

            # --- 2. LÓGICA DE KAFRA (A CADA 15 VEZES) ---
            if contador >= 15:

                # ---> NOVO: TERMO DE SEGURANÇA (F1) <---
                print(">>>[SEGURANÇA] Pressionando F1 (Auto Pot)...")
                placa.write(b"P\n")
                placa.flush()
                time.sleep(0.6) # Aguarda meio segundo para a cura/pot pegar no servidor

                # --- 1. CHECAGEM DE VIDA (SEGURANÇA NA KAFRA) ---
                r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)
                if g_hp < 100: 
                    print(">>> [MORTE DETECTADA!] Bot pausado na Kafra. Reviva o personagem e ative o Caps Lock.")
                    while True:
                        if stop_event.is_set(): 
                            break 
                        time.sleep(1)
                        try:
                            r_hp_novo, g_hp_novo, b_hp_novo = pyautogui.pixel(hp_x, hp_y)
                        except:
                            continue
                        if g_hp_novo >= 100 and macro_autorizado():
                            print(">>> [RETOMANDO] Personagem vivo. Voltando...")
                            break

                print(">>> [KAFRA] Iniciando limpeza...")
                placa.write(b"S\n") 
                placa.flush()
                time.sleep(2.0) # Espera a Kafra abrir totalmente

                for volta in range(12):
                    if not macro_autorizado() or stop_event.is_set(): break

                    placa.write(f"M{ygg_x},{ygg_y}\n".encode())
                    placa.flush()
                    time.sleep(0.8)

                    try: 
                        r, g, b = pyautogui.pixel(ygg_x, ygg_y)
                        if abs(r - 206) < 10 and abs(g - 214) < 10 and abs(b - 230) < 10:
                            print("Inventário limpo.")
                            break
                    except: break

                    placa.write(b"R\n") # Guarda/Limpa
                    placa.flush()
                    time.sleep(0.8)

                # --- 3. RESET TOTAL ---
                print(">>> [RESET] Forçando retorno ao chão e foco...")

                # Move para o chão (841, 599) e clica para dar foco no mundo
                placa.write(f"M{mira_x},{mira_y}\n".encode())
                placa.flush()
                time.sleep(0.3)
                placa.write(b"L\n") # Clique de foco para tirar seleção de chat/NPC
                placa.flush()
                time.sleep(0.3)

                # 3 ESCs para garantir que NADA ficou aberto
                for _ in range(3):
                    placa.write(b"\x1b") # ESC
                    placa.flush()
                    time.sleep(0.2)

                # Duplo Teleporte de limpeza
                print("Teleporte de limpeza...")
                for i in range(2):
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(1.3)

                contador = 0 
                print(">>>[PRONTO] Script reiniciado com foco no chão.")

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(1)

    print(">>> MACRO FINALIZADO.")
