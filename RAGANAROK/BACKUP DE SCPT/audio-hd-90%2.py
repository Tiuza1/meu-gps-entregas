import mss
import numpy as np
import time
import random
from threading import Lock

# --- CONFIGURAÇÕES ---
X_HP, Y_HP = 1532, 64
LIMITE_VERDE = 150 

def executar(placa, stop_event):
    """
    Esta função é chamada pelo Gerenciador de Macros.
    'placa' é a conexão serial já aberta pelo gerenciador.
    'stop_event' serve para parar o script quando você clicar em OFF.
    """
    print("Script de HP Iniciado")
    
    with mss.mss() as sct:
        monitor = {"top": Y_HP, "left": X_HP, "width": 1, "height": 1}
        
        while not stop_event.is_set():
            img = sct.grab(monitor)
            px = img.pixel(0, 0)
            
            # px[1] é o canal VERDE
            verde_atual = px[1]

            if verde_atual < LIMITE_VERDE:
                try:
                    # Usamos a placa que o gerenciador nos passou
                    placa.write(b'P')
                    placa.flush()
                    # Delay humano
                    time.sleep(random.uniform(0.08, 0.14))
                except Exception as e:
                    print(f"Erro ao enviar para placa: {e}")
                    break
            else:
                time.sleep(0.01) # Pequena pausa para não fritar o processador