"""C05 用：細かい雪が降り続く透過レイヤー（1920x1080・24fps）を作る。"""
import numpy as np, subprocess, sys
W, H, FPS, DUR = 1920, 1080, 24, 7.0
rng = np.random.default_rng(11)
n = 150
x0 = rng.uniform(0, W, n); y0 = rng.uniform(-H * 0.1, H, n)
vy = rng.uniform(35, 80, n); amp = rng.uniform(8, 24, n); fq = rng.uniform(0.25, 0.7, n); ph = rng.uniform(0, 6.28, n)
rad = rng.uniform(1.4, 3.4, n); al = rng.uniform(0.45, 0.85, n)
kern = {}
def k(r):
    key = round(r, 1)
    if key not in kern:
        s = int(np.ceil(r * 3)); yy, xx = np.mgrid[-s:s + 1, -s:s + 1]
        kern[key] = np.exp(-(xx ** 2 + yy ** 2) / (2 * (r / 1.6) ** 2))
    return kern[key]
out = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "png", "-pix_fmt", "rgba", sys.argv[1]], stdin=subprocess.PIPE)
for f in range(int(DUR * FPS)):
    t = f / FPS
    a = np.zeros((H, W), np.float32)
    ys = (y0 + vy * t) % (H * 1.1) - H * 0.05
    xs = x0 + amp * np.sin(2 * np.pi * fq * t + ph)
    for i in range(n):
        kk = k(rad[i]) * al[i]; s = kk.shape[0] // 2
        cx, cy = int(xs[i]), int(ys[i])
        x1, x2, y1, y2 = cx - s, cx + s + 1, cy - s, cy + s + 1
        if x2 <= 0 or y2 <= 0 or x1 >= W or y1 >= H: continue
        kx1, ky1 = max(0, -x1), max(0, -y1); kx2, ky2 = kk.shape[1] - max(0, x2 - W), kk.shape[0] - max(0, y2 - H)
        a[max(0, y1):min(H, y2), max(0, x1):min(W, x2)] = np.maximum(a[max(0, y1):min(H, y2), max(0, x1):min(W, x2)], kk[ky1:ky2, kx1:kx2])
    fr = np.zeros((H, W, 4), np.uint8); fr[..., :3] = 250; fr[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    out.stdin.write(fr.tobytes())
out.stdin.close(); out.wait(); print("ok")
