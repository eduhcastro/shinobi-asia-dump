"""
Interface gráfica simples (Tkinter) para:
- Navegar em uma pasta (explorer)
- Visualizar arquivo texto / imagem
- Decodificar arquivo selecionado
- Decodificar em massa (Decode All)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
from decoder.decode_logic import (
    detect_tj_type,
    decode_single_file,
    iter_tj_files,
)
APP_VERSION = "0.0.0"


class DecoderApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"ShinobiAsia Decoder GUI v{APP_VERSION}")
            self.geometry("1000x600")

            self.current_root: Optional[Path] = None
            self.image_cache = None  # Para manter referência do PhotoImage

            self._build_ui()

        # ------------------------------------------------------------------
        # UI building
        # ------------------------------------------------------------------
        def _build_ui(self):
            # Top bar
            top_frame = ttk.Frame(self)
            top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

            btn_select = ttk.Button(top_frame, text="Selecionar pasta", command=self.select_folder)
            btn_select.pack(side=tk.LEFT)

            self.lbl_root = ttk.Label(top_frame, text="Nenhuma pasta selecionada")
            self.lbl_root.pack(side=tk.LEFT, padx=10)

            btn_decode_all = ttk.Button(top_frame, text="Decode All", command=self.open_decode_all_dialog)
            btn_decode_all.pack(side=tk.RIGHT, padx=5)

            btn_decode_selected = ttk.Button(top_frame, text="Decodificar arquivo selecionado", command=self.decode_selected_file)
            btn_decode_selected.pack(side=tk.RIGHT, padx=5)

            # Main area: left explorer, right preview
            main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
            main_pane.pack(fill=tk.BOTH, expand=True)

            # Explorer (Treeview)
            left_frame = ttk.Frame(main_pane)
            main_pane.add(left_frame, weight=1)

            self.tree = ttk.Treeview(left_frame)
            self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

            scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
            self.tree.configure(yscrollcommand=scroll_y.set)
            scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

            # Preview area
            right_frame = ttk.Frame(main_pane)
            main_pane.add(right_frame, weight=3)

            self.preview_label = ttk.Label(right_frame, text="Preview")
            self.preview_label.pack(side=tk.TOP, anchor="w", padx=5, pady=5)

            self.preview_text = tk.Text(right_frame, wrap="word")
            self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ------------------------------------------------------------------
        # Folder & tree handling
        # ------------------------------------------------------------------
        def select_folder(self):
            folder = filedialog.askdirectory(title="Selecione a pasta raiz com arquivos tj!/tje/tjz")
            if not folder:
                return

            self.current_root = Path(folder)
            self.lbl_root.config(text=str(self.current_root))

            # limpa tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            # adiciona root
            root_id = self.tree.insert("", "end", text=str(self.current_root), open=True, values=[str(self.current_root)])

            self._populate_tree(self.current_root, root_id)

        def _populate_tree(self, directory: Path, parent_id: str):
            # primeiro subpastas, depois arquivos
            try:
                entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except OSError:
                return

            for entry in entries:
                node_id = self.tree.insert(parent_id, "end", text=entry.name, values=[str(entry)], open=False)
                if entry.is_dir():
                    # placeholder child para exibir "expand"
                    self.tree.insert(node_id, "end", text="...", values=["__placeholder__"])

            # bind para quando expandir diretório, carregar filhos reais
            self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)

        def on_tree_open(self, event):
            item_id = self.tree.focus()
            if not item_id:
                return
            children = self.tree.get_children(item_id)
            # se primeiro filho é placeholder, removemos e populamos de verdade
            if len(children) == 1:
                child_values = self.tree.item(children[0], "values")
                if child_values and child_values[0] == "__placeholder__":
                    self.tree.delete(children[0])
                    path_str = self.tree.item(item_id, "values")[0]
                    path = Path(path_str)
                    if path.is_dir():
                        self._populate_tree(path, item_id)

        # ------------------------------------------------------------------
        # Preview
        # ------------------------------------------------------------------
        def on_tree_select(self, event):
            item_id = self.tree.focus()
            if not item_id:
                return

            values = self.tree.item(item_id, "values")
            if not values:
                return

            path = Path(values[0])
            if path.is_dir():
                return

            self.show_preview(path)

        def show_preview(self, path: Path):
            self.preview_text.delete("1.0", tk.END)
            self.image_cache = None

            self.preview_label.config(text=f"Preview: {path.name}")

            # tenta abrir como imagem, se PIL disponível
            if PIL_AVAILABLE and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
                try:
                    img = Image.open(path)
                    img.thumbnail((600, 400))
                    self.image_cache = ImageTk.PhotoImage(img)
                    # Limpa Text e coloca uma pequena instrução + imagem
                    self.preview_text.insert(tk.END, "[Imagem carregada abaixo]")
                    self.preview_text.image_create(tk.END, image=self.image_cache)
                    return
                except Exception as e:
                    self.preview_text.insert(tk.END, f"[Falha ao carregar imagem: {e}]")

            # senão, tenta abrir como texto
            try:
                with path.open("rb") as f:
                    raw = f.read()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")
                self.preview_text.insert(tk.END, text)
            except Exception as e:
                self.preview_text.insert(tk.END, f"Erro ao abrir arquivo: {e}")

        # ------------------------------------------------------------------
        # Decode single
        # ------------------------------------------------------------------
        def decode_selected_file(self):
            item_id = self.tree.focus()
            if not item_id:
                messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
                return

            values = self.tree.item(item_id, "values")
            if not values:
                messagebox.showwarning("Aviso", "Seleção inválida.")
                return

            path = Path(values[0])
            if path.is_dir():
                messagebox.showwarning("Aviso", "Selecione um arquivo, não uma pasta.")
                return

            tj_type = detect_tj_type(path)
            if tj_type == "unknown":
                messagebox.showwarning("Aviso", "Arquivo não parece ser tj!/tje/tjz.")
                return

            # alerta sobre JSON e TJZ
            if tj_type == "tj_bang" and path.suffix.lower() == ".json":
                messagebox.showinfo(
                    "Aviso",
                    "Decodificação de JSON (tj!) ainda não está 100% verificada."
                    "O resultado pode não ser legível."
                )
            if tj_type == "tjz":
                messagebox.showinfo(
                    "Aviso",
                    "Decodificação de arquivos TJZ é experimental."
                    "Pode falhar ou gerar dados inválidos."
                )

            try:
                out_path = decode_single_file(path)
                messagebox.showinfo("Sucesso", f"Arquivo decodificado salvo em:{out_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao decodificar:{e}")

        # ------------------------------------------------------------------
        # Decode All
        # ------------------------------------------------------------------
        def open_decode_all_dialog(self):
            if not self.current_root:
                messagebox.showwarning("Aviso", "Selecione uma pasta primeiro.")
                return

            dialog = DecodeAllDialog(self, self.current_root)


class DecodeAllDialog(tk.Toplevel):
        def __init__(self, master: DecoderApp, root_folder: Path):
            super().__init__(master)
            self.title("Decode All")
            self.geometry("600x400")
            self.root_folder = root_folder

            self.var_tj_bang = tk.BooleanVar(value=True)
            self.var_tje = tk.BooleanVar(value=True)
            self.var_tjz = tk.BooleanVar(value=False)

            self._build_ui()

        def _build_ui(self):
            frm_opts = ttk.Frame(self)
            frm_opts.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

            ttk.Label(frm_opts, text=f"Pasta raiz: {self.root_folder}").pack(anchor="w")

            ttk.Checkbutton(frm_opts, text="Decodificar tj! (JSON ainda pode ficar ilegível)",
                            variable=self.var_tj_bang).pack(anchor="w")
            ttk.Checkbutton(frm_opts, text="Decodificar tje (imagens, PNG/JPG)",
                            variable=self.var_tje).pack(anchor="w")
            ttk.Checkbutton(frm_opts, text="Decodificar tjz (experimental)",
                            variable=self.var_tjz).pack(anchor="w")

            lbl_warn = ttk.Label(
                frm_opts,
                text=(
                    "Aviso:"
                    "- JSON (tj!) ainda não foi totalmente analisado, saída pode parecer corrompida."
                    "- TJZ não foi testado, pode falhar."
                ),
                foreground="red",
                justify="left"
            )
            lbl_warn.pack(anchor="w", pady=(5, 5))

            btn_run = ttk.Button(frm_opts, text="Iniciar Decode All", command=self.run_decode_all)
            btn_run.pack(anchor="w", pady=(5, 5))

            # Log
            frm_log = ttk.Frame(self)
            frm_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            self.txt_log = tk.Text(frm_log, wrap="word")
            self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            scroll_y = ttk.Scrollbar(frm_log, orient=tk.VERTICAL, command=self.txt_log.yview)
            self.txt_log.configure(yscrollcommand=scroll_y.set)
            scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        def log(self, msg: str):
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
            self.update_idletasks()

        def run_decode_all(self):
            from decoder.decode_logic import iter_tj_files, decode_single_file

            include_tj_bang = self.var_tj_bang.get()
            include_tje = self.var_tje.get()
            include_tjz = self.var_tjz.get()

            self.log(f"Iniciando Decode All em: {self.root_folder}")
            self.log(f"  tj!: {include_tj_bang}, tje: {include_tje}, tjz: {include_tjz}")
            self.log("--------------------------------------------------------")

            count_ok = 0
            count_err = 0

            for path, t in iter_tj_files(
                self.root_folder,
                include_tj_bang=include_tj_bang,
                include_tje=include_tje,
                include_tjz=include_tjz,
            ):
                try:
                    out_path = decode_single_file(path)
                    self.log(f"[OK] ({t}) {path} -> {out_path}")
                    count_ok += 1
                except Exception as e:
                    self.log(f"[ERRO] ({t}) {path}: {e}")
                    count_err += 1

            self.log("--------------------------------------------------------")
            self.log(f"Concluído. Sucesso: {count_ok}, Erros: {count_err}")


def main():
    app = DecoderApp()
    app.mainloop()
