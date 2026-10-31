"""金鯱の動画（1920x1080）を、滑らかにした区間の往復で指定の尺にする。使い方: kin_loop.py <滑らかにした動画> <出力.mp4> <最初のコマ> <秒>"""
import subprocess, sys
src, out, first, sec = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
N = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip().split(",")[0])
L = N - first; cyc = 2 * L - 2; rep = int(sec * 24 / cyc) + 2
fc = (f"[0]trim=start_frame={first}:end_frame={N},setpts=PTS-STARTPTS,split[a][b];[b]reverse,trim=start_frame=1:end_frame={L - 1},setpts=PTS-STARTPTS[r];[a][r]concat=n=2:v=1:a=0,format=yuv420p[v]")
tmp = out + ".cycle.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", "24", tmp], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", str(rep), "-i", tmp, "-frames:v", str(round(sec * 24)), "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", "24", out], check=True)
print("ok", out, "1往復", cyc, "コマ", "使うコマ", round(sec * 24))
