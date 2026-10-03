"""Beat verification + copyright-safe lyric timeline.

The reference PV's lesson: never trust the autocorrelation alone. Here the hard anchor is the
line spacing of the vocal (a human wrote those times), and the BPM is defined from that spacing
so that one lyric line is exactly four beats. We then score the onset envelope on that grid to
confirm the choice, and export a timeline that carries **times and sha256 only, no lyric text**.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LRC = Path("D:/CloudMusic/星辰不唏嘘 - シリウスの心臓 (Piano Ver.).lrc")
ANALYSIS = ROOT / "work" / "analysis.json"
TIMELINE = ROOT / "song.timeline.json"
LINES_LOCAL = ROOT / "work" / "lines.local.json"

CREDIT_ROWS = 4          # the first four LRC rows are production credits, not lyrics


def parse_lrc() -> list[tuple[float, str]]:
    rows = []
    for line in LRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", line)
        if m:
            rows.append((int(m[1]) * 60 + float(m[2]), m[3].strip()))
    return rows


def main() -> None:
    rows = parse_lrc()
    credits = [s for _, s in rows[:CREDIT_ROWS]]
    sung = [(t, s) for t, s in rows[CREDIT_ROWS:]]

    # 1. line spacing -> BPM  (one line = 4 beats)
    starts = [t for t, _ in sung]
    gaps = np.diff([t for t, s in sung if "♪" not in s])
    med = float(np.median(gaps))
    beat = med / 4.0
    bpm = 60.0 / beat

    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    env = np.array(data["onset"], dtype=np.float64)
    rate = data["rate"]

    def score(bpm_: float, anchor: float) -> float:
        """Mean onset on the eighth-note grid minus the mean on the off-grid."""
        lag = 60.0 / bpm_ * rate
        out = []
        for ph in np.linspace(0, lag, 32, endpoint=False):
            idx = np.arange(anchor * rate + ph, len(env) - 1, lag).astype(int)
            idx = idx[idx < len(env)]
            if len(idx) < 50:
                continue
            g = env[idx].mean()
            o = env[np.clip((idx + lag / 2).astype(int), 0, len(env) - 1)].mean()
            out.append(g - 0.6 * o)
        return float(np.mean(out))

    grid = {}
    for cand in (bpm / 2, bpm, bpm * 1.5, bpm * 2):
        grid[round(cand, 2)] = round(score(cand, starts[0]), 5)

    print(f"lines {len(sung)}  median spacing {med:.4f}s")
    print(f"-> BPM = {bpm:.3f}  (beat {beat:.4f}s, one line = 4 beats)")
    print("onset-on-grid score (higher = better):")
    for k, v in sorted(grid.items(), key=lambda kv: -kv[1]):
        print(f"   {k:8.2f} BPM   {v:+.5f}")

    # 2. copyright-safe timeline: times + per-line sha256, never the text
    tl = dict(
        source_sha256=hashlib.sha256(LRC.read_bytes()).hexdigest(),
        note="times and per-line digests only; the lyric text is composed on the user's own machine",
        bpm=round(bpm, 4), beat=round(beat, 5), first_line=round(starts[0], 3),
        lines=[dict(t=round(t, 3),
                    end=round(sung[i + 1][0], 3) if i + 1 < len(sung) else round(t + 3.0, 3),
                    sha256=hashlib.sha256(s.encode("utf-8")).hexdigest(),
                    kind=("step" if "♪" in s else "sing"))
               for i, (t, s) in enumerate(sung)],
    )
    TIMELINE.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    LINES_LOCAL.write_text(json.dumps(
        dict(credits=credits,
             lines=[[round(t, 3), s] for t, s in sung]), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {TIMELINE.name} ({len(tl['lines'])} lines, no text) and {LINES_LOCAL.name}")


if __name__ == "__main__":
    main()
