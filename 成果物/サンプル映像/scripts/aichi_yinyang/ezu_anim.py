"""動く絵地図：Kling の絵地図（カメラ固定・高画質版）を順→逆に流し、線・地名・題字の層を重ねる。使い方: ezu_anim.py <絵地図の動画> <出力.mp4>"""
import subprocess, sys
clip, out = sys.argv[1], sys.argv[2]
LAYER = "/tmp/aichi_map/ezanim/layer.png"
N = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", clip],
                       capture_output=True, text=True, check=True).stdout.strip())
# 逆再生は N-2 コマ目から 1 コマ目まで。両端を2回続けないので、ループの継ぎ目でも止まって見えない
fc = (f"[0]trim=end_frame={N},setpts=PTS-STARTPTS,split[a][b];[b]reverse,trim=start_frame=1:end_frame={N - 1},setpts=PTS-STARTPTS[r];"
      "[a][r]concat=n=2:v=1:a=0[v0];[1]format=rgba[l];[v0][l]overlay=0:0:shortest=1,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", clip, "-loop", "1", "-framerate", "24", "-i", LAYER, "-filter_complex", fc,
                "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", out], check=True)
print("ok", out, "コマ数", N + N - 2)
