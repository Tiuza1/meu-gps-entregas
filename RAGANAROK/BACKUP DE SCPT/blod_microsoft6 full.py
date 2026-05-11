import time
import random
import ctypes
import pyautogui

# Função para verificar se o Caps Lock está ligado
def macro_autorizado():
    # 0x14 é o código do Caps Lock
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> [SISTEMA UNIFICADO V3] INICIADO")
    print(">>> MODO: 15 CICLOS DE FARM -> LIMPEZA KAFRA")
    
    # Coordenadas (Ajuste conforme sua resolução)
    ygg_x, ygg_y = 55, 199 
    centro_x, centro_y = 839, 527
    hp_x, hp_y = 1490, 64
    
    contador = 0

    while not stop_event.is_set():
        # Se Caps Lock estiver desligado, o macro pausa
        if not macro_autorizado():
            time.sleep(0.5)
            continue 

        try:
            # --- PARTE 1: CHECAGEM DE SEGURANÇA (HP) ---
            try:
                r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)
                if g_hp < 100: 
                    print(">>> [ALERTA] HP BAIXO OU MORTE! Tentando recuperar...")
                    placa.write(b"X\n") # Comando de reviver ou Alt+6
                    placa.flush()
                    time.sleep(2)
            except Exception as e:
                print(f"Erro ao ler pixel de HP: {e}")

            # --- PARTE 2: CICLO DE FARM (TELEPORTE + ATAQUE) ---
            print(f"Iniciando Ciclo {contador + 1}/15")
            
            # Teleporte (Botão T)
            placa.write(b"T\n")
            placa.flush()
            time.sleep(random.uniform(0.6, 1.0))

            # Sequência de Ataque (Botão A)
            for _ in range(3):
                if not macro_autorizado(): break
                placa.write(b"A\n")   
                placa.flush()
                time.sleep(random.uniform(0.1, 0.2))
            
            time.sleep(random.uniform(0.8, 1.2))
            contador += 1

# ... (início do código permanece igual)

            # --- PARTE 3: LÓGICA DE LIMPEZA (A CADA 15 CICLOS) ---
            if contador >= 15:
                print(">>> [KAFRA] Iniciando limpeza de inventário...")
                
                placa.write(b"S\n") # Abre Kafra
                placa.flush()
                time.sleep(1.5)

                tentativas_limpeza = 0
                
                # Loop de limpeza de slots
                while tentativas_limpeza < 12 and not stop_event.is_set():
                    if not macro_autorizado(): break
                    
                    # 1. Move para o primeiro slot para checar o que tem lá
                    placa.write(f"M{ygg_x},{ygg_y}\n".encode())
                    placa.flush()
                    time.sleep(0.6) # Espera o mouse chegar

                    # 2. Captura a cor atual do slot
                    try:
                        r, g, b = pyautogui.pixel(ygg_x, ygg_y)
                    except:
                        continue

                    # --- NOVA LIBERAÇÃO: CHECAGEM DE SLOT VAZIO (COR DA SUA IMAGEM) ---
                    # Se a cor for próxima de 206, 214, 230 (cinza azulado do fundo)
                    # Usei uma margem de erro de 10 para garantir que funcione mesmo com variações leves
                    if abs(r - 206) < 10 and abs(g - 214) < 10 and abs(b - 230) < 10:
                        print(f">>> [CHECK] Slot vazio detectado ({r},{g},{b}). Saindo da limpeza...")
                        break # Sai do loop de limpeza e volta pro farm

                    # --- LÓGICA DA YGG ---
                    # Se for amarelado (YGG)
                    elif r > 200 and g > 170:
                        print(">>> YGG Detectada! Guardando...")
                        placa.write(b"R\n")
                        placa.flush()
                        time.sleep(0.8)
                    
                    # --- LÓGICA DE ITEM LIXO ---
                    # Se não for a cor do fundo e nem a YGG, considera lixo
                    else: 
                        print(f"Limpando item lixo (Cor: {r},{g},{b})...")
                        placa.write(b"R\n")
                        placa.flush()
                        time.sleep(0.8)
                        tentativas_limpeza += 1

                # Retorno e Reset
                placa.write(f"M{centro_x},{centro_y}\n".encode())
                placa.flush()
                contador = 0
                print(">>> [SISTEMA] Inventário pronto. Farm Reiniciado.")

# ... (resto do código)
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(1)

    print(">>> MACRO FINALIZADO.")