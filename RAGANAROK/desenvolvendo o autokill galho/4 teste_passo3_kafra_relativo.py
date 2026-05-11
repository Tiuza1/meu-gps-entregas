import time
import pyautogui
import ctypes
import winsound

def is_active():
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def executar(placa, stop_event):
    winsound.Beep(1000, 200) 

    item_x, item_y = 89, 201 
    r_vazio, g_vazio, b_vazio = 206, 214, 230 
    ultimo_armazem = time.time()

    while not stop_event.is_set():
        if not is_active():
            time.sleep(0.1)
            continue

        try:
            tempo_atual = time.time()

            if tempo_atual - ultimo_armazem > 30.0:
                print("\n>>> [KAFRA] Hora de guardar os Galhos Secos!")
                winsound.Beep(600, 150)
                winsound.Beep(600, 150)

                placa.write(b"S\n")
                placa.flush()
                time.sleep(0.8) 

                print(">>> [KAFRA] Movendo para o inventário...")

                # --- O SEGREDO DO MOUSE RELATIVO ---
                # Como a sua placa agora usa o modo "Turbo" (letra V) que viaja de forma relativa
                # Nós lemos onde o seu mouse está parado agora, calculamos a distância e mandamos o pulo!
                atual_x, atual_y = pyautogui.position()
                delta_x = item_x - atual_x
                delta_y = item_y - atual_y

                placa.write(f"V{delta_x},{delta_y}\n".encode())
                placa.flush()
                time.sleep(0.5) # Dá meio segundo para o mouse voar até lá

                for _ in range(15):
                    if not is_active() or stop_event.is_set(): break

                    try: 
                        r, g, b = pyautogui.pixel(item_x, item_y)
                        if abs(r - r_vazio) < 10 and abs(g - g_vazio) < 10 and abs(b - b_vazio) < 10:
                            print(">>> [KAFRA] Inventário Limpo! Todos os galhos foram guardados.")
                            break
                    except Exception as e:
                        break

                    placa.write(b"R\n")
                    placa.flush()
                    time.sleep(0.6) 

                print(">>> [KAFRA] Retomando caça com Teleporte...")
                placa.write(b"T\n")
                placa.flush()
                time.sleep(1.0)

                print(">>> [KAFRA] Finalizado com sucesso!")
                ultimo_armazem = time.time()

            time.sleep(0.1) 

        except Exception as e:
            time.sleep(1)
