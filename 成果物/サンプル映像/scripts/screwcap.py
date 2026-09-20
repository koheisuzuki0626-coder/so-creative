# -*- coding: utf-8 -*-
"""まもりばのチューブの白いキャップを、押し開けるタイプから回すタイプに直す。

生成写真のキャップにはパカっと開ける爪がついている。動画の他のカット
（生成）はネジ式なので、爪を消して、回す合図になる縦リブを入れる。
"""
import numpy as np
from PIL import Image, ImageFilter

# 実測（2048px の商品写真での座標）
TAB = (930, 1584, 1126, 1704)      # 爪とその影の範囲 (x0,y0,x1,y1)
SRC_ABOVE = (1566, 1582)           # 爪の上の、きれいな行
SRC_BELOW = (1706, 1720)           # 爪の下の、きれいな行
CAP_TOP_EDGE, CAP_TOP_MID = 1522, 1550   # キャップ上端（端と中央でずれる）
CAP_STRAIGHT, CAP_BOT = 1692, 1734       # 胴がまっすぐな下限と、底
CAP_CX, CAP_HW = 1026.0, 144.0


def cap_mask(shape):
    """キャップの白い面だけを 0..1 で返す。"""
    h, w = shape
    y = np.arange(h)[:, None]
    x = np.arange(w)[None, :]
    t = (x - CAP_CX) / CAP_HW
    inside_x = np.clip((1.0 - np.abs(t)) / 0.06, 0, 1)      # 左右の端をなだらかに

    top = CAP_TOP_EDGE + (CAP_TOP_MID - CAP_TOP_EDGE) * np.clip(1 - t * t, 0, 1)
    m_top = np.clip((y - top) / 14.0, 0, 1)

    # 底は丸い
    dy = np.clip((y - CAP_STRAIGHT) / (CAP_BOT - CAP_STRAIGHT), 0, None)
    shrink = np.sqrt(np.clip(1 - dy * dy, 0, 1))
    m_bot = np.clip((CAP_BOT - y) / 10.0, 0, 1) * np.clip(
        (shrink * CAP_HW - np.abs(x - CAP_CX)) / 10.0 + 1, 0, 1)

    return np.clip(inside_x * m_top * m_bot, 0, 1)


def erase_tab(a, rng):
    """爪を、上下のきれいな行から縦に補間して埋める。境目は羽根でぼかす。"""
    x0, y0, x1, y1 = TAB
    top = a[SRC_ABOVE[0]:SRC_ABOVE[1], x0:x1].mean(0)
    bot = a[SRC_BELOW[0]:SRC_BELOW[1], x0:x1].mean(0)

    fill = np.empty((y1 - y0, x1 - x0, 3), np.float32)
    for i in range(y1 - y0):
        t = (y0 + i - SRC_ABOVE[1]) / max(SRC_BELOW[0] - SRC_ABOVE[1], 1)
        t = min(max(t, 0.0), 1.0)
        t = t * t * (3 - 2 * t)
        fill[i] = top * (1 - t) + bot * t
    fill += rng.normal(0, 1.8, fill.shape)

    # 羽根つきのマスクで差し替える
    fy = np.ones(y1 - y0)
    fx = np.ones(x1 - x0)
    k = 16
    fy[:k] = np.linspace(0, 1, k)
    fy[-k:] = np.linspace(1, 0, k)
    fx[:k] = np.linspace(0, 1, k)
    fx[-k:] = np.linspace(1, 0, k)
    al = (fy[:, None] * fx[None, :])[..., None]

    reg = a[y0:y1, x0:x1]
    a[y0:y1, x0:x1] = reg * (1 - al) + fill * al
    return a


def add_ribs(a, n=38, depth=6.5):
    """回す合図の縦リブ。円筒に沿って端ほど詰まり、左から光が当たる。"""
    h, w = a.shape[:2]
    m = cap_mask((h, w))
    x = np.arange(w)[None, :]
    t = np.clip((x - CAP_CX) / CAP_HW, -1.0, 1.0)
    theta = np.arcsin(t * 0.995)
    ridge = np.sin(theta * n)            # 山の左が明るく、右が暗い
    shade = np.cos(theta) ** 0.6         # 端では見えなくなる
    delta = (ridge * shade * depth) * m
    a += delta[..., None]
    return a


def fix(src, dst):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(11)
    a = erase_tab(a, rng)
    a = add_ribs(a)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(dst)
    return dst


if __name__ == "__main__":
    import sys
    print(fix(sys.argv[1], sys.argv[2]))
