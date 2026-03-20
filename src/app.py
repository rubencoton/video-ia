from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from video_processor import process_video


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "output"


class VideoIAApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("VIDEO IA - App Local")
        self.root.geometry("760x620")
        self.root.minsize(760, 620)

        self.video_path = tk.StringVar()
        self.image_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Listo para generar.")

        self._build_ui()

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, padx=18, pady=18)
        main.pack(fill="both", expand=True)

        title = tk.Label(
            main,
            text="VIDEO IA LOCAL",
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        )
        title.pack(fill="x", pady=(0, 12))

        subtitle = tk.Label(
            main,
            text=(
                "Sube tu video, tu imagen y escribe un prompt.\n"
                "La app genera un video en la carpeta output."
            ),
            font=("Segoe UI", 11),
            justify="left",
            anchor="w",
        )
        subtitle.pack(fill="x", pady=(0, 16))

        self._file_picker(
            parent=main,
            label="1) Video de entrada",
            var=self.video_path,
            button_text="Elegir video",
            filetypes=[("Videos", "*.mp4;*.mov;*.mkv;*.avi"), ("Todos", "*.*")],
        )

        self._file_picker(
            parent=main,
            label="2) Imagen de referencia",
            var=self.image_path,
            button_text="Elegir imagen",
            filetypes=[("Imagenes", "*.png;*.jpg;*.jpeg;*.webp"), ("Todos", "*.*")],
        )

        prompt_label = tk.Label(
            main,
            text="3) Prompt (que quieres conseguir)",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        prompt_label.pack(fill="x", pady=(12, 6))

        self.prompt_box = tk.Text(main, height=8, font=("Segoe UI", 11), wrap="word")
        self.prompt_box.pack(fill="x")

        hint = tk.Label(
            main,
            text=(
                "Ejemplos de palabras que detecta: blanco y negro, sepia, mas brillo, "
                "contraste, cinematic."
            ),
            font=("Segoe UI", 10),
            fg="#444444",
            justify="left",
            anchor="w",
        )
        hint.pack(fill="x", pady=(6, 14))

        actions = tk.Frame(main)
        actions.pack(fill="x")

        self.generate_btn = tk.Button(
            actions,
            text="Generar video",
            font=("Segoe UI", 11, "bold"),
            bg="#1f6feb",
            fg="white",
            padx=14,
            pady=8,
            command=self._on_generate_click,
        )
        self.generate_btn.pack(side="left")

        open_output_btn = tk.Button(
            actions,
            text="Abrir carpeta output",
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
            command=self._open_output_folder,
        )
        open_output_btn.pack(side="left", padx=(10, 0))

        status_title = tk.Label(
            main,
            text="Estado",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        status_title.pack(fill="x", pady=(16, 4))

        status_box = tk.Label(
            main,
            textvariable=self.status_text,
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            bg="#f3f6fb",
            padx=10,
            pady=10,
        )
        status_box.pack(fill="x")

    def _file_picker(
        self,
        parent: tk.Widget,
        label: str,
        var: tk.StringVar,
        button_text: str,
        filetypes: list[tuple[str, str]],
    ) -> None:
        title = tk.Label(parent, text=label, font=("Segoe UI", 11, "bold"), anchor="w")
        title.pack(fill="x", pady=(0, 4))

        row = tk.Frame(parent)
        row.pack(fill="x", pady=(0, 10))

        entry = tk.Entry(row, textvariable=var, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, ipady=4)

        btn = tk.Button(
            row,
            text=button_text,
            font=("Segoe UI", 10),
            padx=10,
            command=lambda: self._browse_file(var, filetypes),
        )
        btn.pack(side="left", padx=(8, 0))

    def _browse_file(self, var: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        selected = filedialog.askopenfilename(filetypes=filetypes)
        if selected:
            var.set(selected)

    def _open_output_folder(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta output.\n{exc}")

    def _on_generate_click(self) -> None:
        video = self.video_path.get().strip()
        image = self.image_path.get().strip()
        prompt = self.prompt_box.get("1.0", "end").strip()

        if not video:
            messagebox.showwarning("Falta video", "Selecciona un video antes de continuar.")
            return
        if not image:
            messagebox.showwarning("Falta imagen", "Selecciona una imagen antes de continuar.")
            return
        if not prompt:
            messagebox.showwarning("Falta prompt", "Escribe un prompt antes de continuar.")
            return

        self.generate_btn.config(state="disabled")
        self.status_text.set("Procesando... puede tardar unos segundos.")

        worker = threading.Thread(
            target=self._run_generation,
            args=(video, image, prompt),
            daemon=True,
        )
        worker.start()

    def _run_generation(self, video: str, image: str, prompt: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        result = process_video(video, image, prompt, str(OUTPUT_DIR))
        self.root.after(0, lambda: self._finish_generation(result.ok, result.message, result.output_video))

    def _finish_generation(self, ok: bool, msg: str, output_video: Path) -> None:
        self.generate_btn.config(state="normal")

        final_message = f"{msg}\n\nSalida:\n{output_video}"
        self.status_text.set(final_message)

        if ok:
            messagebox.showinfo("Listo", final_message)
        else:
            messagebox.showwarning("Terminado con aviso", final_message)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    VideoIAApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
