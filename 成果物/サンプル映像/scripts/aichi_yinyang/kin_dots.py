"""金鯱が大きく動くと玉が魚に隠れるので、絵から切り抜いた玉を城の本当の位置に重ねて固定する（上の層 top.png を top_dots.png にする）。"""
import json, pathlib
import numpy as np
from PIL import Image, ImageFilter
F = pathlib.Path("/tmp/aichi_map/fanim"); p = json.load(open(F / "params.json"))
src = Image.open(pathlib.Path.home() / "Desktop/絵画_2026-10-27/陰陽_案1_金鯱_本物の形.png").convert("RGB")
s = p["s"]; top = Image.open(F / "top.png").convert("RGBA")
for (gx, gy), (px, py), name in (((1192.74, 1369.80), p["P1"], "金"), ((846.13, 681.28), p["P2"], "黒")):
    R = 44                                                     # 絵（2048px）の上の半径
    box = src.crop((int(gx - R), int(gy - R), int(gx + R), int(gy + R)))
    n = round(2 * R * s * 1.125 * 4)                                   # 4倍で作って縮める（縁をきれいに）
    b = box.resize((n, n), Image.LANCZOS)
    yy, xx = np.mgrid[0:n, 0:n]; r = np.hypot(xx - n / 2 + .5, yy - n / 2 + .5)
    rad = 18.0 * 4; a = np.clip((rad - r) / 4.0, 0, 1) * 255
    sp = b.convert("RGBA"); sp.putalpha(Image.fromarray(a.astype(np.uint8)))
    sp = sp.resize((n // 4, n // 4), Image.LANCZOS)
    top.alpha_composite(sp, (round(px - sp.size[0] / 2), round(py - sp.size[1] / 2)))
top.save(F / "top_dots.png"); print("ok", top.size)
