"""金鯱の動画（1920x1080・中央に正方形の絵）を、地図の上に回転・拡大して重ねる。使い方: fusion_anim.py <金鯱の動画> <出力.mp4> [秒数]"""
import json, math, subprocess, sys
clip, out = sys.argv[1], sys.argv[2]; dur = sys.argv[3] if len(sys.argv) > 3 else None
F = "/tmp/aichi_map/fanim"; p = json.load(open(f"{F}/params.json"))
SZ, WC, GX, GY, th = p["SZ"], p["WC"], p["GX"], p["GY"], p["theta"]
X0, Y0 = p["P1"][0] - WC / 2, p["P1"][1] - WC / 2
R0 = SZ / 2 * 0.977
# color の既定は25fps。r=24 を付けないと24fpsの動画と混ざって毎秒1コマ重複する（10-30 実測）
fc = (f"[1]fps=24,setpts=PTS-STARTPTS,crop=1080:1080:420:0,scale={SZ}:{SZ}:flags=lanczos,format=rgba[pt];"
      f"color=c=black:s={SZ}x{SZ}:r=24:d=1,format=gray,geq=lum='255*clip(({R0:.2f}-hypot(X-{SZ/2},Y-{SZ/2}))/({R0*0.2:.2f}),0,1)'[mk];"
      f"[pt][mk]alphamerge[pa];color=c=white:s={SZ}x{SZ}:r=24[wsq];[wsq][pa]overlay=shortest=1[pw];"
      f"[pw]pad={WC}:{WC}:{WC/2-GX:.1f}:{WC/2-GY:.1f}:color=white,rotate={th:.6f}:ow={WC}:oh={WC}:fillcolor=white[pr];"
      f"color=c=white:s=1920x1080:r=24[wc];[wc][pr]overlay=x={X0:.1f}:y={Y0:.1f}:shortest=1,format=gbrp[layer];"
      f"[0]format=gbrp[bs];[bs][layer]blend=all_mode=multiply:shortest=1,format=yuv420p[mix];[mix][2]overlay=0:0:shortest=1,format=yuv420p[v]")
cmd = ["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "24", "-i", f"{F}/base.png", "-i", clip, "-loop", "1", "-framerate", "24", "-i", f"{F}/top.png",
       "-filter_complex", fc, "-map", "[v]", *(["-t", dur] if dur else ["-shortest"]), "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", out]
subprocess.run(cmd, check=True); print("ok", out)
