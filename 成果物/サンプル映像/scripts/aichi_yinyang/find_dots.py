"""絵の中の「目」（小さな円）の中心を、色と範囲から測る。"""
import numpy as np, subprocess, sys
def load(p):
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip().split(","))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(int)
def blob(img, box, cond):
    x0, y0, x1, y1 = box; sub = img[y0:y1, x0:x1]
    m = cond(sub[..., 0], sub[..., 1], sub[..., 2]); ys, xs = np.nonzero(m)
    if len(xs) < 50: return None
    # いちばん大きい塊だけを見るため、中央値の近くに絞る
    cx, cy = np.median(xs), np.median(ys); r = np.sqrt(((xs - cx) ** 2 + (ys - cy) ** 2))
    k = r < np.percentile(r, 70) * 1.6
    return (x0 + xs[k].mean(), y0 + ys[k].mean(), int(k.sum()))
D = "/Users/suzukikohei/Desktop/絵画_2026-10-27/"
kin = load(D + "陰陽_案1_金鯱_本物の形.png")
print("金鯱 黒い玉", blob(kin, (770, 610, 900, 750), lambda r, g, b: (r < 60) & (g < 60) & (b < 60)))
print("金鯱 金の玉", blob(kin, (1080, 1240, 1320, 1480), lambda r, g, b: (r > 170) & (g > 120) & (b < 110) & (r - b > 90)))
yin = load(D + "陰陽_案2_尾張と三河_v2.png")
print("案2 月の円盤", blob(yin, (880, 440, 1180, 740), lambda r, g, b: (b > 60) & (r < 70) & (g < 80)))
print("案2 太陽", blob(yin, (880, 1300, 1180, 1620), lambda r, g, b: (r > 200) & (g > 140) & (b < 120)))
