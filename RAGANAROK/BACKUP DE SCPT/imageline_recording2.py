import tkinter as tk
from tkinter import filedialog, messagebox
import serial
import serial.tools.list_ports
from threading import Thread, Event
import importlib.util
import os
import keyboard
import time

# --- BUSCA A PLACA ---
def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

class MacroManager:
    def __init__(self, root):
        self.root = root
        self.root.title("RAGBRAZIL - ULTRA MANAGER (POLLLING MODE)")
        self.root.geometry("500x600")
        self.root.configure(bg="#1a1a1a")
        self.root.attributes("-topmost", True)

        self.placa = None
        self.scripts_carregados = {} 

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
        tk.Label(root, text="GERENCIADOR DE MACROS", bg="#1a1a1a", fg="cyan", font=("Arial", 14, "bold")).pack(pady=10)
        self.lbl_hw = tk.Label(root, text=status_txt, bg="#1a1a1a", fg=color)
        self.lbl_hw.pack()

        self.frame_lista = tk.Frame(root, bg="#1a1a1a")
        self.frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Button(root, text="+ IMPORTAR NOVO SCRIPT (.py)", command=self.importar_script, 
                  bg="#333", fg="white", font=("Arial", 10, "bold"), height=2).pack(side="bottom", fill="x", padx=20, pady=20)

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

        tk.Label(frame_item, text=nome_arquivo, bg="#252525", fg="white", width=18, anchor="w").pack(side="left", padx=5)
        
        ent_hotkey = tk.Entry(frame_item, width=8, bg="#333", fg="cyan", justify="center")
        ent_hotkey.insert(0, "home") # Tecla padrão
        ent_hotkey.pack(side="left", padx=5)

        btn_toggle = tk.Button(frame_item, text="OFF", width=8, bg="gray", fg="white",
                              command=lambda n=nome_arquivo: self.toggle_script(n))
        btn_toggle.pack(side="right", padx=5)

        # Guarda referência
        self.scripts_carregados[nome_arquivo] = {
            'caminho': caminho,
            'btn': btn_toggle,
            'ent': ent_hotkey,
            'stop_event': None,
            'status': False
        }

        # Inicia o monitor de tecla exclusivo para este script
        t_key = Thread(target=self.monitorar_tecla, args=(nome_arquivo,), daemon=True)
        t_key.start()

    def monitorar_tecla(self, nome):
        """ Monitoramento Ativo (Polling) - Funciona melhor em jogos protegidos """
        while True:
            if nome not in self.scripts_carregados: break
            
            script = self.scripts_carregados[nome]
            tecla = script['ent'].get().lower().strip()
            
            if tecla:
                try:
                    # Verifica se a tecla está pressionada AGORA
                    if keyboard.is_pressed(tecla):
                        # Usa root.after para que a mudança de UI ocorra na thread principal
                        self.root.after(0, self.toggle_script, nome)
                        
                        # Espera soltar a tecla para não ligar/desligar repetidamente
                        while keyboard.is_pressed(tecla):
                            time.sleep(0.1)
                except:
                    pass # Tecla inválida temporariamente enquanto o usuário digita
            
            time.sleep(0.05) # Delay de 50ms (rápido o suficiente e não pesa no PC)

    def toggle_script(self, nome):
        script = self.scripts_carregados[nome]
        
        if not script['status']:
            # LIGAR
            try:
                if not self.placa:
                    messagebox.showerror("Erro", "Conecte a placa primeiro!")
                    return

                # Importação dinâmica
                spec = importlib.util.spec_from_file_location(nome.replace(".py",""), script['caminho'])
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                
                if hasattr(modulo, 'executar'):
                    script['status'] = True
                    script['btn'].config(text="ON", bg="green")
                    script['ent'].config(state="disabled") # Trava a tecla enquanto roda
                    script['stop_event'] = Event()
                    
                    t = Thread(target=modulo.executar, args=(self.placa, script['stop_event']), daemon=True)
                    t.start()
                else:
                    messagebox.showerror("Erro", "Script sem a função executar(placa, stop_event)")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao iniciar: {e}")
        else:
            # DESLIGAR
            script['status'] = False
            script['btn'].config(text="OFF", bg="gray")
            script['ent'].config(state="normal")
            if script['stop_event']:
                script['stop_event'].set()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroManager(root)
    root.mainloop()