"""方案 A（上采样 4K）的质量取证。

A 方案不重绘像素，只把 720p 母版插值放大。所以唯一需要回答的是：
**放大这一步本身引入了多少损失？**

判据用「4K -> 降采样回 720p -> 与原帧逐像素比」：
- MAE 越接近 0，说明 lanczos 放大几乎没破坏原有信息（4K 只是把同样的像素摊薄）
- 同时出视觉对比图：720p 像素放大 vs 4K lanczos，看的是"边缘是方块还是平滑"
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pv"))

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import engine

OUT = HERE.parent / "out"
T = 100.0
S = 3

im = engine.frame(T).convert("RGB")
W, H = im.size
up_l = im.resize((W * S, H * S), Image.LANCZOS)
up_n = im.resize((W * S, H * S), Image.NEAREST)

back = up_l.resize((W, H), Image.LANCZOS)
a = np.asarray(im, dtype=np.int16)
b = np.asarray(back, dtype=np.int16)
d = np.abs(a - b)
print(f"source          {W}x{H}")
print(f"upscaled        4K {W*S}x{H*S}  flags=lanczos")
print(f"round-trip MAE  4K -> 720p = {d.mean():.3f}    max {d.max()}    "
      f"identical {(a == b).all(axis=2).mean() * 100:.2f}%")

box = (0, 0, 640, 360)
big = (1920, 1080)
left = im.crop(box).resize(big, Image.NEAREST)
right = up_l.crop((0, 0, 1920, 1080))

cw = 1400
ch = int(big[1] * cw / big[0])
left = left.resize((cw, ch), Image.LANCZOS)
right = right.resize((cw, ch), Image.LANCZOS)

sheet = Image.new("RGB", (cw, ch * 2 + 76), (10, 8, 6))
dr = ImageDraw.Draw(sheet)
f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 21)
dr.text((10, 8), "720p original pixels, x3 nearest  --  how 720p looks on a 4K panel",
        font=f, fill=(255, 176, 0))
sheet.paste(left, (0, 38))
dr.text((10, ch + 46), "4K upscaled, flags=lanczos  --  what plan A actually delivers",
        font=f, fill=(255, 176, 0))
sheet.paste(right, (0, ch + 76))
sheet.save(OUT / "ttl4k_compare.png")
print(f"saved {OUT / 'ttl4k_compare.png'}  {sheet.size}")
