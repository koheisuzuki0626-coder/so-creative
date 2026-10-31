"""4本まとめ・動きを増やした版：各場面にカメラの動きを足してつなぐ。使い方: one_cam.py <油絵.mp4> <尾張と三河.mp4> <金鯱×地図.mp4> <絵地図.mp4> <出力.mp4>
カメラは (時刻 → 倍率・中心) の式で持つ。金鯱→絵地図は同じ式を両方にかけるので、溶ける間も地図の位置が揃う。"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
oil, yin, kin, ezu, out = sys.argv[1:6]
TMP = pathlib.Path("/tmp/aichi_map/one"); PAPER = "#e9e2d2"; H = 980; Y = 50; XF = 1.0; FPS = 24
def wall(w, name):
    x = (1920 - w) // 2
    im = Image.new("RGB", (1920, 1080), PAPER)
    sh = Image.new("L", (1920, 1080), 0); ImageDraw.Draw(sh).rectangle([x + 6, Y + 10, x + w + 6, Y + H + 10], fill=110)
    im.paste(Image.new("RGB", (1920, 1080), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    p = TMP / name; im.save(p); return p, x
def probe(p, f): return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", f"stream={f}", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout.strip()
def ss(a, b, t):   # なめらかに a→b（t は 0〜1）
    t = min(1.0, max(0.0, t)); e = t * t * (3 - 2 * t); return a + (b - a) * e
oil_w = round(1080 * H / 1444); oil_w -= oil_w % 2
w0, x0 = wall(oil_w, "wall_oil.png"); w1, x1 = wall(H, "wall_sq.png")
D = [float(probe(p, "duration")) for p in (oil, yin, kin, ezu)]
t0 = [0.0, D[0] - XF]; t0.append(t0[1] + D[1] - XF); t0.append(t0[2] + D[2] - XF); total = t0[3] + D[3]
print("開始", t0, "尺", total)
TP = t0[3] + XF / 2                     # 金鯱→絵地図の溶けの中央＝いちばん寄った所
CM = (787.0, 470.0); ZM = 1.22          # 太極図の中心へ寄る
def cam_oil(t):                         # 顔へ寄る
    p = t / D[0]; return ss(1.0, 1.28, p), ss(960, 970, p), ss(540, 430, p)
def cam_yin(t):                         # 名古屋の街の寄りから、太極図の全体へ引く
    p = (t - 0.3) / (D[1] - 0.8); return ss(1.55, 1.0, p), ss(793, 960, p), ss(732, 540, p)
def cam_kin_ezu(t):                     # t は全体の時刻
    if t <= TP:
        p = (t - t0[2]) / (TP - t0[2]); return ss(1.0, ZM, p), ss(960, CM[0], p), ss(540, CM[1], p)
    p = (t - TP) / 4.0; return ss(ZM, 1.0, p), ss(CM[0], 960, p), ss(CM[1], 540, p)
def render(args, vf, cam, start, name, n):
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", *args, "-vf" if vf and "[" not in vf else "-filter_complex", vf, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    p = TMP / name
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(p)], stdin=subprocess.PIPE)
    size = 1920 * 1080 * 3; i = 0
    while True:
        b = dec.stdout.read(size)
        if len(b) < size: break
        im = Image.frombytes("RGB", (1920, 1080), b)
        z, cx, cy = cam(start + i / FPS)
        cx = min(1920 - 960 / z, max(960 / z, cx)); cy = min(1080 - 540 / z, max(540 / z, cy))   # 画面の外を映さない
        if abs(z - 1) > 1e-4 or abs(cx - 960) > 1e-3 or abs(cy - 540) > 1e-3:
            im = im.transform((1920, 1080), Image.AFFINE, (1 / z, 0, cx - 960 / z, 0, 1 / z, cy - 540 / z), Image.BICUBIC)
        enc.stdin.write(im.tobytes()); i += 1
    enc.stdin.close(); enc.wait(); dec.wait(); print(name, i, "コマ"); return p
norm = "fps=24,format=rgb24"
n = [round(d * FPS) for d in D]
a = render(["-i", oil, "-loop", "1", "-framerate", "24", "-i", str(w0)], f"[0]scale={oil_w}:{H}:flags=lanczos,setsar=1[p];[1][p]overlay={x0}:{Y}:shortest=1,{norm}", lambda t: cam_oil(t), 0.0, "seg_a.mp4", n[0])
b = render(["-i", yin, "-loop", "1", "-framerate", "24", "-i", str(w1)], f"[0]scale={H}:{H}:flags=lanczos,setsar=1[p];[1][p]overlay={x1}:{Y}:shortest=1,{norm}", lambda t: cam_yin(t - t0[1]), t0[1], "seg_b.mp4", n[1])
c = render(["-i", kin], norm, cam_kin_ezu, t0[2], "seg_c.mp4", n[2])
d = render(["-i", ezu], norm, cam_kin_ezu, t0[3], "seg_d.mp4", n[3])
nm = "fps=24,format=yuv420p,setsar=1,settb=AVTB"
fc = (f"[0]{nm}[v0];[1]{nm}[v1];[2]{nm}[v2];[3]{nm}[v3];"
      f"[v0][v1]xfade=transition=fade:duration={XF}:offset={t0[1]}[x1];[x1][v2]xfade=transition=fade:duration={XF}:offset={t0[2]}[x2];[x2][v3]xfade=transition=fade:duration={XF}:offset={t0[3]}[x3];"
      f"[x3]fade=t=in:st=0:d=0.8:color=0xe9e2d2,fade=t=out:st={total - 1.2}:d=1.2:color=0xe9e2d2,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b), "-i", str(c), "-i", str(d), "-filter_complex", fc, "-map", "[v]", "-t", str(total),
                "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", "-movflags", "+faststart", out], check=True)
json.dump({"t0": t0, "D": D, "total": total}, open(TMP / "cam_timeline.json", "w")); print("ok", out)
