import os, subprocess, re, time, csv, sys
import xml.etree.cElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, scrolledtext
import threading

# --- IDs ÚNICOS DO APP ---
ID_CODIGO = 'com.jtexpress.braout:id/tv_bill_code'
ID_NOME = 'com.jtexpress.braout:id/tv_wait_name'
ID_ENDERECO = 'com.jtexpress.braout:id/tv_wait_adress'
ID_TEL_BTN = 'com.jtexpress.braout:id/iv_wait_phone'

ultimo_nome_salvo = ""
ultimo_numero_salvo = ""

def get_coords(bounds_str):
    """ Retorna x1, y1, x2, y2 """
    if not bounds_str: return 0, 0, 0, 0
    res = re.findall(r'\d+', bounds_str)
    return int(res[0]), int(res[1]), int(res[2]), int(res[3])

def extrair_local_inteligente(texto):
    if not texto: return "Sem Quadra", ""
    
    # 1. Tenta extrair o CEP primeiro (Ex: 72853-280 ou 72853280)
    cep_encontrado = ""
    match_cep = re.search(r'(7285\d)[-.\s]?(\d{3})', texto)
    if match_cep:
        cep_encontrado = f"{match_cep.group(1)}-{match_cep.group(2)}"
        
    # 2. Tenta extrair a Quadra normalmente
    padrao_quadra = r'((?:QUADRA|QD|QR|Q|CONJUNTO|CJ|CONJ)\.?\s*\d+)'
    match_quadra = re.search(padrao_quadra, texto, re.IGNORECASE)
    
    if match_quadra:
        res = match_quadra.group(1).upper().strip()
        quadra_final = re.sub(r'(QUADRA|QD|QR)\s+\1', r'\1', res)
        return quadra_final, cep_encontrado
    
    # 3. SE NÃO TEM QUADRA, MAS TEM CEP, DEDUZ A QUADRA!
    if match_cep:
        # Pega a segunda parte do CEP (os 3 últimos números)
        sufixo_cep = match_cep.group(2)
        # Tira os zeros da frente (Ex: "080" vira "80")
        numero_deduzido = str(int(sufixo_cep))
        quadra_deduzida = f"Q {numero_deduzido}"
        return quadra_deduzida, cep_encontrado
        
    # 4. Se não tem quadra e nem CEP, pega as 3 primeiras palavras do endereço
    palavras = [p for p in texto.split() if len(p) > 1 or p.isalnum()]
    quadra_fallback = " ".join(palavras[:3]) if palavras else "LOCAL"
    return quadra_fallback, cep_encontrado

def extrair_do_discador():
    time.sleep(0.8)
    if os.path.exists("dialer.xml"): os.remove("dialer.xml")
    subprocess.run("adb shell uiautomator dump /sdcard/dialer.xml", shell=True, capture_output=True)
    subprocess.run("adb pull /sdcard/dialer.xml .", shell=True, capture_output=True)
    try:
        tree = ET.parse("dialer.xml")
        for n in tree.getroot().iter('node'):
            text = n.get('text')
            if text:
                limpo = re.sub(r'\D', '', text)
                if len(limpo) >= 8: return limpo
    except: pass
    return ""

def voltar_ao_app():
    subprocess.run("adb shell input keyevent 4", shell=True)
    time.sleep(0.33)
    subprocess.run("adb shell input keyevent 4", shell=True)
    time.sleep(0.67)

def capturar_com_tentativas(x, y, nome):
    global ultimo_numero_salvo, ultimo_nome_salvo
    for t in range(3):
        subprocess.run(f"adb shell input tap {x} {y}", shell=True)
        num = extrair_do_discador()
        if num == "" or (num == ultimo_numero_salvo and nome != ultimo_nome_salvo):
            voltar_ao_app()
            continue
        ultimo_numero_salvo, ultimo_nome_salvo = num, nome
        voltar_ao_app()
        return num
    return "ERRO"

def rodar_extrator_v6(lista_negra):
    data = datetime.now().strftime("%d-%m-%Y")
    arquivo_csv = f"clientes_do_dia ({data}).csv"

    processados = set()
    if os.path.exists(arquivo_csv):
        with open(arquivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader: processados.add(row[1])

    print(f"[*] Escaneamento iniciado em {data}.")
    print("[*] Aguardando pacotes na tela...\n" + "-"*40)

    while True:
        if os.path.exists("v.xml"): os.remove("v.xml")
        subprocess.run("adb shell uiautomator dump /sdcard/v.xml", shell=True, capture_output=True)
        subprocess.run("adb pull /sdcard/v.xml .", shell=True, capture_output=True)

        try:
            tree = ET.parse("v.xml")
            root = tree.getroot()
            all_nodes = list(root.iter('node'))

            codigos_nodes = sorted(
                [n for n in all_nodes if n.get('resource-id') == ID_CODIGO],
                key=lambda x: get_coords(x.get('bounds'))[1]
            )

            nomes_nodes = [n for n in all_nodes if n.get('resource-id') == ID_NOME]
            enderecos_nodes = [n for n in all_nodes if n.get('resource-id') == ID_ENDERECO]
            botoes_nodes = [n for n in all_nodes if n.get('resource-id') == ID_TEL_BTN]

            if len(codigos_nodes) > 0:
                print(f"\n--- Lendo {len(codigos_nodes)} pacotes na tela ---")

            for i in range(len(codigos_nodes)):
                node_cod = codigos_nodes[i]
                p_id = node_cod.get('text')

                if p_id in processados or p_id in lista_negra:
                    continue

                y_inicio = get_coords(node_cod.get('bounds'))[1]
                y_fim = get_coords(codigos_nodes[i+1].get('bounds'))[1] if (i+1) < len(codigos_nodes) else 2500

                meu_nome = next((n for n in nomes_nodes if y_inicio <= get_coords(n.get('bounds'))[1] <= y_fim), None)
                meu_end = next((e for e in enderecos_nodes if y_inicio <= get_coords(e.get('bounds'))[1] <= y_fim), None)
                meu_btn = next((b for b in botoes_nodes if y_inicio <= get_coords(b.get('bounds'))[1] <= y_fim), None)

                if meu_nome is not None and meu_btn is not None:
                    nome_cli = meu_nome.get('text')
                    txt_end = meu_end.get('text') if meu_end is not None else ""
                    # Agora a função retorna duas coisas: a quadra e o cep!
                    quadra, cep = extrair_local_inteligente(txt_end)

                    x1, y1, x2, y2 = get_coords(meu_btn.get('bounds'))
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                    print(f"[*] Extraindo: {nome_cli} | {quadra} | {cep}")
                    tel = capturar_com_tentativas(cx, cy, nome_cli)

                    if tel != "ERRO":
                        with open(arquivo_csv, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            # Se o arquivo estiver vazio, cria o cabeçalho com o CEP
                            if os.path.getsize(arquivo_csv) == 0:
                                writer.writerow(["Nome", "Pacote", "Telefone", "Local", "CEP"])
                            # Escreve a linha inteira incluindo o CEP
                            writer.writerow([nome_cli, p_id, tel, quadra, cep])
                        processados.add(p_id)

            # Scroll curto para manter a precisão
            subprocess.run("adb shell input swipe 500 1200 500 800 900", shell=True)
            time.sleep(1.0)

        except KeyboardInterrupt: 
            print("\n[!] Escaneamento parado pelo usuário.")
            break
        except Exception as e: 
            print(f"Erro: {e}")
            time.sleep(0.67)

# --- CLASSE DO PAINEL DE LOG (GUI) ---
class PainelLog(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Extrator Pro - Painel de Status")
        self.geometry("800x500")
        self.configure(bg="black")
        
        # Área de texto com rolagem parecida com CMD
        self.text_area = scrolledtext.ScrolledText(
            self, bg="black", fg="#00FF00", font=("Consolas", 11), wrap=tk.WORD
        )
        self.text_area.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Redireciona o print() normal do Python para jogar os textos dentro desta janela
        sys.stdout = self
        sys.stderr = self

    def write(self, string):
        self.text_area.insert(tk.END, string)
        self.text_area.see(tk.END) # Rola automaticamente para baixo
        
    def flush(self):
        pass

def iniciar_app():
    painel = PainelLog()
    
    # Caixa de diálogo para a lista negra (evita travar a janela preta)
    lista_str = simpledialog.askstring(
        "Lista Negra", 
        "IDs para PULAR separados por vírgula:\n(Deixe em branco e dê OK para continuar)", 
        parent=painel
    )
    
    lista_negra = [i.strip() for i in lista_str.split(",")] if lista_str else []
    
    # Roda o extrator em uma Thread separada (para a janela do painel não travar)
    thread_extrator = threading.Thread(target=rodar_extrator_v6, args=(lista_negra,))
    thread_extrator.daemon = True # Mata a thread se você fechar a janela no [X]
    thread_extrator.start()
    
    # Mantém a janela aberta
    painel.mainloop()

if __name__ == "__main__":
    iniciar_app()