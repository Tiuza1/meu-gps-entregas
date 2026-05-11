import pyautogui
import time
import ctypes

def botao_scroll_pressionado():
    # Verifica se o botão do meio do mouse (Scroll/Rodinha) está sendo pressionado (0x04)
    # GetAsyncKeyState retorna um valor com o bit mais significativo setado (0x8000) se estiver apertado
    return ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000

def executar(placa, stop_event):
    print(">>> SCRIPT DE SPAM DE SKILL INICIADO")
    print(">>> ATIVAÇÃO: [SEGURE O SCROLL DO MOUSE] | PAUSA: [SOLTE O SCROLL]")

    while not stop_event.is_set():
        if not botao_scroll_pressionado():
            time.sleep(0.05)
            continue

        try:
            placa.write(b"Q\n")
            placa.flush()
            
            # Delay de 350ms conforme solicitado
            time.sleep(0.35)

        except Exception as e:
            print(f"Erro no loop de Spam: {e}")
            time.sleep(0.5)

    print(">>> SCRIPT DE SPAM FINALIZADO.")