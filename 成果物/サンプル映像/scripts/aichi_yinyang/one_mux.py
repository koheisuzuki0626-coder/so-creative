"""音を −16 LUFS に揃えて（2パス・音色は変えない）映像に載せる。使い方: one_mux.py <映像.mp4> <音.wav> <出力.mp4>"""
import json, re, subprocess, sys
v, a, out = sys.argv[1:4]
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
m = json.loads(re.search(r"\{[^{}]*\}", r, re.S).group(0)); print("測定", m["input_i"], m["input_tp"], m["input_lra"])
af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
      f"measured_thresh={m['input_thresh']}:offset={m['target_offset']},aresample=48000")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", v, "-i", a, "-map", "0:v", "-map", "1:a", "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
print("ok", out)
