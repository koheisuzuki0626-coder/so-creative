"""4本まとめの音：BGM＋SE。SEは映像の明るさ・雲・動きを測った値に合わせて鳴らす。使い方: one_se.py <映像.mp4> <BGM.wav> <出力.wav>
左＝尾張（夜）／右＝三河（昼）で音の位置も揃える。"""
import subprocess, sys, wave
import numpy as np
video, bgm_path, out = sys.argv[1:4]
SR = 48000; T = 34.0; N = int(SR * T); FPS = 24
rng = np.random.default_rng(34)
def t_(n): return np.arange(n) / SR
def db(x): return 10 ** (x / 20)
def fft_shape(x, gain):
    X = np.fft.rfft(x); X *= gain(np.fft.rfftfreq(len(x), 1 / SR)); return np.fft.irfft(X, len(x))
def pink(n):
    return fft_shape(rng.standard_normal(n), lambda f: 1 / np.sqrt(np.maximum(f, 20)))
def band(x, lo, hi):
    return fft_shape(x, lambda f: np.clip((f - lo * 0.8) / (lo * 0.2 + 1e-9), 0, 1) * np.clip((hi * 1.25 - f) / (hi * 0.25), 0, 1))
def rms_to(x, target_db, mask=None):
    v = x if mask is None else x[mask]
    return x * db(target_db) / (np.sqrt(np.mean(v ** 2)) + 1e-12)
def peak_to(x, target_db): return x * db(target_db) / (np.abs(x).max() + 1e-12)
dry = np.zeros((2, N)); send = np.zeros((2, N))
def put(sig, at=0.0, pan=0.0, wet=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if j <= i: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    s = sig[:j - i]
    dry[0, i:j] += s * l; dry[1, i:j] += s * r
    send[0, i:j] += s * l * wet; send[1, i:j] += s * r * wet

# ---- 映像を測る（1920x1080 を 1/4 にして）----
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", "scale=480:270", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 270, 480, 3).astype(np.float32)
sec = np.arange(len(fr)) / FPS
def region(x0, x1, y0, y1): return fr[:, y0 // 4:y1 // 4, x0 // 4:x1 // 4]
def norm_in(v, a, b):
    m = (sec >= a) & (sec <= b); lo, hi = v[m].min(), v[m].max()
    # 区間の端で急に鳴り出すと「プツッ」と出るので、0.8秒かけて出入りさせる
    taper = np.clip((sec - a) / 0.8, 0, 1) * np.clip((b - sec) / 0.8, 0, 1)
    return np.clip((v - lo) / (hi - lo + 1e-6), 0, 1) * taper
def smooth(v, s):
    k = max(1, int(s * FPS)) | 1; return np.convolve(np.pad(v, k, mode="edge"), np.ones(k) / k, mode="same")[k:-k]
def curve(v):  # 24fps → 音の時間軸
    return np.interp(t_(N), sec, v)
gold = norm_in(smooth(region(920, 1000, 707, 787).mean((1, 2, 3)), 0.25), 10.0, 18.0)   # 金の玉の明るさ
ycl = norm_in(smooth(region(1130, 1370, 250, 400).mean((1, 2, 3)), 0.5), 10.0, 17.3)    # 三河の空の雲
kin = region(440, 1120, 100, 880).mean(-1); km = np.r_[0, np.abs(np.diff(kin, axis=0)).mean((1, 2))]
kmv = norm_in(smooth(km, 0.6), 19.2, 23.8)                                              # 金鯱の動き
cst = norm_in(smooth(region(630, 750, 265, 385).mean((1, 2, 3)), 0.25), 25.0, 33.0)     # 名古屋城の光
ecl = norm_in(smooth(region(1090, 1430, 280, 450).mean((1, 2, 3)), 0.5), 25.0, 33.0)    # 三河の山の雲
print("各カーブの最大", [round(float(c.max()), 2) for c in (gold, ycl, kmv, cst, ecl)])
print("金の玉のピーク %.2f秒 雲のピーク %.2f秒 名古屋城のピーク %.2f秒 山の雲のピーク %.2f秒" % (sec[gold.argmax()], sec[ycl.argmax()], sec[cst.argmax()], sec[ecl.argmax()]))

# ---- 音の部品 ----
def swell(n, a, b):       # n サンプルのうち a 秒で入り b 秒で抜ける
    x = t_(n); d = n / SR; return np.clip(x / a, 0, 1) * np.clip((d - x) / b, 0, 1)
def air(dur):             # 溶けに合わせた風（低→高→低）
    n = int(SR * dur); x = t_(n) / dur; e = np.sin(np.pi * x) ** 2
    return band(pink(n), 300, 1200) * e * (1 - x) + band(pink(n), 1200, 5000) * e * x * 0.8
def sparrow():            # 窓の外の小鳥（チュン・チュン）
    parts = []
    for k in range(rng.integers(2, 4)):
        d = float(rng.uniform(0.05, 0.08)); n = int(SR * d); x = t_(n) / d
        f = rng.uniform(4600, 5400) * (1 - 0.28 * x) * (1 + 0.04 * np.sin(2 * np.pi * 42 * t_(n)))
        parts.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x) ** 1.5)
        parts.append(np.zeros(int(SR * rng.uniform(0.09, 0.15))))
    return band(np.concatenate(parts), 2500, 7000)
def fuurin(strikes=6):    # 風鈴
    n = int(SR * 2.6); s = np.zeros(n); at = 0.0
    for k in range(strikes):
        f = rng.uniform(2100, 3000); i = int(at * SR); m = n - i; x = t_(m)
        s[i:] += sum(a * np.sin(2 * np.pi * f * r * x + p) * np.exp(-x * d) for r, a, d, p in ((1, 1, 2.6, 0), (2.76, .45, 5, 1), (5.4, .22, 9, 2))) * rng.uniform(.5, 1)
        at += float(rng.uniform(0.09, 0.26))
    return s
def waves(dur, period, phase=0.0):
    n = int(SR * dur); x = t_(n)
    sw = (0.28 + 0.72 * np.sin(np.pi * x / period + phase) ** 2) ** 1.5
    return band(pink(n), 60, 1400) * sw + band(pink(n), 1500, 5000) * sw ** 3 * 0.35
def pip(f, amp):
    n = int(SR * 0.22); x = t_(n); return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.1 * x)) * np.exp(-x * 42) * amp * np.clip(x / 0.001, 0, 1)
def sparkle(c, base_rate, lo_pan, hi_pan, at0, at1, target):   # 街の灯り：明るいほど多く鳴る
    t0 = at0
    while t0 < at1:
        lv = float(c[int(t0 * FPS)]) if int(t0 * FPS) < len(c) else 0
        rate = base_rate * (0.35 + 1.4 * lv)
        put(pip(float(rng.uniform(3400, 7800)), db(target) * float(rng.uniform(.45, 1)) * (0.6 + 0.6 * lv)), t0, float(rng.uniform(lo_pan, hi_pan)), 0.6)
        t0 += float(rng.exponential(1 / rate))
def taiko(dur=1.8):
    n = int(SR * dur); x = t_(n); f = 62 * (1 + 0.6 * np.exp(-x * 18))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 4.5) + band(rng.standard_normal(n), 60, 900) * np.exp(-x * 40) * 0.6
def suzu(dur=2.4, ticks=9):   # 金のきらめき（鈴）
    n = int(SR * dur); s = np.zeros(n); at = 0.0
    for k in range(ticks):
        i = int(at * SR); x = t_(n - i)
        for r in rng.uniform(1900, 6400, 5):
            s[i:] += np.sin(2 * np.pi * r * x + rng.uniform(0, 6)) * np.exp(-x * rng.uniform(4, 9)) * (1 - k / (ticks * 1.4))
        at += float(rng.uniform(0.03, 0.07))
    return s
def ping(f):                  # 2つの玉
    n = int(SR * 2.4); x = t_(n)
    return sum(a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * d) for r, a, d in ((1, 1, 3.2), (2.0, .4, 5), (3.01, .22, 8), (4.2, .1, 12))) * np.clip(x / 0.002, 0, 1)
def bonsho(f=146.83, dur=4.6):   # 梵鐘
    n = int(SR * dur); x = t_(n); s = np.zeros(n)
    for r, a, d in ((0.5, 1.0, 0.6), (1.0, .8, 0.8), (1.19, .35, 1.2), (1.5, .3, 1.5), (2.0, .45, 1.3), (2.83, .25, 2.2), (3.76, .16, 3), (4.8, .1, 4.5)):
        s += a * (np.sin(2 * np.pi * f * r * x) + 0.8 * np.sin(2 * np.pi * (f * r + 0.45) * x)) * np.exp(-x * d)
    return s * np.clip(x / 0.004, 0, 1) + band(rng.standard_normal(n), 80, 900) * np.exp(-x * 30) * 1.2

# ---- 窓辺（油絵の人物 0〜9.8秒）----
n = int(SR * 10.0); room = band(pink(n), 150, 1200) * swell(n, 1.5, 1.4) * (0.75 + 0.25 * np.sin(2 * np.pi * t_(n) / 5))
for pan in (-0.5, 0.2): put(rms_to(band(pink(n), 150, 1200) * swell(n, 1.5, 1.4), -35) if pan > 0 else rms_to(room, -34), 0, pan)
for at, pan in ((2.4, -0.62), (3.05, -0.55), (6.35, -0.6)):           # 窓は画面の左
    put(peak_to(sparrow(), -20), at, pan, 0.7)
# ---- 絵が替わる所の風 ----
for at in (8.7, 17.7, 23.7):
    put(rms_to(air(1.7), -27), at, -0.15, 0.3); put(rms_to(air(1.7), -28), at, 0.15, 0.3)
put(peak_to(fuurin(), -19), 9.3, 0.2, 0.7)                            # 尾張と三河の入り
# ---- 尾張と三河（9〜19秒）----
n = int(SR * 10.6); put(rms_to(waves(10.6, 4.6, 0.6) * swell(n, 1.6, 1.8), -31), 8.8, 0.45, 0.2)   # 湾は画面の右
n2 = int(SR * 10.4); put(rms_to(band(pink(n2), 80, 420) * swell(n2, 1.5, 1.5), -36), 9.0, -0.5)   # 夜の街の低いうなり
sparkle(smooth(gold, 0.2), 5.0, -0.85, -0.15, 9.8, 18.2, -23)
tt = t_(N); gc = curve(gold) ** 1.6
pad = sum(np.sin(2 * np.pi * f * tt) + np.sin(2 * np.pi * (f + 0.7) * tt) for f in (293.66, 440.0, 587.33))
put(rms_to(pad * gc, -30.5, gc > gc.max() * 0.4), 0, -0.25, 0.5)                   # 金の玉が光るぶんだけ鳴る
yc = curve(ycl) ** 1.2; put(rms_to(band(pink(N), 500, 3000) * yc, -33, yc > yc.max() * 0.4), 0, 0.5, 0.3)   # 雲の風
# ---- 金鯱×地図（18〜25秒）----
put(peak_to(taiko(), -9), 18.5, 0, 0.25)                             # 金鯱が現れる
put(peak_to(suzu(), -19), 18.55, -0.1, 0.8)
kc = curve(kmv) ** 1.3 * np.clip((tt - 18.7) / 0.8, 0, 1) * np.clip((24.8 - tt) / 0.8, 0, 1)
put(rms_to((band(pink(N), 150, 700) + 0.5 * band(pink(N), 800, 2600)) * kc, -30, kc > kc.max() * 0.4), 0, -0.05, 0.35)   # ひれの水音
put(peak_to(ping(1174.66), -16), 20.0, -0.33, 0.7)                    # 金の玉＝名古屋城（画面の位置に合わせる）
put(peak_to(ping(880.0), -16), 20.75, -0.09, 0.7)                     # 黒い玉＝岡崎城
# ---- 絵地図（24〜34秒）----
n = int(SR * 10.2); put(rms_to(waves(10.2, 5.2, 1.4) * swell(n, 1.8, 2.0), -31), 23.9, 0.0, 0.2)  # 海は画面の下
sparkle(smooth(cst, 0.2), 4.5, -0.7, -0.2, 24.6, 32.4, -24)
ec = curve(ecl) ** 1.2; put(rms_to(band(pink(N), 400, 2800) * ec, -32, ec > ec.max() * 0.4), 0, 0.45, 0.3)   # 山の雲の風
put(peak_to(taiko(2.2), -10), 29.8, 0, 0.3)                           # 締め（BGMの最後の音と同時）
put(peak_to(bonsho(), -11), 29.82, 0, 0.5)

# ---- 響き ----
def reverb(x, rt=1.7):
    n = int(SR * rt * 1.4); e = np.exp(-6.9 * t_(n) / rt)
    ir = band(rng.standard_normal(n), 200, 6500) * e; ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n; return np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
wetL, wetR = reverb(send[0]), reverb(send[1])
se = dry + np.vstack([wetL, wetR]) * 0.6
w = wave.open(bgm_path); b = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64).reshape(-1, 2).T / 32768; w.close()
b = b[:, :N] if b.shape[1] >= N else np.pad(b, ((0, 0), (0, N - b.shape[1])))
BG = db(-9.0)
mix = b * BG + se
fade = np.clip(tt / 1.0, 0, 1) * np.clip((T - tt) / 1.8, 0, 1)
mix *= fade
print("区間ごとのRMS(dB) [全帯域 BGM / SE] [スマホで聞こえる帯域 200Hz〜 BGM / SE]")
hp = lambda v: np.vstack([fft_shape(c, lambda f: np.clip((f - 150) / 100, 0, 1)) for c in v])
bh, sh = hp(b * BG), hp(se)
for a, c, name in ((0, 9, "油絵"), (9, 18, "尾張と三河"), (18, 24, "金鯱"), (24, 29.5, "絵地図"), (29.5, 34, "締め")):
    i, j = int(a * SR), int(c * SR); r = lambda v: 20 * np.log10(np.sqrt(np.mean(v[:, i:j] ** 2)) + 1e-12)
    print(f"  {name}: {r(b * BG):.1f} / {r(se):.1f}  ［{r(bh):.1f} / {r(sh):.1f}］")
print("ピーク", round(float(np.abs(mix).max()), 3))
mix = mix / max(1.0, np.abs(mix).max() / 0.95)
o = wave.open(out, "wb"); o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR); o.writeframes((mix.T * 32767).astype(np.int16).tobytes()); o.close(); print("ok", out)
