"""4本まとめの音：BGM＋SE。SEは各場面の元の動画（カメラをかける前）を測った値に合わせて鳴らす。
使い方: one_se.py <cam_timeline.json> <油絵> <尾張と三河> <金鯱×地図> <絵地図> <BGM.wav> <出力.wav>
左＝尾張（夜）／右＝三河（昼）で音の位置も揃える。"""
import json, subprocess, sys, wave
import numpy as np
tl_path, oil, yin, kin, ezu, bgm_path, out = sys.argv[1:8]
TL = json.load(open(tl_path)); TA, TB, TC, TD = TL["t0"]; T = TL["total"]
SR = 48000; N = int(SR * T); FPS = 24; NF = int(T * FPS) + 2
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

# ---- 各場面の元の動画を測る（全体の時刻の配列にして返す）----
def load(p, w=480):
    W, H = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True, check=True).stdout.strip().split(","))
    h = int(round(H * w / W / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32), w / W
def smooth(v, s):
    k = max(1, int(s * FPS)) | 1; return np.convolve(np.pad(v, k, mode="edge"), np.ones(k) / k, mode="same")[k:-k]
def place(v, t_off, edge=0.5):              # 0〜1 に揃えて全体の時刻へ置く。端は edge 秒かけて出入りさせる（プツッを防ぐ）
    v = np.asarray(v, float); v = (v - v.min()) / (v.max() - v.min() + 1e-6)
    n = len(v); e = np.clip(np.arange(n) / (edge * FPS), 0, 1) * np.clip((n - 1 - np.arange(n)) / (edge * FPS), 0, 1)
    o = np.zeros(NF); i = int(t_off * FPS); j = min(NF, i + n); o[i:j] = (v * e)[:j - i]; return o
def reg(fr, k, x0, x1, y0, y1): return fr[:, int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)]
def motion(a):
    g = a.mean(-1); return np.r_[0, np.abs(np.diff(g, axis=0)).mean((1, 2))]
f_oil, k = load(oil)
c_cloth = place(smooth(motion(reg(f_oil, k, 250, 950, 150, 1000)), 0.3), TA)          # 人物の動き
c_win = place(smooth(reg(f_oil, k, 0, 230, 0, 1000).mean((1, 2, 3)), 0.4), TA)        # 窓の光
f_y, k = load(yin)
c_gold = place(smooth(reg(f_y, k, 490, 590, 718, 818).mean((1, 2, 3)), 0.25), TB)     # 金の玉の明るさ
c_ycl = place(smooth(reg(f_y, k, 620, 1000, 170, 420).mean((1, 2, 3)), 0.4), TB)      # 雲
bay = reg(f_y, k, 500, 900, 400, 520); c_bay = place(smooth(np.abs(bay - bay[0]).mean((1, 2, 3)), 0.4), TB)   # 湾の波
win = reg(f_y, k, 120, 520, 500, 900); c_city = place(smooth(np.abs(win - win[0]).mean((1, 2, 3)), 0.4), TB)  # 城と街の灯り
f_k, k = load(kin)
c_kin = place(smooth(motion(reg(f_k, k, 300, 1200, 40, 880)), 0.35), TC)              # 金鯱の動き
f_e, k = load(ezu)
c_cst = place(smooth(reg(f_e, k, 630, 750, 265, 385).mean((1, 2, 3)), 0.25), TD)      # 名古屋城の光
c_ecl = place(smooth(reg(f_e, k, 1090, 1430, 280, 450).mean((1, 2, 3)), 0.5), TD)     # 山の雲
sec = np.arange(NF) / FPS
for nm, c in (("人物", c_cloth), ("窓の光", c_win), ("金の玉", c_gold), ("雲", c_ycl), ("湾", c_bay), ("街", c_city), ("金鯱", c_kin), ("名古屋城", c_cst), ("山の雲", c_ecl)):
    print(f"{nm} ピーク {sec[c.argmax()]:.2f}秒", end="  ")
print()
def curve(v): return np.interp(t_(N), sec, v)

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

# ---- 窓辺（油絵の人物）----
tt = t_(N)
n = int(SR * (TB + 1.2)); room = band(pink(n), 150, 1200) * swell(n, 1.0, 1.0) * (0.75 + 0.25 * np.sin(2 * np.pi * t_(n) / 5))
put(rms_to(room, -34), 0, -0.5); put(rms_to(band(pink(n), 150, 1200) * swell(n, 1.0, 1.0), -35), 0, 0.2)
for at, pan in ((0.9, -0.62), (1.5, -0.55), (3.3, -0.6)):             # 窓は画面の左
    put(peak_to(sparrow(), -20), at, pan, 0.7)
cc = curve(c_cloth) ** 1.2; put(rms_to(band(pink(N), 1200, 6000) * cc, -35, cc > cc.max() * 0.4), 0, 0.1, 0.25)   # 衣擦れ
wc = curve(c_win) ** 1.2; put(rms_to(band(pink(N), 400, 2400) * wc, -34, wc > wc.max() * 0.4), 0, -0.6, 0.3)      # 窓の外の風
# ---- 絵が替わる所の風 ----
for at in (TB - 0.3, TC - 0.3, TD - 0.3):
    put(rms_to(air(1.7), -27), at, -0.15, 0.3); put(rms_to(air(1.7), -28), at, 0.15, 0.3)
put(peak_to(fuurin(), -19), TB + 0.3, 0.2, 0.7)                       # 尾張と三河の入り
# ---- 尾張と三河 ----
n = int(SR * 5.6); bc = curve(c_bay) ** 0.8
wv = np.zeros(N); w0 = waves(5.6, 2.6, 0.6); i = int((TB - 0.2) * SR); wv[i:i + n] = (w0 * swell(n, 0.8, 0.8))[:N - i] if i + n > N else w0 * swell(n, 0.8, 0.8)
put(rms_to(wv * (0.45 + 0.55 * bc), -30, wv != 0), 0, 0.45, 0.2)      # 湾は画面の右。波が立つほど大きく
n2 = int(SR * 5.6); put(rms_to(band(pink(n2), 80, 420) * swell(n2, 0.9, 0.9), -36), TB - 0.1, -0.5)   # 夜の街の低いうなり
sparkle(smooth(c_city, 0.2), 8.0, -0.85, -0.15, TB + 0.5, TC + 0.6, -23)   # 灯りが増えるほど多く鳴る
gc = curve(c_gold) ** 1.6
pad = sum(np.sin(2 * np.pi * f * tt) + np.sin(2 * np.pi * (f + 0.7) * tt) for f in (293.66, 440.0, 587.33))
put(rms_to(pad * gc, -30.5, gc > gc.max() * 0.4), 0, -0.25, 0.5)      # 金の玉が光るぶんだけ鳴る
yc = curve(c_ycl) ** 1.2; put(rms_to(band(pink(N), 500, 3000) * yc, -32, yc > yc.max() * 0.4), 0, 0.5, 0.3)   # 雲の風
# ---- 金鯱×地図 ----
put(peak_to(taiko(), -9), TC + 0.5, 0, 0.25)                          # 金鯱が現れる
put(peak_to(suzu(), -19), TC + 0.55, -0.1, 0.8)
for k_, g in ((1.55, -15), (4.47, -14)):                              # 泳ぎのいちばん大きい所で低い脈
    put(peak_to(taiko(1.4), g), TC + k_, 0, 0.2)
kc = curve(c_kin) ** 1.2
put(rms_to((band(pink(N), 150, 700) + 0.5 * band(pink(N), 800, 2600)) * kc, -28, kc > kc.max() * 0.4), 0, -0.05, 0.35)   # ひれの水音
put(peak_to(ping(1174.66), -16), TC + 2.3, -0.33, 0.7)                # 金の玉＝名古屋城（画面の位置に合わせる）
put(peak_to(ping(880.0), -16), TC + 3.0, -0.09, 0.7)                  # 黒い玉＝岡崎城
# ---- 絵地図 ----
n = int(SR * (T - TD + 0.2)); put(rms_to(waves(n / SR, 5.2, 1.4) * swell(n, 1.8, 2.0), -31), TD - 0.1, 0.0, 0.2)   # 海は画面の下
sparkle(smooth(c_cst, 0.2), 4.5, -0.7, -0.2, TD + 0.6, T - 1.6, -24)
ec = curve(c_ecl) ** 1.2; put(rms_to(band(pink(N), 400, 2800) * ec, -32, ec > ec.max() * 0.4), 0, 0.45, 0.3)   # 山の雲の風
END = T - 4.2                                                         # BGMの最後の音と同時
put(peak_to(taiko(2.2), -10), END, 0, 0.3)
put(peak_to(bonsho(), -11), END + 0.02, 0, 0.5)

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
for a, c, name in ((0, TB, "油絵"), (TB, TC, "尾張と三河"), (TC, TD, "金鯱"), (TD, END, "絵地図"), (END, T, "締め")):
    i, j = int(a * SR), int(c * SR); r = lambda v: 20 * np.log10(np.sqrt(np.mean(v[:, i:j] ** 2)) + 1e-12)
    print(f"  {name}: {r(b * BG):.1f} / {r(se):.1f}  ［{r(bh):.1f} / {r(sh):.1f}］")
print("ピーク", round(float(np.abs(mix).max()), 3))
mix = mix / max(1.0, np.abs(mix).max() / 0.95)
o = wave.open(out, "wb"); o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR); o.writeframes((mix.T * 32767).astype(np.int16).tobytes()); o.close(); print("ok", out)
