import mss
import numpy as np
import time
import random
import ctypes  # <--- Adicionado para ler o estado do teclado
from threading import Lock

# --- CONFIGURAÇÕES ---
X_HP, Y_HP = 1532, 64
LIMITE_VERDE = 150 

def macro_autorizado():
    """ Verifica se a luz do Caps Lock (0x14) está ligada """
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    """
    Esta função é chamada pelo Gerenciador de Macros.
    """
    print(">>> SCRIPT DE HP INICIADO")
    print(">>> ATIVAÇÃO: [CAPS LOCK ON] | PAUSA: [CAPS LOCK OFF]")
    
    with mss.mss() as sct:
        monitor = {"top": Y_HP, "left": X_HP, "width": 1, "height": 1}
        
        while not stop_event.is_set():
            # --- NOVA VERIFICAÇÃO DE SEGURANÇA ---
            if not macro_autorizado():
                # Se o Caps Lock estiver desligado, o script 'dorme' 
                # e não tira print da tela nem envia comandos
                time.sleep(0.3)
                continue

            # Captura o pixel da barra de HP
            img = sct.grab(monitor)
            px = img.pixel(0, 0)
            
            # px[1] é o canal VERDE
            verde_atual = px[1]

            if verde_atual < LIMITE_VERDE:
                try:
                    # Envia o comando 'P' (definido no seu code.py para F1)
                    placa.write(b'P')
                    placa.flush()
                    
                    # Delay humano para não floodar poção rápido demais
                    time.sleep(random.uniform(0.08, 0.14))
                except Exception as e:
                    print(f"Erro ao enviar para placa: {e}")
                    break
            else:
                # Se o HP estiver cheio, espera um tempo mínimo para a próxima checagem
                time.sleep(0.01)

    print(">>> SCRIPT DE HP FINALIZADO.")