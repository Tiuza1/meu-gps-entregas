import pyautogui
import time
import random
import ctypes
from threading import Lock

# --- CONFIGURAÇÕES INICIAIS ---
def macro_autorizado():
    """ Verifica se a luz do Num Lock (0x90) está ligada """
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def configurar_posicao(stop_event):
    msg = (
        "Vamos configurar o AUTOPOT.\n\n"
        "1. Clique em OK para fechar esta janela.\n"
        "2. Mova a seta do mouse até a BARRA DE VIDA do jogo (exatamente onde você quer usar poção).\n"
        "3. Aperte a tecla ESPAÇO no teclado para salvar."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "Configuração de Autopot", 0x40 | 0x0)

    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            try:
                r, g, b = pyautogui.pixel(x, y)
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\nCor atual RGB: ({r}, {g}, {b})\n\nO Autopot já está funcionando!"
            except:
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\n\nO Autopot já está funcionando!"
            ctypes.windll.user32.MessageBoxW(0, conf_msg, "Sucesso", 0x40 | 0x0)
            time.sleep(1.0)
            return x, y
        time.sleep(0.05)

    return None, None

def executar(placa, stop_event):
    X_HP, Y_HP = configurar_posicao(stop_event)

    if X_HP is None or Y_HP is None:
        return

    print("\n>>> SCRIPT DE HP (ALTA PERFORMANCE) INICIADO COM SUCESSO")
    print(">>> ATIVAÇÃO: [NUM LOCK ON] | PAUSA: [NUM LOCK OFF]")

    while not stop_event.is_set():
        if not macro_autorizado():
            time.sleep(0.1)
            continue

        try:
            r, g, b = pyautogui.pixel(X_HP, Y_HP)

            if r > 180 or b > 200:
                print(f">>> [AUTOPOT] HP Vazio detectado! RGB:({r}, {g}, {b}) - Usando Poção!")
                placa.write(b"P\n")
                placa.flush()
                time.sleep(random.uniform(0.03, 0.06))
            else:
                time.sleep(0.005)

        except Exception as e:
            print(f"Erro no loop do Autopot: {e}")
            time.sleep(0.1)

    print(">>> SCRIPT DE HP FINALIZADO.")