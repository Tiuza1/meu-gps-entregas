import time
import random
import ctypes
import pyautogui

def macro_autorizado():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> [SISTEMA V7] - RESET TOTAL POR CLIQUE")
    
    # Coordenadas
    ygg_x, ygg_y = 53, 201 
    centro_x, centro_y = 839, 527
    hp_x, hp_y = 1490, 64
    
    contador = 0

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(0.5)
            continue 

        try:
            # --- 1. CICLO DE FARM ---
            # Antes de atacar, garante que o foco está no centro
            if contador == 0:
                placa.write(f"M{centro_x},{centro_y}\n".encode())
                placa.write(b"L\n") # CLIQUE ESQUERDO para garantir foco igual ao 'Início'
                placa.flush()
                time.sleep(0.2)

            print(f"Farmando... Ciclo: {contador + 1}/15")
            placa.write(b"T\n")
            placa.flush()
            time.sleep(1.0)

            for _ in range(3):
                placa.write(b"A\n") # Magia/Ataque
                placa.flush()
                time.sleep(0.15)
                # O "Clique Extra" que você sugeriu para desbugar a magia:
                placa.write(b"L\n") # Clique esquerdo após a magia
                placa.flush()
                time.sleep(0.1)
            
            time.sleep(0.8)
            contador += 1

            # --- 2. LÓGICA DE KAFRA ---
            if contador >= 15:
                print(">>> [KAFRA] Limpando...")
                placa.write(b"S\n") 
                placa.flush()
                time.sleep(1.8)

                for volta in range(12):
                    if not macro_autorizado() or stop_event.is_set(): break
                    placa.write(f"M{ygg_x},{ygg_y}\n".encode())
                    placa.flush()
                    time.sleep(0.6)

                    try: r, g, b = pyautogui.pixel(ygg_x, ygg_y)
                    except: break

                    if abs(r - 206) < 10 and abs(g - 214) < 10 and abs(b - 230) < 10:
                        break

                    placa.write(b"R\n") # Guarda/Limpa
                    placa.flush()
                    time.sleep(0.8)

                # --- 3. O RESET MÁGICO (VOLTAR AO ESTADO INICIAL) ---
                print(">>> [RESET] Forçando estado inicial do script...")
                
                # A. Move para o centro
                placa.write(f"M{centro_x},{centro_y}\n".encode())
                placa.flush()
                time.sleep(0.3)

                # B. CLIQUE ESQUERDO NO CENTRO (Isso desbuga o foco do NPC/Chat)
                placa.write(b"L\n") 
                placa.flush()
                time.sleep(0.3)

                # C. Três ESCs para garantir que NADA ficou aberto
                for _ in range(3):
                    placa.write(b"\x1b") # ESC
                    placa.flush()
                    time.sleep(0.2)

                # D. DUPLO TELEPORTE DE LIMPEZA
                for i in range(2):
                    print(f"Teleporte de limpeza {i+1}/2...")
                    placa.write(b"T\n")
                    placa.flush()
                    time.sleep(1.3)

                # E. CLIQUE FINAL DE FOCO
                placa.write(b"L\n")
                placa.flush()
                
                contador = 0 
                print(">>> [OK] Script resetado. Começando como se fosse a primeira vez.")

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(1)

    print(">>> MACRO FINALIZADO.")