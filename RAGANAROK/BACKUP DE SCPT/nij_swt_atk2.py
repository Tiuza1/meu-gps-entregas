import time
import ctypes

def macro_ataque_ativo():
    # Verifica o estado da luz do CAPS LOCK (0x14)
    # Retorna 1 se estiver acesa, 0 se estiver apagada
    return ctypes.windll.user32.GetKeyState(0x14) & 1

def executar(placa, stop_event):
    print(">>> GATILHO COMBO MORTAL INICIADO")
    print(">>> ATIVAÇÃO: Aperte o CAPS LOCK (Liga ou Desliga)")
    
    # Salva o estado atual da luz logo que o script abre
    estado_anterior_luz = macro_ataque_ativo()

    while not stop_event.is_set():
        estado_atual_luz = macro_ataque_ativo()
        
        # Se a luz mudou de estado (ligou ou desligou)
        if estado_atual_luz != estado_anterior_luz:
            
            # Atualiza a memória
            estado_anterior_luz = estado_atual_luz
            
            try:
                # Manda o comando 'C' (Combo) para a placa
                placa.write(b"C\n")
                placa.flush()
                
                acao = "LIGOU" if estado_atual_luz == 1 else "DESLIGOU"
                print(f"[{time.strftime('%H:%M:%S')}] CAPS LOCK {acao} -> Combo Disparado!")
                
                # Trava o script por 0.3s (300ms) para não mandar o combo 2 vezes 
                # se você apertar o botão muito forte ou muito fraco (debounce mecânico)
                time.sleep(0.3)
                
            except Exception as e:
                print(f"Erro no loop do Combo: {e}")
                time.sleep(0.5)
                
        # Esse sleep define quão rápido o script percebe a luz
        # 0.005s = 200 vezes por segundo. Praticamente instantâneo!
        time.sleep(0.005) 

    print(">>> SCRIPT GATILHO FINALIZADO.")