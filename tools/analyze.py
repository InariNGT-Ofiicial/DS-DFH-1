"""Clock calibration for the Sirius PV.

Measures, on the real audio (never a guess):
  - spectral-flux onset envelope
  - BPM by autocorrelation of the onset envelope (metrical-comb scored, so octave errors lose)
  - section energy profile (to place the long instrumental passages)
  - the seven-band features the mascot reacts to, at 48 rows/s

Writes work/analysis.json and prints a summary. All numbers used later in the film
are copied from here, not invented.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parents[1]
WAV = ROOT / "audio" / "song_mono22k.wav"
OUT = ROOT / "work" / "analysis.json"

SR = 22050
HOP = 459              # 22050 / 459 = 48.039 rows a second: the same warning the reference PV hit
RATE = SR / HOP
NFFT = 1024
BANDS = [(40, 120), (120, 300), (300, 700), (700, 1500), (1500, 3000), (3000, 6000), (6000, 10000)]


def load() -> np.ndarray:
    with wave.open(str(WAV), "rb") as w:
        assert w.getframerate() == SR, w.getframerate()
        assert w.getnchannels() == 1
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def spectrogram(x: np.ndarray) -> np.ndarray:
    win = np.hanning(NFFT).astype(np.float32)
    frames = sliding_window_view(x, NFFT)[::HOP] * win
    return np.abs(np.fft.rfft(frames, axis=1)).T          # (freq, time)


def onset_env(S: np.ndarray) -> np.ndarray:
    d = np.diff(S, axis=1)
    flux = np.maximum(d, 0.0).sum(axis=0)
    flux = np.concatenate([[0.0], flux])
    # half-second moving average as the slow reference, flux minus it
    k = int(0.25 * RATE)
    slow = np.convolve(flux, np.ones(k) / k, mode="same")
    env = np.maximum(flux - slow, 0.0)
    ref = np.sort(env)[int(len(env) * 0.99)] or 1.0      # ★ () or 1.0: a bare `or` on a numpy scalar still works here
    return env / ref


def estimate_bpm(env: np.ndarray) -> dict:
    """Metrical comb: for each candidate BPM, sum the onset envelope on its beat grid and on its
    half-beat (offbeat) grid, and score how much of the energy falls exactly on grid vs off it."""
    env = env - env.mean()
    lo, hi = 50.0, 190.0
    cands = np.arange(lo, hi, 0.02)
    n = len(env)
    lag_min = max(2, int(60.0 / hi * RATE))
    lag_max = min(n - 2, int(60.0 / lo * RATE))
    res = []
    for bpm in cands:
        lag = 60.0 / bpm * RATE
        # phase: average alignment over all starting offsets is expensive; sample 32 phases
        best = -1e9
        for ph in np.linspace(0, lag, 24, endpoint=False):
            idx = np.arange(ph, n - 1, lag)
            ii = idx.astype(int)
            grid = env[ii].sum() / max(1, len(ii))
            off = env[np.clip((ii + lag / 2).astype(int), 0, n - 1)].sum() / max(1, len(ii))
            score = grid - 0.6 * off
            if score > best:
                best = score
        res.append(best)
    res = np.array(res)
    # prefer the slower of two equally good octaves (avoid double-time)
    order = np.argsort(res)[::-1]
    top = []
    for i in order:
        b = cands[i]
        if any(abs(b - t) < 6 or abs(b * 2 - t) < 6 or abs(b / 2 - t) < 6 for t in top):
            continue
        top.append(round(float(b), 2))
        if len(top) >= 5:
            break
    return dict(best=top[0], candidates=top)


def section_profile(env: np.ndarray, rms: np.ndarray) -> list[dict]:
    """1-second energy, so the long instrumental stretches show up as their own plateaus."""
    sec = int(RATE)
    rows = []
    for i in range(0, len(rms) - sec, sec):
        rows.append(dict(t=i / RATE, rms=float(rms[i:i + sec].mean()),
                         onset=float(env[i:i + sec].mean())))
    lo = min(r["rms"] for r in rows)
    hi = max(r["rms"] for r in rows)
    for r in rows:
        r["norm"] = (r["rms"] - lo) / (hi - lo + 1e-9)
    return rows


def main() -> None:
    x = load()
    dur = len(x) / SR
    S = spectrogram(x)
    env = onset_env(S)
    loud = np.sqrt(np.convolve(x ** 2, np.ones(int(0.02 * SR)) / int(0.02 * SR), mode="same"))
    bpm = estimate_bpm(env)

    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    bands = []
    for lo, hi in BANDS:
        m = (freqs >= lo) & (freqs < hi)
        bands.append(S[m].mean(axis=0))
    bands = np.array(bands)

    def norm(v):
        ref = np.sort(v)[int(len(v) * 0.98)] or 1.0
        return np.clip(v / ref, 0, 1)

    def follow(v, a, r):
        out = np.empty_like(v)
        s = 0.0
        for i, y in enumerate(v):
            s += (y - s) * (a if y > s else r)
            out[i] = s
        return out

    data = dict(
        duration=round(dur, 3), rate=round(RATE, 4), bpm=bpm,
        loud=[round(float(v), 3) for v in follow(norm(loud[::HOP][:len(env)]), 0.6, 0.15)],
        bands=[[round(float(v), 3) for v in follow(norm(b), 0.6, 0.18)] for b in bands],
        onset=[round(float(v), 3) for v in follow(env, 0.9, 0.25)],
    )
    OUT.write_text(json.dumps(data), encoding="utf-8")

    print(f"duration {dur:.3f}s  rows {len(env)}  rate {RATE:.4f}/s")
    print(f"BPM best={bpm['best']}  candidates={bpm['candidates']}")
    prof = section_profile(env, loud)
    # print a coarse 5-second energy ribbon so the structure is visible at a glance
    print("energy ribbon (5 s per cell, . = quiet, # = loud):")
    line, lab = [], []
    for i in range(0, len(prof), 5):
        chunk = prof[i:i + 5]
        v = sum(r["norm"] for r in chunk) / len(chunk)
        line.append(" .:-=+*#@"[min(8, int(v * 8.99))])
        lab.append(f"{int(chunk[0]['t'])}")
    print("".join(line))
    print(" ".join(lab))


if __name__ == "__main__":
    main()
