"""4本を1本に：油絵の人物→尾張と三河→金鯱×地図→絵地図。絵は紙の色の壁に掛けた形で 1920x1080 に置く。使い方: one_make.py <BGM.wav> <出力.mp4>"""
import pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
bgm, out = sys.argv[1], sys.argv[2]
D = pathlib.Path.home() / "Desktop/絵画_2026-10-27"; TMP = pathlib.Path("/tmp/aichi_map/one")
CLIPS = {"oil": D / "油絵の人物_動画.mp4", "sq": D / "尾張と三河_動画.mp4", "kin": D / "融合_金鯱×地図_動画.mp4", "ezu": D / "絵地図_動画.mp4"}
PAPER = "#e9e2d2"; H = 980; Y = 50; XF = 1.0
def wall(w, name):
    x = (1920 - w) // 2
    im = Image.new("RGB", (1920, 1080), PAPER)
    sh = Image.new("L", (1920, 1080), 0); ImageDraw.Draw(sh).rectangle([x + 6, Y + 10, x + w + 6, Y + H + 10], fill=110)
    im.paste(Image.new("RGB", (1920, 1080), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    p = TMP / name; im.save(p); return p, x
def probe(p, f): return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", f"stream={f}", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout.strip()
oil_w = round(1080 * H / 1444); oil_w -= oil_w % 2
w0, x0 = wall(oil_w, "wall_oil.png"); w1, x1 = wall(H, "wall_sq.png")
dur = [float(probe(CLIPS[k], "duration")) for k in ("oil", "sq", "kin", "ezu")]
off1 = dur[0] - XF; off2 = off1 + dur[1] - XF; off3 = off2 + dur[2] - XF; total = off3 + dur[3]
norm = "fps=24,format=yuv420p,setsar=1,settb=AVTB"
fc = (f"[0]scale={oil_w}:{H}:flags=lanczos,setsar=1[p0];[1]format=yuv420p,setsar=1[w0];[w0][p0]overlay={x0}:{Y}:shortest=1,{norm}[v0];"
      f"[2]scale={H}:{H}:flags=lanczos,setsar=1[p1];[3]format=yuv420p,setsar=1[w1];[w1][p1]overlay={x1}:{Y}:shortest=1,{norm}[v1];"
      f"[4]{norm}[v2];[5]{norm}[v3];"
      f"[v0][v1]xfade=transition=fade:duration={XF}:offset={off1}[x1];[x1][v2]xfade=transition=fade:duration={XF}:offset={off2}[x2];[x2][v3]xfade=transition=fade:duration={XF}:offset={off3}[x3];"
      f"[x3]fade=t=in:st=0:d=0.8:color=0xe9e2d2,fade=t=out:st={total - 1.2}:d=1.2:color=0xe9e2d2,format=yuv420p[v];"
      f"[6]atrim=0:{total},afade=t=in:d=1.0,afade=t=out:st={total - 2}:d=2,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]")
cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(CLIPS["oil"]), "-loop", "1", "-framerate", "24", "-i", str(w0), "-i", str(CLIPS["sq"]), "-loop", "1", "-framerate", "24", "-i", str(w1),
       "-i", str(CLIPS["kin"]), "-i", str(CLIPS["ezu"]), "-i", bgm, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", str(total),
       "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True); print("ok", out, "尺", total, "つなぎ目", off1, off2, off3)
