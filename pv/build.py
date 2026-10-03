"""One-shot build: check -> render (parallel, no intermediate files) -> encode -> verify.

Sections are independent so a failure is cheap:
    python build.py check
    python build.py render --frames 48        # calibration slice first
    python build.py render --workers 4
    python build.py encode
    python build.py verify

Why there is no PNG sequence in the middle: at 7922 frames the PNG route wrote 7922 small files and
measured ~1.1 MB/s -- the renders averaged 0.077 s, so the wall clock was almost entirely the file
system (real-time scanning, one event per file). Streaming each worker's frames straight into its own
ffmpeg, and splicing the lossless segments afterwards, removes that cost and keeps the master lossless.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
SR = HERE.parent
sys.path.insert(0, str(HERE))

# ffmpeg is resolved in this order: $PV_FFMPEG, then ffmpeg on PATH, then the layout this build was
# made in. The first two are what a fresh clone will hit - see docs/FONTS.md for the two fonts.
FFMPEG = (os.environ.get("PV_FFMPEG")
          or shutil.which("ffmpeg")
          or str(SR.parent / "_tools" / "ffmpeg" / "bin" / "ffmpeg.exe"))
AUDIO = Path(os.environ.get("PV_SONG", SR / "audio" / "song.mp3"))
TIMELINE = SR / "song.timeline.json"
SEG = SR / "work" / "segments"
OUT = SR / "out"
W, H, FPS = 1280, 720, 24
CHUNK = 120          # 5 s of film per segment: many enough to balance, few enough to splice fast


def total_frames() -> int:
    import pvclock as ck
    return int(round(ck.SONG_LEN * FPS))


def jobs_for(total: int) -> list[tuple[int, int, int]]:
    return [(f, min(f + CHUNK, total), i) for i, f in enumerate(range(0, total, CHUNK))]


# ---------------------------------------------------------------- workers


def _render_segment(job: tuple[int, int, int]):
    """Render [f0, f1) and stream it into this segment's own lossless ffmpeg.

    There is no segment cache. There used to be -- `if seg.exists(): return "cached"` -- and it made
    the build lie: five shots were edited, `render` reported all 7922 frames cached in 0.6 s, and
    `verify` then failed at MAE 12.7 because the master was still the previous film. Keying the
    cache on a digest of the sources fixed that, and then the cache drop itself was refused by the
    safe-delete guard at 50 files, which failed the build a second time. A full render costs about
    three minutes, which is cheap enough to simply not have the problem: every build renders every
    frame, and ffmpeg overwrites the segment in place with -y so nothing is ever deleted either."""
    f0, f1, idx = job
    seg = SEG / f"{idx:04d}.mkv"
    import engine
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}", "-framerate", str(FPS),
           "-i", "-", "-c:v", "utvideo", "-pix_fmt", "rgb24", str(seg)]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(f0, f1):
            p.stdin.write(engine.frame(f / FPS).tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode != 0:
        raise SystemExit(f"segment {idx}: ffmpeg exited {p.returncode}")
    return f0, f1, f1 - f0, time.time() - t0, "ok"


def cmd_render(workers: int, limit: int | None) -> int:
    SEG.mkdir(parents=True, exist_ok=True)
    total = limit or total_frames()
    jobs = jobs_for(total)
    print(f"render {total} frames -> {len(jobs)} segments, {workers} workers")
    t0 = time.time()
    done = 0
    with Pool(workers) as pool:
        for f0, f1, n, dt, tag in pool.imap_unordered(_render_segment, jobs):
            done += n
            el = time.time() - t0
            eta = el / max(1, done) * (total - done) if done else 0
            print(f"  {f1:>6}/{total}  {tag:<6} +{n:>4} in {dt:5.1f}s   elapsed {el:6.1f}s  eta {eta:6.1f}s",
                  flush=True)
    print(f"render done in {time.time() - t0:.1f}s")
    return 0


# ---------------------------------------------------------------- encode


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"ffmpeg failed: {r.returncode}")


def cmd_encode() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    segs = sorted(SEG.glob("*.mkv"))
    if not segs:
        print("no segments")
        return 1
    lst = SEG / "list.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="utf-8")
    master = OUT / "sirius_master.mkv"
    deliver = OUT / "sirius_pv.mp4"
    print(f"=== encode: splice {len(segs)} segments ===")
    # -c:v copy: the segments are already lossless, so the splice must not touch a pixel
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-i", str(AUDIO), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "flac",
          "-shortest", str(master)])
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(master),
          "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
          "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "320k",
          "-movflags", "+faststart", str(deliver)])
    for p in (master, deliver):
        print(f"  {p.name}  {p.stat().st_size / 1e6:.1f} MB")
    return 0


# ---------------------------------------------------------------- verify


def cmd_verify() -> int:
    """Re-render a few instants from source and compare, pixel for pixel, with the master. MAE exactly
    0 proves both 'rendered here' and 'reproducible' in a single measurement."""
    import numpy as np
    import engine
    from PIL import Image
    master = OUT / "sirius_master.mkv"
    if not master.exists():
        print("no master yet")
        return 1
    # One instant per revision, so a regression in any earlier change still shows up here: the
    # programme scenes (121 = 钱学森 portrait, 147 = rostrum, 161 = 星箭对接), the China map (258),
    # the 人民日报 page (294). Section 07 gets four of its own, one per shot, because the whole
    # point of the rework was that its four shots are four different instruments: 205 roster,
    # 216.5 cumulative count, 230 the 1970-2026 span, 241 the machines in place.
    picks = [8.3, 11.3, 20.0, 43.5, 48.6, 80.6, 100.0, 121.0, 147.0, 161.0, 184.5, 189.0,
             205.0, 216.5, 230.0, 241.0, 258.0, 264.0, 277.5, 281.8, 294.0, 300.0]
    tmp = SR / "work" / "verify"
    tmp.mkdir(parents=True, exist_ok=True)
    print("=== verify: source re-render vs master ===")
    lines, worst = [], 0.0
    for t in picks:
        f = int(round(t * FPS))
        dst = tmp / f"m_{f:06d}.png"
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(master),
              "-vf", f"select=eq(n\\,{f})", "-vsync", "0", "-frames:v", "1", str(dst)])
        a = np.asarray(Image.open(dst).convert("RGB"), dtype=np.int16)
        b = np.asarray(engine.frame(f / FPS).convert("RGB"), dtype=np.int16)
        mae = float(np.abs(a - b).mean())
        same = float((a == b).all(axis=2).mean()) * 100
        worst = max(worst, mae)
        lines.append(f"  t={t:7.2f} f={f:>6}  MAE {mae:7.3f}   identical {same:5.1f}%")
    for s in lines:
        print(s)
    print(f"worst MAE {worst:.3f}")
    (OUT / "sirius_verify.txt").write_text("\n".join(lines + [f"worst MAE {worst:.3f}"]), encoding="utf-8")
    return 0


def cmd_check() -> int:
    import direction as dr
    import pvclock as ck
    import tuikit as tk
    ok = True
    print("=== check ===")
    # The newspaper frame is set in three faces the rest of the film does not use; if any of them
    # is missing the 报头 falls back to nothing and the page renders blank across a third of the
    # frame, so they are a build prerequisite rather than a nicety.
    for label, path in (("ffmpeg", Path(FFMPEG)), ("audio", AUDIO), ("timeline", TIMELINE),
                        ("F_CJK", Path(tk.F_CJK)), ("F_MONO", Path(tk.F_MONO)),
                        ("F_KAI", Path(tk.F_KAI)), ("F_HEI", Path(tk.F_HEI)),
                        ("F_SONG", Path(tk.F_SONG))):
        good = path.exists()
        ok &= good
        print(f"[{'OK ' if good else 'BAD'}] {label:<9} {path}")
    bad = dr.check_variety() + dr.check_clock()
    ok &= not bad
    print(f"[{'OK ' if not bad else 'BAD'}] lint       {len(bad)} issue(s)")
    for line in bad[:10]:
        print("        ", line)
    print(f"[OK ] shape      {total_frames()} frames @ {FPS} fps  ({ck.SONG_LEN:.3f} s)")
    print(f"[OK ] clock      BPM {ck.BPM:.3f}  beat {ck.BEAT:.4f} s  {len(ck.ROWS)} lyric rows")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "render", "encode", "verify", "all"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--frames", type=int, default=None)
    a = ap.parse_args()
    if a.cmd == "check":
        return cmd_check()
    if a.cmd == "render":
        return cmd_render(a.workers, a.frames)
    if a.cmd == "encode":
        return cmd_encode()
    if a.cmd == "verify":
        return cmd_verify()
    rc = cmd_check()
    if rc:
        return rc
    rc = cmd_render(a.workers, a.frames)
    if rc or a.frames:
        return rc
    rc = cmd_encode()
    return rc or cmd_verify()


if __name__ == "__main__":
    raise SystemExit(main())
