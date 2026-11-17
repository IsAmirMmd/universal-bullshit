"""Noise / denoise GUI (Computer Vision, HW1).

    python noise_gui.py [image]                     # interactive
    python noise_gui.py --noise Rayleigh --screenshot out.png   # render once, save window, quit

Pick one of the six noise models, set its parameters, add it to the image, then
restore the image.  Because the app knows which noise was added (type and
parameters), "Auto" picks the matching filter and feeds it the noise statistics.
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
from PIL import Image, ImageGrab, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from denoise_filters import AUTO, BIAS_MODES, METHODS, denoise, psnr, ssim
from noise_models import BY_NAME, MODELS

HERE = Path(__file__).resolve().parent
DEFAULT_IMAGE = HERE.parent / "images" / "input.png"
VIEW = 330  # displayed image size (px); enlarged to fit the screen in App.__init__


class App(tk.Tk):
    def __init__(self, image_path: Path):
        super().__init__()
        self.title("Noise models & restoration — Computer Vision HW1")
        self.configure(padx=8, pady=8)
        self.rng_seed = tk.IntVar(value=0)
        self.noise_name = tk.StringVar(value=MODELS[0].name)
        self.method = tk.StringVar(value=METHODS[0])
        self.bias = tk.StringVar(value=BIAS_MODES[0])
        self.ksize = tk.IntVar(value=5)
        self.param_vars: dict[str, tk.Variable] = {}
        self.clean = self.noisy = self.restored = self.eta = None
        self._photos = {}
        global VIEW
        # three image panels next to a ~480 px control column
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        VIEW = int(max(240, min(480, (sw - 620) // 3, sh - 420)))
        # a Label without an image measures width/height in *characters*, so an
        # empty panel would be hundreds of characters wide; keep a blank image in it
        self._blank = tk.PhotoImage(width=VIEW, height=VIEW)

        self._build()
        self.load_image(image_path)

    # ------------------------------------------------------------------ UI
    def _build(self):
        ctl = ttk.Frame(self)
        ctl.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        view = ttk.Frame(self)
        view.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)

        # image file
        f = ttk.LabelFrame(ctl, text="Image", padding=6)
        f.pack(fill="x")
        ttk.Button(f, text="Open image…", command=self.ask_image).pack(fill="x")
        ttk.Button(f, text="Save noisy + restored…", command=self.save).pack(fill="x", pady=(4, 0))

        # noise
        f = ttk.LabelFrame(ctl, text="1. Noise", padding=6)
        f.pack(fill="x", pady=6)
        cb = ttk.Combobox(f, textvariable=self.noise_name, values=[m.name for m in MODELS],
                          state="readonly", width=28)
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_noise_change())
        self.formula = ttk.Label(f, foreground="#555", wraplength=260)
        self.formula.pack(fill="x", pady=(4, 2))
        self.param_box = ttk.Frame(f)
        self.param_box.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, text="random seed").pack(side="left")
        ttk.Spinbox(row, from_=0, to=9999, textvariable=self.rng_seed, width=7).pack(side="right")
        ttk.Button(f, text="Add noise", command=self.add_noise).pack(fill="x", pady=(6, 0))

        # restoration
        f = ttk.LabelFrame(ctl, text="2. Denoise (noise type is known)", padding=6)
        f.pack(fill="x")
        ttk.Label(f, text="filter").pack(anchor="w")
        ttk.Combobox(f, textvariable=self.method, values=METHODS, state="readonly", width=28).pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="window size k").pack(side="left")
        ttk.Spinbox(row, values=(3, 5, 7, 9, 11), textvariable=self.ksize, width=5, state="readonly").pack(side="right")
        ttk.Label(f, text="bias correction (additive noise)").pack(anchor="w")
        ttk.Combobox(f, textvariable=self.bias, values=BIAS_MODES, state="readonly", width=28).pack(fill="x")
        ttk.Button(f, text="Denoise", command=self.run_denoise).pack(fill="x", pady=(6, 0))
        ttk.Button(f, text="Add noise + denoise", command=self.add_and_denoise).pack(fill="x", pady=(4, 0))

        # metrics
        f = ttk.LabelFrame(ctl, text="Result", padding=6)
        f.pack(fill="x", pady=6)
        self.metrics = ttk.Label(f, text="—", font=("Consolas", 10), justify="left")
        self.metrics.pack(anchor="w")

        # images
        imgs = ttk.Frame(view)
        imgs.pack(fill="x")
        self.panels = {}
        for i, key in enumerate(("Original", "Noisy", "Restored")):
            cell = ttk.Frame(imgs)
            cell.grid(row=0, column=i, padx=4)
            lab = ttk.Label(cell, text=key, font=("Segoe UI", 10, "bold"))
            lab.pack()
            pan = tk.Label(cell, image=self._blank, width=VIEW, height=VIEW, bg="#ddd")
            pan.pack()
            self.panels[key] = (lab, pan)

        # noise PDF vs histogram
        self.fig = Figure(figsize=(8, 2.5), dpi=96)
        self.ax_pdf = self.fig.add_subplot(1, 2, 1)
        self.ax_hist = self.fig.add_subplot(1, 2, 2)
        self.fig.subplots_adjust(left=0.06, right=0.98, bottom=0.2, top=0.86, wspace=0.22)
        self.canvas = FigureCanvasTkAgg(self.fig, master=view)
        self.canvas.get_tk_widget().pack(fill="x", pady=(8, 0))
        self._fit_chart()
        # when the window first appears on a scaled display (e.g. 125 %) matplotlib
        # multiplies the chart size by that factor; set the size again afterwards
        self.canvas.get_tk_widget().bind("<Map>", lambda e: self.after(100, self._fit_chart), add="+")
        self.after(300, self._fit_chart)

        self.on_noise_change()

    def _fit_chart(self):
        """Chart as wide as the image row, in real pixels."""
        w, h = 3 * (VIEW + 12), int(max(240, 0.6 * VIEW))
        self.canvas.get_tk_widget().configure(width=w, height=h)
        self.fig.set_size_inches(w / self.fig.dpi, h / self.fig.dpi, forward=False)
        self.canvas.draw_idle()

    def on_noise_change(self):
        model = BY_NAME[self.noise_name.get()]
        self.formula.configure(text=model.formula)
        for w in self.param_box.winfo_children():
            w.destroy()
        self.param_vars = {}
        for prm in model.params:
            row = ttk.Frame(self.param_box)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=prm.label, width=16).pack(side="left")
            var = tk.DoubleVar(value=prm.default)
            ent = ttk.Entry(row, width=7, textvariable=var)
            ent.pack(side="right")
            sc = ttk.Scale(row, from_=prm.lo, to=prm.hi, variable=var,
                           command=lambda v, var=var, prm=prm: var.set(self._snap(float(v), prm)))
            sc.pack(side="right", fill="x", expand=True, padx=4)
            self.param_vars[prm.key] = var
        self.method_hint()

    def method_hint(self):
        model = BY_NAME[self.noise_name.get()]
        self.formula.configure(text=f"{model.formula}\nAuto filter → {AUTO[model.name]}")

    @staticmethod
    def _snap(v, prm):
        v = round(v / prm.step) * prm.step
        return int(round(v)) if prm.integer else round(v, 4)

    def params(self) -> dict:
        model = BY_NAME[self.noise_name.get()]
        out = {}
        for prm in model.params:
            try:
                v = float(self.param_vars[prm.key].get())
            except (tk.TclError, ValueError):
                v = prm.default
            v = min(max(v, prm.lo), prm.hi)
            out[prm.key] = int(round(v)) if prm.integer else v
        return out

    # ------------------------------------------------------------- actions
    def ask_image(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tif"), ("All", "*.*")])
        if p:
            self.load_image(Path(p))

    def load_image(self, path: Path):
        im = Image.open(path).convert("RGB")
        self.clean = np.asarray(im, dtype=np.float64)
        self.noisy = self.restored = self.eta = None
        self.show("Original", self.clean)
        self.show("Noisy", None)
        self.show("Restored", None)
        self.metrics.configure(text=f"{path.name}\n{im.width}×{im.height}")

    def add_noise(self):
        if self.clean is None:
            return
        model = BY_NAME[self.noise_name.get()]
        p = self.params()
        rng = np.random.default_rng(int(self.rng_seed.get()))
        noisy, eta = model.apply(self.clean, p, rng)
        self.noisy = np.rint(noisy)  # what an 8-bit file would store
        self.eta = eta
        self.restored = None
        self.noise_used = (model, p)
        self.show("Noisy", self.noisy, f"Noisy — {model.name}")
        self.show("Restored", None)
        self.plot_noise(model, p, eta)
        self.update_metrics()

    def run_denoise(self):
        if self.noisy is None:
            messagebox.showinfo("Denoise", "Add noise first.")
            return
        model, p = self.noise_used  # the noise we know was applied
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            out, used = denoise(self.noisy, model, p, self.method.get(),
                                k=int(self.ksize.get()), bias=self.bias.get())
        finally:
            self.configure(cursor="")
        self.restored = np.rint(out)
        self.show("Restored", self.restored, f"Restored — {used}")
        self.update_metrics()

    def add_and_denoise(self):
        self.add_noise()
        self.run_denoise()

    def save(self):
        if self.noisy is None:
            return
        d = filedialog.askdirectory()
        if not d:
            return
        tag = self.noise_used[0].name.split()[0].lower()
        Image.fromarray(self.noisy.astype(np.uint8)).save(Path(d) / f"noisy_{tag}.png")
        if self.restored is not None:
            Image.fromarray(self.restored.astype(np.uint8)).save(Path(d) / f"restored_{tag}.png")

    # ------------------------------------------------------------- display
    def show(self, key, arr, title=None):
        lab, pan = self.panels[key]
        lab.configure(text=title or key)
        if arr is None:
            pan.configure(image=self._blank)
            return
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        im.thumbnail((VIEW, VIEW), Image.LANCZOS)
        ph = ImageTk.PhotoImage(im)
        self._photos[key] = ph
        pan.configure(image=ph)

    def update_metrics(self):
        lines = []
        if self.noisy is not None:
            lines.append(f"noisy    PSNR {psnr(self.clean, self.noisy):6.2f} dB  SSIM {ssim(self.clean, self.noisy):.3f}")
        if self.restored is not None:
            lines.append(f"restored PSNR {psnr(self.clean, self.restored):6.2f} dB  SSIM {ssim(self.clean, self.restored):.3f}")
        self.metrics.configure(text="\n".join(lines) or "—")

    def plot_noise(self, model, p, eta):
        a1, a2 = self.ax_pdf, self.ax_hist
        a1.clear(); a2.clear()
        if model.additive:
            lo, hi = model.support(p)
            z = np.linspace(lo, hi, 600)
            a1.plot(z, model.pdf(z, p), color="#c0392b", lw=2)
            a1.set_title(f"{model.name}: theoretical p(z)", fontsize=9)
            a2.hist(eta.ravel()[::7], bins=120, range=(lo, hi), density=True, color="#5d8aa8", alpha=0.85,
                    label="added noise samples")
            a2.plot(z, model.pdf(z, p), color="#c0392b", lw=1.5, label="p(z)")
            m, v = model.mean_var(p)
            a2.set_title(f"histogram of added noise  (mean {eta.mean():.1f} / theory {m:.1f}, "
                         f"std {eta.std():.1f} / {np.sqrt(v):.1f})", fontsize=9)
            a2.legend(fontsize=8)
        else:
            a1.bar([0, 255], [p["pa"], p["pb"]], width=8, color="#c0392b")
            a1.set_xlim(-20, 275)
            a1.set_xticks([0, 255], ["a (pepper)", "b (salt)"])
            a1.set_title("Impulse: theoretical P(z=a)=Pa, P(z=b)=Pb", fontsize=9)
            gray = self.noisy.mean(2)
            a2.hist(gray.ravel(), bins=256, range=(0, 255), density=True, color="#5d8aa8")
            a2.set_yscale("log")
            a2.set_title("histogram of noisy image (log scale): spikes at a=0 and b=255", fontsize=9)
        for a in (a1, a2):
            a.tick_params(labelsize=8)
        self.canvas.draw_idle()

    def screenshot(self, path: Path):
        self.attributes("-topmost", True)  # make sure nothing covers the window
        self.lift()
        self.update()
        self.after(300)
        self.update()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=str(DEFAULT_IMAGE))
    ap.add_argument("--noise", help="start with this noise model (name prefix)")
    ap.add_argument("--screenshot", help="add noise, denoise, save a window screenshot and exit")
    args = ap.parse_args()

    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = App(Path(args.image))
    if args.noise:
        name = next(m.name for m in MODELS if m.name.lower().startswith(args.noise.lower()))
        app.noise_name.set(name)
        app.on_noise_change()
    if args.screenshot:
        def shoot():
            app.add_and_denoise()
            app.after(800, lambda: (app.screenshot(Path(args.screenshot)), app.destroy()))
        app.after(500, shoot)
    app.mainloop()


if __name__ == "__main__":
    main()
