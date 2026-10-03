"""Calibration step: lints first, then a handful of static frames. Nothing is rendered at scale
until these look right (the reference PV's rule: no 'let's just run it and see')."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import direction as dr                                                # noqa: E402
import pvclock as ck                                                  # noqa: E402

print("=== lint ===")
v = dr.check_variety()
print(f"variety: {'OK' if not v else 'FAIL'} ({len(v)})")
for line in v[:20]:
    print("   ", line)
ck_bad = dr.check_clock()
print(f"clock:   {'OK' if not ck_bad else 'FAIL'} ({len(ck_bad)})")
for line in ck_bad[:20]:
    print("   ", line)
print(f"shots:   {len(dr.SHOTS)}  cover {dr.SHOTS[0]['start']:.3f} .. {dr.SHOTS[-1]['end']:.3f}")
gaps = [(a["name"], b["name"], b["start"] - a["end"])
        for a, b in zip(dr.SHOTS, dr.SHOTS[1:]) if abs(b["start"] - a["end"]) > 1e-6]
print(f"gaps:    {'none' if not gaps else gaps}")

if "--frames" in sys.argv:
    import engine
    picks = [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
    for t in picks:
        t0 = time.time()
        img = engine.frame(t)
        name = f"cal_{t:07.2f}.png".replace(".", "_", 1)
        img.save(os.path.join(out, name))
        print(f"t={t:7.2f}  {dr.shot_at(t)['name']:<16} {time.time() - t0:5.2f}s  -> {name}")
