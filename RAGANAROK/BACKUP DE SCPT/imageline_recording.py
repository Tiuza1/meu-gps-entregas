import tkinter as tk
from tkinter import filedialog, messagebox
import serial
import serial.tools.list_ports
from threading import Thread, Event
import importlib.util
import os

# --- BUSCA A PLACA ---
def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

class MacroManager:
    def __init__(self, root):
        self.root = root
        self.root.title("RAGBRAZIL - MACRO MANAGER")
        self.root.geometry("400x500")
        self.root.configure(bg="#1a1a1a")
        self.root.attributes("-topmost", True)

        self.placa = None
        self.scripts_carregados = {} # {nome_do_arquivo: {'thread': T, 'stop_event': E, 'status': False}}

        # Inicializa Placa
        porta = encontrar_placa()
        try:
            self.placa = serial.Serial(porta, 9600, timeout=0)
            status_txt = f"PLACA OK: {porta}"
            color = "green"
        except:
            status_txt = "PLACA NÃO ENCONTRADA"
            color = "red"

        # UI
        tk.Label(root, text="GERENCIADOR DE MACROS", bg="#1a1a1a", fg="cyan", font=("Arial", 12, "bold")).pack(pady=10)
        self.lbl_hw = tk.Label(root, text=status_txt, bg="#1a1a1a", fg=color)
        self.lbl_hw.pack()

        self.frame_lista = tk.Frame(root, bg="#1a1a1a")
        self.frame_lista.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Button(root, text="+ IMPORTAR NOVO SCRIPT (.py)", command=self.importar_script, bg="#333", fg="white").pack(side="bottom", fill="x", padx=10, pady=10)

    def importar_script(self):
        caminho = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if not caminho: return
        
        nome_arquivo = os.path.basename(caminho)
        if nome_arquivo in self.scripts_carregados:
            messagebox.showwarning("Aviso", "Este script já foi carregado.")
            return

        # Cria linha na interface
        frame_item = tk.Frame(self.frame_lista, bg="#252525", pady=5)
        frame_item.pack(fill="x", pady=2)

        tk.Label(frame_item, text=nome_arquivo, bg="#252525", fg="white", width=20, anchor="w").pack(side="left", padx=5)
        
        btn_toggle = tk.Button(frame_item, text="OFF", width=8, bg="gray", fg="white",
                              command=lambda n=nome_arquivo: self.toggle_script(n))
        btn_toggle.pack(side="right", padx=5)

        # Guarda referência
        self.scripts_carregados[nome_arquivo] = {
            'caminho': caminho,
            'btn': btn_toggle,
            'stop_event': None,
            'status': False
        }

    def toggle_script(self, nome):
        script = self.scripts_carregados[nome]
        
        if not script['status']:
            # LIGAR
            if not self.placa:
                messagebox.showerror("Erro", "Conecte a placa primeiro!")
                return
                
            script['status'] = True
            script['btn'].config(text="ON", bg="green")
            script['stop_event'] = Event()
            
            # Carrega o arquivo dinamicamente
            spec = importlib.util.spec_from_file_location("modulo_macro", script['caminho'])
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            
            # Inicia em uma Thread separada passando a placa
            t = Thread(target=modulo.executar, args=(self.placa, script['stop_event']), daemon=True)
            t.start()
            print(f"Script {nome} INICIADO.")
        else:
            # DESLIGAR
            script['status'] = False
            script['btn'].config(text="OFF", bg="gray")
            script['stop_event'].set()
            print(f"Script {nome} PARADO.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroManager(root)
    root.mainloop()