import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import serial
import serial.tools.list_ports
from threading import Thread, Event
import importlib.util
import os
import time
import ctypes
import pygame
import json

BUILDS_FILE = 'builds_manager.json'

# --- CONFIGURAÇÕES DE SISTEMA ---
def encontrar_placa():
    for p in serial.tools.list_ports.comports():
        if "Serial" in p.description or "USB" in p.description or "CircuitPython" in p.description:
            return p.device
    return None

class MacroManager:
    def __init__(self, root):
        self.root = root
        self.root.title("RAGBRAZIL - TOTAL INPUT MANAGER")
        self.root.geometry("550x760")
        self.root.configure(bg="#121212")
        self.root.attributes("-topmost", True)

        # Inicializa Pygame para Joystick (Arcade)
        pygame.init()
        pygame.joystick.init()
        self.conectar_joystick()

        self.placa = None
        self.scripts_carregados = {}
        self.gravando_para = None
        self.builds = {}

        porta = encontrar_placa()
        try:
            self.placa = serial.Serial(porta, 9600, timeout=0)
            status_txt = f"PLACA: {porta} | JOYSTICK: {'OK' if pygame.joystick.get_count() > 0 else 'N/D'}"
            status_color = "#00ff00"
        except:
            status_txt = "PLACA NÃO ENCONTRADA"
            status_color = "#ff0000"

        tk.Label(root, text="GERENCIADOR DE MACROS", bg="#121212", fg="#00ffff", font=("Consolas", 16, "bold")).pack(pady=15)
        self.lbl_status = tk.Label(root, text=status_txt, bg="#121212", fg=status_color, font=("Consolas", 10))
        self.lbl_status.pack()

        # --- PAINEL DE BUILDS ---
        build_frame = tk.Frame(root, bg="#1a1a2e", relief="groove", bd=1)
        build_frame.pack(fill="x", padx=15, pady=(8, 0))

        tk.Label(build_frame, text="BUILDS", bg="#1a1a2e", fg="#aaaaff",
                 font=("Consolas", 9, "bold")).pack(side="top", anchor="w", padx=8, pady=(4, 0))

        row_salvar = tk.Frame(build_frame, bg="#1a1a2e")
        row_salvar.pack(fill="x", padx=8, pady=3)

        tk.Label(row_salvar, text="Nome:", bg="#1a1a2e", fg="#cccccc", font=("Arial", 9)).pack(side="left")
        self.entry_build = tk.Entry(row_salvar, bg="#2a2a3e", fg="white", insertbackground="white",
                                    relief="flat", width=22, font=("Arial", 9))
        self.entry_build.pack(side="left", padx=(4, 8))
        tk.Button(row_salvar, text="SALVAR BUILD", command=self._salvar_build,
                  bg="#1a3a1a", fg="#00ff88", font=("Arial", 9, "bold"),
                  relief="flat", padx=6).pack(side="left")

        row_carregar = tk.Frame(build_frame, bg="#1a1a2e")
        row_carregar.pack(fill="x", padx=8, pady=(0, 6))

        self.combo_builds = ttk.Combobox(row_carregar, state="readonly", width=24, font=("Arial", 9))
        self.combo_builds.pack(side="left", padx=(0, 6))
        tk.Button(row_carregar, text="CARREGAR", command=self._carregar_build,
                  bg="#1a2a3a", fg="#00ccff", font=("Arial", 9, "bold"),
                  relief="flat", padx=6).pack(side="left", padx=(0, 4))
        tk.Button(row_carregar, text="DELETAR", command=self._deletar_build,
                  bg="#3a1a1a", fg="#ff5555", font=("Arial", 9, "bold"),
                  relief="flat", padx=6).pack(side="left")

        # --- LISTA DE SCRIPTS ---
        self.frame_lista = tk.Frame(root, bg="#121212")
        self.frame_lista.pack(fill="both", expand=True, padx=15, pady=10)

        # --- BOTÕES INFERIORES ---
        btn_container = tk.Frame(root, bg="#121212")
        btn_container.pack(side="bottom", fill="x", padx=30, pady=20)

        self.btn_importar = tk.Button(btn_container, text="+ IMPORTAR SCRIPT", command=self.importar_script,
                                     bg="#333", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_importar.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_limpar = tk.Button(btn_container, text="🗑 LIMPAR TUDO", command=self.limpar_todos_scripts,
                                   bg="#442222", fg="#ff5555", font=("Arial", 10, "bold"), height=2)
        self.btn_limpar.pack(side="right", fill="x", expand=True, padx=5)

        # Carrega builds salvas do arquivo
        self._carregar_builds()

    # ── SISTEMA DE BUILDS ────────────────────────────────────────────────────

    def _carregar_builds(self):
        if os.path.exists(BUILDS_FILE):
            try:
                with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                    self.builds = json.load(f)
            except Exception as e:
                print(f"[BUILDS] Erro ao ler arquivo de builds: {e}")
                self.builds = {}
        else:
            self.builds = {}
        self._atualizar_combo_builds()

    def _atualizar_combo_builds(self):
        nomes = list(self.builds.keys())
        self.combo_builds['values'] = nomes
        if nomes:
            self.combo_builds.set(nomes[-1])
        else:
            self.combo_builds.set('')

    def _salvar_builds_arquivo(self):
        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.builds, f, ensure_ascii=False, indent=2)

    def _salvar_build(self):
        nome = self.entry_build.get().strip()
        if not nome:
            messagebox.showwarning("Aviso", "Digite um nome para a build.")
            return
        if not self.scripts_carregados:
            messagebox.showwarning("Aviso", "Nenhum script carregado para salvar.")
            return

        scripts_da_build = []
        for s_nome, s_data in self.scripts_carregados.items():
            id_input = s_data['id_input']
            # tuple não é serializável em JSON — converte para lista
            if isinstance(id_input, tuple):
                id_input = list(id_input)
            scripts_da_build.append({
                'nome':         s_nome,
                'caminho':      s_data['caminho'],
                'tipo_input':   s_data['tipo_input'],
                'id_input':     id_input,
                'btn_key_text': s_data['btn_key'].cget('text')
            })

        self.builds[nome] = scripts_da_build
        self._salvar_builds_arquivo()
        self._atualizar_combo_builds()
        self.combo_builds.set(nome)
        messagebox.showinfo("Build Salva", f"Build '{nome}' salva com {len(scripts_da_build)} script(s).")

    def _carregar_build(self):
        nome = self.combo_builds.get()
        if not nome or nome not in self.builds:
            messagebox.showwarning("Aviso", "Selecione uma build válida.")
            return

        # Para e limpa todos os scripts atuais
        for s_nome in list(self.scripts_carregados.keys()):
            s = self.scripts_carregados[s_nome]
            if s['status'] and s['stop_event']:
                s['stop_event'].set()
        self.scripts_carregados.clear()
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        # Recria os scripts da build salvos (todos OFF)
        nao_encontrados = []
        for s_data in self.builds[nome]:
            if os.path.exists(s_data['caminho']):
                id_input   = s_data.get('id_input')
                tipo_input = s_data.get('tipo_input')
                # joystick foi salvo como lista, volta para tuple
                if tipo_input == 'joystick' and isinstance(id_input, list):
                    id_input = tuple(id_input)
                self._importar_script_com_dados(
                    s_data['caminho'], tipo_input, id_input,
                    s_data.get('btn_key_text', 'CLIQUE P/ DEFINIR')
                )
            else:
                nao_encontrados.append(s_data['nome'])

        if nao_encontrados:
            messagebox.showwarning("Build carregada com avisos",
                                   "Arquivos não encontrados:\n" + "\n".join(nao_encontrados))
        else:
            print(f"[BUILDS] '{nome}' carregada com {len(self.builds[nome])} script(s).")

    def _deletar_build(self):
        nome = self.combo_builds.get()
        if not nome or nome not in self.builds:
            messagebox.showwarning("Aviso", "Selecione uma build para deletar.")
            return
        if messagebox.askyesno("Deletar Build", f"Deletar a build '{nome}'?"):
            del self.builds[nome]
            self._salvar_builds_arquivo()
            self._atualizar_combo_builds()

    def _importar_script_com_dados(self, caminho, tipo_input, id_input, btn_key_text):
        nome = os.path.basename(caminho)
        if nome in self.scripts_carregados:
            return

        frame = tk.Frame(self.frame_lista, bg="#1e1e1e", pady=10)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=nome, bg="#1e1e1e", fg="white", width=15, anchor="w").pack(side="left", padx=10)

        tem_key = tipo_input is not None and id_input is not None
        btn_key = tk.Button(frame,
                            text=btn_key_text if tem_key else "CLIQUE P/ DEFINIR",
                            width=15,
                            bg="#222" if tem_key else "#444",
                            fg="#00ff00" if tem_key else "#00ffff",
                            command=lambda n=nome: self.iniciar_gravacao(n))
        btn_key.pack(side="left", padx=10)

        btn_onoff = tk.Button(frame, text="OFF", width=8, bg="#555", fg="white",
                              font=("Arial", 9, "bold"),
                              command=lambda n=nome: self.toggle_script(n))
        btn_onoff.pack(side="right", padx=10)

        self.scripts_carregados[nome] = {
            'caminho': caminho, 'btn_onoff': btn_onoff, 'btn_key': btn_key, 'frame': frame,
            'status': False, 'stop_event': None, 'tipo_input': tipo_input, 'id_input': id_input
        }
        Thread(target=self.monitor_execucao, args=(nome,), daemon=True).start()

    # ── MÉTODOS ORIGINAIS (sem alteração) ────────────────────────────────────

    def conectar_joystick(self):
        """ Inicializa todos os joysticks conectados """
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()

    def limpar_todos_scripts(self):
        """ Para todos os scripts e limpa a interface """
        if not self.scripts_carregados:
            return

        if messagebox.askyesno("Limpar Tudo", "Deseja remover todos os scripts da lista?"):
            # 1. Para todos os scripts que estão rodando
            for nome in list(self.scripts_carregados.keys()):
                script = self.scripts_carregados[nome]
                if script['status'] and script['stop_event']:
                    script['stop_event'].set()

            # 2. Limpa o dicionário de dados
            self.scripts_carregados.clear()

            # 3. Remove todos os widgets dentro do frame de lista
            for widget in self.frame_lista.winfo_children():
                widget.destroy()

            print("Todos os scripts foram removidos.")

    def importar_script(self):
        caminho = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if not caminho: return

        nome = os.path.basename(caminho)

        # Evita duplicados com o mesmo nome
        if nome in self.scripts_carregados:
            messagebox.showwarning("Aviso", "Este script já foi importado.")
            return

        frame = tk.Frame(self.frame_lista, bg="#1e1e1e", pady=10)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=nome, bg="#1e1e1e", fg="white", width=15, anchor="w").pack(side="left", padx=10)

        btn_key = tk.Button(frame, text="CLIQUE P/ DEFINIR", width=15, bg="#444", fg="#00ffff",
                            command=lambda n=nome: self.iniciar_gravacao(n))
        btn_key.pack(side="left", padx=10)

        btn_onoff = tk.Button(frame, text="OFF", width=8, bg="#555", fg="white", font=("Arial", 9, "bold"),
                             command=lambda n=nome: self.toggle_script(n))
        btn_onoff.pack(side="right", padx=10)

        self.scripts_carregados[nome] = {
            'caminho': caminho, 'btn_onoff': btn_onoff, 'btn_key': btn_key, 'frame': frame,
            'status': False, 'stop_event': None, 'tipo_input': None, 'id_input': None
        }
        Thread(target=self.monitor_execucao, args=(nome,), daemon=True).start()

    def iniciar_gravacao(self, nome):
        self.gravando_para = nome
        self.scripts_carregados[nome]['btn_key'].config(text="PRESSIONE ALGO...", bg="#ff8800", fg="black")
        Thread(target=self.capturar_proximo_input, args=(nome,), daemon=True).start()

    def capturar_proximo_input(self, nome):
        detectado = False
        while self.gravando_para == nome:
            if nome not in self.scripts_carregados: break # Caso tenha sido limpo durante a gravação

            for i in range(0x01, 0xFF):
                if ctypes.windll.user32.GetAsyncKeyState(i) & 0x8000:
                    nome_tecla = {0x05: "Mouse Lateral 1", 0x06: "Mouse Lateral 2"}.get(i, f"Tecla: {hex(i)}")
                    self.scripts_carregados[nome]['tipo_input'] = 'teclado_mouse'
                    self.scripts_carregados[nome]['id_input'] = i
                    self.root.after(0, self.finalizar_gravacao, nome, nome_tecla)
                    detectado = True
                    break

            if not detectado:
                pygame.event.pump()
                for j_idx, joy in enumerate(self.joysticks):
                    for b in range(joy.get_numbuttons()):
                        if joy.get_button(b):
                            self.scripts_carregados[nome]['tipo_input'] = 'joystick'
                            self.scripts_carregados[nome]['id_input'] = (j_idx, b)
                            self.root.after(0, self.finalizar_gravacao, nome, f"Arcade Btn: {b}")
                            detectado = True
                            break

            if detectado: break
            time.sleep(0.05)

    def finalizar_gravacao(self, nome, texto):
        self.gravando_para = None
        if nome in self.scripts_carregados:
            self.scripts_carregados[nome]['btn_key'].config(text=texto, bg="#222", fg="#00ff00")

    def monitor_execucao(self, nome):
        while True:
            # Se o script foi removido da lista, encerra essa thread de monitoramento
            if nome not in self.scripts_carregados:
                break

            script = self.scripts_carregados.get(nome)
            if not script or script['id_input'] is None or self.gravando_para == nome:
                time.sleep(0.1); continue

            ativou = False
            if script['tipo_input'] == 'teclado_mouse':
                if ctypes.windll.user32.GetAsyncKeyState(script['id_input']) & 0x8000:
                    ativou = True
            elif script['tipo_input'] == 'joystick':
                pygame.event.pump()
                j_idx, b_idx = script['id_input']
                if self.joysticks[j_idx].get_button(b_idx):
                    ativou = True

            if ativou:
                self.root.after(0, self.toggle_script, nome)
                while True: # Debounce
                    time.sleep(0.1)
                    if nome not in self.scripts_carregados: break
                    if script['tipo_input'] == 'teclado_mouse':
                        if not (ctypes.windll.user32.GetAsyncKeyState(script['id_input']) & 0x8000): break
                    else:
                        pygame.event.pump()
                        if not self.joysticks[j_idx].get_button(b_idx): break
            time.sleep(0.05)

    def toggle_script(self, nome):
        if nome not in self.scripts_carregados: return

        script = self.scripts_carregados[nome]
        if not script['status']:
            if not self.placa: return
            try:
                spec = importlib.util.spec_from_file_location("mod", script['caminho'])
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                script['status'] = True
                script['btn_onoff'].config(text="ON", bg="#006600")
                script['stop_event'] = Event()
                Thread(target=modulo.executar, args=(self.placa, script['stop_event']), daemon=True).start()
            except Exception as e: print(f"Erro: {e}")
        else:
            script['status'] = False
            script['btn_onoff'].config(text="OFF", bg="#555")
            if script['stop_event']: script['stop_event'].set()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroManager(root)
    root.mainloop()
