"""Kling の動画を落として、尺と解像度を確かめ、時間をずらした6コマを1枚に並べる。
使い方: python3 kling_qc.py C05=URL C06=URL ..."""
import subprocess, sys, pathlib
K = pathlib.Path("/tmp/aichi_map/kling")
for arg in sys.argv[1:]:
    cut, url = arg.split("=", 1)
    f = K / f"{cut}_raw.mp4"
    subprocess.run(["curl", "-sfL", "-o", str(f), url], check=True)
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                           "-of", "compact=p=0:nk=1", str(f)], capture_output=True, text=True).stdout.split()
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout)
    ts = [d * i / 6 + 0.05 for i in range(6)]
    args = []
    for t in ts: args += ["-ss", f"{t:.2f}", "-i", str(f)]
    fc = "".join(f"[{i}:v]scale=640:-2[v{i}];" for i in range(6)) + "[v0][v1][v2]hstack=3[a];[v3][v4][v5]hstack=3[b];[a][b]vstack"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args, "-filter_complex", fc, "-frames:v", "1", str(K / f"{cut}_qc.jpg")], check=True)
    print(cut, info, f"{d:.2f}s")
