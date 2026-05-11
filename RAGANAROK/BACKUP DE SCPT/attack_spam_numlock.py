import pyautogui
import time
import ctypes  

def macro_ataque_ativo():
    # Verifica a luz do NUM LOCK (0x90)
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def executar(placa, stop_event):
    print(">>> SCRIPT DE SPAM DE SKILL INICIADO")
    print(">>> ATIVAÇÃO: [NUM LOCK LIGADO] | PAUSA: [NUM LOCK DESLIGADO]")

    while not stop_event.is_set():
        if not macro_ataque_ativo():
            time.sleep(0.05)
            continue

        try:
            placa.write(b"Q\n")
            placa.flush()
            time.sleep(0.12)

        except Exception as e:
            print(f"Erro no loop de Spam: {e}")
            time.sleep(0.5)

    print(">>> SCRIPT DE SPAM FINALIZADO.")
