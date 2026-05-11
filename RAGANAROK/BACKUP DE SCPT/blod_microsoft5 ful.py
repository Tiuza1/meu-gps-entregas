import time
import random
import ctypes
import pyautogui

# Função para verificar se o Caps Lock está ligado
def macro_autorizado():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> MACRO COMPLEXO INICIADO!")
    print(">>> CICLO: 15 FARM -> KAFRA -> LIMPEZA")
    
    largura, altura = pyautogui.size()
    cx, cy = largura // 2, altura // 2
    
    contador = 0

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(0.4)
            continue 

        try:
            # --- PARTE 1: O QUE ELE JÁ FAZ (FARM) ---
            # 1. TELEPORTE
            placa.write(b'T')
            placa.flush()
            time.sleep(random.uniform(0.4, 0.7))

            # 2. ATAQUE
            for _ in range(3):
                if not macro_autorizado(): break
                placa.write(b'A')   
                placa.flush()
                time.sleep(random.uniform(0.1, 0.2))
            
            time.sleep(random.uniform(0.8, 1.2))
            
            # INCREMENTA O CONTADOR
            contador += 1
            print(f"Ciclo: {contador}/15")

            # --- PARTE 2: LÓGICA DO STORAGE (A CADA 15 VEZES) ---
            if contador >= 15:
                print(">>> INICIANDO LIMPEZA NA KAFRA...")
                
                # 1. Abrir Storage (Alt+1) enviado via placa
                placa.write(b'S')
                placa.flush()
                time.sleep(1.2) # Espera a janela abrir

                # 2. Mover mouse para a posição do item
                target_x, target_y = 1433, 930
                pyautogui.moveTo(target_x, target_y, duration=0.1)
                time.sleep(0.5)

                # 3. Verificação de Cor (RGB: 247, 230, 148)
                # Diferença B-R: 148 - 247 = -99
                r, g, b = pyautogui.pixel(target_x, target_y)
                diff = b - r
                
                if r == 247 and g == 230 and b == 148 or diff == -99:
                    print("Item detectado! Guardando...")
                    # 4. Alt + Clique Direito via placa
                    placa.write(b'R')
                    placa.flush()
                    time.sleep(0.2) # tempo de 100ms como solicitado
                else:
                    print(f"Item não detectado ou cor diferente: R:{r} G:{g} B:{b}")

                # 5. Alt+3 para Teleportar e fechar janelas/voltar ao spot
                time.sleep(2.0)
                placa.write(b'T')
                placa.flush()
                
                # Reinicia o contador
                contador = 0
                print(">>> VOLTANDO AO FARM.")

        except Exception as e:
            print(f"Erro: {e}")
            break

    print(">>> MACRO FINALIZADO.")