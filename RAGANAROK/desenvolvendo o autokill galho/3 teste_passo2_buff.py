import time
import ctypes
import winsound

def is_active():
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def executar(placa, stop_event):
    winsound.Beep(1000, 200) 

    # 60.0 segundos = 1 Minuto cravado
    # Tiramos os 60 iniciais para ele buffar na mesma hora que ligar o Num Lock
    ultimo_buff = time.time() - 60.0 

    while not stop_event.is_set():
        if not is_active():
            time.sleep(0.1)
            continue

        try:
            tempo_atual = time.time()

            # --- SISTEMA DE BUFF (A cada 60s) ---
            if tempo_atual - ultimo_buff > 60.0:
                print(">>> [BUFF] Parando tudo para castar o Buff...")

                # Som Rápido
                winsound.Beep(1200, 100)
                winsound.Beep(1800, 100)

                # Para tudo e manda a placa usar a habilidade
                placa.write(b"B\n")
                placa.flush()

                # Pausa curtíssima, apenas para o buff ativar e o boneco poder teleportar logo em seguida
                time.sleep(0.5)

                print(">>> [BUFF] Concluído! Retomando caça...")
                ultimo_buff = time.time()

            # Caça Invisível
            time.sleep(0.1) 

        except Exception as e:
            time.sleep(1)
