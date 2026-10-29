"""全21カットをつなぎ、音を載せる。AI画のカットは、静止画（STILL）かKlingの動画（KLING_DIR に Cxx.mp4 があればそちら）を使う。"""
import subprocess, pathlib, sys, os
FR = pathlib.Path("/tmp/aichi_map/frames"); AN = pathlib.Path("/tmp/aichi_map/anim"); ED = pathlib.Path("/tmp/aichi_map/edit")
AUDIO, OUTFILE = sys.argv[1], sys.argv[2]
KLING = pathlib.Path(os.environ.get("KLING_DIR", "/nonexistent"))
SEGDIR = ED / "seg"; SEGDIR.mkdir(exist_ok=True)
import json
CUTS = [tuple(x) for x in json.load(open("/tmp/aichi_map/timeline.json"))]
KB = {  # 静止画の動き：z=ズーム式、x,y=位置式（on=出力コマ番号、N=総コマ数）
 "C05": ("1+0.08*on/N", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
 "C06": ("1.10", "(iw-iw/zoom)*(1-on/N)", "(ih-ih/zoom)/2"),
 "C09": ("1+0.10*on/N", "(iw-iw/zoom)/2", "(ih-ih/zoom)*(0.60-0.10*on/N)"),
 "C10": ("1.05+0.05*on/N", "(iw-iw/zoom)/2+14*sin(on*1.7)+9*sin(on*0.73)", "(ih-ih/zoom)/2+11*cos(on*1.3)"),
 "C11": ("1+0.05*on/N", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
 "C13": ("1.12", "(iw-iw/zoom)*on/N", "(ih-ih/zoom)/2"),
 "C14": ("1+0.10*on/N", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
 "C17": ("1+0.12*on/N", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
 "C18": ("1.12", "(iw-iw/zoom)*on/N", "(ih-ih/zoom)/2"),
}
ENC = ["-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "24"]
def run(cmd): subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *cmd], check=True)
segs = []
for cut, d in CUTS:
    n = round(d * 24); out = SEGDIR / f"{cut}.mp4"; tel = ED / f"tel_{cut}.png"
    tel_in = ["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(tel)] if tel.exists() else []
    tel_f = (f";[1]format=rgba,fade=in:st=0.5:d=0.5:alpha=1,fade=out:st={d - 0.9}:d=0.5:alpha=1[tl];[v][tl]overlay=0:0[v2]") if tel.exists() else ";[v]null[v2]"
    tail = f",fade=out:st={d - 0.8}:d=0.8" if cut == "C21" else ""
    if (AN / f"{cut}.mp4").exists() and not (cut == "C21" and (KLING / "C21.mp4").exists()):   # 絵地図の締めがあれば、そちらを優先
        run(["-i", str(AN / f"{cut}.mp4"), *tel_in, "-filter_complex", f"[0]setpts=PTS-STARTPTS{tail}[v]{tel_f}", "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
    elif cut == "C21" and (KLING / "C21.mp4").exists():
        # 最後：C20 の地図から絵地図へ溶けて替わる。縮尺をC20にそろえて（0.966倍）から、ゆっくり寄る
        last20 = sorted((AN / "C20").glob("f*.jpg"))[-1]
        title = pathlib.Path("/tmp/aichi_map/v4/title.png")
        zf = f"[1]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=24,setsar=1,pad=1988:1118:34:19:color=0xe9e2d2,zoompan=z='1+0.0766*on/{n - 1}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s=1920x1080:fps=24,trim=duration={d},setpts=PTS-STARTPTS[k]"
        run(["-loop", "1", "-framerate", "24", "-t", "1.2", "-i", str(last20), "-i", str(KLING / "C21.mp4"), "-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(title),
             "-filter_complex", f"[0]scale=1920:1080,setsar=1,format=yuv420p,fps=24,settb=AVTB[a];{zf};[k]format=yuv420p,fps=24,settb=AVTB[k2];[a][k2]xfade=transition=fade:duration=1.2:offset=0[v];"
                                f"[2]format=rgba,fade=in:st=1.2:d=1.0:alpha=1[tl];[v][tl]overlay=0:0,fade=out:st={d - 0.8}:d=0.8[v2]",
             "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
    elif (KLING / f"{cut}.mp4").exists():
        kb = f"[0]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=24,setsar=1,setpts=PTS-STARTPTS"
        if cut == "C11":   # Kling の動画でも、後半は地図の勾玉に溶けて替わる
            yin = AN / "C07" / "f0000.jpg"
            run(["-i", str(KLING / f"{cut}.mp4"), "-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(yin), *(["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(tel)] if tel.exists() else []),
                 "-filter_complex", f"{kb},trim=duration={d}[a];[1]scale=1920:1080,setsar=1[b];[a][b]xfade=transition=fade:duration=1.5:offset={d - 1.5}[v]" + (f";[2]format=rgba,fade=in:st=0.5:d=0.5:alpha=1,fade=out:st={d - 0.9}:d=0.5:alpha=1[tl];[v][tl]overlay=0:0[v2]" if tel.exists() else ";[v]null[v2]"),
                 "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
        elif (KLING / f"{cut}_snow.mov").exists():   # 雪を重ねる（C05）
            run(["-i", str(KLING / f"{cut}.mp4"), "-i", str(KLING / f"{cut}_snow.mov"), *(["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(tel)] if tel.exists() else []),
                 "-filter_complex", f"{kb}[k];[1]format=rgba[s];[k][s]overlay=0:0[v]" + (f";[2]format=rgba,fade=in:st=0.5:d=0.5:alpha=1,fade=out:st={d - 0.9}:d=0.5:alpha=1[tl];[v][tl]overlay=0:0[v2]" if tel.exists() else ";[v]null[v2]"),
                 "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
        else:
            run(["-i", str(KLING / f"{cut}.mp4"), *tel_in, "-filter_complex", f"{kb}[v]{tel_f}", "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
    else:
        z, x, y = (e.replace("N", str(n - 1)) for e in KB[cut])
        src = FR / (f"{cut}_src.png" if (FR / f"{cut}_src.png").exists() else f"{cut}.png")
        base = f"[0]scale=3840:-2,zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1920x1080:fps=24,setsar=1"
        if cut == "C11":   # 後半で地図の勾玉に溶けて替わる
            yin = AN / "C07" / "f0000.jpg"
            run(["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(src), "-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(yin), *(["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(tel)] if tel.exists() else []),
                 "-filter_complex", f"{base}[a];[1]scale=1920:1080,setsar=1[b];[a][b]xfade=transition=fade:duration=1.5:offset={d - 1.5}[v]" + (f";[2]format=rgba,fade=in:st=0.5:d=0.5:alpha=1,fade=out:st={d - 0.9}:d=0.5:alpha=1[tl];[v][tl]overlay=0:0[v2]" if tel.exists() else ";[v]null[v2]"),
                 "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
        else:
            run(["-loop", "1", "-framerate", "24", "-t", str(d), "-i", str(src), *tel_in, "-filter_complex", f"{base}[v]{tel_f}", "-map", "[v2]", "-frames:v", str(n), *ENC, str(out)])
    segs.append(out); print(cut, "ok", flush=True)
lst = ED / "list.txt"; lst.write_text("".join(f"file '{s}'\n" for s in segs))
run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(ED / "video.mp4")])
run(["-i", str(ED / "video.mp4"), "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
     "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", OUTFILE])
print("done", OUTFILE)
