## Auto (filter chosen from the noise type)

| noise | params | filter | PSNR noisy | SSIM noisy | PSNR restored | SSIM restored |
|---|---|---|---|---|---|---|
| Gaussian | mu=0, sigma=25 | Adaptive local (uses σ²) | 21.31 | 0.441 | 29.21 | 0.865 |
| Rayleigh | a=0, b=800 | Adaptive local (uses σ²) | 21.15 | 0.763 | 32.90 | 0.943 |
| Gamma (Erlang) | a=0.2, b=4 | Adaptive local (uses σ²) | 23.12 | 0.826 | 34.35 | 0.958 |
| Exponential | a=0.06 | Adaptive local (uses σ²) | 22.88 | 0.730 | 31.48 | 0.917 |
| Uniform | a=0, b=60 | Adaptive local (uses σ²) | 19.47 | 0.694 | 31.65 | 0.932 |
| Impulse (salt & pepper) | pa=0.05, pb=0.05 | Adaptive median | 14.13 | 0.164 | 39.53 | 0.990 |

## PSNR (dB) of every filter

| noise | Arithmetic mean | Geometric mean | Contraharmonic | Median | Alpha-trimmed mean | Adaptive local (uses σ²) | Adaptive median | Non-local means (uses σ) |
|---|---|---|---|---|---|---|---|---|
| Gaussian | 27.95 | 26.29 | 23.74 | 27.88 | 28.85 | **29.21** | 24.25 | 27.85 |
| Rayleigh | 28.33 | 24.06 | 23.45 | 24.64 | 29.64 | **32.90** | 24.13 | 28.36 |
| Gamma (Erlang) | 28.55 | 25.78 | 24.92 | 27.09 | 29.97 | **34.35** | 26.62 | 29.44 |
| Exponential | 28.55 | 26.50 | 24.53 | 28.98 | 29.70 | **31.48** | 27.25 | 30.85 |
| Uniform | 28.10 | 22.51 | 22.08 | 22.49 | 29.18 | **31.65** | 21.86 | 28.47 |
| Impulse (salt & pepper) | 23.73 | 12.83 | 13.75 | 35.05 | 29.31 | 14.13 | **39.53** | 14.33 |

## Bias correction, adaptive local filter

| noise | PDF + clipping (exact) | Subtract noise mean | None |
|---|---|---|---|
| Gaussian | 29.21 | 27.96 | 27.96 |
| Rayleigh | 32.90 | 24.31 | 21.83 |
| Gamma (Erlang) | 34.35 | 26.27 | 23.70 |
| Exponential | 31.48 | 26.62 | 24.72 |
| Uniform | 31.65 | 22.68 | 20.37 |
