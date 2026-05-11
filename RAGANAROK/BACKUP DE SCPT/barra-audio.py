import pyautogui # Só para pegar a posição do mouse agora
import time

print("Posicione o mouse sobre a barra de HP (no ponto de 25%) em 5 segundos...")
time.sleep(5)

try:
    while True:
        x, y = pyautogui.position()
        # Pega a cor do pixel onde o mouse está
        cor = pyautogui.pixel(x, y)
        print(f"Posição: X={x} Y={y} | Cor RGB: {cor}", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nLocalização capturada!")