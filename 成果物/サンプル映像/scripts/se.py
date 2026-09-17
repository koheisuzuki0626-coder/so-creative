# -*- coding: utf-8 -*-
"""効果音（SE）を numpy で合成し、BGM とミックスして各本のオーディオを作る。

Higgsfield の generate_audio はスピーチ専用で、SFX モデル（mirelo_text_to_audio）は
ゲーム生成パイプライン専用と明記されていて単体では使えない。よって自前で合成する。
人の声は作らない（不自然になるため）。環境音とモノの音だけ。
"""
import numpy as np
import os
import wave

from bgm import SR, fft_filter, normalize, write_wav, build_02, build_04, reverb

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(20260917)


def _t(n):
    return np.arange(n) / SR


def pink(n, seed=0):
    """1/f ノイズ。環境音のベース。"""
    w = np.random.default_rng(seed).normal(0, 1, n)
    X = np.fft.rfft(w)
    fr = np.fft.rfftfreq(n, 1 / SR)
    fr[0] = fr[1]
    X /= np.sqrt(fr)
    x = np.fft.irfft(X, n)
    return x / (np.abs(x).max() + 1e-9)


def slow_am(n, lo=0.55, hi=1.0, rate=0.35, seed=1):
    """ゆっくりした振幅の揺れ。環境音が一本調子にならないように。"""
    g = np.random.default_rng(seed)
    t = _t(n)
    m = np.zeros(n)
    for f, ph in zip((rate, rate * 2.3, rate * 0.6), g.uniform(0, 6.28, 3)):
        m += np.sin(2 * np.pi * f * t + ph)
    m /= 3
    return lo + (hi - lo) * (m + 1) / 2


def ambience_outdoor(n, level=0.26, seed=2):
    """屋外。低い風と遠い環境の層。"""
    x = normalize(fft_filter(pink(n, seed), 900, "lp"), 1.0)
    x += normalize(fft_filter(pink(n, seed + 1), 120, "hp"), 0.3)
    return normalize(x, 1.0) * slow_am(n, 0.5, 1.0, 0.22, seed) * level


def ambience_room(n, level=0.16, seed=5):
    """室内。空調の低いうなりと薄いヒス。"""
    x = normalize(fft_filter(pink(n, seed), 420, "lp"), 1.0)
    hum = np.sin(2 * np.pi * 108 * _t(n)) * 0.14
    hiss = normalize(fft_filter(pink(n, seed + 1), 3000, "hp"), 0.12)
    return normalize(x + hum + hiss, 1.0) * slow_am(n, 0.7, 1.0, 0.15, seed) * level


def sizzle(n, level=0.6, seed=7, pops=42):
    """焼き音。帯域を絞ったノイズ＋ランダムなパチパチ。"""
    g = np.random.default_rng(seed)
    base = fft_filter(pink(n, seed), 1500, "hp")
    base = normalize(fft_filter(base, 9000, "lp"), 1.0)
    base *= slow_am(n, 0.65, 1.0, 0.8, seed)
    out = base * 0.55
    # パチパチ：短く鋭い減衰音を散らす
    for _ in range(pops):
        p = int(g.uniform(0, max(1, n - SR // 8)))
        ln = int(g.uniform(0.004, 0.02) * SR)
        t = _t(ln)
        cl = normalize(fft_filter(g.uniform(-1, 1, ln), g.uniform(2200, 6500), "hp"), 1.0)
        out[p:p + ln] += cl * np.exp(-t * g.uniform(180, 520)) * g.uniform(0.5, 1.4)
    return normalize(out, 1.0) * level


def tap(n, at, level=0.5, seed=11):
    """指でタブレットを叩く音。"""
    g = np.random.default_rng(seed)
    p = int(at * SR)
    ln = int(0.09 * SR)
    if p + ln > n:
        ln = n - p
    t = _t(ln)
    click = normalize(fft_filter(g.uniform(-1, 1, ln), 1800, "hp"), 1.0) * np.exp(-t * 260)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 90) * 0.5
    out = np.zeros(n)
    out[p:p + ln] += (click + body) * level
    return out


def keystrokes(n, start, count=9, level=0.3, seed=13):
    """キーボードの打鍵。間隔をばらす。"""
    g = np.random.default_rng(seed)
    out = np.zeros(n)
    at = start
    for _ in range(count):
        p = int(at * SR)
        ln = int(0.05 * SR)
        if p + ln >= n:
            break
        t = _t(ln)
        k = normalize(fft_filter(g.uniform(-1, 1, ln), 2600, "hp"), 1.0) * np.exp(-t * 420)
        k += np.sin(2 * np.pi * 320 * t) * np.exp(-t * 300) * 0.3
        out[p:p + ln] += k * g.uniform(0.7, 1.2) * level
        at += g.uniform(0.09, 0.2)
    return out


def clink(n, at, level=0.3, f0=2400, seed=17):
    """食器・箸が触れる音。"""
    g = np.random.default_rng(seed)
    p = int(at * SR)
    ln = int(0.4 * SR)
    if p + ln > n:
        ln = max(0, n - p)
    if ln <= 0:
        return np.zeros(n)
    t = _t(ln)
    x = np.zeros(ln)
    for k, a in ((1.0, 1.0), (2.01, 0.5), (3.4, 0.28), (5.2, 0.14)):
        x += np.sin(2 * np.pi * f0 * k * t) * a
    x *= np.exp(-t * 26)
    x += normalize(fft_filter(g.uniform(-1, 1, ln), 4000, "hp"), 1.0) * np.exp(-t * 300) * 0.35
    out = np.zeros(n)
    out[p:p + ln] += x / 2 * level
    return out


def drip(n, at, level=0.35, seed=19):
    """汁が落ちる音。ピッチが下がる短い音。"""
    p = int(at * SR)
    ln = int(0.12 * SR)
    if p + ln > n:
        ln = max(0, n - p)
    if ln <= 0:
        return np.zeros(n)
    t = _t(ln)
    f = 1500 * np.exp(-t * 26) + 320
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34)
    out = np.zeros(n)
    out[p:p + ln] += x * level
    return out


def seg(n, a, b, fade=0.12):
    """区間 [a,b) の窓。境界はクロスフェードでつなぐ。"""
    g = np.zeros(n)
    i0, i1 = int(a * SR), min(n, int(b * SR))
    g[i0:i1] = 1.0
    nf = int(fade * SR)
    if i0 > 0:
        g[i0:i0 + nf] = np.linspace(0, 1, nf)
    if i1 < n:
        g[max(i0, i1 - nf):i1] = np.linspace(1, 0, i1 - max(i0, i1 - nf))
    return g


def se_02(dur=15.0):
    """C1 資材置き場 0-5 / C2 事務所 5-10 / C3 俯瞰 10-15"""
    n = int(dur * SR)
    out = np.zeros(n)
    out += ambience_outdoor(n, 0.30, 2) * seg(n, 0, 5.05)
    out += ambience_room(n, 0.20, 5) * seg(n, 4.95, 10.05)
    out += ambience_outdoor(n, 0.24, 23) * seg(n, 9.95, dur)
    # タブレットのタップ2回（顔を上げる直前）
    out += tap(n, 0.9, 0.42) + tap(n, 1.45, 0.38, seed=12)
    # 事務所：打鍵と、うなずく前に紙を置く音
    out += keystrokes(n, 5.3, 8, 0.4)
    out += clink(n, 7.6, 0.1, 1200, seed=31)
    # 屋外に戻ってから遠くで金属が触れる音
    out += clink(n, 11.4, 0.07, 800, seed=37)
    return out


def se_04a(dur=15.0):
    """C1 フライパン 0-6 / C2 箸 6-11 / C3 食卓 11-15"""
    n = int(dur * SR)
    out = np.zeros(n)
    out += sizzle(n, 1.15, 7, 56) * seg(n, 0, 6.1)
    out += ambience_room(n, 0.10, 41) * seg(n, 5.9, dur)
    # 箸のカット：残り火の弱い焼き音＋汁が落ちる
    out += sizzle(n, 0.3, 9, 10) * seg(n, 6.0, 11.0)
    out += drip(n, 8.7, 0.3)
    out += clink(n, 6.4, 0.16, 2600, seed=43)
    # 食卓：食器と箸
    for at, lv, f0, sd in ((11.3, 0.3, 2200, 51), (12.1, 0.22, 1700, 53),
                           (13.0, 0.26, 2900, 59), (13.9, 0.2, 2000, 61)):
        out += clink(n, at, lv, f0, sd)
    return out


def se_04b(dur=15.0):
    """C3 食卓 0-5 / C1 フライパン 5-11 / C2 箸 11-15"""
    n = int(dur * SR)
    out = np.zeros(n)
    out += ambience_room(n, 0.13, 41) * seg(n, 0, 5.1)
    for at, lv, f0, sd in ((0.7, 0.32, 2200, 51), (1.6, 0.24, 1700, 53),
                           (2.6, 0.28, 2900, 59), (3.7, 0.2, 2000, 61)):
        out += clink(n, at, lv, f0, sd)
    out += sizzle(n, 1.15, 7, 56) * seg(n, 4.9, 11.1)
    out += sizzle(n, 0.3, 9, 10) * seg(n, 11.0, dur)
    out += ambience_room(n, 0.10, 41) * seg(n, 10.9, dur)
    out += drip(n, 13.2, 0.3)
    out += clink(n, 11.4, 0.16, 2600, seed=43)
    return out


def machine_hum(n, level=0.2, seed=101):
    """工場・倉庫の低い機械音。うなりを2つ重ねて揺らす。"""
    x = normalize(fft_filter(pink(n, seed), 500, "lp"), 1.0)
    t = _t(n)
    x += np.sin(2 * np.pi * 96 * t) * 0.10
    x += np.sin(2 * np.pi * 143 * t) * 0.06
    return normalize(x, 1.0) * slow_am(n, 0.75, 1.0, 0.11, seed) * level


def tool_clink(n, at, level=0.3, f0=3200, seed=103):
    """工具・金具が当たる音。clink より高く硬い。"""
    return clink(n, at, level, f0, seed)


def footsteps(n, start, count=6, level=0.18, seed=107):
    """コンクリートの上の足音。間隔をばらす。"""
    g = np.random.default_rng(seed)
    out = np.zeros(n)
    at = start
    for _ in range(count):
        p = int(at * SR)
        ln = int(0.11 * SR)
        if p + ln >= n:
            break
        t = _t(ln)
        body = np.sin(2 * np.pi * 120 * t) * np.exp(-t * 60) * 0.6
        scuff = normalize(fft_filter(g.uniform(-1, 1, ln), 1600, "hp"), 1.0) * np.exp(-t * 90)
        out[p:p + ln] += (body + scuff * 0.5) * g.uniform(0.8, 1.2) * level
        at += g.uniform(0.42, 0.62)
    return out


def forklift_beep(n, at, level=0.16, count=3):
    """電動フォークリフトの走行警告音。1kHz 前後の短い連続音。"""
    out = np.zeros(n)
    for k in range(count):
        p = int((at + k * 0.62) * SR)
        ln = int(0.22 * SR)
        if p + ln >= n:
            break
        t = _t(ln)
        env = np.minimum(1.0, t / 0.01) * np.minimum(1.0, (t[-1] - t) / 0.02)
        out[p:p + ln] += (np.sin(2 * np.pi * 1020 * t) * 0.7
                          + np.sin(2 * np.pi * 2040 * t) * 0.15) * env * level
    return out


def drum_tumble(n, level=0.26, seed=113):
    """洗濯機のドラムが回る音。低いゴロゴロと水の層。"""
    base = normalize(fft_filter(pink(n, seed), 900, "lp"), 1.0)
    t = _t(n)
    rot = 0.7 + 0.3 * np.sin(2 * np.pi * 0.8 * t)      # 1回転 1.25秒くらい
    water = normalize(fft_filter(pink(n, seed + 1), 2400, "hp"), 0.35)
    return (base * rot + water) * level


def buzzer(n, at, level=0.2):
    """乾燥機の終了ブザー。"""
    p = int(at * SR)
    ln = min(int(0.7 * SR), max(0, n - p))
    if ln <= 0:
        return np.zeros(n)
    t = _t(ln)
    env = np.minimum(1.0, t / 0.02) * np.exp(-t * 1.6)
    x = (np.sin(2 * np.pi * 740 * t) * 0.6 + np.sin(2 * np.pi * 1480 * t) * 0.2)
    out = np.zeros(n)
    out[p:p + ln] += x * env * level
    return out


def rain_drip(n, level=0.12, seed=127, count=26):
    """雨上がりの水滴。夜の屋外に置く。"""
    g = np.random.default_rng(seed)
    out = np.zeros(n)
    for _ in range(count):
        at = g.uniform(0, max(0.1, n / SR - 0.3))
        out += drip(n, at, level * g.uniform(0.5, 1.2), seed=int(g.integers(1, 9999)))
    return out


def se_03(dur=15.0):
    """03 採用。C1 教える 0-5 / C2 ノギス 5-10 / C3 引き 10-15"""
    n = int(dur * SR)
    out = np.zeros(n)
    out += machine_hum(n, 0.26, 101) * seg(n, 0, dur)
    out += tool_clink(n, 1.4, 0.2, 3400, 131)
    out += tool_clink(n, 6.2, 0.26, 4200, 137)   # ノギスを当てる
    out += tool_clink(n, 8.1, 0.16, 2800, 139)
    out += footsteps(n, 10.6, 7, 0.16)           # 引きのカットで人が歩く
    out += tool_clink(n, 12.9, 0.14, 3000, 149)
    return out


def se_05(dur=15.0):
    """05 SNS。店先 0-2.5 / ドラム 2.5-5 / 乾燥機 5-7.5 /
    畳む 7.5-10 / 店内 10-12.5 / 店先 12.5-15"""
    n = int(dur * SR)
    out = np.zeros(n)
    # 夜の屋外（頭と尻）
    out += ambience_outdoor(n, 0.2, 151) * (seg(n, 0, 2.7) + seg(n, 12.3, dur))
    out += rain_drip(n, 0.1, 127, 10) * seg(n, 0, 2.7)
    # 室内＋ドラム
    out += ambience_room(n, 0.13, 153) * seg(n, 2.4, 12.6)
    out += drum_tumble(n, 0.3, 113) * seg(n, 2.4, 5.2)
    out += drum_tumble(n, 0.12, 157) * seg(n, 5.0, 12.6)   # 奥で回り続ける
    out += buzzer(n, 5.15, 0.18)                            # 乾燥機が鳴る
    out += clink(n, 7.7, 0.12, 1500, 163)                   # タオルを台に置く
    out += clink(n, 9.1, 0.1, 1800, 167)
    return out


def se_07(dur=15.0):
    """07 社内向け。装備 0-5 / 通路 5-10 / 指さし 10-15。BGMなしなのでSEだけで持たせる"""
    n = int(dur * SR)
    out = np.zeros(n)
    out += machine_hum(n, 0.3, 171) * seg(n, 0, dur)
    # 装備：ジッパーと金具
    out += tool_clink(n, 1.1, 0.24, 2600, 173)
    out += tool_clink(n, 2.6, 0.18, 3800, 179)
    out += clink(n, 3.9, 0.14, 2200, 181)
    # 通路：フォークリフトの警告音と足音
    out += forklift_beep(n, 5.6, 0.2, 4)
    out += footsteps(n, 8.6, 4, 0.2)
    # 指さし確認：足音と棚の金属音
    out += footsteps(n, 10.4, 3, 0.15)
    out += tool_clink(n, 12.4, 0.16, 3000, 191)
    return out


def mix(bgm, se, se_level=0.9, path=None):
    n = min(len(bgm), len(se))
    m = bgm[:n] * 0.82 + reverb(se[:n], mix=0.1) * se_level
    m = normalize(np.tanh(m * 1.15), 0.9)
    if path:
        write_wav(path, m)
    return m


def rms_db(x):
    return 20 * np.log10(max(np.sqrt(np.mean(x ** 2)), 1e-9))


if __name__ == "__main__":
    from bgm import build_05
    b02, b04, b05 = build_02(), build_04(), build_05()
    s02, s04a, s04b = se_02(), se_04a(), se_04b()
    # 03 は 02 の BGM を流用（構成案どおり）。07 は BGM なしで SE だけ
    silent = np.zeros(len(b02))
    for name, b, s in (("02", b02, s02), ("04a", b04, s04a), ("04b", b04, s04b),
                       ("03", b02, se_03()), ("05", b05, se_05()),
                       ("07", silent, se_07())):
        # 07 は BGM が無いので SE を上げる
        m = mix(b, s, se_level=1.6 if name == "07" else 0.9,
                path=f"{HERE}/audio_{name}.wav")
        print(f"audio_{name}.wav  BGM {rms_db(b):6.1f}dB  SE {rms_db(s):6.1f}dB  "
              f"mix {rms_db(m):6.1f}dB  peak {np.abs(m).max():.3f}")
