#!/usr/bin/env python3
"""OGP 画像（assets/ogp.png）を濃色の配色に塗り替える。

なぜ「作り直す」ではなく「塗り替える」なのか
--------------------------------------------
元画像は assets/src/ogp.html をブラウザで撮ったものだが、この作業環境では
Google Fonts（Inter / Zen Kaku Gothic New）がブラウザに読み込まれない。
撮り直すと字形が別のフォントに置き換わってしまうので、既にある PNG の
「色だけ」を画素単位で入れ替える。字送りも字形もそのまま残る。

やっていること
--------------
1. 地の面 B を取り出す。クロージング（膨張→収縮）で暗い細い形＝文字だけを
   消し、白い札のような大きく明るい形の輪郭は残す。そのあと中央値フィルタで
   窓の跡（角張った段差）をならす。
2. 各画素を B と前景色 F の合成 P = (1-a)B + aF とみなし、F の候補
   （黒・インク・ブランドの深緑）それぞれで a を最小二乗で解き、
   残差が最も小さい候補を採る。
3. B を濃色側へ、F を濃色の上で読める側へ置き換えて合成し直す。
4. 濃い地では階調の段差が帯になって見えるので、±0.55 の粒で散らす。

一度きりの変換であることに注意。出来上がった濃色の PNG にもう一度かけると
二重に変換される。やり直すときは git から明るいほうの版を戻してから実行する:
    git show <明るい版のcommit>:assets/ogp.png > /tmp/ogp-light.png
    python3 scripts/recolor-ogp.py /tmp/ogp-light.png assets/ogp.png

使い方: python3 scripts/recolor-ogp.py [入力] [出力]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

SRC = sys.argv[1] if len(sys.argv) > 1 else 'assets/ogp.png'
DST = sys.argv[2] if len(sys.argv) > 2 else 'assets/ogp.png'

# 元画像の地の明るさ（#e2ebe5 の相対輝度）。ここを境に暗い側／明るい側を分ける
BG_LUM = 232.6
LO = np.array([22., 25., 24.])   # にじみの一番暗いところ
MID = np.array([29., 32., 31.])  # --bg  #1d201f
HI = np.array([44., 50., 48.])   # --card #2c3230（白い札はここに来る）
# 前景: (元の色, 濃色版)
FG = [
    (np.array([0., 0., 0.]),     np.array([242., 244., 243.])),  # 真っ黒 → --ink
    (np.array([29., 29., 31.]),  np.array([242., 244., 243.])),  # #1d1d1f → --ink
    (np.array([28., 92., 69.]),  np.array([121., 194., 161.])),  # #1c5c45 → --accent
]
W = np.array([.2126, .7152, .0722])


def main():
    src = Image.open(SRC).convert('RGB')
    bg = (src.filter(ImageFilter.MaxFilter(15))
             .filter(ImageFilter.MinFilter(15))
             .filter(ImageFilter.MedianFilter(31))
             .filter(ImageFilter.GaussianBlur(2)))
    P = np.asarray(src, dtype=float)
    B = np.asarray(bg, dtype=float)

    lum = B @ W
    # にじみは元の時点で階調が粗く、濃色に写すと同心円の帯になる。
    # 暗い側だけ強くぼかして連続した傾斜に戻す（白い札は明るい側なので鈍らない）
    soft = np.asarray(Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(7)), dtype=float)[..., None]
    lum = lum[..., None]

    tl = np.clip((soft - 214.) / (BG_LUM - 214.), 0, 1)
    th = np.clip((lum - BG_LUM) / (255. - BG_LUM), 0, 1)
    Bn = np.where(lum < BG_LUM, LO + (MID - LO) * tl, MID + (HI - MID) * th)

    best_res = best_new = None
    for F, Fn in FG:
        d = B - F
        a = np.clip((((B - P) * d).sum(-1) / ((d * d).sum(-1) + 1e-6)), 0, 1)[..., None]
        res = np.abs(P - ((1 - a) * B + a * F)).sum(-1)
        new = (1 - a) * Bn + a * Fn
        if best_res is None:
            best_res, best_new = res, new
        else:
            m = res < best_res
            best_res = np.where(m, res, best_res)
            best_new = np.where(m[..., None], new, best_new)

    # 粒はにじみの傾斜がある範囲にだけ置く。平らな地まで散らすと
    # PNG が圧縮しづらくなってファイルが 3 倍になる
    rng = np.random.default_rng(626)
    grain = rng.uniform(-0.55, 0.55, best_new.shape) * (lum < BG_LUM - 0.5)
    out = np.clip(best_new + grain, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(DST)
    print(f'{DST} を書き出した（合成の残差 平均 {best_res.mean():.2f} / 最大 {best_res.max():.0f}）')


if __name__ == '__main__':
    main()
