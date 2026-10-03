"""Minimal LRC reader: turn a .lrc into the (start, text) list `pvclock` wants.

Only the two things this pipeline needs: timed lyric lines and '[offset:]'. Metadata tags
(`[ti:]`, `[ar:]`, ...) are kept out of the way, and blank lines are dropped so the row count
matches `song.timeline.json` (which was built from the same file).

    python tools/lrc.py input.lrc            # what would be produced
    python tools/lrc.py input.lrc --json     # write work/lines.local.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

# [mm:ss.xx] and [mm:ss.xxx] both occur in the wild; also [mm:ss]
_STAMP = re.compile(r"\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]")


def parse_lrc(text: str) -> list[tuple[float, str]]:
    """[(start_seconds, line_text)] in file order, offset applied, blanks dropped."""
    offset = 0.0
    for m in re.finditer(r"\[offset:\s*([+-]?\d+)\s*\]", text, re.I):
        offset = int(m.group(1)) / 1000.0

    out: list[tuple[float, str]] = []
    for raw in text.splitlines():
        stamps = _STAMP.findall(raw)
        if not stamps:
            continue
        body = _STAMP.sub("", raw).strip()
        if not body:
            continue
        for mm, ss, frac in stamps:
            # '5' -> 0.5 s, '50' -> 0.50 s, '500' -> 0.500 s: one rule covers all three.
            sub = int(frac) / (10 ** len(frac)) if frac else 0.0
            out.append((round(int(mm) * 60 + int(ss) + sub + offset, 3), body))
    out.sort(key=lambda r: r[0])
    return out


def digest_of(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lrc", type=Path)
    ap.add_argument("--json", action="store_true", help="write work/lines.local.json")
    ap.add_argument("--credits", nargs="*", default=[], help="credit lines to embed")
    ap.add_argument("-o", "--out", type=Path, default=None)
    a = ap.parse_args()

    rows = parse_lrc(a.lrc.read_text(encoding="utf-8"))
    tl = json.loads((Path(__file__).resolve().parent.parent / "song.timeline.json")
                    .read_text(encoding="utf-8"))["lines"]
    print(f"{a.lrc.name}: {len(rows)} lyric rows, timeline has {len(tl)}")

    if len(rows) == len(tl):
        bad = [i for i, (_, s) in enumerate(rows) if digest_of(s) != tl[i]["sha256"]]
        dt = [i for i, (t, _) in enumerate(rows) if abs(t - tl[i]["t"]) > 0.02]
        print(f"  sha256 mismatches: {len(bad)}{' -> ' + str(bad[:8]) if bad else ''}")
        print(f"  timing drift >20 ms: {len(dt)}{' -> ' + str(dt[:8]) if dt else ''}")
        if not bad and not dt:
            print("  OK - same edition, same timings")
    else:
        print("  row count differs; not comparing")

    if a.json:
        out = a.out or (Path(__file__).resolve().parent.parent / "work" / "lines.local.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"credits": a.credits, "lines": [[t, s] for t, s in rows]},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
