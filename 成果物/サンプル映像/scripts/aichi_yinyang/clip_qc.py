"""生成動画の確認：6コマの一覧と、色・動きの推移。使い方: clip_qc.py <動画> <出力.jpg> [crop=W:H:X:Y]"""
import subprocess, sys, numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]; crop = sys.argv[3] if len(sys.argv) > 3 else None
vf = (f"crop={crop}," if crop else "")
ims = []
for t in [0, 1, 2, 3, 4, 4.95]:
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", vf + "scale=480:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    import io; ims.append(Image.open(io.BytesIO(p)).convert("RGB"))
w, h = ims[0].size
s = Image.new("RGB", (w * 3 + 20, h * 2 + 10), "white")
for i, im in enumerate(ims): s.paste(im, ((i % 3) * (w + 10), (i // 3) * (h + 10)))
s.save(out, quality=85)
import io as _io
one = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-frames:v", "1", "-vf", vf + "scale=240:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
hh = Image.open(_io.BytesIO(one)).size[1]
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-vf", vf + "scale=240:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, hh, 240, 3).astype(np.float32)
print("コマ", len(fr), "画面全体の色 最初", fr[0].mean((0, 1)).round(1), "最後", fr[-1].mean((0, 1)).round(1))
# 画面を4x4に分けて、各マスの色の変化が一番大きい所を見る
gh, gw = hh // 4, 60
worst = []
for y in range(4):
    for x in range(4):
        v = fr[:, y * gh:(y + 1) * gh, x * gw:(x + 1) * gw].mean((1, 2))
        ch = np.abs(v - v[0]).max(0)
        worst.append((float(ch.max()), (x, y), int(np.abs(v - v[0]).max(1).argmax())))
worst.sort(reverse=True)
print("色の変化が大きいマス(変化量, (列,行), コマ):", [(round(a, 1), b, c) for a, b, c in worst[:4]])
d = np.abs(np.diff(fr.mean(-1), axis=0)).mean((1, 2))
print("動き 中央値 %.3f 最大 %.3f(%dコマ目)  最初→最後 %.3f" % (np.median(d), d.max(), d.argmax(), np.abs(fr[-1] - fr[0]).mean()))
