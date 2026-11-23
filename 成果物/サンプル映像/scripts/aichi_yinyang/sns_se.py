"""縦型SNS版：BGMにSEを足す。使い方: sns_se.py <BGM.wav> <出力.wav>（BGMは one_bgm.py で作る）。
   SEは本編 audio_mix.py と同じ合成（コンパス＝scratch、目が落ちる＝blip）。
   コンパス（2.5〜9kHz）はBGMと200Hzより上で比べる（BGMの大半は73Hzの持続音で、スマホでは鳴らないため）。
   目が落ちる（blip・180/140Hz）は高域をほぼ持たないので、全帯域で比べる。200Hz以上で比べると、
   無い高域を合わせようとして全体が巨大になり、最大音量を占めて BGM が沈む（2026-11-08 に一度やった）。"""
import numpy as np, wave, sys
SR = 48000; src, out = sys.argv[1], sys.argv[2]
w = wave.open(src); bgm = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).T / 32767.0; w.close()
N = bgm.shape[1]; rng = np.random.default_rng(29)
def t_(n): return np.arange(n) / SR
def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
def scratch(dur, rate=6.0):
    n = int(SR * dur); x = t_(n); s = bp(rng.standard_normal(n), 2500, 9000)
    strokes = np.clip(np.sin(2 * np.pi * rate * x + 3 * np.sin(2 * np.pi * 0.7 * x)), 0, 1) ** 2
    return s * strokes * np.clip(x / 0.2, 0, 1) * np.clip((dur - x) / 0.3, 0, 1)
def blip(f=180, dur=0.35):
    n = int(SR * dur); x = t_(n); return np.sin(2 * np.pi * f * x * (1 - 0.3 * x)) * np.exp(-x * 14)
rms = lambda x: float(np.sqrt(np.mean(x ** 2)) + 1e-12)
ref = rms(bp(bgm.mean(0), 200, 20000))                       # BGMの200Hz以上の音量（全体）
ref_full = rms(bgm.mean(0))                                   # BGMの全帯域の音量
print(f"BGM 200Hz以上 RMS = {20*np.log10(ref):.1f} dBFS")
se = np.zeros_like(bgm)
def place(sig, at, ratio, pan, label, full=False):
    hp = sig if full else bp(sig, 200, 20000); act = hp[: max(1, int(SR * 0.25))] if len(sig) < SR else hp
    g = ratio * (ref_full if full else ref) / rms(act)                                 # 鳴っている区間の音量を BGM×ratio に合わせる
    i = int(at * SR); j = min(N, i + len(sig)); l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    se[0, i:j] += sig[: j - i] * g * l; se[1, i:j] += sig[: j - i] * g * r
    print(f"  {label:<26} {at:5.2f}s  対BGM {20*np.log10(ratio):+.1f}dB（{'全帯域' if full else '200Hz以上'}）")
place(scratch(1.9, 3.0), 4.55, 0.8, 0.0, "コンパス（円をひとつ描く）")
place(blip(180), 9.00, 1.4, -0.3, "目が落ちる：名古屋城（左）", full=True)
place(blip(140), 9.15, 1.4, +0.3, "目が落ちる：岡崎城（右）", full=True)
x = bgm + se; x = x / max(1e-6, np.abs(x).max()) * 0.89
w = wave.open(out, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((x.T * 32767).astype(np.int16).tobytes()); w.close(); print("ok", out)
