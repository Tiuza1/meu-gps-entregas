import os
import sys
import threading
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    import matchering as mg
    MATCHERING_OK = True
    MATCHERING_ERROR = ""
except Exception as e:
    mg = None
    MATCHERING_OK = False
    MATCHERING_ERROR = str(e)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    DND_OK = False

APP_TITLE = "Matchering Desktop UI"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
AUDIO_TYPES = [("Arquivos de áudio", "*.wav *.mp3 *.flac *.aiff *.ogg"), ("Todos os arquivos", "*.*")]

BaseWindow = ctk.CTk
if DND_OK:
    class BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass

class App(BaseWindow):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x780")
        self.minsize(960, 700)

        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        self.target_path = ctk.StringVar(value="")
        self.ref_path = ctk.StringVar(value="")
        self.out_dir = ctk.StringVar(value=str(base_dir / "output"))
        self.format_var = ctk.StringVar(value="pcm24")
        self.suffix_var = ctk.StringVar(value="_matched")
        self.status_var = ctk.StringVar(value="Pronto.")
        self.batch_items = []
        self.is_processing = False

        self.build_ui()
        self.update_preview()
        self.update_batch_preview()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray12"))
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=APP_TITLE, font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=18, pady=(14, 4), sticky="w")
        subtitle = "Interface Python nativa — use o botão PROCESSAR AGORA para rodar sem copiar código."
        ctk.CTkLabel(top, text=subtitle, text_color=("gray40", "gray70")).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")

        self.tabs = ctk.CTkTabview(self, segmented_button_selected_color="#0f766e")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        self.tabs.add("Arquivo único")
        self.tabs.add("Batch")
        self.tabs.add("Instalação")

        self.build_single_tab(self.tabs.tab("Arquivo único"))
        self.build_batch_tab(self.tabs.tab("Batch"))
        self.build_install_tab(self.tabs.tab("Instalação"))

        bottom = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(bottom, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.progress = ctk.CTkProgressBar(bottom)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.progress.set(0)

    def register_drop(self, widget, key):
        if DND_OK:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", lambda e, k=key: self.on_drop(e, k))
            except Exception:
                pass

    def build_drop_zone(self, parent, label_text, variable, choose_command, key):
        wrap = ctk.CTkFrame(parent)
        wrap.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(wrap, text=label_text, anchor="w", font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", padx=12, pady=(12, 6))

        zone = ctk.CTkFrame(wrap, height=124, fg_color=("gray95", "gray17"), border_width=1, border_color=("gray80", "gray28"))
        zone.pack(fill="x", padx=12, pady=(0, 8))
        zone.pack_propagate(False)
        inner_text = "Arraste e solte aqui\nou clique para escolher arquivo"
        inner = ctk.CTkLabel(zone, text=inner_text, justify="center")
        inner.pack(expand=True)
        zone.bind("<Button-1>", lambda e: choose_command())
        inner.bind("<Button-1>", lambda e: choose_command())
        self.register_drop(zone, key)
        self.register_drop(inner, key)

        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        row.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(row, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<KeyRelease>", lambda e: self.update_preview())
        ctk.CTkButton(row, text="Escolher", width=100, command=choose_command).grid(row=0, column=1)

    def build_single_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)

        self.build_drop_zone(left, "Seu áudio (target)", self.target_path, self.pick_target, "target")
        self.build_drop_zone(left, "Stem de referência", self.ref_path, self.pick_ref, "ref")

        opts = ctk.CTkFrame(left)
        opts.pack(fill="x", padx=8, pady=8)
        opts.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(opts, text="Formato de saída").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        ctk.CTkOptionMenu(opts, values=["pcm16", "pcm24", "pcm32"], variable=self.format_var, command=lambda *_: self.update_preview()).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkLabel(opts, text="Sufixo").grid(row=0, column=1, sticky="w", padx=12, pady=(12, 6))
        ctk.CTkOptionMenu(opts, values=["_matched", "_ref", "_adjusted"], variable=self.suffix_var, command=lambda *_: self.update_preview()).grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))

        out = ctk.CTkFrame(left)
        out.pack(fill="x", padx=8, pady=8)
        out.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(out, text="Pasta de saída").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        out_entry = ctk.CTkEntry(out, textvariable=self.out_dir)
        out_entry.grid(row=1, column=0, sticky="ew", padx=(12, 8), pady=(0, 12))
        out_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        ctk.CTkButton(out, text="Escolher pasta", width=130, command=self.pick_output_dir).grid(row=1, column=1, padx=(0, 12), pady=(0, 12))

        action_box = ctk.CTkFrame(left)
        action_box.pack(fill="x", padx=8, pady=8)
        action_box.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(action_box, text="Atualizar preview", command=self.update_preview).grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        self.process_btn = ctk.CTkButton(action_box, text="PROCESSAR AGORA", fg_color="#0f766e", hover_color="#115e59", command=self.process_single, font=ctk.CTkFont(weight="bold"))
        self.process_btn.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        ctk.CTkLabel(right, text="Código Python gerado", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 8))
        self.preview = ctk.CTkTextbox(right, wrap="none", font=("Consolas", 13))
        self.preview.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ctk.CTkButton(right, text="Copiar código", command=self.copy_preview).pack(anchor="e", padx=14, pady=(0, 14))

    def build_batch_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)

        ctk.CTkLabel(left, text="Adicionar par target → referência", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 10))
        self.batch_target = ctk.CTkEntry(left, placeholder_text="vocal.wav")
        self.batch_target.pack(fill="x", padx=14, pady=6)
        self.batch_ref = ctk.CTkEntry(left, placeholder_text="ref_vocal.wav")
        self.batch_ref.pack(fill="x", padx=14, pady=6)
        ctk.CTkButton(left, text="Adicionar", command=self.add_batch).pack(anchor="e", padx=14, pady=10)

        self.batch_list = ctk.CTkTextbox(left, height=280, font=("Consolas", 13))
        self.batch_list.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ctk.CTkButton(left, text="Limpar lista", fg_color="#7c2d12", hover_color="#9a3412", command=self.clear_batch).pack(anchor="e", padx=14, pady=(0, 14))

        ctk.CTkLabel(right, text="Script batch gerado", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 8))
        self.batch_preview = ctk.CTkTextbox(right, wrap="none", font=("Consolas", 13))
        self.batch_preview.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ctk.CTkButton(right, text="Copiar script batch", command=self.copy_batch_preview).pack(anchor="e", padx=14, pady=(0, 14))

    def build_install_tab(self, tab):
        txt = ctk.CTkTextbox(tab, font=("Consolas", 13))
        txt.pack(fill="both", expand=True, padx=12, pady=12)
        txt.insert("1.0", self.install_text())
        txt.configure(state="disabled")

    def install_text(self):
        return (
            "Instalação recomendada\n\n"
            "1) Instale Python Portable ou Python normal\n"
            "   python --version\n\n"
            "2) Instale FFmpeg e adicione ao PATH\n"
            "   ffmpeg -version\n\n"
            "3) Instale dependências\n"
            "   pip install matchering customtkinter tkinterdnd2\n\n"
            "4) Rode este arquivo clicando nele (associado a .pyw ou .py)\n\n"
            f"Status do Matchering: {'OK' if MATCHERING_OK else 'ERRO - ' + MATCHERING_ERROR}\n"
            f"Drag and drop: {'OK' if DND_OK else 'desativado (instale tkinterdnd2)'}\n"
        )

    def normalize_drop_path(self, raw):
        raw = raw.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        return raw

    def on_drop(self, event, key):
        path = self.normalize_drop_path(event.data)
        if key == "target":
            self.target_path.set(path)
        else:
            self.ref_path.set(path)
        self.update_preview()
        self.status_var.set(f"Arquivo carregado em {key}: {Path(path).name}")

    def pick_target(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_TYPES)
        if path:
            self.target_path.set(path)
            self.update_preview()

    def pick_ref(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_TYPES)
        if path:
            self.ref_path.set(path)
            self.update_preview()

    def pick_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.out_dir.set(path)
            self.update_preview()

    def build_single_code(self):
        target = self.target_path.get().strip() or "seu_audio.wav"
        reference = self.ref_path.get().strip() or "stem_referencia.wav"
        fmt = self.format_var.get().strip() or "pcm24"
        outdir = self.out_dir.get().strip() or "./output"
        suffix = self.suffix_var.get().strip() or "_matched"
        stem = Path(target).stem if target else "seu_audio"
        outfile = str(Path(outdir) / f"{stem}{suffix}.wav")
        return (
            f"import os\n"
            f"import matchering as mg\n\n"
            f"os.makedirs(r\"{outdir}\", exist_ok=True)\n\n"
            f"mg.process(\n"
            f"    target=r\"{target}\",\n"
            f"    reference=r\"{reference}\",\n"
            f"    results=[mg.{fmt}(r\"{outfile}\")]\n"
            f")"
        )

    def update_preview(self):
        code = self.build_single_code()
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", code)

    def copy_preview(self):
        self.clipboard_clear()
        self.clipboard_append(self.preview.get("1.0", "end").strip())
        self.status_var.set("Código copiado para a área de transferência.")

    def add_batch(self):
        target = self.batch_target.get().strip()
        reference = self.batch_ref.get().strip()
        if not target or not reference:
            messagebox.showwarning("Atenção", "Preencha target e referência.")
            return
        self.batch_items.append((target, reference))
        self.batch_target.delete(0, "end")
        self.batch_ref.delete(0, "end")
        self.render_batch_list()
        self.update_batch_preview()

    def render_batch_list(self):
        self.batch_list.delete("1.0", "end")
        if not self.batch_items:
            self.batch_list.insert("1.0", "Nenhum par adicionado ainda.")
            return
        for i, (target, reference) in enumerate(self.batch_items, 1):
            self.batch_list.insert("end", f"{i:02d}. {target} -> {reference}\n")

    def clear_batch(self):
        self.batch_items.clear()
        self.render_batch_list()
        self.update_batch_preview()

    def build_batch_code(self):
        lines = [
            "from pathlib import Path",
            "import os",
            "import matchering as mg",
            "",
            "os.makedirs(r\"./output\", exist_ok=True)",
            "",
            "stems = {",
        ]
        if self.batch_items:
            for target, reference in self.batch_items:
                lines.append(f"    r\"{target}\": r\"{reference}\",")
        else:
            lines.append("    # adicione pares aqui")
        lines.extend([
            "}",
            "",
            "for target, reference in stems.items():",
            "    out = f\"./output/matched_{Path(target).stem}.wav\"",
            "    mg.process(target=target, reference=reference, results=[mg.pcm24(out)])",
            "    print(f\"OK: {target} -> {out}\")",
        ])
        return "\n".join(lines)

    def update_batch_preview(self):
        code = self.build_batch_code()
        self.batch_preview.delete("1.0", "end")
        self.batch_preview.insert("1.0", code)
        self.render_batch_list()

    def copy_batch_preview(self):
        self.clipboard_clear()
        self.clipboard_append(self.batch_preview.get("1.0", "end").strip())
        self.status_var.set("Script batch copiado.")

    def process_single(self):
        if self.is_processing:
            return
        if not MATCHERING_OK:
            messagebox.showerror("Erro", f"A biblioteca matchering não está disponível.\n\n{MATCHERING_ERROR}")
            return
        target = self.target_path.get().strip()
        reference = self.ref_path.get().strip()
        if not target or not reference:
            messagebox.showwarning("Atenção", "Selecione target e referência.")
            return
        if not Path(target).exists() or not Path(reference).exists():
            messagebox.showwarning("Atenção", "Um dos arquivos selecionados não existe mais.")
            return
        self.is_processing = True
        self.process_btn.configure(state="disabled")
        self.progress.set(0.15)
        self.status_var.set("Processando...")
        threading.Thread(target=self._process_single_worker, daemon=True).start()

    def _process_single_worker(self):
        try:
            target = self.target_path.get().strip()
            reference = self.ref_path.get().strip()
            fmt = self.format_var.get().strip() or "pcm24"
            outdir = Path(self.out_dir.get().strip() or "./output")
            outdir.mkdir(parents=True, exist_ok=True)
            suffix = self.suffix_var.get().strip() or "_matched"
            outfile = outdir / f"{Path(target).stem}{suffix}.wav"
            result_factory = getattr(mg, fmt)
            self.after(0, lambda: self.progress.set(0.4))
            mg.process(target=target, reference=reference, results=[result_factory(str(outfile))])
            self.after(0, lambda: self.on_process_done(outfile))
        except Exception as e:
            tb = traceback.format_exc()
            self.after(0, lambda: self.on_process_error(e, tb))

    def on_process_done(self, outfile):
        self.is_processing = False
        self.process_btn.configure(state="normal")
        self.progress.set(1)
        self.status_var.set(f"Concluído: {outfile.name}")
        messagebox.showinfo("Concluído", f"Arquivo gerado:\n{outfile}")
        self.after(1200, lambda: self.progress.set(0))

    def on_process_error(self, error, traceback_text):
        self.is_processing = False
        self.process_btn.configure(state="normal")
        self.progress.set(0)
        self.status_var.set("Erro no processamento.")
        messagebox.showerror("Erro", f"{error}\n\n{traceback_text}")

    def on_close(self):
        if self.is_processing:
            if not messagebox.askyesno("Fechar", "Ainda há um processamento em andamento. Deseja sair mesmo assim?"):
                return
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
