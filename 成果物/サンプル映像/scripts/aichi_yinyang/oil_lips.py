"""油絵の人物の動画で開いた口を閉じる：口が閉じているコマの唇を、顔の動きを追って重ねる。使い方: oil_lips.py <入力> <出力.mp4>"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageFilter
src, out = sys.argv[1], sys.argv[2]
W, H = 1080, 1444
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
REF = 20; F0, F1 = 22, 86          # 重ねる範囲。F0〜F0+6 で入れ、F1-6〜F1 で抜く
CX, CY, RX, RY, FEATHER = 633, 578, 92, 46, 16
def gray(f): return np.asarray(Image.fromarray(f).convert("L").filter(ImageFilter.GaussianBlur(2.0)), dtype=np.float32)
g0 = gray(fr[REF])
# 顔の動きは、唇を避けて鼻のまわりとあごで測る
boxes = [(585, 470, 705, 535), (560, 630, 720, 690)]
def cost(g, dx, dy):
    c = 0.0
    for x0, y0, x1, y1 in boxes:
        a = g[y0 + dy:y1 + dy, x0 + dx:x1 + dx]; b = g0[y0:y1, x0:x1]
        c += float(np.mean(((a - a.mean()) - (b - b.mean())) ** 2))
    return c
track = np.zeros((len(fr), 2)); px, py = 0, 0
for i in range(REF, len(fr)):
    g = gray(fr[i]); best = (1e18, px, py)
    for dy in range(py - 6, py + 7):
        for dx in range(px - 6, px + 7):
            c = cost(g, dx, dy)
            if c < best[0]: best = (c, dx, dy)
    px, py = best[1], best[2]; track[i] = (px, py)
k = np.ones(7) / 7
track = np.c_[np.convolve(np.pad(track[:, 0], 3, mode="edge"), k, "valid"), np.convolve(np.pad(track[:, 1], 3, mode="edge"), k, "valid")]
print("顔の動き（px）最大", np.abs(track[F0:F1]).max(0).round(1), "| f28", track[28].round(1), "f52", track[52].round(1), "f76", track[76].round(1))
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
res = fr.copy()
for i in range(F0, F1 + 1):
    a = min(1.0, (i - F0) / 6) * min(1.0, (F1 - i) / 6)
    if a <= 0: continue
    dx, dy = track[i]
    r = np.hypot((xx - CX - dx) / RX, (yy - CY - dy) / RY)
    m = np.clip((1 - r) * min(RX, RY) / FEATHER, 0, 1); m = m * m * (3 - 2 * m) * a
    x0, x1, y0, y1 = int(CX + dx - RX - 8), int(CX + dx + RX + 8), int(CY + dy - RY - 8), int(CY + dy + RY + 8)
    ref = np.asarray(Image.fromarray(fr[REF]).transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy), Image.BICUBIC), dtype=np.float32)
    ring = (r > 1.0) & (r < 1.4)      # 光の変化に合わせる（周りの明るさを揃える）
    gain = fr[i][ring].mean(0) / (ref[ring].mean(0) + 1e-6)
    p = ref * gain
    res[i, y0:y1, x0:x1] = np.clip(fr[i, y0:y1, x0:x1] * (1 - m[y0:y1, x0:x1, None]) + p[y0:y1, x0:x1] * m[y0:y1, x0:x1, None], 0, 255).astype(np.uint8)
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
p.stdin.write(res.tobytes()); p.stdin.close(); p.wait(); print("ok", out)
