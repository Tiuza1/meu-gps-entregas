import time
import ctypes

# Comando Q na placa: 4x (F3 + click) = ~80ms de execucao
# Ciclo alvo: 133ms total
# PC sleep: 133ms  (Arduino roda 80ms + 53ms idle antes do proximo envio)

SPAM_INTERVAL = 0.100  # 133ms entre envios

def macro_ataque_ativo():
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> SCRIPT WS - SPAM DE SKILL INICIADO")
    print(f">>> INTERVALO: {int(SPAM_INTERVAL*1000)}ms por ciclo (placa executa ~80ms + {int((SPAM_INTERVAL-0.080)*1000)}ms idle)")
    print(">>> ATIVACAO: [CAPS LOCK LIGADO] | PAUSA: [CAPS LOCK DESLIGADO]")

    while not stop_event.is_set():
        if not macro_ataque_ativo():
            time.sleep(0.05)
            continue

        try:
            placa.write(b"Q\n")
            placa.flush()
            time.sleep(SPAM_INTERVAL)

        except Exception as e:
            print(f"Erro no loop WS: {e}")
            time.sleep(0.5)

    print(">>> SCRIPT WS FINALIZADO.")
