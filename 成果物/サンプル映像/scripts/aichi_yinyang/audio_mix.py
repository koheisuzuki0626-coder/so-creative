"""仮編集の音：BGM（和の音階）・効果音・ナレーションを混ぜて1本のwavにする。"""
import numpy as np, wave, json, sys, pathlib
SR = 48000
TLN = json.load(open("/tmp/aichi_map/timeline.json"))
START = {}; acc = 0.0
for k, d in TLN:
    START[k] = acc; acc += d
T = acc; N = int(SR * (T + 0.5))
rng = np.random.default_rng(29)
NA_DIR = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
def t_(n): return np.arange(n) / SR
def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if j <= i: return
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    buf[0, i:j] += sig[:j - i] * gain * l; buf[1, i:j] += sig[:j - i] * gain * r
def lp(x, a):            # 1次のローパス（a: 0〜1、小さいほど強い）
    y = np.empty_like(x); acc = 0.0
    for k in range(len(x)):
        acc += a * (x[k] - acc); y[k] = acc
    return y
def lpv(x, cut):         # 速いローパス（FFT）
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[f > cut] *= np.exp(-(f[f > cut] - cut) / (cut * 0.3)); return np.fft.irfft(X, len(x))
def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
bgm = np.zeros((2, N)); se = np.zeros((2, N)); na = np.zeros(N)

# ---- 持続音（D と A、ゆっくり揺れる）----
tt = t_(N)
drone = (0.55 * np.sin(2 * np.pi * 73.42 * tt) + 0.35 * np.sin(2 * np.pi * 110.0 * tt + 1.0) + 0.12 * np.sin(2 * np.pi * 146.83 * tt))
drone *= 0.55 + 0.45 * np.sin(2 * np.pi * tt / 11.0) ** 2
env = np.clip(tt / 4.0, 0, 1) * np.clip((T - tt) / 3.0, 0, 1)
bgm[0] += drone * env * 0.16; bgm[1] += drone * env * 0.16 * 0.95

# ---- 琴のような爪弾き（都節：D Eb G A Bb）----
SCALE = [293.66, 311.13, 392.00, 440.00, 466.16, 587.33, 622.25, 783.99]
def pluck(f, dur=2.2):
    n = int(SR * dur); x = t_(n)
    s = sum(a * np.sin(2 * np.pi * f * h * x) * np.exp(-x * (2.2 + 1.6 * h)) for h, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12)))
    att = np.exp(-x * 120) * rng.standard_normal(n) * 0.25
    return (s + att) * np.clip(x / 0.004, 0, 1)
dens = [(0, START["C04"], 2.4), (START["C04"], START["C08"], 1.9), (START["C08"], START["C12"], 2.2), (START["C12"], START["C16"], 1.8), (START["C16"], START["C19"], 1.2), (START["C19"], T - 2, 2.8)]
for a, b, step in dens:
    t0 = a + 0.8
    while t0 < b - 0.5:
        if not (START["C10"] <= t0 <= START["C11"]):   # 雨の場面では弾かない
            f = SCALE[rng.integers(0, len(SCALE))]
            place(bgm, pluck(f), t0, 0.14, pan=float(rng.uniform(-0.5, 0.5)))
            if rng.random() < 0.35:
                place(bgm, pluck(SCALE[rng.integers(0, 5)] / 2), t0 + 0.18, 0.10, pan=float(rng.uniform(-0.4, 0.4)))
        t0 += step * float(rng.uniform(0.7, 1.3))

# ---- 尺八のような息の音 ----
def breath(f, dur):
    n = int(SR * dur); x = t_(n); vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * x) * np.clip(x / 1.0, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph)
    noise = bp(rng.standard_normal(n), f * 0.8, f * 3.5) * 0.6
    e = np.clip(x / 0.6, 0, 1) * np.clip((dur - x) / 1.2, 0, 1)
    return (tone * 0.8 + noise) * e
for at, f, d in ((START["C03"] + 0.6, 293.66, 5.0), (START["C13"] + 0.4, 392.0, 5.2), (START["C21"] + 0.2, 293.66, 4.3)):
    place(bgm, breath(f, d), at, 0.10, pan=-0.1)

# ---- 効果音 ----
def noise(n): return rng.standard_normal(n)
def scratch(dur, rate=6.0):
    n = int(SR * dur); x = t_(n); s = bp(noise(n), 2500, 9000)
    strokes = np.clip(np.sin(2 * np.pi * rate * x + 3 * np.sin(2 * np.pi * 0.7 * x)), 0, 1) ** 2
    return s * strokes * np.clip(x / 0.2, 0, 1) * np.clip((dur - x) / 0.3, 0, 1)
place(se, scratch(4.2), START["C01"] + 0.2, 0.05)                      # C01 ペン
place(se, scratch(2.6, 3.0), START["C02"] + 1.0, 0.04)                 # C02 コンパス
def blip(f=180, dur=0.35):
    n = int(SR * dur); x = t_(n); return np.sin(2 * np.pi * f * x * (1 - 0.3 * x)) * np.exp(-x * 14)
place(se, blip(), START["C03"] + 5.3, 0.35); place(se, blip(140), START["C03"] + 5.5, 0.35)   # C03 目が落ちる
def taiko(dur=1.6):
    n = int(SR * dur); x = t_(n); f = 62 * (1 + 0.6 * np.exp(-x * 18))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 4.5)
    hit = lpv(noise(n), 900) * np.exp(-x * 40) * 0.6
    return body + hit
place(se, taiko(), START["C07"] + 0.4, 0.55); place(se, taiko(), START["C15"] + 0.3, 0.55)    # C07 / C15 の脈
for ck in ("C04", "C08", "C12", "C16"): place(se, taiko(1.2), START[ck], 0.25)  # 章題
n = int(SR * 8.6); x = t_(n)                                         # C10 雨と雷
rain = lpv(noise(n), 6000) * 0.5 + bp(noise(n), 1500, 7000) * 0.5
place(se, rain * np.clip(x / 0.8, 0, 1) * np.clip((8.6 - x) / 1.0, 0, 1), START["C10"], 0.12)
place(se, rain * 0.6, START["C10"], 0.05, pan=0.6)
m = int(SR * 3.5); y = t_(m)
thunder = lpv(noise(m), 160) * (np.exp(-y * 1.3) * (0.4 + 0.6 * (y > 0.05)))
place(se, thunder / (np.abs(thunder).max() + 1e-9), START["C10"] + 3.8, 0.5)
def knock(f=900):
    k = int(SR * 0.25); z = t_(k); return bp(noise(k), f * 0.6, f * 2.2) * np.exp(-z * 38)
for i in range(9):                                                   # C13 槌
    place(se, knock(700 + 80 * (i % 3)), START["C13"] + 0.4 + i * 0.62 + rng.uniform(-0.05, 0.05), 0.22, pan=float(rng.uniform(-0.6, 0.6)))
for i in range(17):                                                  # C17 織機
    place(se, knock(1800), START["C17"] + 0.3 + i * 0.33, 0.12, pan=0.3 if i % 2 else -0.3)
k = int(SR * 4.0); z = t_(k)                                         # C18 火花→現代の機械音
crack = bp(noise(k), 3000, 12000) * (rng.random(k) < 0.004).astype(float) * 4
place(se, crack * np.clip((4 - z) / 1.0, 0, 1), START["C18"] + 0.3, 0.25)
k2 = int(SR * 4.0); z2 = t_(k2)
hum = (np.sin(2 * np.pi * 110 * z2) + 0.5 * np.sin(2 * np.pi * 220 * z2) + 0.3 * lpv(noise(k2), 400)) * np.clip((z2) / 2.0, 0, 1) * np.clip((4 - z2) / 0.8, 0, 1)
place(se, hum, START["C18"] + 3.0, 0.06)

# ---- ナレーション ----
names = json.load(open(NA_DIR / "na.json"))
for k in names:
    w = wave.open(str(NA_DIR / f"{k}.wav")); a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768; w.close()
    a = a / (np.abs(a).max() + 1e-9) * 0.7
    i = int((START[k] + 0.35) * SR); na[i:i + len(a)] += a[:N - i]
# ---- ナレーション中はBGMを下げる ----
envn = np.abs(na); win = int(SR * 0.25); envn = np.convolve(envn, np.ones(win) / win, mode="same")
duck = 1 - 0.55 * np.clip(envn / 0.05, 0, 1)
duck = np.convolve(duck, np.ones(int(SR * 0.3)) / int(SR * 0.3), mode="same")
mix = bgm * duck + se + np.vstack([na, na])
fade = np.clip((T - tt) / 1.5, 0, 1); mix *= fade
mix /= max(1.0, np.abs(mix).max() / 0.95)
pcm = (mix.T * 32767).astype(np.int16)
w = wave.open(str(OUT), "w"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print("ok", OUT)
