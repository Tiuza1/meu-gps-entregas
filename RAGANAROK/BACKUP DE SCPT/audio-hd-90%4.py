import pyautogui
import time
import random
import ctypes  
from threading import Lock

# --- CONFIGURAÇÕES ---
# Coloquei a mesma coordenada 1490 do outro script. Se for 1532 mesmo, basta alterar!
X_HP, Y_HP = 1490, 64  
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
    
    while not stop_event.is_set():
        # --- VERIFICAÇÃO DE SEGURANÇA ---
        if not macro_autorizado():
            # Se o Caps Lock estiver desligado, o script 'dorme' 
            time.sleep(0.3)
            continue

        try:
            # Captura o pixel exato da barra de HP usando PyAutoGUI (seguro e já testado)
            r, g, b = pyautogui.pixel(X_HP, Y_HP)
            
            # Checa o nível da cor VERDE
            if g < LIMITE_VERDE:
                print(f">>> [AUTOPOT] HP Baixo (Verde: {g}) - Usando Poção!")
                # Envia o comando 'P' com a quebra de linha essencial
                placa.write(b"P\n")
                placa.flush()
                
                # Delay humano para não floodar poção rápido demais
                time.sleep(random.uniform(0.08, 0.14))
            else:
                # Se o HP estiver cheio, espera um tempo mínimo
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Erro no loop do Autopot: {e}")
            time.sleep(0.5)

    print(">>> SCRIPT DE HP FINALIZADO.")