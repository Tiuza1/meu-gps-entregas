import os
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

APP_TITLE = "MusicGen Helper (casco)"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(820, 520)

        base_dir = Path.cwd()
        self.ref_audio = ctk.StringVar(value="")
        self.prompt = ctk.StringVar(value="trap beat dark, 90 bpm, 808 forte")
        self.mode = ctk.StringVar(value="melody")
        self.duration = ctk.IntVar(value=8)
        self.out_dir = ctk.StringVar(value=str(base_dir / "saidas_musicgen"))
        self.status = ctk.StringVar(value="Pronto.")

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray12"))
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(top, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        sub = ctk.CTkLabel(top, text="Casco de interface para testar no Python portable (sem IA ainda).", text_color=("gray40", "gray70"))
        sub.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="w")

        main = ctk.CTkFrame(self)
        main.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Bloco: arquivo de referência
        ref_frame = ctk.CTkFrame(left)
        ref_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ref_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ref_frame, text="Áudio de referência", anchor="w", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(ref_frame, text="(trecho que o modelo vai usar como melodia/estilo)", anchor="w", text_color=("gray40", "gray70")).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")
        row = ctk.CTkFrame(ref_frame, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        row.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(row, textvariable=self.ref_audio)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row, text="Escolher", width=110, command=self.pick_ref_audio).grid(row=0, column=1)

        # Bloco: prompt de texto
        prompt_frame = ctk.CTkFrame(left)
        prompt_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        prompt_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(prompt_frame, text="Prompt de texto", anchor="w", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(prompt_frame, text="(ex: trap dark 90bpm, piano gospel, etc.)", anchor="w", text_color=("gray40", "gray70")).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")
        ctk.CTkEntry(prompt_frame, textvariable=self.prompt).grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))

        # Bloco: opções
        opts = ctk.CTkFrame(left)
        opts.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        opts.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(opts, text="Modo", anchor="w").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkOptionMenu(opts, values=["melody", "style"], variable=self.mode).grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkLabel(opts, text="Duração (s)", anchor="w").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkOptionMenu(opts, values=["8", "10", "12"], command=self._on_duration_change).grid(row=1, column=1, padx=12, pady=(0, 12), sticky="ew")

        # Bloco: pasta de saída
        out = ctk.CTkFrame(left)
        out.grid(row=3, column=0, sticky="ew", padx=8, pady=8)
        out.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(out, text="Pasta de saída", anchor="w").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        row2 = ctk.CTkFrame(out, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        row2.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row2, textvariable=self.out_dir).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row2, text="Escolher pasta", width=130, command=self.pick_out_dir).grid(row=0, column=1)

        # Bloco: botões principais
        actions = ctk.CTkFrame(left)
        actions.grid(row=4, column=0, sticky="ew", padx=8, pady=(8, 4))
        actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(actions, text="Testar painel (sem IA)", command=self.fake_generate).grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        ctk.CTkButton(actions, text="(futuro) Rodar MusicGen", fg_color="#0f766e", hover_color="#115e59").grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        # Lado direito: log
        ctk.CTkLabel(right, text="Log", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=0, column=0, padx=14, pady=(14, 4), sticky="w")
        self.log = ctk.CTkTextbox(right, wrap="word", font=("Consolas", 12))
        self.log.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        self.log.insert("end", "Painel carregado. Ainda sem integração com IA.
")

        # Status + barra
        bottom = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(bottom, textvariable=self.status, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew")

    def _on_duration_change(self, value:str):
        try:
            self.duration.set(int(value))
        except ValueError:
            self.duration.set(8)

    def pick_ref_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Áudio", "*.wav *.mp3 *.flac *.ogg *.aiff"), ("Todos", "*.*")])
        if p:
            self.ref_audio.set(p)
            self._log(f"Áudio de referência selecionado: {p}")

    def pick_out_dir(self):
        p = filedialog.askdirectory()
        if p:
            self.out_dir.set(p)
            self._log(f"Pasta de saída alterada para: {p}")

    def fake_generate(self):
        """Simula uma geração, só pra testar o painel no Python portable."""
        ref = self.ref_audio.get().strip() or "(nenhum)"
        prompt = self.prompt.get().strip()
        mode = self.mode.get().strip()
        dur = self.duration.get()
        out_dir = Path(self.out_dir.get().strip() or "./saidas_musicgen")
        out_dir.mkdir(parents=True, exist_ok=True)
        dummy_out = out_dir / f"dummy_{mode}_{dur}s.txt"
        dummy_out.write_text(f"Simulação de geração:
ref={ref}
prompt={prompt}
mode={mode}
duration={dur}", encoding="utf-8")
        self.status.set(f"Simulação concluída. Arquivo dummy salvo em {dummy_out}")
        self._log(f"[OK] Simulação de geração criada em {dummy_out}")
        messagebox.showinfo("Simulação", f"Painel funcionando. Arquivo dummy salvo em:
{dummy_out}")

    def _log(self, text:str):
        self.log.insert("end", text + "
")
        self.log.see("end")

if __name__ == "__main__":
    app = App()
    app.mainloop()
