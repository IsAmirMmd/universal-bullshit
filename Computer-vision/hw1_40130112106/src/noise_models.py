"""Six noise models from Gonzalez & Woods, chapter 5 (Gaussian, Rayleigh,
Erlang/Gamma, Exponential, Uniform, Impulse).

Every model knows three things about itself:
  * how to draw samples (to corrupt an image),
  * its theoretical PDF p(z) (to draw the curve next to the histogram),
  * its mean and variance (used by the denoising filters).

All intensities are in 8-bit units [0, 255]. Images are float64 arrays.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import factorial, pi, sqrt

import numpy as np
from scipy import stats

L = 255.0  # max intensity


@dataclass
class Param:
    key: str
    label: str
    default: float
    lo: float
    hi: float
    step: float = 1.0
    integer: bool = False


@dataclass
class NoiseModel:
    name: str
    params: list[Param]
    additive: bool = True  # False only for impulse noise
    formula: str = ""

    # --- overridden per model -------------------------------------------
    def sample(self, shape, p, rng):  # pragma: no cover - abstract
        raise NotImplementedError

    def pdf(self, z, p):  # pragma: no cover - abstract
        raise NotImplementedError

    def mean_var(self, p) -> tuple[float, float]:  # pragma: no cover
        raise NotImplementedError

    def ppf(self, q, p):
        """Inverse CDF; used to build deterministic quantile samples."""
        raise NotImplementedError

    # --- shared ------------------------------------------------------------
    def defaults(self) -> dict:
        return {prm.key: prm.default for prm in self.params}

    def apply(self, img: np.ndarray, p: dict, rng=None):
        """Corrupt `img` (float, 0..255). Returns (noisy_clipped, noise_field)."""
        rng = np.random.default_rng() if rng is None else rng
        eta = self.sample(img.shape, p, rng)
        noisy = np.clip(img + eta, 0, L)
        return noisy, eta

    def support(self, p):
        """x-range for plotting the PDF."""
        m, v = self.mean_var(p)
        s = sqrt(v)
        return m - 4.5 * s, m + 4.5 * s


# ---------------------------------------------------------------------------
class Gaussian(NoiseModel):
    def __init__(self):
        super().__init__(
            "Gaussian",
            [Param("mu", "mean  μ", 0, -50, 50), Param("sigma", "std  σ", 25, 1, 80)],
            formula="p(z) = 1/(√(2π)σ) · exp(-(z-μ)² / 2σ²)",
        )

    def sample(self, shape, p, rng):
        return rng.normal(p["mu"], p["sigma"], shape)

    def pdf(self, z, p):
        return stats.norm.pdf(z, p["mu"], p["sigma"])

    def ppf(self, q, p):
        return stats.norm.ppf(q, p["mu"], p["sigma"])

    def mean_var(self, p):
        return p["mu"], p["sigma"] ** 2


class Rayleigh(NoiseModel):
    """p(z) = 2/b (z-a) exp(-(z-a)^2 / b) for z >= a."""

    def __init__(self):
        super().__init__(
            "Rayleigh",
            [Param("a", "a  (offset)", 0, -50, 50), Param("b", "b", 800, 10, 5000, 10)],
            formula="p(z) = 2/b·(z-a)·exp(-(z-a)²/b),  z ≥ a",
        )

    def sample(self, shape, p, rng):
        u = rng.random(shape)
        return p["a"] + np.sqrt(-p["b"] * np.log1p(-u))

    def pdf(self, z, p):
        x = z - p["a"]
        return np.where(x >= 0, 2.0 / p["b"] * x * np.exp(-(x ** 2) / p["b"]), 0.0)

    def ppf(self, q, p):
        return p["a"] + np.sqrt(-p["b"] * np.log1p(-q))

    def mean_var(self, p):
        return p["a"] + sqrt(pi * p["b"] / 4), p["b"] * (4 - pi) / 4

    def support(self, p):
        m, v = self.mean_var(p)
        return p["a"] - 5, m + 5 * sqrt(v)


class Gamma(NoiseModel):
    """Erlang: p(z) = a^b z^(b-1) / (b-1)! e^(-az), z >= 0, b a positive integer."""

    def __init__(self):
        super().__init__(
            "Gamma (Erlang)",
            [Param("a", "a  (rate)", 0.2, 0.01, 2.0, 0.01), Param("b", "b  (shape, int)", 4, 1, 20, 1, True)],
            formula="p(z) = aᵇ zᵇ⁻¹ / (b-1)! · e^(-az),  z ≥ 0",
        )

    def sample(self, shape, p, rng):
        return rng.gamma(int(p["b"]), 1.0 / p["a"], shape)

    def pdf(self, z, p):
        a, b = p["a"], int(p["b"])
        zz = np.maximum(z, 0)
        return np.where(z >= 0, a ** b * zz ** (b - 1) / factorial(b - 1) * np.exp(-a * zz), 0.0)

    def ppf(self, q, p):
        return stats.gamma.ppf(q, int(p["b"]), scale=1.0 / p["a"])

    def mean_var(self, p):
        a, b = p["a"], int(p["b"])
        return b / a, b / a ** 2

    def support(self, p):
        m, v = self.mean_var(p)
        return -5, m + 5 * sqrt(v)


class Exponential(NoiseModel):
    """p(z) = a e^(-az), z >= 0  (Erlang with b = 1)."""

    def __init__(self):
        super().__init__(
            "Exponential",
            [Param("a", "a  (rate)", 0.06, 0.005, 1.0, 0.005)],
            formula="p(z) = a · e^(-az),  z ≥ 0",
        )

    def sample(self, shape, p, rng):
        return rng.exponential(1.0 / p["a"], shape)

    def pdf(self, z, p):
        return np.where(z >= 0, p["a"] * np.exp(-p["a"] * np.maximum(z, 0)), 0.0)

    def ppf(self, q, p):
        return -np.log1p(-q) / p["a"]

    def mean_var(self, p):
        return 1 / p["a"], 1 / p["a"] ** 2

    def support(self, p):
        return -5, 6 / p["a"]


class Uniform(NoiseModel):
    def __init__(self):
        super().__init__(
            "Uniform",
            [Param("a", "a  (low)", 0, -100, 100), Param("b", "b  (high)", 60, -100, 150)],
            formula="p(z) = 1/(b-a),  a ≤ z ≤ b",
        )

    def _ab(self, p):
        a, b = p["a"], p["b"]
        return (a, b) if b > a else (b, a + 1e-6)

    def sample(self, shape, p, rng):
        a, b = self._ab(p)
        return rng.uniform(a, b, shape)

    def pdf(self, z, p):
        a, b = self._ab(p)
        return np.where((z >= a) & (z <= b), 1.0 / (b - a), 0.0)

    def ppf(self, q, p):
        a, b = self._ab(p)
        return a + (b - a) * q

    def mean_var(self, p):
        a, b = self._ab(p)
        return (a + b) / 2, (b - a) ** 2 / 12

    def support(self, p):
        a, b = self._ab(p)
        pad = 0.25 * (b - a)
        return a - pad, b + pad


class Impulse(NoiseModel):
    """Salt-and-pepper: value a (=0, pepper) with prob Pa, b (=255, salt) with prob Pb."""

    def __init__(self):
        super().__init__(
            "Impulse (salt & pepper)",
            [Param("pa", "Pa  (pepper prob)", 0.05, 0.0, 0.5, 0.01), Param("pb", "Pb  (salt prob)", 0.05, 0.0, 0.5, 0.01)],
            additive=False,
            formula="p(z) = Pa for z=a (0),  Pb for z=b (255),  1-Pa-Pb otherwise",
        )

    def apply(self, img, p, rng=None):
        rng = np.random.default_rng() if rng is None else rng
        # one decision per pixel, shared by all colour channels (true black/white dots)
        u = rng.random(img.shape[:2])
        noisy = img.copy()
        pepper = u < p["pa"]
        salt = (u >= p["pa"]) & (u < p["pa"] + p["pb"])
        noisy[pepper] = 0
        noisy[salt] = L
        return noisy, noisy - img

    def mean_var(self, p):
        return 0.0, 0.0  # not meaningful for impulse noise

    def support(self, p):
        return -10, 265


MODELS: list[NoiseModel] = [Gaussian(), Rayleigh(), Gamma(), Exponential(), Uniform(), Impulse()]
BY_NAME = {m.name: m for m in MODELS}


# ---------------------------------------------------------------------------
# Effect of clipping.  With a known PDF we can compute, for every true value f,
# what the clipped observation g = clip(f + eta, 0, 255) looks like on average:
#     h(f) = E[g | f]      v(f) = Var[g | f]
# A smoothing filter estimates h(f); inverting h gives back f, which removes the
# noise mean (bias) AND the bias caused by clipping near black/white.
# ---------------------------------------------------------------------------
@dataclass
class ClipTables:
    f: np.ndarray = field(repr=False)
    h: np.ndarray = field(repr=False)
    v: np.ndarray = field(repr=False)

    def invert(self, m: np.ndarray) -> np.ndarray:
        return np.interp(m, self.h, self.f)

    def var_at(self, f: np.ndarray) -> np.ndarray:
        return np.interp(f, self.f, self.v)


def clip_tables(model: NoiseModel, p: dict, n_q: int = 4000) -> ClipTables:
    q = (np.arange(n_q) + 0.5) / n_q
    eta = np.asarray(model.ppf(q, p), dtype=float)  # deterministic quantile samples
    f = np.linspace(0, L, 1021)
    g = np.clip(f[:, None] + eta[None, :], 0, L)
    h = g.mean(1)
    v = g.var(1)
    # make h strictly increasing so np.interp can invert it
    h = np.maximum.accumulate(h) + np.linspace(0, 1e-6, h.size)
    return ClipTables(f, h, v)
