"""Find the spoken passages in the song, so the film can fill them instead of leaving rests.

A piano note and a human voice differ in three measurable ways, and this scans for all three:
  - spectral flatness in the speech band (300-3400 Hz): a voice is noisier than a struck string
  - syllabic modulation: a voice turns its own energy on and off 2-8 times a second
  - formant spread: a voice puts energy in three broad humps, not one narrow comb

Everything here is read-only diagnostics; nothing in the film depends on a guess.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parents[1]
WAV = ROOT / "audio" / "song_mono22k.wav"
OUT = ROOT / "work" / "voicescan.json"

SR = 22050
HOP = 459                      # same grid as analyze.py: 48.039 rows/s
RATE = SR / HOP
NFFT = 1024


def load() -> np.ndarray:
    with wave.open(str(WAV), "rb") as w:
        assert w.getframerate() == SR
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def spectrogram(x: np.ndarray) -> np.ndarray:
    win = np.hanning(NFFT).astype(np.float32)
    frames = sliding_window_view(x, NFFT)[::HOP] * win
    return np.abs(np.fft.rfft(frames, axis=1)).T


def main() -> None:
    x = load()
    S = spectrogram(x)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    band = (freqs >= 300) & (freqs < 3400)
    Sb = S[band]
    eps = 1e-10

    # 1. spectral flatness: geometric mean / arithmetic mean, per frame
    flat = np.exp(np.log(Sb + eps).mean(axis=0)) / (Sb.mean(axis=0) + eps)

    # 2. syllabic modulation: envelope of the speech band, energy at 2-8 Hz
    env = Sb.sum(axis=0)
    k = max(1, int(0.02 * RATE))
    env = np.convolve(env, np.ones(k) / k, mode="same")
    e = env - env.mean()
    spec = np.abs(np.fft.rfft(e * np.hanning(len(e))))
    mf = np.fft.rfftfreq(len(e), 1.0 / RATE)
    syl = spec[(mf >= 2.0) & (mf <= 8.0)].sum() / (spec.sum() + eps)

    # 3. band-limited loudness ratio: voice sits in 300-3400; piano bass does not
    lo = (freqs < 250)
    ratio = Sb.sum(axis=0) / (S[lo].sum(axis=0) + eps)

    def smooth(v, n):
        return np.convolve(v, np.ones(n) / n, mode="same")

    w = int(0.35 * RATE)
    flat_s = smooth(flat, w)
    syl_s = smooth(np.full_like(syl, 0.0) + 0.0, w)     # placeholder for shape
    # syllable modulation is a global-ish property; recompute locally in 3 s windows
    win_n = int(3.0 * RATE)
    syl_loc = np.zeros_like(env)
    for i in range(0, len(env), win_n):
        seg = e[i:i + win_n]
        if len(seg) < win_n // 2:
            break
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1.0 / RATE)
        m = (fr >= 2.0) & (fr <= 8.0)
        v = sp[m].sum() / (sp.sum() + eps)
        syl_loc[i:i + len(seg)] = v
    syl_s = smooth(syl_loc, int(1.2 * RATE))
    rat_s = smooth(np.log10(ratio + eps), int(0.6 * RATE))

    def z(v):
        return (v - np.median(v)) / (np.percentile(v, 75) - np.percentile(v, 25) + 1e-9)

    score = 0.9 * z(flat_s) + 0.7 * z(syl_s) + 0.5 * z(rat_s)

    print(f"rows {len(env)}  dur {len(x)/SR:.3f}s   (0.5 s per cell below)")
    print("score ribbon:  ' '=-2  .=-1  :=0  +=1  *=2  #=3  @=4")
    line, lab = [], []
    step = int(0.5 * RATE)
    for i in range(0, len(score) - step, step):
        v = score[i:i + step].mean()
        line.append(" .:+*#@"[min(6, max(0, int((v + 2.0) * 1.5)))])
        lab.append(f"{int(i/RATE)}")
    print("".join(line))
    print(" ".join(lab))

    # contiguous stretches above a threshold = the candidate spoken passages.
    # Close 0.4 s holes first (a speaker pauses), then keep runs of at least 1.5 s.
    thr = float(np.percentile(score, 88))
    hi = (score > thr).astype(np.int8)
    gap = int(0.4 * RATE)
    i = 0
    while i < len(hi):
        if hi[i] == 0:
            j = i
            while j < len(hi) and hi[j] == 0:
                j += 1
            if i > 0 and j < len(hi) and (j - i) <= gap:
                hi[i:j] = 1                      # it was only a breath
            i = j
        else:
            i += 1
    runs = []
    i = 0
    while i < len(hi):
        if hi[i]:
            j = i
            while j < len(hi) and hi[j]:
                j += 1
            a, b = i / RATE, j / RATE
            if b - a >= 1.5:
                runs.append((round(a, 2), round(b, 2), round(float(score[i:j].mean()), 2)))
            i = j
        else:
            i += 1
    print("\ncandidate spoken passages (>=1.5 s):")
    for a, b, s in runs:
        print(f"  {a:7.2f} - {b:7.2f}   ({b-a:5.1f} s)  score {s}")

    OUT.write_text(json.dumps(dict(thr=thr, runs=runs,
                                   flat=[round(float(v), 4) for v in flat_s[::int(RATE)]],
                                   syl=[round(float(v), 4) for v in syl_s[::int(RATE)]],
                                   ratio=[round(float(v), 3) for v in rat_s[::int(RATE)]]),
                              ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
