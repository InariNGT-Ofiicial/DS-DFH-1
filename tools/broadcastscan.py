"""Locate the news-broadcast passages, calibrated on a known positive.

The spectrogram of 291.8-298 s looks like nothing else in the song: a dense broadband block that
stops dead around 3 kHz, with no vibrato contours. That is a band-limited broadcast insert, not a
piano and not a voice singing over one. So: measure that signature, then scan for it.

Signature (per 0.5 s):
  band100   energy 100 Hz - 3 kHz / energy 0 - 11 kHz     (broadcast: nearly all of it)
  hf        energy 6 - 11 kHz / energy 100 Hz - 4 kHz     (broadcast: ~0)
  flat      spectral flatness inside 300 - 2500 Hz        (broadcast: high, it is noisy speech)
  crest     peak / rms of the band envelope               (broadcast: low, it is compressed)
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WAV = ROOT / "audio" / "song_mono22k.wav"
OUT = ROOT / "work" / "broadcast.json"

SR = 22050
NFFT = 1024
HOP = 256                      # 86 rows/s: fine enough for a 0.4 s event
FLO, FHI = 60.0, 11000.0


def load() -> np.ndarray:
    with wave.open(str(WAV), "rb") as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def spec(x: np.ndarray) -> np.ndarray:
    win = np.hanning(NFFT).astype(np.float32)
    n = (len(x) - NFFT) // HOP + 1
    out = np.zeros((NFFT // 2 + 1, n), np.float32)
    for s in range(0, n, 4096):
        e = min(n, s + 4096)
        idx = np.arange(s, e) * HOP
        out[:, s:e] = np.abs(np.fft.rfft(x[idx[:, None] + np.arange(NFFT)] * win, axis=1)).T
    return out


def main() -> None:
    x = load()
    S = spec(x)
    P = S ** 2
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    rate = SR / HOP

    def m(a, b):
        return (freqs >= a) & (freqs < b)

    e_all = P.sum(axis=0) + 1e-12
    band100 = P[m(100, 3000)].sum(axis=0) / e_all
    hf = P[m(6000, 11000)].sum(axis=0) / (P[m(100, 4000)].sum(axis=0) + 1e-12)
    Sb = S[m(300, 2500)] + 1e-10
    flat = np.exp(np.log(Sb).mean(axis=0)) / Sb.mean(axis=0)

    def blk(v, sec):
        k = max(1, int(sec * rate))
        n = len(v) // k
        return v[:n * k].reshape(n, k).mean(axis=1), k

    b100, k = blk(band100, 0.5)
    bhf, _ = blk(hf, 0.5)
    bflat, _ = blk(flat, 0.5)
    crest = np.zeros_like(b100)
    env = P[m(100, 4000)].sum(axis=0)
    for i in range(len(b100)):
        seg = env[i * k:(i + 1) * k]
        crest[i] = seg.max() / (seg.mean() + 1e-12)
    t = np.arange(len(b100)) * 0.5

    # --- calibrate on the known positive (291.8-298) and known negatives
    def stat(a, b):
        sel = (t >= a) & (t < b)
        return dict(t=f"{a}-{b}", band100=round(float(b100[sel].mean()), 3),
                    hf=round(float(bhf[sel].mean()), 4), flat=round(float(bflat[sel].mean()), 3),
                    crest=round(float(crest[sel].mean()), 1))

    print("  window                band100    hf      flat   crest")
    for a, b in [(291.8, 298.0), (298.5, 309.0), (170.0, 180.0), (120.0, 130.0),
                 (0.0, 20.0), (230.0, 262.0), (60.0, 80.0)]:
        s = stat(a, b)
        print(f"  {s['t']:<20} {s['band100']:>7} {s['hf']:>7} {s['flat']:>7} {s['crest']:>7}")

    # --- score and threshold
    def z(v):
        v = np.asarray(v, float)
        return (v - np.median(v)) / (np.percentile(v, 75) - np.percentile(v, 25) + 1e-9)

    score = 1.0 * z(b100) + 1.0 * z(-bhf) + 1.0 * z(bflat) + 0.6 * z(-crest)
    thr = float(np.percentile(score, 93))

    hi = (score > thr).astype(np.int8)
    gap = int(1.0 / 0.5)                    # close gaps up to 1 s
    i = 0
    while i < len(hi):
        if hi[i] == 0:
            j = i
            while j < len(hi) and hi[j] == 0:
                j += 1
            if 0 < i and j < len(hi) and (j - i) <= gap:
                hi[i:j] = 1
            i = j
        else:
            i += 1

    runs, i = [], 0
    while i < len(hi):
        if hi[i]:
            j = i
            while j < len(hi) and hi[j]:
                j += 1
            a, b = float(t[i]), float(t[min(j, len(t) - 1)])
            if b - a >= 2.0:
                runs.append((round(a, 2), round(b, 2), round(float(score[i:j].mean()), 2)))
            i = j
        else:
            i += 1

    print(f"\nthreshold {thr:.2f}")
    print("passages matching the broadcast signature (>= 2 s):")
    for a, b, sc in runs:
        print(f"  {a:7.2f} - {b:7.2f}   ({b-a:5.1f} s)  score {sc}")

    OUT.write_text(json.dumps(dict(thr=thr, runs=runs,
                                   t=[round(float(v), 2) for v in t[::2]],
                                   band100=[round(float(v), 4) for v in b100[::2]],
                                   hf=[round(float(v), 5) for v in bhf[::2]],
                                   flat=[round(float(v), 4) for v in bflat[::2]],
                                   crest=[round(float(v), 2) for v in crest[::2]]),
                              ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
