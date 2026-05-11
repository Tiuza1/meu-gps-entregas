import pyautogui
import time
import random
import ctypes  
from threading import Lock

# --- CONFIGURAÇÕES INICIAIS ---
LIMITE_VERDE = 150 

def macro_autorizado():
    """ Verifica se a luz do Caps Lock (0x14) está ligada """
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def configurar_posicao():
    print("\n=======================================================")
    print(">>> [CONFIGURAÇÃO DO AUTOPOT] - Posicione o seu mouse <<<")
    print("=======================================================")
    print("1. Leve a seta do mouse ATÉ A BARRA DE HP, exatamente no local")
    print("   onde a cor verde some quando você precisa usar a poção.")
    print("2. Pressione a tecla 'ESPAÇO' para confirmar a posição.")
    print("=======================================================\n")

    # Aguarda a tecla Espaço (0x20) ser pressionada
    while True:
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            # Captura também a cor atual para dar feedback ao usuário
            try:
                r, g, b = pyautogui.pixel(x, y)
                print(f">>> [POSIÇÃO CAPTURADA] X: {x}, Y: {y} | Cor Verde atual: {g}")
            except Exception as e:
                print(f">>> [POSIÇÃO CAPTURADA] X: {x}, Y: {y} (Aviso: Não foi possível ler a cor no momento)")

            time.sleep(1.0) # Delay para não registrar múltiplos espaços
            return x, y
        time.sleep(0.05)

def executar(placa, stop_event):
    """
    Esta função é chamada pelo Gerenciador de Macros.
    """
    # Primeiro passo: Pede para o usuário configurar a posição
    X_HP, Y_HP = configurar_posicao()

    print("\n>>> SCRIPT DE HP INICIADO COM SUCESSO")
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
