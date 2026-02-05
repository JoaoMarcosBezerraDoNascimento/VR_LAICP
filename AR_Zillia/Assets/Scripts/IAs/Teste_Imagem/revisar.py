import os
import re
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json

# ----------------------------
# CONFIG PADRÃO (pastas)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "imagens")
RESULTS_DIR = os.path.join(BASE_DIR, "saida_txt")
LOG_PATH = os.path.join(BASE_DIR, "review_log.csv")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

FIELDS = [
    "Resto_Solda_GoldFinger",
    "Arranhoes_Placa_Trilhas",
    "Residuos_Cola_Sujeira_Manchas",
    "Falta_Componentes",
    "Etiqueta_Zilia_Smart_Falha_Leitura",
]

GABARITOS_DIR = os.path.join(BASE_DIR, "gabaritos")

RE_DURACAO = re.compile(r"^\s*#\s*duracao_ms\s*:\s*(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
RE_MODELO  = re.compile(r"^\s*#\s*modelo\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

def ensure_dir(dirpath: str):
    os.makedirs(dirpath, exist_ok=True)

def extract_duration_ms(txt_content: str):
    m = RE_DURACAO.search(txt_content)
    return int(m.group(1)) if m else None

def extract_model(txt_content: str):
    m = RE_MODELO.search(txt_content)
    return m.group(1).strip() if m else None

def extract_first_json_object(txt_content: str):
    first = txt_content.find("{")
    last = txt_content.rfind("}")
    if first >= 0 and last > first:
        chunk = txt_content[first:last+1].strip()
        try:
            return json.loads(chunk)
        except:
            return None
    return None

def normalize_sim_nao(v):
    if v is None:
        return None
    v = str(v).strip().upper()
    if v in ("SIM", "YES", "Y", "TRUE", "1"):
        return "SIM"
    if v in ("NAO", "NÃO", "NO", "N", "FALSE", "0"):
        return "NAO"
    return None

def stem_no_ext(filename: str) -> str:
    return os.path.splitext(os.path.basename(filename))[0]

# Regex para capturar linha "# arquivo: nome.ext"
RE_ARQUIVO = re.compile(r"^\s*#\s*arquivo\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

def list_files_sorted(folder, ext):
    if not os.path.isdir(folder):
        return []
    files = []
    for f in os.listdir(folder):
        if f.lower().endswith(ext):
            files.append(os.path.join(folder, f))
    files.sort(key=lambda p: os.path.basename(p).lower())
    return files


def index_images(images_dir):
    """
    Cria um índice: nome_arquivo (case-insensitive) -> caminho absoluto
    Também cria um índice por basename sem extensão.
    """
    by_name = {}
    by_stem = {}

    if not os.path.isdir(images_dir):
        return by_name, by_stem

    for root, _, files in os.walk(images_dir):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            full = os.path.join(root, fn)
            key = fn.lower()
            stem = os.path.splitext(fn)[0].lower()
            by_name[key] = full
            # se repetir stem, mantém o primeiro encontrado
            by_stem.setdefault(stem, full)

    return by_name, by_stem


def read_text_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_image_name_from_txt(txt_content):
    """
    Tenta pegar o nome da imagem a partir da linha '# arquivo: ...'
    Retorna string ou None.
    """
    m = RE_ARQUIVO.search(txt_content)
    if not m:
        return None
    # pode vir com caminho, pega só o basename
    raw = m.group(1).strip()
    return os.path.basename(raw)


def find_image_path(img_name, img_index_by_name, img_index_by_stem):
    """
    Resolve o caminho da imagem:
    1) match exato nome.ext
    2) match por stem
    """
    if not img_name:
        return None

    key = img_name.lower()
    if key in img_index_by_name:
        return img_index_by_name[key]

    stem = os.path.splitext(img_name)[0].lower()
    return img_index_by_stem.get(stem)


class ReviewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Revisão de Resultados - Imagem + TXT")
        self.geometry("1200x750")

        # Índices
        self.txt_files = list_files_sorted(RESULTS_DIR, ".txt")
        self.img_by_name, self.img_by_stem = index_images(IMAGES_DIR)

        if not self.txt_files:
            messagebox.showerror(
                "Nenhum resultado encontrado",
                f"Não achei arquivos .txt em:\n{RESULTS_DIR}\n\n"
                f"Crie a pasta e rode o analisador primeiro."
            )
            self.destroy()
            return

        # Estado
        self.i = 0
        self.current_photo = None

        # UI
        self._build_ui()
        self._load_current()

        # Teclas
        self.bind("<Left>", lambda e: self.prev_item())
        self.bind("<Right>", lambda e: self.next_item())
        self.bind("a", lambda e: self.approve())
        self.bind("r", lambda e: self.reject())

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self, padding=8)
        top.pack(side="top", fill="x")

        self.status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.status_var).pack(side="left")

        ttk.Button(top, text="Anterior (←)", command=self.prev_item).pack(side="right", padx=4)
        ttk.Button(top, text="Próximo (→)", command=self.next_item).pack(side="right", padx=4)
        ttk.Button(top, text="Aprovar (A)", command=self.approve).pack(side="right", padx=4)
        ttk.Button(top, text="Reprovar (R)", command=self.reject).pack(side="right", padx=4)

        # Main split
        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(side="top", fill="both", expand=True)

        # Left: image
        left = ttk.Frame(main, padding=8)
        main.add(left, weight=1)

        self.image_label = ttk.Label(left, text="(imagem aqui)", anchor="center")
        self.image_label.pack(fill="both", expand=True)

        # Right: text
        right = ttk.Frame(main, padding=8)
        main.add(right, weight=1)

        self.txt_title_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.txt_title_var, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 6))

        self.text_box = tk.Text(right, wrap="word")
        self.text_box.pack(fill="both", expand=True)
        self.text_box.configure(state="disabled")

        # Bottom hint
        bottom = ttk.Frame(self, padding=6)
        bottom.pack(side="bottom", fill="x")
        ttk.Label(
            bottom,
            text="Atalhos: ←/→ navegar | A aprovar | R reprovar",
        ).pack(side="left")

    def _load_current(self):
        txt_path = self.txt_files[self.i]
        txt_name = os.path.basename(txt_path)

        content = read_text_file(txt_path)
        img_name = extract_image_name_from_txt(content)
        img_path = find_image_path(img_name, self.img_by_name, self.img_by_stem)

        # Atualiza status
        img_disp = img_name if img_name else "(não encontrado no TXT: # arquivo: ...)"
        img_path_disp = img_path if img_path else "(imagem não encontrada na pasta imagens/)"
        self.status_var.set(
            f"[{self.i+1}/{len(self.txt_files)}] TXT: {txt_name} | IMG: {img_disp} | PATH: {img_path_disp}"
        )
        self.txt_title_var.set(f"Resultado: {txt_name}")

        # Atualiza texto
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)
        self.text_box.configure(state="disabled")

        # Atualiza imagem
        self._show_image(img_path)

    def _show_image(self, img_path):
        if not img_path or not os.path.exists(img_path):
            self.image_label.configure(text="Imagem não encontrada.\nVerifique a linha '# arquivo:' no TXT e a pasta imagens/.",
                                      image="")
            self.current_photo = None
            return

        try:
            img = Image.open(img_path)
            img = img.convert("RGB")

            # Redimensiona para caber no painel (mantendo proporção)
            panel_w = max(self.image_label.winfo_width(), 600)
            panel_h = max(self.image_label.winfo_height(), 600)

            img.thumbnail((panel_w, panel_h), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.current_photo = photo  # manter referência
            self.image_label.configure(image=photo, text="")
        except Exception as e:
            self.image_label.configure(text=f"Falha ao abrir imagem:\n{e}", image="")
            self.current_photo = None

    def prev_item(self):
        if self.i > 0:
            self.i -= 1
            self._load_current()

    def next_item(self):
        if self.i < len(self.txt_files) - 1:
            self.i += 1
            self._load_current()

    def _write_log(self, decision):
        txt_path = self.txt_files[self.i]
        txt_name = os.path.basename(txt_path)
        content = read_text_file(txt_path)
        img_name = extract_image_name_from_txt(content) or ""
        img_path = find_image_path(img_name, self.img_by_name, self.img_by_stem) or ""

        file_exists = os.path.exists(LOG_PATH)
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["decision", "txt_file", "image_name_in_txt", "image_path"])
            w.writerow([decision, txt_name, img_name, img_path])

    def approve(self):
        self._write_log("APPROVE")
        self.next_item()

    def reject(self):
        self._write_log("REJECT")
        self.next_item()


if __name__ == "__main__":
    # Checagens rápidas
    if not os.path.isdir(IMAGES_DIR):
        print(f"[AVISO] Pasta imagens/ não existe em: {IMAGES_DIR}")
    if not os.path.isdir(RESULTS_DIR):
        print(f"[AVISO] Pasta saida_txt/ não existe em: {RESULTS_DIR}")

    app = ReviewApp()
    app.mainloop()
