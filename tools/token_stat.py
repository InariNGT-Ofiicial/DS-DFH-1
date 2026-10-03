"""Count tokens actually spent, straight out of the session transcripts.

Source of truth = the `usage` block the provider returns with every assistant output, which the host
appends to each record in `<project>/<session>.jsonl`. We sum reported numbers; we never estimate
from text or character counts.

Shape of one record (2026-10-01, deepseek-v4.1-flash):
    {"type": "message" | "function_call", "message": {"usage": {...}}, "providerData": {"usage": {...}}}
The two usage blocks are the SAME request seen twice (snake_case vs camelCase) -- so a record must be
counted exactly once, never per-block.

Counter semantics (verified against samples, do NOT assume the Anthropic convention here):
    input_tokens        total input, *including* everything served from cache
    cache_read_input_tokens   the cached subset of input_tokens  (NOT additive)
    output_tokens       generated
    total_tokens        == input_tokens + output_tokens
So:
    fresh input = input_tokens - cache_read_input_tokens   <- the part that is not cache-served
    processed   = sum(total_tokens)
Additive counters are reported separately; `fresh input` is derived.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

PROJ = Path.home() / ".workbuddy" / "projects"
DB = Path.home() / ".workbuddy" / "workbuddy.db"

# relative price weights, only to fold four counters into one comparable number.
# cache is cheap, output is dear. Edit here if prices change; not a quote, a shape.
W_FRESH, W_CACHE, W_OUT = 1.0, 0.1, 4.0


def usage_of(rec: dict):
    """One record -> one usage dict, or None. Prefers the snake_case copy."""
    msg = rec.get("message")
    if isinstance(msg, dict):
        u = msg.get("usage")
        if isinstance(u, dict) and "input_tokens" in u:
            return u
    pd = rec.get("providerData")
    if isinstance(pd, dict):
        u = pd.get("usage")
        if isinstance(u, dict) and "inputTokens" in u:
            return {"input_tokens": u.get("inputTokens", 0),
                    "output_tokens": u.get("outputTokens", 0),
                    "total_tokens": u.get("totalTokens", 0),
                    "cache_read_input_tokens": 0}
    return None


def blank():
    return {"reqs": 0, "in": 0, "cache_read": 0, "cache_write": 0, "out": 0,
            "total": 0, "by_type": {}, "models": {}}


def scan(path: Path, acc: dict) -> None:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            u = usage_of(rec)
            if not u:
                continue
            it = int(u.get("input_tokens") or 0)
            ot = int(u.get("output_tokens") or 0)
            cr = int(u.get("cache_read_input_tokens") or 0)
            cw = int(u.get("cache_creation_input_tokens") or 0)
            tot = int(u.get("total_tokens") or (it + ot))
            acc["reqs"] += 1
            acc["in"] += it
            acc["cache_read"] += cr
            acc["cache_write"] += cw
            acc["out"] += ot
            acc["total"] += tot
            t = rec.get("type", "?")
            acc["by_type"][t] = acc["by_type"].get(t, 0) + 1
            mm = rec.get("providerData") or {}
            name = mm.get("requestModelName") or mm.get("model")
            if name:
                acc["models"][name] = acc["models"].get(name, 0) + 1


def add(dst, src):
    for k in ("reqs", "in", "cache_read", "cache_write", "out", "total"):
        dst[k] += src[k]
    for k in ("by_type", "models"):
        for kk, vv in src[k].items():
            dst[k][kk] = dst[k].get(kk, 0) + vv


def fmt(n):
    return f"{n:,}"


def M(n):
    return f"{n/1e6:.2f}M"


def report(title, a):
    fresh = a["in"] - a["cache_read"]
    fold = fresh * W_FRESH + a["cache_read"] * W_CACHE + a["cache_write"] * W_CACHE + a["out"] * W_OUT
    print(f"\n{'='*62}\n{title}\n{'='*62}")
    print(f"  API requests                 {fmt(a['reqs'])}")
    print(f"  input  (total)         {fmt(a['in']):>16}   {M(a['in'])}")
    print(f"    - served from cache  {fmt(a['cache_read']):>16}   {M(a['cache_read'])}"
          f"   ({100*a['cache_read']/max(1,a['in']):.1f}% of input)")
    print(f"    = fresh input        {fmt(fresh):>16}   {M(fresh)}")
    if a["cache_write"]:
        print(f"  cache write            {fmt(a['cache_write']):>16}   {M(a['cache_write'])}")
    print(f"  output                 {fmt(a['out']):>16}   {M(a['out'])}")
    print(f"  ------------------------------------------------------------------")
    print(f"  TOTAL processed        {fmt(a['total']):>16}   {M(a['total'])}")
    print(f"  price-folded equiv     {fmt(int(fold)):>16}   {M(int(fold))}"
          f"   (cache x{W_CACHE}, output x{W_OUT})")
    if a["by_type"]:
        print(f"  by record type: " + ", ".join(f"{k}={v}" for k, v in sorted(a['by_type'].items())))
    if a["models"]:
        print(f"  models: " + ", ".join(f"{k}={v}" for k, v in sorted(a['models'].items())))


def credits(session_ids):
    """The platform's own credit counter, per request, from session_usage.credit_json."""
    if not DB.exists():
        return None
    try:
        c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
        total, hit, rows = 0.0, 0, []
        for sid in session_ids:
            r = c.execute("select used,size,credit_json from session_usage where session_id=?",
                          (sid,)).fetchone()
            if not r:
                continue
            used, size, cj = r
            s = 0.0
            n = 0
            if cj:
                try:
                    d = json.loads(cj)
                    s = sum(float(v) for v in d.values() if isinstance(v, (int, float)))
                    n = len(d)
                except Exception:
                    pass
            total += s
            hit += 1
            rows.append((sid, used, size, s, n))
        return total, hit, rows
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="*", default=None, help="project dir names under ~/.workbuddy/projects")
    ap.add_argument("--match", default=None, help="substring filter on project dir names")
    args = ap.parse_args()

    if not PROJ.exists():
        print(f"no {PROJ}")
        return
    dirs = sorted(d for d in PROJ.iterdir() if d.is_dir())
    if args.dirs:
        want = set(args.dirs)
        dirs = [d for d in dirs if d.name in want]
    if args.match:
        dirs = [d for d in dirs if args.match in d.name]
    if not dirs:
        print("no matching dirs")
        return

    grand = blank()
    for d in dirs:
        files = sorted(d.glob("*.jsonl"))
        if not files:
            continue
        acc = blank()
        for f in files:
            scan(f, acc)
        if not acc["reqs"]:
            continue
        add(grand, acc)
        report(f"{d.name}   ({len(files)} session file)"
               f"   [{sum(f.stat().st_size for f in files)/1e6:.1f} MB]", acc)
    if len(dirs) > 1 and grand["reqs"]:
        report(f"GRAND TOTAL across {len(dirs)} workspaces", grand)


if __name__ == "__main__":
    main()
