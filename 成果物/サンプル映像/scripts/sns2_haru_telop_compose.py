"""SNSショート②（HARU COFFEE STAND）のテロップを、ステッカーの見た目で載せ直す。

    venv/bin/python sns2_haru_telop_design.py <ステッカー置き場>      # 先に絵を作る
    python3 sns2_haru_telop_compose.py <素材置き場> <ステッカー置き場> <出力.mp4>

素材置き場に要るもの（どれも 素材元_台帳.md から Drive で取れる）:
    1224_474b5d92.mp4 / 1219_09db0347.mp4 / 1203_92567696.mp4  … 文字なしの元クリップ
    10_sns.mp4  … 元の完成品（音だけ使う）
文字の時間・暗転は元の完成品から測った値（2026-10-21）。
"""
import json, subprocess, sys
S, D, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
meta = json.load(open(f"{D}/meta.json"))
# 名前, 出る, 消え始め(Noneなら最後まで)
T = [("cap1",0.6,4.42),("cap2",5.6,9.42),("end1",11.5,None),("end2",12.0,None),("end3",12.5,None)]
POP = 0.35   # 弾む時間
def s_expr(t0):
    u = f"clip((t-{t0})/{POP},0,1)"
    # 0.55 → 1.0（easeOutBack で少し行き過ぎて戻る）
    return f"(0.55+0.45*(1+2.70158*pow({u}-1,3)+1.70158*pow({u}-1,2)))"
inputs = ["-i",f"{S}/1224_474b5d92.mp4","-i",f"{S}/1219_09db0347.mp4","-i",f"{S}/1203_92567696.mp4","-i",f"{S}/10_sns.mp4"]
fc = ["[0:v]trim=0:5,setpts=PTS-STARTPTS,scale=1080:1920,setsar=1,fps=24[a]",
      "[1:v]trim=0:5,setpts=PTS-STARTPTS,scale=1080:1920,setsar=1,fps=24[b]",
      "[2:v]trim=0:5,setpts=PTS-STARTPTS,scale=1080:1920,setsar=1,fps=24[c]",
      "[a][b][c]concat=n=3:v=1[v0]"]
last = "v0"
for i,(k,t0,t1) in enumerate(T):
    idx = 4+i
    inputs += ["-loop","1","-framerate","24","-t","15","-i",f"{D}/{k}.png"]
    s = s_expr(t0)
    f = f"[{idx}:v]format=rgba,scale=w='max(2,iw*{s})':h='max(2,ih*{s})':eval=frame,fade=in:st={t0}:d=0.12:alpha=1"
    if t1: f += f",fade=out:st={t1}:d=0.3:alpha=1"
    fc.append(f + f"[s{i}]")
    m = meta[k]
    fc.append(f"[{last}][s{i}]overlay=x='{m['cx']}-w/2':y='{m['cy']}-h/2':eval=frame:enable='gte(t,{t0})'[v{i+1}]")
    last = f"v{i+1}"
fc.append(f"[{last}]fade=out:st=14.42:d=0.58,format=yuv420p[v]")
cmd = ["ffmpeg","-loglevel","error","-y",*inputs,"-filter_complex",";".join(fc),"-map","[v]","-map","3:a",
       "-c:v","libx264","-crf","16","-preset","slow","-c:a","copy","-t","15","-movflags","+faststart",OUT]
subprocess.run(cmd, check=True); print("ok")
