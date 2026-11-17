"""Batch run used for the written answer: applies all six noises to the test
image, restores each one, and writes result images plus PSNR tables.

    python make_results.py      ->  ../results/
"""
from pathlib import Path

import numpy as np
from PIL import Image

from denoise_filters import AUTO, BIAS_MODES, METHODS, denoise, psnr, ssim
from noise_models import MODELS

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"
CROP = (slice(250, 470), slice(330, 550))  # face / bow tie, shown at 2x
SEED = 0


def u8(a):
    return Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8))


def tag(model):
    return model.name.split()[0].lower()


def strip(clean, noisy, restored, path):
    """original | noisy | restored for a zoomed crop."""
    tiles = [u8(x[CROP]).resize((440, 440), Image.NEAREST) for x in (clean, noisy, restored)]
    gap = 8
    canvas = Image.new("RGB", (3 * 440 + 2 * gap, 440), "white")
    for i, t in enumerate(tiles):
        canvas.paste(t, (i * (440 + gap), 0))
    canvas.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    clean = np.asarray(Image.open(HERE.parent / "images" / "input.png").convert("RGB"), dtype=np.float64)
    rows, table, ablation = [], [], []
    for model in MODELS:
        p = model.defaults()
        noisy, _ = model.apply(clean, p, np.random.default_rng(SEED))
        noisy = np.rint(noisy)
        restored, used = denoise(noisy, model, p)
        restored = np.rint(restored)
        u8(noisy).save(OUT / f"noisy_{tag(model)}.png")
        u8(restored).save(OUT / f"restored_{tag(model)}.png")
        strip(clean, noisy, restored, OUT / f"crop_{tag(model)}.png")
        rows.append((model.name, p, used, psnr(clean, noisy), ssim(clean, noisy),
                     psnr(clean, restored), ssim(clean, restored)))

        line = [model.name]
        for meth in METHODS[1:]:
            k = 3 if meth in ("Median", "Geometric mean", "Contraharmonic") else 5
            f, _ = denoise(noisy, model, p, meth, k=k)
            line.append(psnr(clean, np.rint(f)))
        table.append(line)

        if model.additive:
            ab = [model.name]
            for b in BIAS_MODES:
                f, _ = denoise(noisy, model, p, AUTO[model.name], bias=b)
                ab.append(psnr(clean, np.rint(f)))
            ablation.append(ab)

    md = ["## Auto (filter chosen from the noise type)", "",
          "| noise | params | filter | PSNR noisy | SSIM noisy | PSNR restored | SSIM restored |",
          "|---|---|---|---|---|---|---|"]
    for n, p, used, a, b, c, d in rows:
        ps = ", ".join(f"{k}={v:g}" for k, v in p.items())
        md.append(f"| {n} | {ps} | {used} | {a:.2f} | {b:.3f} | {c:.2f} | {d:.3f} |")
    md += ["", "## PSNR (dB) of every filter", "",
           "| noise | " + " | ".join(METHODS[1:]) + " |", "|---" * len(METHODS) + "|"]
    for line in table:
        best = max(line[1:])
        md.append(f"| {line[0]} | " + " | ".join(f"**{v:.2f}**" if v == best else f"{v:.2f}" for v in line[1:]) + " |")
    md += ["", "## Bias correction, adaptive local filter", "",
           "| noise | " + " | ".join(BIAS_MODES) + " |", "|---" * (len(BIAS_MODES) + 1) + "|"]
    for line in ablation:
        md.append(f"| {line[0]} | " + " | ".join(f"{v:.2f}" for v in line[1:]) + " |")
    (OUT / "metrics.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
