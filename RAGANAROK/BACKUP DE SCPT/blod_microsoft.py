import serial
import serial.tools.list_ports
import time
import random
import pyautogui

# --- FUNÇÃO PARA ACHAR A PLACA ---
def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

PORTA_COM = encontrar_placa()

try:
    # Abre a conexão com a placa
    placa = serial.Serial(PORTA_COM, 9600, timeout=0)
    print(f"--- CONECTADO NA {PORTA_COM} ---")
    print("MODO DOSE DUPLA (2X) ATIVADO!")
except:
    print("ERRO: Placa não encontrada. Verifique o USB ou feche o Thonny.")
    time.sleep(5)
    exit()

def loop_farm_2x():
    largura, altura = pyautogui.size()
    cx, cy = largura // 2, altura // 2

    print("Iniciando em 3 segundos... Foque na janela do Rag!")
    time.sleep(3)

    while True:
        # 1. TELEPORTE 2X (A placa já faz o 2x interno)
        placa.write(b'T')
        # Espera o mapa carregar (0.7s a 0.9s)
        time.sleep(random.uniform(0.7, 0.9))

        # 2. MOVIMENTAÇÃO 2X
        # Sorteia um ponto ao redor do char
        px = cx + random.randint(-120, 120)
        py = cy + random.randint(-120, 120)
        pyautogui.moveTo(px, py, duration=0.03)
        placa.write(b'L') 
        time.sleep(random.uniform(0.3, 0.4))

        # 3. ATAQUE 2X (A placa faz 2x F3 + Click)
        # Move o mouse pro pé do boneco para agrupar o mob
        pyautogui.moveTo(cx + random.randint(-10, 10), cy + random.randint(-10, 10), duration=0.03)
        placa.write(b'A')
        
        # 4. TEMPO DA MAGIA
        # Como é 2x, os monstros morrem muito rápido
        time.sleep(random.uniform(2.5, 3.2))

if __name__ == "__main__":
    try:
        loop_farm_2x()
    except KeyboardInterrupt:
        print("\nMacro parado pelo usuário.")
        if 'placa' in locals() and placa.is_open:
            placa.close()