import pyautogui
import time
import random
import ctypes
from threading import Lock
import json
import os
import mss
import numpy as np

# NOME DO ARQUIVO ONDE A CONFIGURAÇÃO SERÁ SALVA
ARQUIVO_CFG = "config_autopot_numlock.json"

def carregar_ou_calibrar(nome_arquivo, funcao_calibrar, stop_event):
    """
    Verifica se o .json existe. Pergunta ao usuário se deseja usar.
    Retorna um dicionário com as configurações.
    """
    if os.path.exists(nome_arquivo):
        resposta = ctypes.windll.user32.MessageBoxW(
            0,
            f"Configuração encontrada!\n\nDeseja carregar os dados salvos e pular a calibração?",
            "Aproveitar Configuração?",
            0x04 | 0x20 | 0x40000
        )
        if resposta == 6: # SIM
            try:
                with open(nome_arquivo, 'r') as f:
                    return json.load(f)
            except Exception as e:
                ctypes.windll.user32.MessageBoxW(0, f"Erro ao ler arquivo. Recalibrando...", "Erro", 0x10 | 0x40000)

    dados = funcao_calibrar(stop_event)

    if dados is not None:
        with open(nome_arquivo, 'w') as f:
            json.dump(dados, f, indent=4)

    return dados

def macro_autorizado():
    """ Verifica se a luz do Num Lock (0x90) está ligada """
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def configurar_posicao(stop_event):
    msg = (
        "Vamos configurar o AUTOPOT.\n\n"
        "1. Clique em OK para fechar esta janela.\n"
        "2. Mova a seta do mouse até a BARRA DE VIDA do jogo.\n"
        "3. Aperte a tecla ESPAÇO no teclado para salvar."
    )

    ctypes.windll.user32.MessageBoxW(0, msg, "Configuração de Autopot", 0x40 | 0x0)

    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()
            try:
                r, g, b = pyautogui.pixel(x, y)
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\nCor atual RGB: ({r}, {g}, {b})\n\nO Autopot já está pronto para o Num Lock!"
            except:
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\n\nO Autopot já está pronto para o Num Lock!"

            ctypes.windll.user32.MessageBoxW(0, conf_msg, "Sucesso", 0x40 | 0x0)
            time.sleep(1.0)
            
            # --- CORREÇÃO: RETORNAR COMO DICIONÁRIO ---
            return {"x": x, "y": y}
            
        time.sleep(0.05)

    return None

def executar(placa, stop_event):
    # --- CORREÇÃO: USAR A FUNÇÃO QUE LÊ E SALVA O JSON ---
    cfg = carregar_ou_calibrar(ARQUIVO_CFG, configurar_posicao, stop_event)
    
    if cfg is None:
        return
        
    X_HP = cfg["x"]
    Y_HP = cfg["y"]

    print("\n>>> SCRIPT DE HP (ALTA PERFORMANCE) INICIADO COM SUCESSO")
    print(">>> ATIVAÇÃO: [NUM LOCK LIGADO] | PAUSA: [NUM LOCK DESLIGADO]")

    estado_anterior = macro_autorizado()
    if estado_anterior:
        print(">>> [STATUS] Autopot LIGADO")
    else:
        print(">>> [STATUS] Autopot PAUSADO")

    # Região mínima de 1x1 pixel ao redor do ponto calibrado (mss é muito mais leve que pyautogui.pixel)
    regiao_hp = {'left': X_HP, 'top': Y_HP, 'width': 1, 'height': 1}

    with mss.mss() as sct:
        while not stop_event.is_set():
            estado_atual = macro_autorizado()

            if estado_atual != estado_anterior:
                if estado_atual:
                    print(">>> [STATUS] Autopot LIGADO")
                else:
                    print(">>> [STATUS] Autopot PAUSADO")
                estado_anterior = estado_atual

            if not estado_atual:
                time.sleep(0.1)
                continue

            try:
                pixel = np.array(sct.grab(regiao_hp))
                b, g, r = int(pixel[0, 0, 0]), int(pixel[0, 0, 1]), int(pixel[0, 0, 2])

                if r > 180 or b > 200:
                    print(f">>> [AUTOPOT] HP Vazio detectado! RGB:({r}, {g}, {b}) - Usando Poção!")

                    placa.write(b"P\n")
                    placa.flush()

                    time.sleep(random.uniform(0.03, 0.06))
                else:
                    time.sleep(0.05)

            except Exception as e:
                print(f"Erro no loop do Autopot: {e}")
                time.sleep(0.1)

    print(">>> SCRIPT DE HP FINALIZADO.")