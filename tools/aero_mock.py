"""标定样张: 空气动力学画成「仪表」而不是「象形图」。

两个版本做 A/B，回答一个问题 —— 「塞公式」能不能解决上一轮实测出的那个洞：
    v1 = 只塞内容，调色板不动（还是 amber）
    v2 = 同一张图 + 一层白热（每帧只砸一个元素）

数据全部来自 tools/aero_probe.py 的实算结果，不是编的。
量出墨量/高光/峰值，和上一轮本片实测的 4.53% / 0.00% / 155.8 对比。

用法： python tools/aero_mock.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pv"))
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import tuikit as tk  # noqa: E402

W, H = tk.W, tk.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

# ---------------------------------------------------------------- 数据（实算）
A_1970, A_2009 = 7782.5, 7623.5          # km 半长轴
PERI_1970, PERI_2009 = 439.0, 430.0
APO_1970, APO_2009 = 2384.0, 2075.0
DA = A_1970 - A_2009                      # 159.0
REVS = 179934
RM_PER_REV = DA * 1000 / REVS             # 0.884 m
MS_PER_REV = 1.16                         # ms
DRAG_G = 5.34e-9
AM = 0.004540                             # m^2/kg
TWR = 1.2761
MAXQ_KPA, MAXQ_T, MAXQ_H, MAXQ_M = 18.9, 66.0, 9.3, 1.13
# 2026 外推（衰减随高度降低加速，故比线性更低）—— 标注为外推
A_2026 = A_2009 - (17.0 / 39.0) * DA * 1.25


def hot_col(level, hot):
    """hot=0 时完全是片子的 amber；hot>0 时把最亮的笔画往白里推。"""
    c = tk.amb(level)
    if hot <= 0.0:
        return c
    w = max(0.0, min(1.0, (level - 0.55) / 0.45)) * hot
    return tuple(int(c[i] + (247 - c[i]) * w) for i in range(3))


def chart(img, d, rect, hot, area=False):
    x0, y0, x1, y1 = rect
    pw, ph = x1 - x0, y1 - y0
    LO, HI = 7590.0, 7800.0

    def X(yr):        # yr: 1970..2026
        return x0 + pw * (yr - 1970) / 56.0

    def Y(v):
        return y0 + ph * (HI - v) / (HI - LO)

    def A(yr):
        if yr <= 2009:
            return A_1970 + (A_2009 - A_1970) * (yr - 1970) / (2009 - 1970)
        return A_2009 + (A_2026 - A_2009) * (yr - 2009) / (2026 - 2009)

    # --- 网格
    for k in range(7):
        yy = y0 + ph * k / 6.0
        d.line([(x0, yy), (x1, yy)], fill=tk.amb(0.085))
    for k in range(9):
        xx = x0 + pw * k / 8.0
        d.line([(xx, y0), (xx, y1)], fill=tk.amb(0.055))
    # --- 面积填充: 曲线下方到轴。这是「面」——墨量的真正来源，线条永远堆不出来
    if area:
        for xx in range(int(x0), int(X(2026)) + 1):
            yr = 1970 + 56.0 * (xx - x0) / pw
            yc = Y(A(yr))
            if yc >= y1:
                continue
            span = max(1.0, y1 - yc)
            for yy in range(int(yc), int(y1)):
                lv = 0.48 * (1.0 - (yy - yc) / span) ** 1.4
                d.point((xx, yy), fill=tk.amb(lv))
    # --- 轴
    d.line([(x0, y1), (x1, y1)], fill=tk.amb(0.30))
    d.line([(x0, y0), (x0, y1)], fill=tk.amb(0.30))
    # 实测段 1970->2009 实线
    pts = []
    for k in range(80):
        yr = 1970 + (2009 - 1970) * k / 79.0
        v = A_1970 + (A_2009 - A_1970) * (k / 79.0)
        pts.append((X(yr), Y(v)))
    d.line(pts, fill=hot_col(0.92, hot), width=2)
    # 外推段 2009->2026 虚线
    for k in range(40):
        yr0 = 2009 + (2026 - 2009) * k / 40.0
        yr1 = 2009 + (2026 - 2009) * (k + 0.55) / 40.0
        v0 = A_2009 + (A_2026 - A_2009) * (k / 40.0)
        v1 = A_2009 + (A_2026 - A_2009) * ((k + 0.55) / 40.0)
        d.line([(X(yr0), Y(v0)), (X(yr1), Y(v1))], fill=tk.amb(0.42))
    # 测点
    for yr, v, lab in ((1970, A_1970, "1970 入轨"), (2009, A_2009, "2009 重测")):
        cx, cy = X(yr), Y(v)
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=hot_col(1.0, hot), width=2)
        d.line([(cx, cy), (cx, y1)], fill=tk.amb(0.20))
    # 光标 + 读数（这里就是那个「白热」的落点）
    cur = X(2026)
    d.line([(cur, y0), (cur, y1)], fill=tk.amb(0.35))
    # --- 刻度
    fm = tk.font(tk.F_MONO, 11)
    for yr in (1970, 1980, 1990, 2000, 2009, 2026):
        d.text((X(yr) - 14, y1 + 6), str(yr), font=fm, fill=tk.amb(0.45))
    for v in (7800, 7750, 7700, 7650, 7600):
        d.text((x0 - 44, Y(v) - 7), f"{v}", font=fm, fill=tk.amb(0.40))
    d.text((x0 - 44, y0 - 20), "a / km", font=fm, fill=tk.amb(0.5))


def build(hot, path, area=False):
    img = Image.new("RGB", (W, H), tk.BG)
    d = ImageDraw.Draw(img)
    # ---- chrome: 顶部条
    d.rectangle([0, 0, W, 26], fill=tk.amb(0.06))
    d.line([(0, 26), (W, 26)], fill=tk.amb(0.22))
    d.text((14, 7), "DFH-1  /  轨道力学  /  1970-2026",
           font=tk.font(tk.F_CJK, 13), fill=tk.amb(0.75))
    d.text((W - 300, 7), "Δa = -159.0 km  39 yr",
           font=tk.font(tk.F_MONO, 12), fill=tk.amb(0.6))
    # ---- 大面板框
    P = (70, 80, 830, 560)
    d.rectangle([P[0] - 40, P[1] - 46, P[2] + 24, P[3] + 30], outline=tk.amb(0.18))
    d.text((P[0] - 28, P[1] - 40), "半长轴衰减  a(t)", font=tk.font(tk.F_CJK, 14),
           fill=hot_col(0.95, hot))
    chart(img, d, P, hot, area)
    # ---- 主读数（白热落点）
    hd = tk.font(tk.F_MONO_B, 40)
    d.text((P[0] + 300, P[1] + 34), "0.884", font=hd, fill=hot_col(1.0, hot))
    d.text((P[0] + 300 + 132, P[1] + 52), "m / 圈", font=tk.font(tk.F_CJK, 15),
           fill=tk.amb(0.7))
    d.text((P[0] + 300, P[1] + 92), "每绕地球一周，半长轴只降不到一米",
           font=tk.font(tk.F_CJK, 13), fill=tk.amb(0.62))
    # ---- 右侧读数卡
    C = (880, 80, 1230, 560)
    d.rectangle([C[0], C[1], C[2], C[3]], outline=tk.amb(0.18))
    d.text((C[0] + 12, C[1] - 24), "阻力  a_d = ½ρv²·C_D·A/m",
           font=tk.font(tk.F_CJK, 13), fill=tk.amb(0.8))
    rows = [
        ("迎风面积  A", "0.7854 m²"),
        ("面积质量比 A/m", "0.00454 m²/kg"),
        ("近地点速度 v", "8.115 km/s"),
        ("有效密度 ρ  [假定]", "1.6e-13 kg/m³"),
        ("阻力/重力", "5.34e-9"),
        ("每圈周期增加", "+1.16 ms"),
        ("起飞推重比", "1.276"),
        ("max-Q  [假定]", "18.9 kPa"),
        ("max-Q 马赫数", "1.13"),
        ("滞止温度", "12 °C"),
    ]
    fm = tk.font(tk.F_MONO, 13)
    fc = tk.font(tk.F_CJK, 13)
    yy = C[1] + 18
    for k, (a, b) in enumerate(rows):
        if k in (4, 7):
            d.line([(C[0] + 10, yy - 6), (C[2] - 10, yy - 6)], fill=tk.amb(0.12))
        d.text((C[0] + 12, yy), a, font=fc, fill=tk.amb(0.52))
        d.text((C[0] + 12, yy + 17), b, font=fm, fill=hot_col(0.88, hot))
        yy += 44
    # ---- 底部状态行
    d.line([(0, H - 30), (W, H - 30)], fill=tk.amb(0.20))
    d.text((14, H - 24), "[事实] 439/2384 km · 173 kg · 114 min · 2009 重测 430/2075",
           font=tk.font(tk.F_CJK, 12), fill=tk.amb(0.55))
    d.text((W - 470, H - 24), "[假定] C_D=2.2 · Isp=260s  ·  推算项已标注",
           font=tk.font(tk.F_CJK, 12), fill=tk.amb(0.40))
    img.save(path)
    return img


def metrics(img):
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    L = a.mean(axis=2)
    edge = (abs(np.diff(L, axis=1)).mean() + abs(np.diff(L, axis=0)).mean()) / 2
    return L.mean(), (L > 38).mean() * 100, (L > 120).mean() * 100, \
        (L > 190).mean() * 100, L.max(), edge


if __name__ == "__main__":
    print(f"{'版本':<22} {'mean':>6} {'墨%':>6} {'亮%':>6} {'高光%':>6} {'峰值':>6} {'边缘':>6}")
    print(f"{'本片实测(13帧)':<22} {'':>6} {4.53:>6.2f} {1.29:>6.2f} {0.00:>6.2f} {155.8:>6.1f} {2.90:>6.2f}")
    print(f"{'原片实测(14帧)':<22} {'':>6} {10.41:>6.2f} {2.49:>6.2f} {0.51:>6.2f} {242.0:>6.1f} {'':>6}")
    for tag, hot, area in (("v1  只塞内容", 0.0, False),
                           ("v2  +白热层", 0.92, False),
                           ("v3  面积图", 0.0, True),
                           ("v4  面积+白热", 0.92, True)):
        p = os.path.normpath(os.path.join(OUT, f"mock_aero_{tag.split()[0]}.png"))
        img = build(hot, p, area)
        m = metrics(img)
        print(f"{tag:<22} {m[0]:6.1f} {m[1]:6.2f} {m[2]:6.2f} {m[3]:6.2f} {m[4]:6.1f} {m[5]:6.2f}   -> {p}")
