import time
import random
import ctypes
import pyautogui

def macro_autorizado():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>>[SISTEMA V10 - CORREÇÃO DEFINITIVA] - POSIÇÃO FIXA 841, 599")
    
    # --- COORDENADAS FIXAS ---
    mira_x, mira_y = 841, 599  # Onde o mouse deve ficar para a magia pegar no chão
    ygg_x, ygg_y = 53, 201     # Slot da YGG
    hp_x, hp_y = 1490, 64      # Barra de HP
    
    contador = 0

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(0.5)
            continue 

        try:
            # --- 1. CICLO DE FARM ---
            # IGUAL AO V7: Move e foca APENAS no início do ciclo! (Evita spam e bug no hardware)
            if contador == 0:
                placa.write(f"M{mira_x},{mira_y}\n".encode())
                placa.write(b"L\n") # CLIQUE DE FOCO
                placa.flush()
                time.sleep(0.3)

            print(f"Farmando... Ciclo: {contador + 1}/15")
            
            # Teleporte (Agora com o personagem livre para usar a skill)
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
            
            # [CORREÇÃO CRÍTICA]: O V10 havia removido o delay do V7.
            # Sem isso, o personagem não tem tempo de sair da animação da magia 
            # e o jogo IGNORA o Teleporte do próximo turno!
            time.sleep(0.8) 
            
            contador += 1

            # --- 2. LÓGICA DE KAFRA (A CADA 15 VEZES) ---
            if contador >= 15:
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

                # --- 3. RESET TOTAL (MOLDADO IGUAL AO V7) ---
                print(">>> [RESET] Forçando retorno ao chão e foco...")
                
                # Move para o chão (841, 599) e clica para dar foco no mundo
                placa.write(f"M{mira_x},{mira_y}\n".encode())
                placa.flush()
                time.sleep(0.3)
                placa.write(b"L\n") # Clique de foco para tirar seleção de chat/NPC
                placa.flush()
                time.sleep(0.3)

                # 3 ESCs para garantir que NADA ficou aberto (No V10 original tinham apenas 2)
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