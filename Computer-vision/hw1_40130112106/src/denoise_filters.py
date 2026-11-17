"""Restoration filters from Gonzalez & Woods ch. 5 (+ non-local means) and the
"known noise" pipeline that picks a filter and its parameters from the noise
model.  Images are float64 HxWx3 arrays in [0, 255].
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage as ndi

from noise_models import L, NoiseModel, clip_tables


def _per_channel(fn, img, *a, **k):
    if img.ndim == 2:
        return fn(img, *a, **k)
    return np.dstack([fn(img[..., c], *a, **k) for c in range(img.shape[2])])


def _box(x, k):
    return ndi.uniform_filter(x, size=(k, k) + (1,) * (x.ndim - 2), mode="reflect")


# --- order 1: mean filters -------------------------------------------------
def arithmetic_mean(g, k=5):
    return _box(g, k)


def geometric_mean(g, k=3):
    return np.exp(_box(np.log(g + 1.0), k)) - 1.0


def contraharmonic(g, k=3, Q=1.5):
    """Q > 0 removes pepper, Q < 0 removes salt."""
    g = g + 1.0
    return _box(g ** (Q + 1), k) / np.maximum(_box(g ** Q, k), 1e-12) - 1.0


# --- order statistics ------------------------------------------------------
def median(g, k=3):
    return _per_channel(ndi.median_filter, g, size=k, mode="reflect")


def alpha_trimmed(g, k=5, d=6):
    """Drop d/2 lowest and d/2 highest of the k*k values, average the rest."""
    def one(ch):
        win = np.lib.stride_tricks.sliding_window_view(np.pad(ch, k // 2, mode="reflect"), (k, k))
        win = np.sort(win.reshape(*ch.shape, k * k), axis=-1)
        return win[..., d // 2: k * k - d // 2].mean(-1)
    return _per_channel(one, g)


# --- adaptive filters ------------------------------------------------------
def adaptive_local(g, noise_var, k=7):
    """f = g - (σ_η² / σ_L²)(g - m_L), ratio capped at 1.  noise_var may be an array."""
    m = _box(g, k)
    var_l = np.maximum(_box(g * g, k) - m * m, 1e-6)
    ratio = np.minimum(noise_var / var_l, 1.0)
    return g - ratio * (g - m)


def adaptive_median(g, s_max=7):
    """Gonzalez's adaptive median filter (levels A and B), vectorised."""
    def one(ch):
        out = ch.copy()
        done = np.zeros(ch.shape, bool)
        for s in range(3, s_max + 1, 2):
            zmin = ndi.minimum_filter(ch, s, mode="reflect")
            zmax = ndi.maximum_filter(ch, s, mode="reflect")
            zmed = ndi.median_filter(ch, s, mode="reflect")
            level_a = (zmin < zmed) & (zmed < zmax)
            level_b = (zmin < ch) & (ch < zmax)
            sel = level_a & ~done
            out[sel] = np.where(level_b[sel], ch[sel], zmed[sel])
            done |= level_a
        out[~done] = zmed[~done]  # window reached s_max: output z_med
        return out
    return _per_channel(one, g)


# --- non-local means -------------------------------------------------------
def nl_means(g, h, h_color=None, tmpl=7, search=21):
    u8 = np.clip(np.rint(g), 0, 255).astype(np.uint8)
    out = cv2.fastNlMeansDenoisingColored(u8, None, float(h), float(h_color or h), tmpl, search)
    return out.astype(np.float64)


# ---------------------------------------------------------------------------
METHODS = [
    "Auto (from noise type)",
    "Arithmetic mean",
    "Geometric mean",
    "Contraharmonic",
    "Median",
    "Alpha-trimmed mean",
    "Adaptive local (uses σ²)",
    "Adaptive median",
    "Non-local means (uses σ)",
]

# what "Auto" picks for every noise model
# (chosen from the PSNR table produced by make_results.py)
AUTO = {
    "Gaussian": "Adaptive local (uses σ²)",
    "Rayleigh": "Adaptive local (uses σ²)",
    "Gamma (Erlang)": "Adaptive local (uses σ²)",
    "Exponential": "Adaptive local (uses σ²)",
    "Uniform": "Adaptive local (uses σ²)",
    "Impulse (salt & pepper)": "Adaptive median",
}

# how the noise mean / clipping bias is removed (additive noise only)
BIAS_MODES = ["PDF + clipping (exact)", "Subtract noise mean", "None"]

# filters whose output estimates E[g]; for these the bias can be undone exactly
MEAN_LIKE = {"Arithmetic mean", "Adaptive local (uses σ²)", "Non-local means (uses σ)", "Alpha-trimmed mean"}


def denoise(g: np.ndarray, model: NoiseModel, p: dict, method: str = METHODS[0],
            k: int = 5, bias: str = BIAS_MODES[0]):
    """Restore `g` knowing it was corrupted by `model` with parameters `p`.

    Returns (restored, method_actually_used).
    """
    if method == METHODS[0]:
        method = AUTO[model.name]

    tables = clip_tables(model, p) if (model.additive and bias == BIAS_MODES[0]) else None
    _, var = model.mean_var(p)
    sigma = np.sqrt(var)

    if method == "Arithmetic mean":
        f = arithmetic_mean(g, k)
    elif method == "Geometric mean":
        f = geometric_mean(g, k)
    elif method == "Contraharmonic":
        # pepper-dominated -> Q>0, salt-dominated -> Q<0
        q = 1.5 if (model.additive or p.get("pa", 0) >= p.get("pb", 0)) else -1.5
        f = contraharmonic(g, k, q)
    elif method == "Median":
        f = median(g, k)
    elif method == "Alpha-trimmed mean":
        f = alpha_trimmed(g, k, d=max(2, 2 * ((k * k) // 8)))  # trim ~25 % of the window
    elif method == "Adaptive local (uses σ²)":
        if tables is not None:
            # noise variance actually seen at each pixel (smaller where clipping happens)
            f0 = tables.invert(_box(g, k))
            nv = tables.var_at(f0)
        else:
            nv = var if model.additive else 0.0
        f = adaptive_local(g, nv, k)
    elif method == "Adaptive median":
        f = adaptive_median(g, s_max=max(k, 5))
    elif method == "Non-local means (uses σ)":
        s = sigma if model.additive else 20.0
        # OpenCV filters in Lab, where per-channel RGB noise looks weaker: h ≈ 0.6σ
        f = nl_means(g, h=0.6 * s, h_color=0.6 * s)
    else:
        raise ValueError(method)

    if tables is not None and method in MEAN_LIKE:
        f = tables.invert(f)
    elif model.additive and bias != BIAS_MODES[-1]:
        mu, _ = model.mean_var(p)
        if method in ("Median", "Adaptive median"):
            mu = float(model.ppf(0.5, p))  # a median filter keeps the noise *median*
        f = f - mu  # first-order correction (ignores clipping)
    return np.clip(f, 0, L), method


# --- metrics ---------------------------------------------------------------
def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return float("inf") if mse == 0 else 10 * np.log10(L * L / mse)


def ssim(a, b):
    """Mean SSIM on luminance, Gaussian window σ=1.5 (Wang et al. 2004)."""
    def y(x):
        return x[..., 0] * 0.299 + x[..., 1] * 0.587 + x[..., 2] * 0.114 if x.ndim == 3 else x
    x, z = y(a.astype(np.float64)), y(b.astype(np.float64))
    c1, c2 = (0.01 * L) ** 2, (0.03 * L) ** 2
    gf = lambda t: ndi.gaussian_filter(t, 1.5, truncate=3.5)
    mx, mz = gf(x), gf(z)
    sx, sz, sxz = gf(x * x) - mx * mx, gf(z * z) - mz * mz, gf(x * z) - mx * mz
    s = ((2 * mx * mz + c1) * (2 * sxz + c2)) / ((mx * mx + mz * mz + c1) * (sx + sz + c2))
    return float(s.mean())
