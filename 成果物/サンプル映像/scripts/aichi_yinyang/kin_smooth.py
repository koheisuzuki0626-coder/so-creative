"""金鯱の動画の 0〜LAST コマを使う。17コマ目以降は2コマに1回しか絵が変わらないので、奇数コマだけ残して間を動き補間する。使い方: kin_smooth.py <入力> <出力.mp4> [LAST]"""
import subprocess, sys
src, out = sys.argv[1], sys.argv[2]; LAST = int(sys.argv[3]) if len(sys.argv) > 3 else 44
sel = f"select='lte(n,16)+(gt(n,16)*mod(n,2)*lte(n,{LAST + 1}))'"
# 残したコマを元の時刻に置いたまま 24fps へ補間する（setpts はそのまま）
fc = (f"[0]{sel},setpts=N/24/TB[a];")
# 0〜16 はそのまま、17 以降は 12fps として補間
cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex",
       f"[0]trim=end_frame=17,setpts=PTS-STARTPTS[h];"
       f"[0]trim=start_frame=17:end_frame={LAST + 2},setpts=PTS-STARTPTS,select='not(mod(n,2))',setpts=N/12/TB,minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none[t];"
       f"[h][t]concat=n=2:v=1:a=0,format=yuv420p[v]", "-map", "[v]", "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", out]
subprocess.run(cmd, check=True); print("ok", out)
