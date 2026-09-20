# -*- coding: utf-8 -*-
"""効果音（SE）を numpy で合成し、BGM とミックスして各本のオーディオを作る。

Higgsfield の generate_audio はスピーチ専用で、SFX モデル（mirelo_text_to_audio）は
ゲーム生成パイプライン専用と明記されていて単体では使えない。よって自前で合成する。
人の声は作らない（不自然になるため）。環境音とモノの音だけ。
"""
import numpy as np
import os
import wave

from bgm import (SR, fft_filter, normalize, write_wav, build_02, build_04,
                 build_04_cm, reverb)

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
    """9/20 の組み直しに合わせた。

    並べる 0-1.6 / 焼き 1.6-4.3 / 皿の羽根 4.3-7.2 /
    箸 7.2-10.0 / 食卓 10.0-11.8 / パッケージ 11.8-15
    """
    n = int(dur * SR)
    out = np.zeros(n)
    out += ambience_room(n, 0.10, 41)
    # 並べる：冷たい餃子を鉄に置く音。まだ焼き音はしない
    for at, lv, f0, sd in ((0.35, 0.10, 900, 71), (0.95, 0.09, 820, 73)):
        out += clink(n, at, lv, f0, sd)
    # 焼き：ここで一気に立ち上げる
    out += sizzle(n, 1.20, 7, 58) * seg(n, 1.55, 4.45)
    # 皿に返したあとは残り火
    out += sizzle(n, 0.42, 9, 16) * seg(n, 4.35, 7.35)
    # 箸：弱い焼き音と、汁が落ちる
    out += sizzle(n, 0.24, 11, 8) * seg(n, 7.2, 10.1)
    out += clink(n, 7.45, 0.15, 2600, seed=43)
    out += drip(n, 9.05, 0.30)
    # 食卓：食器と箸
    for at, lv, f0, sd in ((10.15, 0.28, 2200, 51), (10.85, 0.21, 1700, 53),
                           (11.45, 0.24, 2900, 59)):
        out += clink(n, at, lv, f0, sd)
    # パッケージは静か。部屋の音だけ残す
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
    out += tool_clink(n, 2.4, 0.18, 3800, 179)
    out += clink(n, 3.5, 0.14, 2200, 181)
    # 通路：フォークリフトの警告音と足音（映像は 4.2秒でカットが替わる）
    out += forklift_beep(n, 4.9, 0.2, 4)
    out += footsteps(n, 8.2, 4, 0.2)
    # 指さし確認：足音と棚の金属音
    out += footsteps(n, 9.9, 3, 0.15)
    out += tool_clink(n, 12.4, 0.16, 3000, 191)
    return out


def se_03_3min(dur=180.0):
    """03 採用・3分版。全36カット × 5.0秒。

    工場の機械音を通して敷き、章とカットに合わせて強弱を付ける。
    インタビューのカット（17・19・22・25・34）は機械音を大きく下げる
    ―― 声が聞こえる画なので、音数を減らして「話している」ことを示す。
    """
    n = int(dur * SR)
    out = np.zeros(n)
    cut = lambda i: (i - 1) * 5.0          # カット番号 → 開始秒

    # 屋外（1・36）と室内（それ以外）のベース
    out += ambience_outdoor(n, 0.24, 201) * (seg(n, 0, 5.2) + seg(n, cut(36) - 0.2, dur))
    out += machine_hum(n, 0.30, 203) * seg(n, 4.8, cut(36) + 0.2)
    # インタビューと休憩は機械音を落とす（上から薄いベースを重ねて相対的に下げる）
    for i in (17, 19, 22, 25, 34):
        a, b = cut(i), cut(i) + 5.0
        out[int(a * SR):int(b * SR)] *= 0.34
        out += machine_hum(n, 0.07, 205 + i) * seg(n, a, b)
    for i in (20, 21):                      # 休憩スペースと自販機
        a, b = cut(i), cut(i) + 5.0
        out[int(a * SR):int(b * SR)] *= 0.5
        out += ambience_room(n, 0.10, 231 + i) * seg(n, a, b)

    # 第1章 朝
    out += footsteps(n, cut(1) + 2.6, 3, 0.12)            # 自転車を降りて歩く
    out += tool_clink(n, cut(2) + 1.6, 0.16, 2400, 241)   # 名札の金具
    out += footsteps(n, cut(3) + 0.4, 5, 0.10)            # 朝礼に集まる
    out += tool_clink(n, cut(4) + 1.2, 0.2, 2800, 243)    # 電源スイッチ

    # 第2章 仕事
    out += tool_clink(n, cut(6) + 2.4, 0.18, 3000, 245)   # 材料を抜く
    out += tool_clink(n, cut(7) + 1.8, 0.26, 2600, 247)   # チャックを締める
    out += tool_clink(n, cut(7) + 3.1, 0.2, 2600, 249)
    out += tool_clink(n, cut(9) + 1.4, 0.14, 3600, 251)   # 部品を持ち替える
    out += tool_clink(n, cut(10) + 1.6, 0.2, 4200, 253)   # ノギス
    out += tool_clink(n, cut(11) + 2.2, 0.22, 2200, 255)  # トレイの受け渡し
    out += tool_clink(n, cut(12) + 2.6, 0.12, 3800, 257)
    out += tool_clink(n, cut(14) + 1.2, 0.16, 1800, 259)  # 箱を閉じる
    out += tool_clink(n, cut(14) + 3.4, 0.14, 1600, 261)

    # 第3章 人
    out += tool_clink(n, cut(15) + 1.8, 0.14, 3200, 263)
    out += footsteps(n, cut(20) + 0.3, 3, 0.10)
    out += tool_clink(n, cut(21) + 2.2, 0.18, 2000, 265)  # 缶を置く
    out += footsteps(n, cut(23) + 2.4, 4, 0.16)           # 帰る足音
    out += tool_clink(n, cut(24) + 2.0, 0.14, 3200, 267)

    # 第4章 職場
    out += forklift_beep(n, cut(28) + 1.4, 0.10, 2)       # 奥で機械が動く合図
    out += ambience_room(n, 0.12, 269) * seg(n, cut(29), cut(31) + 5.0)
    out += footsteps(n, cut(30) + 1.0, 3, 0.10)
    for k, at in enumerate((0.8, 1.9, 3.2)):              # 食堂の食器
        out += clink(n, cut(31) + at, 0.12, 1600 + k * 300, 271 + k)
    out += tool_clink(n, cut(32) + 1.6, 0.24, 2400, 275)  # タイムカード
    out += tool_clink(n, cut(32) + 3.0, 0.2, 2200, 277)

    # 第5章 締め
    out += footsteps(n, cut(35) + 2.0, 4, 0.12)
    out += ambience_outdoor(n, 0.10, 279) * seg(n, cut(35) + 2.5, dur)
    return out


VO = os.environ.get("SO_VO", f"{HERE}/vo")


def _read_wav(path):
    """wav を -1..1 のモノラルで読む。"""
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    a = a.reshape(-1, ch).mean(axis=1) / 32768.0
    if sr != SR:                       # 24kHz で返ってくるので 48kHz に合わせる
        a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)),
                      np.arange(len(a)), a)
    return a


def _trim(a, thr=0.02):
    """前後の無音を落とす。TTS は頭とお尻に 0.3〜0.5秒の間を付けてくる。"""
    env = np.abs(a)
    idx = np.nonzero(env > env.max() * thr)[0]
    if len(idx) == 0:
        return a
    a = a[idx[0]:idx[-1] + 1]
    nf = int(0.02 * SR)                # ぶつ切りにしない
    a[:nf] *= np.linspace(0, 1, nf)
    a[-nf:] *= np.linspace(1, 0, nf)
    return a / (np.abs(a).max() + 1e-9)


# 男性3人（A 若手・B ベテラン・D 若手2）は同じ声を使う。
# 聞ける日本語の声がこれ1つしかなかったので、リサンプリングで高さをずらして
# 別人に聞こえるようにする。速さも一緒に変わるが、台詞が3〜4.5秒なので
# 数%動いても5秒のカットには収まる。1.0 はそのまま
PITCH = {19: 0.94, 25: 1.04}


def voice_03_3min(dur=180.0, at=0.30, level=0.62):
    """インタビュー5人ぶんの声を、それぞれのカットの頭から at 秒後に置く。"""
    n = int(dur * SR)
    out = np.zeros(n)
    for i in (17, 18, 19, 22, 25, 34):
        f = f"{VO}/vo{i}.wav"
        if not os.path.exists(f):
            print(f"  [voice] {f} が無い")
            continue
        a = _trim(_read_wav(f))
        k = PITCH.get(i, 1.0)
        if k != 1.0:
            a = np.interp(np.arange(0, len(a), k), np.arange(len(a)), a)
        # ピークで揃えると、間の少ない台詞だけ大きく聞こえる。
        # RMS で合わせてからピークだけ抑える
        a = a * (level * 0.22 / max(np.sqrt(np.mean(a ** 2)), 1e-9))
        a = np.tanh(a * 1.6) / 1.6
        p = int(((i - 1) * 5.0 + at) * SR)
        ln = min(len(a), n - p)
        out[p:p + ln] += a[:ln]
    return out


def duck_by(x, ctrl, depth=0.42, attack=0.12, release=0.45, lead=0.0):
    """ctrl が鳴っている間だけ x を下げる。台詞の下で BGM と SE を引く。

    lead を入れると、その秒数だけ先回りして下げ始める。立ち上がりに 0.12秒
    かかるので、先回りしないと語頭の1音が下がりきる前に終わってしまう。
    """
    env = np.abs(ctrl)
    if lead > 0:
        k = int(lead * SR)
        env = np.concatenate([env[k:], np.zeros(k)])
    na, nr = int(attack * SR), int(release * SR)
    # 立ち上がりは速く、戻りはゆっくり（片側移動最大 → 一次で平滑化）
    g = np.zeros(len(env))
    hold = 0.0
    step_up, step_dn = 1.0 / max(na, 1), 1.0 / max(nr, 1)
    thr = env.max() * 0.04 if env.max() > 0 else 1.0
    for i in range(0, len(env), 64):
        on = 1.0 if env[i:i + 64].max() > thr else 0.0
        hold = min(1.0, hold + step_up * 64) if on else max(0.0, hold - step_dn * 64)
        g[i:i + 64] = hold
    return x * (1.0 - depth * g)


def _even(a, win=0.055, amount=0.55, floor=0.06):
    """台詞の粒を揃える。包絡の逆数を amount ぶんだけ掛ける簡易コンプ。

    「フライパンへ」の語尾のように、尻すぼみになる音が焼き音に食われていた。
    """
    n = max(int(win * SR), 1)
    env = np.convolve(np.abs(a), np.ones(n) / n, mode="same")
    env = np.maximum(env, floor * max(env.max(), 1e-9))
    g = (env.max() / env) ** amount
    return a * np.clip(g, 1.0, 4.0)


# 04a のナレーション。テロップと同じ文言を読ませ、最後に商品名。
# (ファイル, 置く秒) — テロップの出だしより 0.2秒 遅らせて、字が先に立つ形にする
VO_04A = [("vo_04a_1.wav", 0.60),     # 凍ったまま、フライパンへ！
          ("vo_04a_2.wav", 4.70),     # 羽根まで、ぱりっと！
          ("vo_04a_3.wav", 7.70),     # 肉汁、そのまま！
          ("vo_kogane.wav", 12.62)]   # こがねギョーザ！（商品カットに変わった直後）


def voice_04a(dur=15.0, level=1.25, lines=None):
    """04a のナレーション。テロップを全部読み、締めに商品名を言う。

    映像の中の人は喋らないので、ここだけ別のナレーター。

    締めは 12.62秒。12.5秒で画面いっぱいの商品カットに変わった直後に置く。
    （11.60 だとピアノが A4 を弾く 11.5625秒の打鍵に語頭の「こ」が重なり、
    聞き取りで「ウガネ」「フガネ」になっていた）
    """
    n = int(dur * SR)
    out = np.zeros(n)
    for name, at in (lines or VO_04A):
        f = f"{VO}/{name}"
        if not os.path.exists(f):
            print(f"  [voice] {f} が無い")
            continue
        a = _trim(_read_wav(f))
        # 子音の抜けを足す。ピアノと環境音の中で語頭が埋もれるのを防ぐ
        a = a + 0.40 * fft_filter(a, 2400, "hp")
        a = _even(a)            # 語尾が焼き音に食われるので粒を揃える
        a = a * (level * 0.30 / max(np.sqrt(np.mean(a ** 2)), 1e-9))
        a = np.tanh(a * 1.5) / 1.5
        p0 = int(at * SR)
        ln = min(len(a), n - p0)
        if ln > 0:
            out[p0:p0 + ln] += a[:ln]
    return out


def mix(bgm, se, se_level=0.9, path=None, peak=0.9, drive=1.15, voice=None,
        duck=0.42, duck_lead=0.0):
    """drive を上げるとサチュレーションが強まり、足音や金具のような
    突出したトランジェントが潰れてピークとRMSの差が縮む。"""
    n = min(len(bgm), len(se))
    bg = bgm[:n] * 0.82
    sfx = reverb(se[:n], mix=0.1) * se_level
    if voice is not None:
        v = voice[:n]
        # 台詞の下だけ音楽と環境音を引く。焼き音は帯域が声と丸かぶりで、
        # 音楽より先に語尾を食うので深めに引く
        m = (duck_by(bg, v, depth=duck, lead=duck_lead)
             + duck_by(sfx, v, depth=min(0.95, duck + 0.20), lead=duck_lead)
             + v)
    else:
        m = bg + sfx
    m = normalize(np.tanh(m * drive), peak)
    if path:
        write_wav(path, m)
    return m


def rms_db(x):
    return 20 * np.log10(max(np.sqrt(np.mean(x ** 2)), 1e-9))


if __name__ == "__main__":
    from bgm import build_05, build_03
    # 04a の BGM は 9/20 に2度差し替えた。1稿が明るすぎ、2稿（短調＋ローズ）は
    # 逆に暗くなった。3稿はピアノで旋律を弾く D メジャー。
    # 使っていない訴求B（04b）は1稿の曲のまま残す
    b02, b04, b05 = build_02(), build_04(), build_05()
    b04cm = build_04_cm()
    s02, s04a, s04b = se_02(), se_04a(), se_04b()
    # 03 は 02 の BGM を流用（構成案どおり）。07 は BGM なしで SE だけ
    silent = np.zeros(len(b02))
    for name, b, s in (("02", b02, s02), ("04a", b04cm, s04a), ("04b", b04, s04b),
                       ("03", b02, se_03()), ("05", b05, se_05()),
                       ("07", silent, se_07()),
                       ("03_3min", build_03(), se_03_3min())):
        # 3分版のインタビューは声を入れず、テロップだけで見せる。
        # 合成音声が日本語として不自然で、サンプルとしてはむしろ不利だった。
        # 声そのものは scripts/vo/ と voice_03_3min() に残してある。
        # 04a だけは、締めの商品名の一言をナレーターに言わせている
        vo = voice_04a() if name == "04a" else None
        # 07 は BGM が無いので SE を上げていたが、上げすぎていた（9/19 に修正）。
        # 納品済みの5本を volumedetect で測ると 07 だけ -14.7dB で、
        # ほかの -16.4〜-18.5dB より大きかった。環境音を入れる設計は変えず、
        # 音量だけ他と同じ帯（-17dB 前後）に揃える。
        # トランジェントが多く AAC 変換でピークが張り付くのは変わらないので drive は据え置き
        m = mix(b, s, se_level=1.2 if name == "07" else 0.9,
                peak=0.52 if name == "07" else 0.9,
                drive=3.2 if name == "07" else 1.15,
                voice=vo,
                # ナレーションの下は深めに、先回りして引く。効いたのは
                # 先回りのほう。0.16 では語頭がピアノに潰されて「ホガネ」に
                # 聞こえていた（聞き取りで確認）
                duck=0.70 if name == "04a" else 0.42,
                duck_lead=0.22 if name == "04a" else 0.0,
                path=f"{HERE}/audio_{name}.wav")
        print(f"audio_{name}.wav  BGM {rms_db(b):6.1f}dB  SE {rms_db(s):6.1f}dB  "
              f"mix {rms_db(m):6.1f}dB  peak {np.abs(m).max():.3f}")
