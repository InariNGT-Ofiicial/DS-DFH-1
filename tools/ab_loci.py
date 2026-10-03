"""A/B the five air-and-orbit loci: same frame, same seed, old els vs new els.

The whole-film 13-point average cannot see this work -- the five loci cover 8-15 s, 45-49 s,
176-179 s and 276-283 s, and a uniform sample lands between all of them. This renders the exact
same frame twice, once with the pre-change element list and once with the current one, so the
difference is the change and nothing else (same shot name, so the same rng seed).

    python tools/ab_loci.py
"""
from __future__ import annotations

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pv"))

import numpy as np                                                       # noqa: E402
from PIL import Image                                                    # noqa: E402

import direction as dr                                                   # noqa: E402
import engine                                                            # noqa: E402
import pvclock as ck                                                     # noqa: E402

# the element lists these five shots carried before this round
OLD = {
    "shot_ascent": [("beam", dict(layers=["80 km", "50 km", "20 km"], dy=-60)),
                    ("rocket", dict(ignited=1.0, lift="auto", climb=0.32))],
    "shot_orbit_period": [("orbit", dict())],
    "shot_ionosphere": [("beam", dict(layers=["电离层 F2", "电离层 E", "D 层", "地面"], packets=9))],
    "shot_drift": [("answer", dict(question="要如何度过", rows=dr.HER_ASCENT, picture=True))],
    "shot_noise": [("answer", dict(question="要如何解说", rows=dr.HER_AFTER, picture=True))],
}
CASES = [("shot_ascent", 10.60), ("shot_orbit_period", 13.60), ("shot_ionosphere", 178.20),
         ("shot_drift", 47.60), ("shot_noise", 281.50)]


def render(shot: dict, t: float) -> Image.Image:
    return engine.post(engine.render_shot(shot, t), ck.glow_arc(t))


def stat(im: Image.Image):
    L = np.asarray(im.convert("RGB"), dtype=np.float32).mean(axis=2)
    edge = (abs(np.diff(L, axis=1)).mean() + abs(np.diff(L, axis=0)).mean()) / 2
    return (L.mean(), (L > 38).mean() * 100, (L > 120).mean() * 100,
            (L > 190).mean() * 100, L.max(), edge)


def main() -> int:
    out = os.path.join(os.path.dirname(HERE), "out")
    print(f"{'镜头':<20} {'版本':<6} {'mean':>6} {'墨%':>6} {'亮%':>6} {'高光%':>6} {'峰值':>6} {'边缘':>6}")
    agg = {"old": np.zeros(6), "new": np.zeros(6)}
    for name, t in CASES:
        cur = dr.shot_at(t)
        old = copy.deepcopy(cur)
        old["els"] = OLD[name]
        for tag, shot in (("old", old), ("new", cur)):
            m = stat(render(shot, t))
            agg[tag] += np.array(m)
            print(f"{name:<20} {tag:<6} {m[0]:6.1f} {m[1]:6.2f} {m[2]:6.2f} {m[3]:6.2f} "
                  f"{m[4]:6.1f} {m[5]:6.2f}")
        # side-by-side for the eye
        a = render(old, t).resize((640, 360), Image.LANCZOS)
        b = render(cur, t).resize((640, 360), Image.LANCZOS)
        sheet = Image.new("RGB", (1288, 360), (10, 9, 6))
        sheet.paste(a, (0, 0))
        sheet.paste(b, (648, 0))
        sheet.save(os.path.join(out, f"ab_{name}.png"))
    n = len(CASES)
    print("-" * 74)
    for tag in ("old", "new"):
        v = agg[tag] / n
        print(f"{'合计平均':<20} {tag:<6} {v[0]:6.1f} {v[1]:6.2f} {v[2]:6.2f} {v[3]:6.2f} "
              f"{v[4]:6.1f} {v[5]:6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
