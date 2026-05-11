import mss
import numpy as np
import cv2
import serial
import serial.tools.list_ports
import time
import random
import pyautogui

# --- CONFIGURAÇÕES DE PERFORMANCE V12 ---
X_HP, Y_HP = 151, 82
LIMITE_DIFERENCA = 35 
IGNORAR_RAIO = 120
AREA_MINIMA_MONSTRO = 1300 # Aumentado para evitar "manchas" pequenas
LIMITE_BRILHO_PRETO = 95   # Rigor total contra sombras
TIMEOUT_SCAN = 1.0

def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

placa_porta = encontrar_placa() or 'COM3'
placa = serial.Serial(placa_porta, 9600, timeout=0)

def mouse_humano(x, y, duration=None):
    if duration is None:
        duration = random.uniform(0.12, 0.28)
    pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)

def aguardar_carregamento(sct, busca):
    """Espera a tela deixar de ser preta após o teleporte"""
    print("Aguardando mapa...")
    t_limite = time.time()
    while time.time() - t_limite < 3.0:
        img = np.array(sct.grab(busca))
        frame_gray = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGRA2BGR), cv2.COLOR_BGR2GRAY)
        brilho_medio = np.mean(frame_gray)
        
        # Se o brilho subir de 45, o mapa carregou
        if brilho_medio > 45:
            time.sleep(0.1) # Pausa milimétrica para estabilizar frames
            return frame_gray
        time.sleep(0.05)
    return None

def encontrar_alvo(sct, busca, gray_antiga):
    img = np.array(sct.grab(busca))
    frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    # Aplica um leve desfoque para ignorar ruídos de textura/parede
    frame_bgr = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
    gray_nova = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(gray_antiga, gray_nova)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    
    # Filtro de Brilho (Mata o preto)
    _, mask_vazio = cv2.threshold(gray_nova, LIMITE_BRILHO_PRETO, 255, cv2.THRESH_BINARY)
    thresh = cv2.bitwise_and(thresh, mask_vazio) 
    
    thresh = cv2.dilate(thresh, None, iterations=2)
    h, w = thresh.shape
    cv2.circle(thresh, (w//2, h//2), IGNORAR_RAIO, 0, -1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > AREA_MINIMA_MONSTRO:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                tx = int(M["m10"] / M["m00"]) + busca["left"]
                ty = int(M["m01"] / M["m00"]) + busca["top"]
                return (tx, ty), gray_nova
    return None, gray_nova

def loop_farm():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        cx, cy = monitor["width"] // 2, monitor["height"] // 2
        busca = {"top": cy - 250, "left": cx - 350, "width": 700, "height": 500}
        
        # Estado inicial
        gray_antiga = np.zeros((500, 700), dtype=np.uint8)

        while True:
            # 1. TELEPORTE E ESPERA INTELIGENTE
            print("\n--- TELEPORTANDO ---")
            placa.write(b'T')
            # Reseta mouse para o centro enquanto pula (suave)
            pyautogui.moveTo(cx + random.randint(-30, 30), cy + random.randint(-30, 30), duration=0.2)
            
            # AGUARDA O MAPA APARECER (Sem tempo fixo!)
            mapa_carregado = aguardar_carregamento(sct, busca)
            if mapa_carregado is not None:
                gray_antiga = mapa_carregado
            
            # 2. RODADA DE ATAQUES (1 a 3)
            objetivo = random.choice([1, 2, 2, 3])
            feitos = 0
            
            while feitos < objetivo:
                alvo_confirmado = None
                t_scan = time.time()
                
                while time.time() - t_scan < TIMEOUT_SCAN:
                    alvo, gray_antiga = encontrar_alvo(sct, busca, gray_antiga)
                    if alvo and alvo != "PRETO":
                        alvo_confirmado = alvo
                        break
                    time.sleep(0.03)

                if alvo_confirmado:
                    tx, ty = alvo_confirmado
                    print(f"Alvo {feitos+1} detectado. Atacando...")
                    
                    # ATAQUE
                    mouse_humano(tx, ty, duration=random.uniform(0.1, 0.2))
                    placa.write(b'A') 
                    
                    # ENTRADA NA SKILL (Delay Humano)
                    time.sleep(random.uniform(0.4, 0.6))
                    # Clica num ponto aleatório no pé
                    pyautogui.click(cx + random.randint(-25, 25), cy + random.randint(-25, 25))
                    
                    feitos += 1
                    # Espera Magnus (Reduzi um pouco para ser mais frenético)
                    time.sleep(random.uniform(3.4, 3.8))
                    
                    # Limpa visão para o próximo bicho
                    img_temp = np.array(sct.grab(busca))
                    gray_antiga = cv2.cvtColor(cv2.cvtColor(img_temp, cv2.COLOR_BGRA2BGR), cv2.COLOR_BGR2GRAY)
                else:
                    break

if __name__ == "__main__":
    print(f"Sacerdote V12 (Fast Load) ON!")
    loop_farm()