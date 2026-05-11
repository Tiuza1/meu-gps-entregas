import time
import pyautogui
import ctypes
import winsound

def is_active():
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def executar(placa, stop_event):
    # Avisos sonoros para sabermos que iniciou (já que não temos console no Gerenciador)
    winsound.Beep(1000, 200) # Bipe curto
    winsound.Beep(1500, 200) # Bipe agudo

    hp_x, hp_y = 1490, 64
    ultima_checagem_hp = time.time()

    while not stop_event.is_set():
        if not is_active():
            time.sleep(0.1)
            continue

        try:
            tempo_atual = time.time()

            if tempo_atual - ultima_checagem_hp > 2.0:
                ultima_checagem_hp = tempo_atual

                r_hp, g_hp, b_hp = pyautogui.pixel(hp_x, hp_y)

                if g_hp < 100: 
                    # Toca um som de SIRENE/ALERTA (grave) para indicar MORTE
                    for _ in range(3):
                        winsound.Beep(500, 300)

                    time.sleep(2.0) 

                    # Envia Alt+6 (Resgate)
                    placa.write(b"X\n")
                    placa.flush()
                    time.sleep(1.0)

                    # Loop de congelamento aguardando a vida voltar e o Num Lock
                    while True:
                        if stop_event.is_set(): 
                            break 

                        time.sleep(1)
                        try:
                            r_novo, g_novo, b_novo = pyautogui.pixel(hp_x, hp_y)
                        except:
                            continue

                        if g_novo >= 100 and is_active():
                            # Som de SUCESSO (Retomando a caça)
                            winsound.Beep(2000, 150)
                            winsound.Beep(2000, 150)
                            ultima_checagem_hp = time.time() 
                            break

            # Caça rodando invisível de fundo (Sem prints no painel)
            time.sleep(0.1) 

        except Exception as e:
            time.sleep(1)
