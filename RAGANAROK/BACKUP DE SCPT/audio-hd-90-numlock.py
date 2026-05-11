import pyautogui
import time
import random
import ctypes  
from threading import Lock

# --- CONFIGURAÇÕES INICIAIS ---
LIMITE_VERDE = 150 

def macro_autorizado():
    """ Verifica se a luz do Num Lock (0x90) está ligada """
    return ctypes.windll.user32.GetKeyState(0x90) & 1

def configurar_posicao(stop_event):
    # Exibe uma caixa de mensagem nativa do Windows (não trava o Gerenciador e é visível para o usuário)
    # Primeiro avisa o que deve ser feito
    msg = (
        "Vamos configurar o AUTOPOT.\n\n"
        "1. Clique em OK para fechar esta janela.\n"
        "2. Mova a seta do mouse até a BARRA DE VIDA do jogo (exatamente onde você quer usar poção).\n"
        "3. Aperte a tecla ESPAÇO no teclado para salvar."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "Configuração de Autopot", 0x40 | 0x0)

    # Fica aguardando o ESPAÇO ser pressionado
    while not stop_event.is_set():
        if ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000:
            x, y = pyautogui.position()

            # Mostra outro popup confirmando que deu certo
            try:
                r, g, b = pyautogui.pixel(x, y)
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\nCor verde atual: {g}\n\nO Autopot já está funcionando!"
            except:
                conf_msg = f"Posição do HP capturada!\nX: {x} | Y: {y}\n\nO Autopot já está funcionando!"

            ctypes.windll.user32.MessageBoxW(0, conf_msg, "Sucesso", 0x40 | 0x0)
            time.sleep(1.0) # Delay de segurança
            return x, y

        time.sleep(0.05)

    return None, None # Retorna vazio caso o usuário desligue o script antes de apertar espaço

def executar(placa, stop_event):
    """
    Esta função é chamada pelo Gerenciador de Macros.
    """
    # Primeiro passo: Pede para o usuário configurar a posição
    X_HP, Y_HP = configurar_posicao(stop_event)

    # Se retornou vazio (porque o usuário apertou OFF no gerenciador antes de confirmar), encerra a função.
    if X_HP is None or Y_HP is None:
        return

    print("\n>>> SCRIPT DE HP INICIADO COM SUCESSO")
    print(">>> ATIVAÇÃO: [NUM LOCK ON] | PAUSA: [NUM LOCK OFF]")

    while not stop_event.is_set():
        # --- VERIFICAÇÃO DE SEGURANÇA ---
        if not macro_autorizado():
            time.sleep(0.3)
            continue

        try:
            r, g, b = pyautogui.pixel(X_HP, Y_HP)

            # Checa o nível da cor VERDE
            if g < LIMITE_VERDE:
                print(f">>> [AUTOPOT] HP Baixo (Verde: {g}) - Usando Poção!")
                # Envia o comando 'P' com a quebra de linha essencial
                placa.write(b"P\n")
                placa.flush()

                # Delay humano
                time.sleep(random.uniform(0.08, 0.14))
            else:
                time.sleep(0.01)

        except Exception as e:
            print(f"Erro no loop do Autopot: {e}")
            time.sleep(0.5)

    print(">>> SCRIPT DE HP FINALIZADO.")
