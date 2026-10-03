"""Profiler: render one representative frame per shot plus one mid-transition frame each, and report
the wall time. Used to find whatever stalls the parallel render."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import direction as dr           # noqa: E402
import engine                    # noqa: E402
import pvclock as ck             # noqa: E402

FPS = ck.FPS
rows = []
for i, s in enumerate(dr.SHOTS):
    mid = (s["start"] + s["end"]) / 2
    trans = s["start"] - 0.25
    for tag, t in (("mid", mid), ("cut", trans)):
        if t <= 0:
            continue
        t0 = time.time()
        engine.frame(t)
        rows.append((time.time() - t0, tag, s["name"], t))

rows.sort(reverse=True)
print("=== slowest 20 ===")
for dt, tag, name, t in rows[:20]:
    print(f"  {dt:7.3f}s  {tag:<4} {name:<18} t={t:8.2f}")
tot = sum(r[0] for r in rows)
mid = sorted(r[0] for r in rows)[len(rows) // 2]
print(f"=== {len(rows)} probes, total {tot:.1f}s, median {mid:.3f}s, mean {tot / len(rows):.3f}s")
