"""動画の一部のコマ範囲だけをゆっくりにして伸ばす（間は動き補間）。ほかのコマはそのまま。
使い方: one_stretch.py <入力> <出力.mp4> <開始コマ>:<終了コマ(含まない)>:<新しいコマ数> [...]
4本まとめ（動きあり）でナレーションが場面に収まるよう、尾張と三河・金鯱×地図の溶けていない区間を伸ばすのに使った（11-04）。"""
import subprocess, sys
src, out, specs = sys.argv[1], sys.argv[2], [tuple(map(int, s.split(":"))) for s in sys.argv[3:]]
N = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", src],
                       capture_output=True, text=True, check=True).stdout.strip().split(",")[0])
parts, cur, fc = [], 0, []
for a, b, n in sorted(specs):
    if a > cur: parts.append((cur, a, None))
    parts.append((a, b, n)); cur = b
if cur < N: parts.append((cur, N, None))
for k, (a, b, n) in enumerate(parts):
    f = f"[0]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
    if n:   # (b-a) コマを n コマぶんの長さに広げて、24fps に補間
        f += f",setpts=PTS*{(n - 1) / (b - a - 1):.6f},minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,tpad=stop_mode=clone:stop=6,trim=end_frame={n}"   # 最初と最後のコマを元のコマに合わせ、端数で欠けたときだけ末尾を複製
    fc.append(f + f",format=yuv420p,setsar=1,settb=1/24,setpts=N[p{k}]")   # コマ番号で時刻を振り直す（つなぎ目でコマが増えないように）
fc.append("".join(f"[p{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[v]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex", ";".join(fc), "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-r", "24", "-movflags", "+faststart", out], check=True)
M = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", out],
                   capture_output=True, text=True, check=True).stdout.strip()
print("ok", out, N, "→", M, "コマ（期待", N + sum(n - (b - a) for a, b, n in specs), "）")
