"""Readable spectrograms: log frequency, fixed dB reference, time and frequency rulers.

The point is to answer one question by eye -- is there a human voice (or any band-limited broadcast
insert) in the long instrumental passages -- and to answer it without guessing.
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parents[1]
WAV = ROOT / "audio" / "song_mono22k.wav"
OUT = ROOT / "out"
SR = 22050
NFFT = 1024
HOP = 128
FLO, FHI = 60.0, 11000.0


def load() -> np.ndarray:
    with wave.open(str(WAV), "rb") as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def spec(x: np.ndarray) -> np.ndarray:
    win = np.hanning(NFFT).astype(np.float32)
    n = (len(x) - NFFT) // HOP + 1
    out = np.zeros((NFFT // 2 + 1, n), np.float32)        # ★ float32 and chunked: this box has ~2 GB
    step = 4096
    for s in range(0, n, step):
        e = min(n, s + step)
        idx = np.arange(s, e) * HOP
        frames = x[idx[:, None] + np.arange(NFFT)] * win
        out[:, s:e] = np.abs(np.fft.rfft(frames, axis=1)).T
    return out


def paint(S: np.ndarray, f0: float, f1: float, x0: float, x1: float, rate: float,
          ref: float, dyn: float = 85.0, w: int = 1560, h: int = 420) -> Image.Image:
    """Decimate time first, then fold frequency onto a log axis. This box has ~2 GB free, so the
    interim arrays are kept to w x h, never to (bins x frames).
    Mean-pool, not max-pool: max over 30 ms of piano lifts every quiet gap and blows the picture out."""
    i0, i1 = max(0, int(x0 * rate)), int(x1 * rate)
    n = i1 - i0
    # 1. mean-pool the time axis down to w columns
    step = max(1, n // w)
    m = (n // step) * step
    cols = S[:, i0:i0 + m].reshape(S.shape[0], -1, step).mean(axis=2).astype(np.float32)
    cols = 20 * np.log10(np.clip(cols, 1e-7, None))
    # 2. fold the log-frequency axis, row by row, straight into the output
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    edges = np.logspace(np.log10(f0), np.log10(f1), h + 1)
    centres = np.sqrt(edges[:-1] * edges[1:])          # geometric centre of each log band
    lut = np.clip(np.searchsorted(freqs, centres), 0, len(freqs) - 1)
    v = np.clip((cols[lut[::-1]] - (ref - dyn)) / dyn, 0, 1)
    rgb = np.empty((h, v.shape[1], 3), np.uint8)
    rgb[..., 0] = (v * 255).astype(np.uint8)
    rgb[..., 1] = (v * 198).astype(np.uint8)
    rgb[..., 2] = (v * 52).astype(np.uint8)
    img = Image.fromarray(rgb, "RGB").resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    # time ruler every 5 s
    t = int(np.ceil(x0 / 5.0) * 5)
    while t <= x1:
        px = int((t - x0) / (x1 - x0) * w)
        d.line([px, 0, px, 6], fill=(90, 90, 90))
        d.line([px, h - 8, px, h], fill=(90, 90, 90))
        d.text((px + 2, h - 11), str(t), fill=(150, 150, 150))
        t += 5
    # frequency ruler at 100 / 300 / 1k / 3k / 8k
    for f in (100, 300, 1000, 3000, 8000):
        if not (f0 <= f <= f1):
            continue
        py = int((np.log(f1) - np.log(f)) / (np.log(f1) - np.log(f0)) * h)
        d.line([0, py, 8, py], fill=(90, 90, 90))
        d.text((11, py - 5), f"{f}", fill=(150, 150, 150))
    return img


def main() -> None:
    x = load()
    S = spec(x)
    rate = SR / HOP
    ref = float(np.percentile(20 * np.log10(S + 1e-6), 99.6))
    print(f"rows {S.shape[1]} rate {rate:.2f}/s  ref {ref:.1f} dB")

    windows = [("full", 0.0, 330.0), ("A", 112.0, 172.0), ("B", 196.0, 266.0),
               ("A_head", 114.0, 130.0), ("A_tail", 143.0, 171.0), ("C", 296.0, 330.0)]
    for tag, a, b in windows:
        img = paint(S, FLO, FHI, a, b, rate, ref, dyn=32.0)
        img.save(OUT / f"sp_{tag}.png")
        print(f"wrote sp_{tag}.png  {a}-{b}s")

    # ---- quantitative: a 1970 broadcast insert is compressed and band-limited.
    # crest  = peak / rms over a 1 s window  (speech ~4-7, piano ~12-25)
    # hf     = energy above 6 kHz / energy in 100 Hz - 4 kHz  (broadcast ~0, piano hammer noise >0)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    hfm = freqs >= 6000
    lfm = (freqs >= 100) & (freqs < 4000)
    sec = int(rate)
    P = S ** 2
    print("\n  t      crest    hf/lf")
    rows = []
    for i in range(0, S.shape[1] - sec, sec):
        blk = S[:, i:i + sec]
        lo = float(blk[lfm].sum())
        hi = float(blk[hfm].sum())
        crest = float(blk.max() / (np.sqrt(P[:, i:i + sec].mean()) + 1e-9))
        rows.append((i / rate, crest, hi / (lo + 1e-9)))
    cr = np.array([r[1] for r in rows])
    hr = np.array([r[2] for r in rows])
    print(f"  crest median {np.median(cr):.1f}  p10 {np.percentile(cr,10):.1f}  p90 {np.percentile(cr,90):.1f}")
    print(f"  hf/lf median {np.median(hr):.4f}  p10 {np.percentile(hr,10):.4f}  p90 {np.percentile(hr,90):.4f}")
    print("  ribbon crest (dense=low=compressed):  " + "".join(
        " .:-=+*#@"[max(0, min(8, int(9 - r[1] / 3.0)))] for r in rows[::4]))
    print("  ribbon hf/lf (dense=high=bright):     " + "".join(
        " .:-=+*#@"[max(0, min(8, int(np.log10(r[2] + 1e-6) * 2 + 8)))] for r in rows[::4]))


if __name__ == "__main__":
    main()
