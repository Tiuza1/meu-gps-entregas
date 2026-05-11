import os
import threading
import time
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

APP_TITLE = "MusicGen Studio"
APP_VERSION = "1.0-casco"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  [{APP_VERSION}]")
        self.geometry("1100x720")
        self.minsize(960, 600)

        base_dir = Path.cwd()

        # --- Variáveis de controle ---
        self.ref_audio      = ctk.StringVar(value="")
        self.mode           = ctk.StringVar(value="melody")
        self.model_size     = ctk.StringVar(value="medium")
        self.duration       = ctk.DoubleVar(value=8.0)
        self.top_k          = ctk.DoubleVar(value=250.0)
        self.temperature    = ctk.DoubleVar(value=1.0)
        self.out_dir        = ctk.StringVar(value=str(base_dir / "saidas_musicgen"))
        self.last_output    = ctk.StringVar(value="")
        self.status_text    = ctk.StringVar(value="Pronto.")

        self._generating    = False
        self._gen_thread    = None

        self._build_ui()
        self._log("Painel carregado. MusicGen ainda não integrado (casco).")

    # ------------------------------------------------------------------ #
    #  UI                                                                   #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)   # painel esq (fixo)
        self.grid_columnconfigure(1, weight=1)   # painel dir (expande)
        self.grid_rowconfigure(1, weight=1)

        # ---- Cabeçalho ------------------------------------------------ #
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray12"))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text=APP_TITLE,
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(14, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text="Interface para geração musical com AudioCraft / MusicGen.",
            text_color=("gray45", "gray65"),
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        # ---- Painel esquerdo (parâmetros) ----------------------------- #
        left_scroll = ctk.CTkScrollableFrame(self, width=360, corner_radius=8)
        left_scroll.grid(row=1, column=0, sticky="nsew", padx=(14, 6), pady=14)
        left_scroll.grid_columnconfigure(0, weight=1)
        self._build_left(left_scroll)

        # ---- Painel direito (log + output) ---------------------------- #
        right = ctk.CTkFrame(self, corner_radius=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 14), pady=14)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        self._build_right(right)

        # ---- Barra de status ------------------------------------------ #
        bar = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))
        bar.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(bar, mode="indeterminate", height=6)
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress.set(0)

        ctk.CTkLabel(bar, textvariable=self.status_text, anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w")

    # ---- Painel esquerdo -------------------------------------------- #
    def _build_left(self, parent):
        pad = {"padx": 12, "pady": (0, 10), "sticky": "ew"}

        # Áudio de referência
        self._section(parent, 0, "Áudio de referência",
                      "(melodia/estilo que o modelo usará como base)")
        row_ref = ctk.CTkFrame(parent, fg_color="transparent")
        row_ref.grid(row=1, **pad)
        row_ref.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row_ref, textvariable=self.ref_audio,
                     placeholder_text="Nenhum arquivo selecionado…"
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row_ref, text="Escolher", width=100,
                      command=self._pick_ref_audio).grid(row=0, column=1)

        # Prompt de texto
        self._section(parent, 2, "Prompt de texto",
                      "ex: trap dark 90bpm  |  piano gospel bright  |  lo-fi chill")
        self.prompt_box = ctk.CTkTextbox(parent, height=90,
                                         font=("Consolas", 13), wrap="word")
        self.prompt_box.grid(row=3, **pad)
        self.prompt_box.insert("end", "trap beat dark, 90 bpm, 808 forte")

        # Modo
        self._section(parent, 4, "Modo de condicionamento", "")
        ctk.CTkSegmentedButton(
            parent, values=["melody", "style", "text-only"],
            variable=self.mode, font=ctk.CTkFont(size=12),
        ).grid(row=5, **pad)

        # Modelo
        self._section(parent, 6, "Tamanho do modelo", "")
        ctk.CTkSegmentedButton(
            parent, values=["small", "medium", "large"],
            variable=self.model_size, font=ctk.CTkFont(size=12),
        ).grid(row=7, **pad)

        # Duração
        self._section(parent, 8, "Duração", "")
        self.lbl_dur = ctk.CTkLabel(parent, text="8 s", anchor="e",
                                    font=ctk.CTkFont(size=12))
        self.lbl_dur.grid(row=8, column=0, padx=12, sticky="e")
        ctk.CTkSlider(
            parent, from_=5, to=30, number_of_steps=25,
            variable=self.duration,
            command=lambda v: self.lbl_dur.configure(text=f"{int(v)} s"),
        ).grid(row=9, **pad)

        # Top-K
        self._section(parent, 10, "Top-K  (diversidade)", "")
        self.lbl_topk = ctk.CTkLabel(parent, text="250", anchor="e",
                                     font=ctk.CTkFont(size=12))
        self.lbl_topk.grid(row=10, column=0, padx=12, sticky="e")
        ctk.CTkSlider(
            parent, from_=50, to=1000, number_of_steps=38,
            variable=self.top_k,
            command=lambda v: self.lbl_topk.configure(text=str(int(v))),
        ).grid(row=11, **pad)

        # Temperature
        self._section(parent, 12, "Temperature  (criatividade)", "")
        self.lbl_temp = ctk.CTkLabel(parent, text="1.00", anchor="e",
                                     font=ctk.CTkFont(size=12))
        self.lbl_temp.grid(row=12, column=0, padx=12, sticky="e")
        ctk.CTkSlider(
            parent, from_=0.1, to=2.0, number_of_steps=38,
            variable=self.temperature,
            command=lambda v: self.lbl_temp.configure(text=f"{v:.2f}"),
        ).grid(row=13, **pad)

        # Pasta de saída
        self._section(parent, 14, "Pasta de saída", "")
        row_out = ctk.CTkFrame(parent, fg_color="transparent")
        row_out.grid(row=15, **pad)
        row_out.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row_out, textvariable=self.out_dir
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row_out, text="Escolher pasta", width=120,
                      command=self._pick_out_dir).grid(row=0, column=1)

        # Botões principais
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=16, padx=12, pady=(14, 8), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_gerar = ctk.CTkButton(
            btn_frame, text="Gerar Música",
            fg_color="#0f766e", hover_color="#115e59",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_gerar,
        )
        self.btn_gerar.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="Cancelar",
            fg_color="#7f1d1d", hover_color="#991b1b",
            state="disabled",
            command=self._on_cancelar,
        )
        self.btn_cancelar.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # ---- Painel direito --------------------------------------------- #
    def _build_right(self, parent):
        # Bloco de saída
        out_frame = ctk.CTkFrame(parent)
        out_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        out_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(out_frame, text="Último arquivo gerado",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        out_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        out_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        out_row.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(out_row, textvariable=self.last_output,
                     state="readonly", font=("Consolas", 12)
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(out_row, text="Copiar caminho", width=130,
                      command=self._copiar_caminho
                      ).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(out_row, text="Abrir pasta", width=100,
                      command=self._abrir_pasta
                      ).grid(row=0, column=2)

        # Log
        log_header = ctk.CTkFrame(parent, fg_color="transparent")
        log_header.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 0))
        log_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_header, text="Log",
                     font=ctk.CTkFont(size=15, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_header, text="Limpar", width=70,
                      command=self._limpar_log
                      ).grid(row=0, column=1)

        self.log_box = ctk.CTkTextbox(
            parent, wrap="word",
            font=("Consolas", 12), state="disabled",
        )
        self.log_box.grid(row=2, column=0, sticky="nsew",
                          padx=12, pady=(4, 12))

    # ---- Helpers de UI ----------------------------------------------- #
    def _section(self, parent, row, title, subtitle):
        ctk.CTkLabel(
            parent, text=title, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=12, pady=(14, 0), sticky="w")
        if subtitle:
            ctk.CTkLabel(
                parent, text=subtitle, anchor="w",
                text_color=("gray45", "gray65"),
                font=ctk.CTkFont(size=11),
            ).grid(row=row, column=0, padx=14, pady=(18, 0), sticky="e")

    # ------------------------------------------------------------------ #
    #  Ações de UI                                                          #
    # ------------------------------------------------------------------ #
    def _pick_ref_audio(self):
        p = filedialog.askopenfilename(
            filetypes=[("Áudio", "*.wav *.mp3 *.flac *.ogg *.aiff"), ("Todos", "*.*")]
        )
        if p:
            self.ref_audio.set(p)
            self._log(f"Ref: {p}")

    def _pick_out_dir(self):
        p = filedialog.askdirectory()
        if p:
            self.out_dir.set(p)
            self._log(f"Pasta de saída: {p}")

    def _copiar_caminho(self):
        caminho = self.last_output.get().strip()
        if not caminho:
            messagebox.showwarning("Aviso", "Nenhum arquivo gerado ainda.")
            return
        self.clipboard_clear()
        self.clipboard_append(caminho)
        self._log("Caminho copiado para a área de transferência.")

    def _abrir_pasta(self):
        caminho = self.last_output.get().strip()
        pasta = str(Path(caminho).parent) if caminho else self.out_dir.get().strip()
        if pasta and Path(pasta).exists():
            os.startfile(pasta)
        else:
            messagebox.showwarning("Aviso", "Pasta não encontrada.")

    def _limpar_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Geração                                                              #
    # ------------------------------------------------------------------ #
    def _on_gerar(self):
        if self._generating:
            return
        self._generating = True
        self._stop_flag = False

        self.btn_gerar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.status_text.set("Gerando…")

        params = {
            "ref_audio":   self.ref_audio.get().strip() or None,
            "prompt":      self.prompt_box.get("1.0", "end").strip(),
            "mode":        self.mode.get(),
            "model_size":  self.model_size.get(),
            "duration":    int(self.duration.get()),
            "top_k":       int(self.top_k.get()),
            "temperature": round(self.temperature.get(), 2),
            "out_dir":     Path(self.out_dir.get().strip() or "./saidas_musicgen"),
        }

        self._log(
            f"Iniciando geração — modelo={params['model_size']}  "
            f"modo={params['mode']}  dur={params['duration']}s  "
            f"top_k={params['top_k']}  temp={params['temperature']}"
        )

        self._gen_thread = threading.Thread(
            target=self._gerar_worker, args=(params,), daemon=True
        )
        self._gen_thread.start()

    def _on_cancelar(self):
        self._stop_flag = True
        self._log("Cancelamento solicitado…")
        self.btn_cancelar.configure(state="disabled")

    def _gerar_worker(self, p: dict):
        try:
            p["out_dir"].mkdir(parents=True, exist_ok=True)

            # ----------------------------------------------------------------
            # TODO: substituir o bloco abaixo pela integração real com MusicGen
            #
            # from audiocraft.models import MusicGen
            # model = MusicGen.get_pretrained(p["model_size"])
            # model.set_generation_params(
            #     duration    = p["duration"],
            #     top_k       = p["top_k"],
            #     temperature = p["temperature"],
            # )
            #
            # if p["mode"] == "text-only" or p["ref_audio"] is None:
            #     wav = model.generate([p["prompt"]])
            # else:
            #     import torchaudio
            #     melody_waveform, sr = torchaudio.load(p["ref_audio"])
            #     wav = model.generate_with_chroma(
            #         descriptions=[p["prompt"]],
            #         melody_wavs=melody_waveform.unsqueeze(0),
            #         melody_sample_rate=sr,
            #     )
            #
            # ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            # out_path = p["out_dir"] / f"musicgen_{ts}.wav"
            # torchaudio.save(str(out_path), wav[0].cpu(), 32000)
            # ----------------------------------------------------------------

            # Simulação enquanto MusicGen não está integrado
            self.after(0, lambda: self._log("  [casco] Simulando geração…"))
            for i in range(1, 5):
                if self._stop_flag:
                    self.after(0, lambda: self._log("  [casco] Geração cancelada."))
                    return
                time.sleep(0.5)
                self.after(0, lambda i=i: self._log(f"  [casco] passo {i}/4…"))

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = p["out_dir"] / f"musicgen_{p['model_size']}_{p['duration']}s_{ts}.txt"
            out_path.write_text(
                f"Simulação de geração\n"
                f"prompt      : {p['prompt']}\n"
                f"ref_audio   : {p['ref_audio']}\n"
                f"mode        : {p['mode']}\n"
                f"model_size  : {p['model_size']}\n"
                f"duration    : {p['duration']}s\n"
                f"top_k       : {p['top_k']}\n"
                f"temperature : {p['temperature']}\n",
                encoding="utf-8",
            )

            self.after(0, lambda: self._on_geracao_concluida(str(out_path)))

        except Exception as exc:
            self.after(0, lambda: self._on_geracao_erro(str(exc)))

    def _on_geracao_concluida(self, out_path: str):
        self.last_output.set(out_path)
        self._log(f"[OK] Arquivo salvo em: {out_path}")
        self.status_text.set(f"Concluído: {Path(out_path).name}")
        self._finalizar_geracao()

    def _on_geracao_erro(self, msg: str):
        self._log(f"[ERRO] {msg}")
        self.status_text.set("Erro na geração.")
        messagebox.showerror("Erro", msg)
        self._finalizar_geracao()

    def _finalizar_geracao(self):
        self._generating = False
        self.progress.stop()
        self.progress.set(0)
        self.btn_gerar.configure(state="normal")
        self.btn_cancelar.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Log                                                                  #
    # ------------------------------------------------------------------ #
    def _log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        linha = f"[{ts}] {text}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", linha)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
