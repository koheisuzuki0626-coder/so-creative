"""4本まとめのBGM（34秒）。本編と同じ合成：持続音＋琴の爪弾き（都節）＋尺八の息。使い方: one_bgm.py <出力.wav>"""
import numpy as np, sys, wave
SR = 48000; T = 34.0; N = int(SR * (T + 0.5))
rng = np.random.default_rng(29)
def t_(n): return np.arange(n) / SR
def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if j <= i: return
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    buf[0, i:j] += sig[:j - i] * gain * l; buf[1, i:j] += sig[:j - i] * gain * r
def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
bgm = np.zeros((2, N)); tt = t_(N)
drone = 0.55 * np.sin(2 * np.pi * 73.42 * tt) + 0.35 * np.sin(2 * np.pi * 110.0 * tt + 1.0) + 0.12 * np.sin(2 * np.pi * 146.83 * tt)
drone *= 0.55 + 0.45 * np.sin(2 * np.pi * tt / 11.0) ** 2
env = np.clip(tt / 3.0, 0, 1) * np.clip((T - tt) / 3.0, 0, 1)
bgm[0] += drone * env * 0.16; bgm[1] += drone * env * 0.16 * 0.95
SCALE = [293.66, 311.13, 392.00, 440.00, 466.16, 587.33, 622.25, 783.99]
def pluck(f, dur=2.2):
    n = int(SR * dur); x = t_(n)
    s = sum(a * np.sin(2 * np.pi * f * h * x) * np.exp(-x * (2.2 + 1.6 * h)) for h, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12)))
    return (s + np.exp(-x * 120) * rng.standard_normal(n) * 0.25) * np.clip(x / 0.004, 0, 1)
t0 = 1.4
while t0 < T - 5.0:
    place(bgm, pluck(SCALE[rng.integers(0, len(SCALE))]), t0, 0.14, pan=float(rng.uniform(-0.5, 0.5)))
    if rng.random() < 0.35:
        place(bgm, pluck(SCALE[rng.integers(0, 5)] / 2), t0 + 0.18, 0.10, pan=float(rng.uniform(-0.4, 0.4)))
    t0 += 2.3 * float(rng.uniform(0.7, 1.3))
for at, f, g in ((T - 4.2, 293.66, 0.15), (T - 4.0, 440.0, 0.11), (T - 3.8, 587.33, 0.10)):   # 締めの1音（D・A・D）
    place(bgm, pluck(f, 3.6), at, g, pan=0.0)
def breath(f, dur):
    n = int(SR * dur); x = t_(n); vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * x) * np.clip(x / 1.0, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph); noise = bp(rng.standard_normal(n), f * 0.8, f * 3.5) * 0.6
    return (tone * 0.8 + noise) * np.clip(x / 0.6, 0, 1) * np.clip((dur - x) / 1.2, 0, 1)
for at, f, d in ((1.0, 293.66, 5.0), (18.6, 392.0, 5.0), (25.4, 293.66, 5.6)):
    place(bgm, breath(f, d), at, 0.10, pan=-0.1)
x = bgm / max(1e-6, np.abs(bgm).max()) * 0.89
w = wave.open(sys.argv[1], "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((x.T * 32767).astype(np.int16).tobytes()); w.close(); print("ok", sys.argv[1])
