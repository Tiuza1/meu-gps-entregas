import time
import random
import ctypes
import pyautogui

# Função para verificar se o Caps Lock está ligado
def macro_autorizado():
    # 0x14 é o código do Caps Lock. 
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> MACRO INICIADO!")
    print(">>> LIGUE O [CAPS LOCK] PARA FARMER")
    print(">>> DESLIGUE O [CAPS LOCK] PARA PAUSAR")

    # Pega o centro da tela para o movimento do mouse
    largura, altura = pyautogui.size()
    cx, cy = largura // 2, altura // 2

    while not stop_event.is_set():
        # --- VERIFICAÇÃO DE PAUSA ---
        if not macro_autorizado():
            time.sleep(0.5)
            continue 

        try:
            # 1. TELEPORTE
            placa.write(b'T')
            placa.flush() # Garante o envio do comando
            time.sleep(random.uniform(0.6, 1.0)) # Espera o teleporte carregar

            if not macro_autorizado(): continue

            
            
            # 3. COMBO DE ATAQUE (Faz 3 sequências de F3 + Click)
            for _ in range(3):
                if not macro_autorizado(): break
                placa.write(b'A')   
                placa.flush()
                # Pequena pausa entre cada clique do combo
                time.sleep(random.uniform(0.1, 0.2))
            
            # 4. ESPERA DA SKILL (Depois dos 3 ataques, espera o delay da skill)
            # Movido para fora do loop 'for' para não travar cada clique
            time.sleep(random.uniform(1.2, 1.8))

        except Exception as e:
            print(f"Erro no loop de execução: {e}")
            break

    print(">>> MACRO FINALIZADO.")