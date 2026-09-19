# -*- coding: utf-8 -*-
"""サンプル映像用の BGM を numpy で合成する。

Higgsfield の generate_audio はスピーチ専用で音楽に使えないため自前で作る。
音源が完全オリジナルなので著作権処理が要らない（会社紹介と同じ方針）。

- 02 サービス紹介：BPM 100。明るくテンポを上げた版（初版は BPM 80 で
  構成案どおり「静かめ・テンポ遅め」だったが、明るくしたいとの指摘で作り直した）
- 04 広告CM：軽快（BPM 128）。キック・クラップ・ベース・スタブ。訴求A/B で同じ曲
"""
import numpy as np
import wave
import os
import sys

SR = 48000
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 基本波形

def _t(n):
    return np.arange(n) / SR


def saw(f, n, detune=0.0):
    t = _t(n)
    ph = 2 * np.pi * f * (1 + detune) * t
    return 2 * (ph / (2 * np.pi) % 1.0) - 1.0


def sine(f, n, phase=0.0):
    return np.sin(2 * np.pi * f * _t(n) + phase)


def tri(f, n):
    x = (f * _t(n)) % 1.0
    return 4 * np.abs(x - 0.5) - 1.0


def noise(n, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def adsr(n, a, d, s, r, sus=0.7):
    """秒指定の ADSR。a+d+r が n を超える場合は縮める。"""
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    ns = max(0, n - na - nd - nr)
    if ns == 0 and na + nd + nr > n:
        k = n / max(1, (na + nd + nr))
        na, nd, nr = int(na * k), int(nd * k), int(nr * k)
        ns = n - na - nd - nr
    env = np.concatenate([
        np.linspace(0, 1, na, endpoint=False) if na else np.zeros(0),
        np.linspace(1, sus, nd, endpoint=False) if nd else np.zeros(0),
        np.full(ns, sus) if ns > 0 else np.zeros(0),
        np.linspace(sus, 0, nr) if nr else np.zeros(0),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def fft_filter(x, cutoff, kind="lp", rolloff=2.2):
    """scipy が無いので FFT でフィルタする。IIR を Python ループで回すと遅すぎる。"""
    n = len(x)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    with np.errstate(divide="ignore", invalid="ignore"):
        if kind == "lp":
            g = 1.0 / (1.0 + (fr / max(1.0, cutoff)) ** rolloff)
        else:
            g = 1.0 / (1.0 + (max(1.0, cutoff) / np.maximum(fr, 1.0)) ** rolloff)
    return np.fft.irfft(X * g, n)


def reverb(x, mix=0.22, taps=((0.031, 0.5), (0.053, 0.38), (0.079, 0.3),
                              (0.113, 0.22), (0.167, 0.16))):
    """マルチタップディレイ＋LPF の簡易リバーブ。"""
    wet = np.zeros_like(x)
    for dt, g in taps:
        d = int(dt * SR)
        wet[d:] += x[:len(x) - d] * g
    wet = fft_filter(wet, 4200, "lp")
    return x * (1 - mix) + wet * mix


# ---------------------------------------------------------------- 音色

def normalize(x, peak=0.89):
    m = np.abs(x).max()
    return x if m < 1e-9 else x * (peak / m)


def note_hz(semi_from_a4):
    return 440.0 * 2 ** (semi_from_a4 / 12)


# D major を基準にする（明るいまま保つ。会社紹介で Bm7 を挟んで暗くなった反省）
NOTE = {"D3": -19, "E3": -17, "F#3": -15, "G3": -14, "A3": -12, "B3": -10,
        "C#4": -8, "D4": -7, "E4": -5, "F#4": -3, "G4": -2, "A4": 0,
        "B4": 2, "C#5": 4, "D5": 5, "E5": 7, "F#5": 9, "A5": 12, "D6": 17}


def pad(chord, n, level=0.16):
    """デチューンした鋸波3枚のパッド。"""
    out = np.zeros(n)
    for name in chord:
        f = note_hz(NOTE[name])
        for det in (-0.004, 0.0, 0.005):
            out += saw(f, n, det)
    out /= (len(chord) * 3)
    out = fft_filter(out, 6400, "lp")
    return out * adsr(n, 0.45, 0.3, 0, 0.7, sus=0.85) * level


def arp(chord, n, step, level=0.1, oct_up=True):
    """三角波のアルペジオ。"""
    out = np.zeros(n)
    ns = int(step * SR)
    names = list(chord) + ([chord[0]] if oct_up else [])
    i = 0
    pos = 0
    while pos < n:
        ln = min(ns, n - pos)
        f = note_hz(NOTE[names[i % len(names)]] + (12 if oct_up and i % len(names) == len(names) - 1 else 0))
        seg = tri(f, ln) * adsr(ln, 0.005, 0.05, 0, 0.12, sus=0.35)
        out[pos:pos + ln] += seg
        pos += ns
        i += 1
    return fft_filter(out, 5200, "lp") * level


def bass(name, n, level=0.22):
    f = note_hz(NOTE[name]) / 2
    x = sine(f, n) * 0.75 + saw(f, n) * 0.25
    x = fft_filter(x, 430, "lp")
    return x * adsr(n, 0.008, 0.12, 0, 0.18, sus=0.8) * level


def stab(chord, n, level=0.14):
    out = np.zeros(n)
    for name in chord:
        f = note_hz(NOTE[name])
        for det in (-0.006, 0.0, 0.006):
            out += saw(f, n, det)
    out /= (len(chord) * 3)
    out = fft_filter(out, 3000, "lp")
    return out * adsr(n, 0.004, 0.09, 0, 0.1, sus=0.25) * level


def kick(n, level=0.55):
    ln = min(n, int(0.26 * SR))
    t = _t(ln)
    f = 62 * np.exp(-t * 18) + 41
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    click = noise(ln, 7) * np.exp(-t * 320) * 0.25
    out = np.zeros(n)
    out[:ln] = (body + click) * level
    return out


def clap(n, level=0.3, seed=3):
    ln = min(n, int(0.2 * SR))
    t = _t(ln)
    base = fft_filter(noise(ln, seed), 1300, "hp")
    env = np.zeros(ln)
    for off, g in ((0.0, 1.0), (0.010, 0.8), (0.021, 0.6)):
        o = int(off * SR)
        env[o:] += np.exp(-t[:ln - o] * 42) * g
    env += np.exp(-t * 11) * 0.22
    out = np.zeros(n)
    out[:ln] = base * env * level
    return out


def hat(n, level=0.14, open_=False, seed=5):
    ln = min(n, int((0.14 if open_ else 0.05) * SR))
    t = _t(ln)
    x = fft_filter(noise(ln, seed), 7200, "hp")
    out = np.zeros(n)
    out[:ln] = x * np.exp(-t * (16 if open_ else 55)) * level
    return out


def bell(name, n, level=0.16, oct_up=12):
    """グロッケン風。倍音を非整数で重ねて速く減衰させる。明るさの決め手。"""
    f = note_hz(NOTE[name] + oct_up)
    t = _t(n)
    x = np.zeros(n)
    for k, a, d in ((1.0, 1.0, 5.5), (2.76, 0.42, 8.0), (5.4, 0.18, 12.0)):
        x += np.sin(2 * np.pi * f * k * t) * np.exp(-t * d) * a
    x += noise(n, 21) * np.exp(-t * 180) * 0.05
    return x / 1.6 * level


def rhodes(chord, n, level=0.16, decay=1.9):
    """エレピ風のFM。搬送波の位相を2倍音で揺らし、揺れ幅だけ速く減衰させる。

    アタックだけ鐘のように鳴って、あとは丸い正弦に落ち着く。lo-fi の和音はこれ。
    """
    t = _t(n)
    out = np.zeros(n)
    for i, name in enumerate(chord):
        f = note_hz(NOTE[name])
        idx = 2.6 * np.exp(-t * 7.0)           # FM の変調指数
        x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 2 * t))
        out += x * np.exp(-t * decay) * (0.86 ** i)
    out = fft_filter(out / len(chord), 3200, "lp")
    a = int(0.014 * SR)
    out[:a] *= np.linspace(0, 1, a)            # 指で押さえた感じの立ち上がり
    return out * level


def rim(n, level=0.2, seed=11):
    """クロススティック。lo-fi はスネアを叩かずこれで2・4を取る。"""
    ln = min(n, int(0.09 * SR))
    t = _t(ln)
    x = fft_filter(noise(ln, seed), 1700, "hp") * np.exp(-t * 70)
    x += np.sin(2 * np.pi * 330 * t) * np.exp(-t * 90) * 0.5
    out = np.zeros(n)
    out[:ln] = x * level
    return out


def kick_soft(n, level=0.45):
    """クリックを入れず、低いまま長く伸ばすキック。4つ打ちのキックとは別物。"""
    ln = min(n, int(0.34 * SR))
    t = _t(ln)
    f = 54 * np.exp(-t * 14) + 38
    out = np.zeros(n)
    out[:ln] = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5) * level
    return fft_filter(out, 220, "lp")


def vinyl(n, level=0.05, seed=17):
    """レコードのヒスとパチパチ。lo-fi の手触りはほぼこれで決まる。"""
    g = np.random.default_rng(seed)
    out = fft_filter(fft_filter(noise(n, seed) * 0.35, 5200, "lp"), 900, "hp")
    for p in g.integers(0, n, int(n / SR * 26)):
        ln = min(int(0.004 * SR), n - p)
        if ln <= 0:
            continue
        out[p:p + ln] += (g.normal(0, 1, ln) * np.exp(-_t(ln) * 900)
                          * g.uniform(0.4, 1.6))
    return out * level


def wow(x, rate=0.7, depth=0.0016, seed=9):
    """テープの揺れ。読み出し位置をゆっくり前後させてピッチを微妙に狂わせる。"""
    n = len(x)
    t = _t(n)
    mod = np.sin(2 * np.pi * rate * t) + 0.4 * np.sin(2 * np.pi * rate * 2.7 * t + 1.1)
    idx = np.clip(np.arange(n) + mod * depth * SR, 0, n - 1)
    return np.interp(idx, np.arange(n), x)


def shaker(n, level=0.07, seed=31):
    """薄いシェイカー。キックを入れずに軽快さを出す。"""
    g = np.random.default_rng(seed)
    ln = min(n, int(0.06 * SR))
    t = _t(ln)
    x = fft_filter(g.uniform(-1, 1, ln), 6500, "hp")
    out = np.zeros(n)
    out[:ln] = normalize(x, 1.0) * np.exp(-t * 60) * level
    return out


def riser(n, level=0.13):
    t = _t(n)
    x = fft_filter(noise(n, 11), 900, "hp")
    sweep = 1.0 / (1.0 + np.exp(-(t / t[-1] - 0.55) * 9))
    return x * sweep * level


def crash(n, level=0.3, seed=13):
    ln = min(n, int(1.6 * SR))
    t = _t(ln)
    x = fft_filter(noise(ln, seed), 2600, "hp")
    out = np.zeros(n)
    out[:ln] = x * np.exp(-t * 2.4) * level
    return out


# ---------------------------------------------------------------- 曲

def duck(sig, trig_positions, n, depth=0.38, dur=0.22):
    """サイドチェイン。キックのたびに沈めて戻す。入れないと音数を足しても団子になる。"""
    g = np.ones(n)
    nd = int(dur * SR)
    shape = depth + (1 - depth) * np.linspace(0, 1, nd) ** 0.6
    for p in trig_positions:
        if p >= n:
            continue
        ln = min(nd, n - p)
        g[p:p + ln] = np.minimum(g[p:p + ln], shape[:ln])
    return sig * g


def build_02(dur=15.0):
    """明るめ・BPM100。1小節2.4秒 × 6小節。進行 D - G - A - D - G - A

    初版は BPM80 の D-A-G-A-D だったが、明るさが足りなかった。
    テンポを上げ、G と A を多く通して上向きに聞こえるようにし、
    アルペジオを16分に細かくして、小節頭にベルを置いた。
    キックは入れない（構成案の「打ち込みは薄く」は残す）。代わりに薄いシェイカー。
    """
    n = int(dur * SR)
    bar = 2.4
    beat = bar / 4
    prog = [["D4", "F#4", "A4", "E5"], ["G3", "B3", "D4", "A4"],
            ["A3", "C#4", "E4", "B4"], ["D4", "F#4", "A4", "E5"],
            ["G3", "B3", "D4", "A4"], ["A3", "C#4", "E4", "B4"]]
    roots = ["D4", "G3", "A3", "D4", "G3", "A3"]
    tops = ["A4", "B4", "C#5", "D5", "B4", "C#5"]
    mix = np.zeros(n)
    for i, ch in enumerate(prog):
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * SR), n - p0)
        mix[p0:p0 + ln] += pad(ch, ln, level=0.26)[:ln]
        # 16分のアルペジオ。1小節目だけ薄く入る
        mix[p0:p0 + ln] += arp(ch, ln, beat / 2, level=0.12 if i else 0.07)[:ln]
        # 小節頭のベル（明るさの決め手）
        lnb = min(int(1.4 * SR), n - p0)
        mix[p0:p0 + lnb] += bell(tops[i], lnb, level=0.2 if i else 0.13)[:lnb]
        # ベースは8分。軽く刻む
        if i >= 1:
            for k in range(8):
                q = p0 + int(k * beat / 2 * SR)
                ln2 = min(int(beat * 0.45 * SR), n - q)
                if ln2 > 0 and q < n:
                    mix[q:q + ln2] += bass(roots[i], ln2, level=0.17)[:ln2]
        # シェイカーは8分の裏
        for k in range(8):
            q = p0 + int((k + 0.5) * beat / 2 * SR)
            if q < n:
                mix[q:] += shaker(n - q, level=0.06 if i else 0.03)
    # 締め（ロゴ）に合わせて 12.4 秒でベルとクラッシュを重ねる
    q = int(12.4 * SR)
    mix[q:] += crash(n - q, level=0.13)
    mix[q:] += bell("D5", n - q, level=0.22)
    mix = fft_filter(mix, 34, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.26)
    mix[:int(0.2 * SR)] *= np.linspace(0, 1, int(0.2 * SR))
    tail = int(1.5 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 2.2), 0.86)


def build_04(dur=15.0):
    """軽快・BPM128。1小節1.875秒 × 8小節。進行 D - A - G - A ×2"""
    n = int(dur * SR)
    bar = 1.875
    beat = bar / 4
    prog = [["D4", "F#4", "A4"], ["A3", "C#4", "E4"],
            ["G3", "B3", "D4"], ["A3", "C#4", "E4"]] * 2
    roots = ["D4", "A3", "G3", "A3"] * 2
    mix = np.zeros(n)
    kicks = []
    for i, ch in enumerate(prog):
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * SR), n - p0)
        # パッドは薄く敷く
        mix[p0:p0 + ln] += pad(ch, ln, level=0.3)[:ln]
        mix[p0:p0 + ln] += arp(ch, ln, 0.234, level=0.24)[:ln]
        for b in range(4):
            q = p0 + int(b * beat * SR)
            if q >= n:
                break
            # キックは表拍
            kicks.append(q)
            mix[q:] += kick(n - q, level=0.3)
            # ベースは8分
            for sub in (0, 0.5):
                r = q + int(sub * beat * SR)
                ln2 = min(int(beat * 0.9 * SR), n - r)
                if ln2 > 0 and r < n:
                    mix[r:r + ln2] += bass(roots[i], ln2, level=0.15)[:ln2]
            # ハットは裏拍。4拍目裏はオープン
            r = q + int(0.5 * beat * SR)
            if r < n:
                mix[r:] += hat(n - r, level=0.2, open_=(b == 3), seed=5 + b)
            # クラップは2・4拍
            if b in (1, 3):
                mix[q:] += clap(n - q, level=0.3, seed=3 + b)
            # スタブは1拍目と3拍裏
            if b == 0:
                ln3 = min(int(beat * 0.55 * SR), n - q)
                mix[q:q + ln3] += stab(ch, ln3, level=0.46)[:ln3]
            if b == 2:
                r = q + int(0.5 * beat * SR)
                ln3 = min(int(beat * 0.5 * SR), n - r)
                if ln3 > 0:
                    mix[r:r + ln3] += stab(ch, ln3, level=0.34)[:ln3]
    # 10秒手前からライザー、11.2秒（ロゴ）でクラッシュ
    q0, q1 = int(9.6 * SR), int(11.15 * SR)
    mix[q0:q1] += riser(q1 - q0, level=0.12)
    mix[q1:] += crash(n - q1, level=0.26)
    mix = duck(mix, kicks, n, depth=0.42, dur=0.2)
    mix = fft_filter(mix, 34, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.16)
    mix[:int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))
    tail = int(1.3 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 1.5), 0.9)


def build_05(dur=15.0):
    """05 SNSショート（縦型）。BPM78 の lo-fi。進行 Dmaj7 - Bm7 - Gmaj7 - A7

    前は BPM120 の4つ打ちに LPF を掛けただけで、house を暗くした音だった。
    lo-fi は速さと手触りで決まるので、組み直す。

      - BPM78・ハーフタイム。キックは1拍目と3拍半だけ、2・4はリムショット
      - 8分はスウィング（裏を18%後ろへ）。機械的に等分しない
      - 和音は Rhodes 風の FM に 7th を積む。**この本だけ短調の色を入れる**
        （ほかの本は Bm7 を避けて明るさを保っているが、夜の画なので外す）
      - レコードのヒスとパチパチを敷き、旋律側にテープの揺れを掛ける
      - 高域は 3.4kHz で落とす。SNS は音を切って見られるので音量は控えめ
    """
    n = int(dur * SR)
    beat = 60.0 / 78
    bar = beat * 4
    sw = beat * 0.5 * 0.18            # スウィングで裏を後ろへずらす量
    prog = [["D4", "F#4", "A4", "C#5"], ["B3", "D4", "F#4", "A4"],
            ["G3", "B3", "D4", "F#4"], ["A3", "C#4", "E4", "G4"]] * 2
    roots = ["D4", "B3", "G3", "A3"] * 2
    # 4小節でひと回りする、抑えた旋律。鳴りっぱなしにしない
    motif = [("F#5", 0.0, 1.5), ("E5", 2.0, 1.0), (None, 0, 0), ("D5", 1.0, 1.0),
             ("B4", 0.0, 1.5), ("D5", 2.5, 0.75), (None, 0, 0), ("C#5", 1.5, 1.5)]

    keys = np.zeros(n)                # 旋律・和音（揺らす側）
    drums = np.zeros(n)               # ドラム（揺らさない側）
    kicks = []
    for i, ch in enumerate(prog):
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * SR), n - p0)
        # 和音は小節頭と2拍半に置く。2発目は弱く、短く
        keys[p0:p0 + ln] += rhodes(ch, ln, level=0.30)[:ln]
        q = p0 + int(2.5 * beat * SR + sw * SR)
        if q < n:
            ln2 = n - q
            keys[q:] += rhodes(ch, ln2, level=0.15, decay=3.2)
        # ベースは根音を1拍目と3拍半に、長めに伸ばす
        for at, lv in ((0.0, 0.26), (2.5, 0.18)):
            r = p0 + int((at * beat + (sw if at % 1 else 0)) * SR)
            ln3 = min(int(beat * 1.2 * SR), n - r)
            if r < n and ln3 > 0:
                keys[r:r + ln3] += bass(roots[i], ln3, level=lv)[:ln3]
        # ドラム。キックは1と3半、リムは2と4
        for at in (0.0, 2.5):
            r = p0 + int((at * beat + (sw if at % 1 else 0)) * SR)
            if r < n:
                kicks.append(r)
                drums[r:] += kick_soft(n - r, level=0.42)
        for at in (1.0, 3.0):
            r = p0 + int(at * beat * SR)
            if r < n:
                drums[r:] += rim(n - r, level=0.20, seed=11 + i * 2 + int(at))
        # ハットは8分。裏をスウィングさせ、音量を1つずつ変えて機械臭さを消す
        for e in range(8):
            at = e * 0.5 * beat + (sw if e % 2 else 0)
            r = p0 + int(at * SR)
            if r >= n:
                break
            lv = 0.085 if e % 2 else 0.055      # 裏を強く（ハーフタイムの推進力）
            drums[r:] += hat(n - r, level=lv, open_=(e == 7), seed=41 + e)
        # 旋律
        name, at, hold = motif[i % len(motif)]
        if name:
            r = p0 + int(at * beat * SR)
            ln4 = min(int(hold * beat * SR), n - r)
            if r < n and ln4 > 0:
                f = note_hz(NOTE[name])
                seg = (tri(f, ln4) * 0.6 + sine(f, ln4) * 0.4)
                keys[r:r + ln4] += (fft_filter(seg, 2600, "lp")
                                    * adsr(ln4, 0.03, 0.25, 0, 0.3, sus=0.5) * 0.15)

    keys = wow(keys)                   # 揺れは旋律側だけ。ドラムに掛けると芯がぼける
    mix = keys + drums
    mix = duck(mix, kicks, n, depth=0.34, dur=0.26)
    mix += vinyl(n, level=0.055)
    mix = fft_filter(mix, 38, "hp", rolloff=3.0)
    mix = fft_filter(mix, 3400, "lp")  # lo-fi の肝。ここを開けると普通のBGMに戻る
    mix = reverb(mix, mix=0.34)
    mix[:int(0.10 * SR)] *= np.linspace(0, 1, int(0.10 * SR))
    tail = int(1.4 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 1.5), 0.86)


def build_03(dur=180.0):
    """03 採用の3分版。BPM100・1小節2.4秒。章に合わせて厚みを変える。

    15秒版（build_02）と同じ進行・同じ音色を使い、
    セクションごとにどの楽器を鳴らすかだけを変える。
    ループを聞かせるのではなく、章の切り替わりで景色が変わるようにする。

      0-20   朝      パッドとベルだけ
      20-68  仕事    ベースとアルペジオが入る
      68-128 人      いちばん厚い。リードのメロディを足す
      128-160 職場   一度落として、数字のカットで持ち上げる
      160-180 締め   全部入り → 最後にリリース
    """
    n = int(dur * SR)
    bar = 2.4
    beat = bar / 4
    prog = [["D4", "F#4", "A4", "E5"], ["G3", "B3", "D4", "A4"],
            ["A3", "C#4", "E4", "B4"], ["D4", "F#4", "A4", "E5"],
            ["G3", "B3", "D4", "A4"], ["A3", "C#4", "E4", "B4"]]
    roots = ["D4", "G3", "A3", "D4", "G3", "A3"]
    tops = ["A4", "B4", "C#5", "D5", "B4", "C#5"]
    leads = ["F#5", "D5", "E5", "F#5", "A5", "E5"]

    def layers_at(t):
        """その時刻でどの層を鳴らすか。"""
        if t < 20:                      # 朝
            return dict(pad=0.26, bell=0.18, arp=0.0, bass=0.0, shaker=0.0, lead=0.0)
        if t < 68:                      # 仕事
            return dict(pad=0.24, bell=0.12, arp=0.12, bass=0.16, shaker=0.05, lead=0.0)
        if t < 128:                     # 人
            return dict(pad=0.26, bell=0.16, arp=0.14, bass=0.18, shaker=0.07, lead=0.13)
        if t < 143:                     # 職場（前半・落とす）
            return dict(pad=0.22, bell=0.10, arp=0.07, bass=0.10, shaker=0.03, lead=0.0)
        if t < 160:                     # 職場（数字で持ち上げる）
            return dict(pad=0.26, bell=0.18, arp=0.14, bass=0.18, shaker=0.07, lead=0.10)
        return dict(pad=0.28, bell=0.20, arp=0.15, bass=0.19, shaker=0.08, lead=0.15)

    mix = np.zeros(n)
    i = 0
    while True:
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        t = i * bar
        L = layers_at(t)
        k = i % 6
        ch, root, top, lead = prog[k], roots[k], tops[k], leads[k]
        ln = min(int(bar * SR), n - p0)
        if L["pad"]:
            mix[p0:p0 + ln] += pad(ch, ln, level=L["pad"])[:ln]
        if L["arp"]:
            mix[p0:p0 + ln] += arp(ch, ln, beat / 2, level=L["arp"])[:ln]
        if L["bell"]:
            lnb = min(int(1.4 * SR), n - p0)
            mix[p0:p0 + lnb] += bell(top, lnb, level=L["bell"])[:lnb]
        if L["lead"]:
            # リードは2小節に1回、長めに伸ばす
            if i % 2 == 0:
                lnl = min(int(1.9 * SR), n - p0)
                mix[p0:p0 + lnl] += bell(lead, lnl, level=L["lead"], oct_up=0)[:lnl]
        if L["bass"]:
            for m in range(8):
                q = p0 + int(m * beat / 2 * SR)
                ln2 = min(int(beat * 0.45 * SR), n - q)
                if ln2 > 0 and q < n:
                    mix[q:q + ln2] += bass(root, ln2, level=L["bass"])[:ln2]
        if L["shaker"]:
            for m in range(8):
                q = p0 + int((m + 0.5) * beat / 2 * SR)
                if q < n:
                    mix[q:] += shaker(n - q, level=L["shaker"])
        i += 1

    # 章の変わり目にクラッシュを置いて切り替えを聞かせる
    for at, lv in ((20.0, 0.10), (68.0, 0.13), (128.0, 0.09), (160.0, 0.14)):
        q = int(at * SR)
        if q < n:
            mix[q:] += crash(n - q, level=lv)
    mix = fft_filter(mix, 34, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.26)
    mix[:int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))
    tail = int(3.0 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 2.2), 0.86)


def marimba(name, n, level=0.2):
    """マリンバ。基音の速い減衰＋4倍音がさらに速く消える。頭に木のクリック。"""
    f = note_hz(NOTE[name])
    t = _t(n)
    x = sine(f, n) * np.exp(-t * 5.5)
    x += 0.45 * sine(f * 4, n) * np.exp(-t * 16)
    x += 0.18 * sine(f * 9.2, n) * np.exp(-t * 40)
    click = noise(min(n, int(0.004 * SR)), seed=7) * 0.25
    x[:len(click)] += click
    return x * level


def build_08(dur=15.0):
    """インフォグラフィック用。明るめ・BPM120。1小節2.0秒 × 7小節＋締め。

    場面が 0/4/8/12 秒で切り替わるので、小節を2.0秒にして
    切り替わりが必ず小節頭に乗るようにする。切り替わりの頭にはベルを置く。
    キックは入れない。マリンバの8分と薄いシェイカーで軽く進める。
    """
    n = int(dur * SR)
    bar = 2.0
    beat = bar / 4
    # NOTE 表に G# が無いので、E は Esus4（E-A-B）で置く。A メジャーの中では濁らない
    prog = [["A3", "C#4", "E4"], ["D4", "F#4", "A4"],
            ["E4", "A4", "B4"], ["A3", "C#4", "E4"],
            ["D4", "F#4", "A4"], ["E4", "A4", "B4"],
            ["A3", "C#4", "E4"]]
    mix = np.zeros(n)
    for i, ch in enumerate(prog):
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * SR), n - p0)
        mix[p0:p0 + ln] += pad(ch, ln, level=0.2)[:ln]
        # マリンバの8分。コードの音を下から順に回す
        seq = ch + [ch[1]] if len(ch) == 3 else ch
        for k in range(8):
            q = p0 + int(k * beat / 2 * SR)
            ln2 = min(int(0.6 * SR), n - q)
            if ln2 > 0 and q < n:
                mix[q:q + ln2] += marimba(seq[k % len(seq)], ln2,
                                          level=0.16 if i else 0.11)[:ln2]
        # シェイカーは8分の裏
        for k in range(8):
            q = p0 + int((k + 0.5) * beat / 2 * SR)
            if q < n:
                mix[q:] += shaker(n - q, level=0.045 if i else 0.025)
    # 場面の切り替わり（4/8秒）の頭にベル
    for sec, name in ((4.0, "A4"), (8.0, "B4")):
        q = int(sec * SR)
        lnb = min(int(1.2 * SR), n - q)
        mix[q:q + lnb] += bell(name, lnb, level=0.15)[:lnb]
    # 締め（ロゴ）は 12.0 秒。ベルとクラッシュ
    q = int(12.0 * SR)
    mix[q:] += crash(n - q, level=0.11)
    mix[q:] += bell("E5", n - q, level=0.2)
    mix = fft_filter(mix, 36, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.24)
    mix[:int(0.15 * SR)] *= np.linspace(0, 1, int(0.15 * SR))
    tail = int(1.6 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 2.1), 0.86)


def build_08_60(dur=60.0):
    """健診案内の60秒版。BPM120・小節2.0秒はそのまま、30小節に伸ばす。

    場面は 0/6/14/22/30/38/46/54 秒で切り替わる（すべて小節頭）。
    切り替わりごとにベルを置き、14秒から柔らかいベースが入って
    前に進む感じを足す。54秒の締めでクラッシュ＋ベル。
    """
    n = int(dur * SR)
    bar = 2.0
    beat = bar / 4
    cycle = [["A3", "C#4", "E4"], ["D4", "F#4", "A4"],
             ["E4", "A4", "B4"], ["A3", "C#4", "E4"]]
    roots = ["A3", "D4", "E4", "A3"]
    mix = np.zeros(n)
    n_bars = int(np.ceil(dur / bar))
    for i in range(n_bars):
        ch = cycle[i % 4]
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * SR), n - p0)
        quiet = i < 3 or i >= 27          # 頭と締めは薄く
        mix[p0:p0 + ln] += pad(ch, ln, level=0.16 if quiet else 0.2)[:ln]
        seq = ch + [ch[1]]
        for k in range(8):
            q = p0 + int(k * beat / 2 * SR)
            ln2 = min(int(0.6 * SR), n - q)
            if ln2 > 0 and q < n:
                mix[q:q + ln2] += marimba(seq[k % len(seq)], ln2,
                                          level=0.11 if quiet else 0.16)[:ln2]
        for k in range(8):
            q = p0 + int((k + 0.5) * beat / 2 * SR)
            if q < n:
                mix[q:] += shaker(n - q, level=0.025 if quiet else 0.045)
        # 14〜54秒は8分のベースで前に進める
        if 14.0 <= i * bar < 54.0:
            for k in range(8):
                q = p0 + int(k * beat / 2 * SR)
                ln2 = min(int(beat * 0.4 * SR), n - q)
                if ln2 > 0 and q < n:
                    mix[q:q + ln2] += bass(roots[i % 4], ln2, level=0.12)[:ln2]
    # 場面の切り替わりにベル
    for j, sec in enumerate((6.0, 14.0, 22.0, 30.0, 38.0, 46.0)):
        q = int(sec * SR)
        lnb = min(int(1.2 * SR), n - q)
        mix[q:q + lnb] += bell("A4" if j % 2 == 0 else "B4", lnb, level=0.14)[:lnb]
    q = int(54.0 * SR)
    mix[q:] += crash(n - q, level=0.11)
    mix[q:] += bell("E5", n - q, level=0.2)
    mix = fft_filter(mix, 36, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.24)
    mix[:int(0.15 * SR)] *= np.linspace(0, 1, int(0.15 * SR))
    tail = int(2.2 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 2.1), 0.86)


def build_ugc(dur=10.0):
    """UGC風ハンドクリーム（まもり葉）用の10秒。ローズと薄いシェイカーだけの
    やわらかい2コード（Fmaj7 → Am7…はNOTE表に無い音があるので F→G/D で置く）。
    lo-fi（05）と使い回さないための小品"""
    n = int(dur * SR)
    bar = 2.4
    prog = [["F#3", "A3", "C#4", "E4"], ["G3", "B3", "D4", "A4"],
            ["F#3", "A3", "C#4", "E4"], ["G3", "B3", "D4", "A4"],
            ["A3", "C#4", "E4", "A4"]]
    mix = np.zeros(n)
    for i, ch in enumerate(prog):
        p0 = int(i * bar * SR)
        if p0 >= n:
            break
        ln = min(int(bar * 1.3 * SR), n - p0)
        mix[p0:p0 + ln] += rhodes(ch, ln, level=0.2, decay=1.6)[:ln]
        for k in range(4):
            q = p0 + int((k + 0.5) * bar / 4 * SR)
            if q < n:
                mix[q:] += shaker(n - q, level=0.03)
    mix = fft_filter(mix, 40, "hp", rolloff=3.0)
    mix = reverb(mix, mix=0.28)
    mix[:int(0.2 * SR)] *= np.linspace(0, 1, int(0.2 * SR))
    tail = int(1.4 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)
    return normalize(np.tanh(mix * 2.0), 0.8)


def write_wav(path, mono, width=0.12):
    """わずかにステレオに広げて 16bit で書く。"""
    d = int(width * 0.004 * SR)
    l = mono.copy()
    r = np.zeros_like(mono)
    r[d:] = mono[:len(mono) - d]
    r = r * 0.98 + mono * 0.02
    st = np.stack([l, r], axis=1)
    st = np.clip(st, -1, 1)
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def rms_report(name, x, marks):
    print(f"[{name}] セクションRMS")
    for (a, b) in marks:
        seg = x[int(a * SR):int(b * SR)]
        if len(seg) == 0:
            continue
        v = np.sqrt(np.mean(seg ** 2))
        db = 20 * np.log10(max(v, 1e-9))
        print(f"  {a:>5.1f}-{b:<5.1f}s  {db:6.1f} dB")


if __name__ == "__main__":
    a = build_02()
    write_wav(f"{OUT}/bgm_02.wav", a)
    rms_report("02", a, [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15)])
    b = build_04()
    write_wav(f"{OUT}/bgm_04.wav", b)
    rms_report("04", b, [(0, 3), (3, 6), (6, 9), (9, 11.2), (11.2, 15)])
    c = build_05()
    write_wav(f"{OUT}/bgm_05.wav", c)
    rms_report("05", c, [(0, 4), (4, 8), (8, 12), (12, 15)])
    d = build_03()
    write_wav(f"{OUT}/bgm_03_3min.wav", d)
    rms_report("03(3分)", d, [(0, 20), (20, 68), (68, 128), (128, 143), (143, 160), (160, 180)])
    e = build_08()
    write_wav(f"{OUT}/bgm_08.wav", e)
    rms_report("08", e, [(0, 4), (4, 8), (8, 12), (12, 15)])
    e60 = build_08_60()
    write_wav(f"{OUT}/bgm_08_60.wav", e60)
    rms_report("08(60秒)", e60, [(0, 6), (6, 22), (22, 38), (38, 54), (54, 60)])
    print("wrote bgm_02 / bgm_04 / bgm_05 / bgm_03_3min / bgm_08")
