"""動画を順→逆に流して、切れ目のないループにする（両端のコマは1回だけ）。使い方: pingpong.py <入力> <出力.mp4> [crop=W:H:X:Y]"""
import subprocess, sys
src, out = sys.argv[1], sys.argv[2]; crop = sys.argv[3] if len(sys.argv) > 3 else None
N = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", src],
                       capture_output=True, text=True, check=True).stdout.strip())
pre = f"crop={crop}," if crop else ""
fc = (f"[0]{pre}trim=end_frame={N},setpts=PTS-STARTPTS,split[a][b];[b]reverse,trim=start_frame=1:end_frame={N - 1},setpts=PTS-STARTPTS[r];"
      "[a][r]concat=n=2:v=1:a=0,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-r", "24", "-movflags", "+faststart", out], check=True)
print("ok", out, "コマ数", 2 * N - 2)
