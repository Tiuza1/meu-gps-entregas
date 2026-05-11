import os, subprocess, re, time, csv
import xml.etree.cElementTree as ET
from datetime import datetime

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
    if not texto: return "LOCAL"
    padrao = r'((?:QUADRA|QD|QR|Q|CONJUNTO|CJ|CONJ)\.?\s*\d+)'
    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        res = match.group(1).upper().strip()
        return re.sub(r'(QUADRA|QD|QR)\s+\1', r'\1', res)
    palavras = [p for p in texto.split() if len(p) > 1 or p.isalnum()]
    return " ".join(palavras[:3]) if palavras else "LOCAL"

def extrair_do_discador():
    time.sleep(1.2)
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
    time.sleep(0.5)
    subprocess.run("adb shell input keyevent 4", shell=True)
    time.sleep(1.0)

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

def rodar_extrator_v6():
    data = datetime.now().strftime("%d-%m-%Y")
    arquivo_csv = f"clientes_do_dia ({data}).csv"
    
    print("\nIDs para PULAR (vírgula) ou ENTER:")
    lista_negra = [i.strip() for i in input("> ").split(",") if i.strip()]
    
    processados = set()
    if os.path.exists(arquivo_csv):
        with open(arquivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader: processados.add(row[1])

    while True:
        if os.path.exists("v.xml"): os.remove("v.xml")
        subprocess.run("adb shell uiautomator dump /sdcard/v.xml", shell=True, capture_output=True)
        subprocess.run("adb pull /sdcard/v.xml .", shell=True, capture_output=True)
        
        try:
            tree = ET.parse("v.xml")
            root = tree.getroot()
            all_nodes = list(root.iter('node'))

            # Pega todos os códigos de barras e ordena de cima para baixo
            codigos_nodes = sorted(
                [n for n in all_nodes if n.get('resource-id') == ID_CODIGO],
                key=lambda x: get_coords(x.get('bounds'))[1]
            )

            # Pega todos os outros elementos da tela
            nomes_nodes = [n for n in all_nodes if n.get('resource-id') == ID_NOME]
            enderecos_nodes = [n for n in all_nodes if n.get('resource-id') == ID_ENDERECO]
            botoes_nodes = [n for n in all_nodes if n.get('resource-id') == ID_TEL_BTN]

            print(f"--- Lendo {len(codigos_nodes)} pacotes na tela ---")

            for i in range(len(codigos_nodes)):
                node_cod = codigos_nodes[i]
                p_id = node_cod.get('text')
                
                if p_id in processados or p_id in lista_negra:
                    continue

                # Define os limites do trilho (deste código até o próximo ou fim da tela)
                y_inicio = get_coords(node_cod.get('bounds'))[1]
                y_fim = get_coords(codigos_nodes[i+1].get('bounds'))[1] if (i+1) < len(codigos_nodes) else 2500

                # Busca o nome, endereço e botão que estão DENTRO deste trilho Y
                meu_nome = next((n for n in nomes_nodes if y_inicio <= get_coords(n.get('bounds'))[1] <= y_fim), None)
                meu_end = next((e for e in enderecos_nodes if y_inicio <= get_coords(e.get('bounds'))[1] <= y_fim), None)
                meu_btn = next((b for b in botoes_nodes if y_inicio <= get_coords(b.get('bounds'))[1] <= y_fim), None)

                if meu_nome is not None and meu_btn is not None:
                    nome_cli = meu_nome.get('text')
                    txt_end = meu_end.get('text') if meu_end is not None else ""
                    quadra = extrair_local_inteligente(txt_end)
                    
                    x1, y1, x2, y2 = get_coords(meu_btn.get('bounds'))
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                    print(f"[*] Extraindo: {nome_cli} | {quadra}")
                    tel = capturar_com_tentativas(cx, cy, nome_cli)
                    
                    if tel != "ERRO":
                        with open(arquivo_csv, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            if os.path.getsize(arquivo_csv) == 0:
                                writer.writerow(["Nome", "Pacote", "Telefone", "Local"])
                            writer.writerow([nome_cli, p_id, tel, quadra])
                        processados.add(p_id)

            # Scroll curto para manter a precisão
            subprocess.run("adb shell input swipe 500 1200 500 800 900", shell=True)
            time.sleep(1.5)

        except KeyboardInterrupt: break
        except Exception as e: print(f"Erro: {e}"); time.sleep(1)

if __name__ == "__main__":
    rodar_extrator_v6()