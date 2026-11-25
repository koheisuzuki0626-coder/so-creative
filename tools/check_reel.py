#!/usr/bin/env python3
"""ヒーローのリールを検品する。組み直すたびに必ず通すこと。

⚠️ 自動で合否を出さない。似ている組を上位から並べて、画像にして見せるだけ。
判定するのは人。理由：2026-10-06 に「同じ工作機械のカットが2つ入っている」と
指摘され、検出器を作ろうとしたが、画素の差では分けられないと分かった。

  実測（128px・384px・640px のいずれでも同じ傾向）
    本物の重複（同じ工作機械）      明度差 13  輪郭差 11〜24
    図解アニメどうし（別の絵）       明度差  9〜11  輪郭差  8〜17

  平らな地の絵（緑一色の図解）は細部が少ないので、別の絵どうしでも
  数値が小さく出る。本物の重複より「似ている」と出てしまうため、
  閾値を置くと必ずどちらかを取りこぼす。

出力：上位の組を並べた画像を /tmp/reel_similar.png に書く。それを見て判断する。

使い方（Pillow が要るので venv の python で）:
  discord-groupchat/venv/bin/python tools/check_reel.py [動画] [カット長=3] [上位=6]
"""
import itertools
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat


def font(size):
    for p in ('/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc', '/System/Library/Fonts/Helvetica.ttc'):
        if pathlib.Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def stray_frames(src: str) -> list:
    """1コマだけ浮いているコマ（前後どちらとも大きく違う）を全コマから探す。

    2026-11-23、切り出しの1コマ目に別の場面が1枚混ざったまま渡した事故の再発防止。
    「前後のコマどうしは似ている」を条件にすると、場面の切り替わりに挟まった
    1コマを取りこぼすので、条件は「前後両方と差が大きい」だけにする。
    白フェードのような意図した演出も引っかかるので、出たものは画で確かめる。
    """
    W, H, TH = 64, 36, 12
    fps = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=r_frame_rate', '-of', 'csv=p=0', src],
                         capture_output=True, text=True).stdout.strip()
    num, _, den = fps.partition('/')
    rate = float(num) / float(den or 1)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={W}:{H},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    size = W * H
    fr = [Image.frombytes('L', (W, H), raw[i * size:(i + 1) * size]) for i in range(len(raw) // size)]
    d = [ImageStat.Stat(ImageChops.difference(fr[i], fr[i + 1])).mean[0] for i in range(len(fr) - 1)]
    return [(i, i / rate) for i in range(1, len(fr) - 1) if d[i - 1] > TH and d[i] > TH]


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else 'assets/works/hero-reel.mp4'
    cut = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    top = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip())
    n = round(dur / cut)
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        for i in range(n):
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{i*cut + cut/2:.2f}', '-i', src,
                            '-frames:v', '1', '-vf', 'scale=320:180',
                            str(tmp / f'{i:03d}.jpg')], check=True)
        ims = [Image.open(tmp / f'{i:03d}.jpg').convert('RGB') for i in range(n)]
        gray = [im.convert('L') for im in ims]
        edge = [g.filter(ImageFilter.FIND_EDGES) for g in gray]
        rows = []
        for a, b in itertools.combinations(range(n), 2):
            c = ImageStat.Stat(ImageChops.difference(gray[a], gray[b])).mean[0]
            e = ImageStat.Stat(ImageChops.difference(edge[a], edge[b])).mean[0]
            rows.append((c + e, c, e, a, b))
        rows.sort()
        rows = rows[:top]

        print(f'{dur:.2f}秒 / {n}カット（{cut}秒ずつ）')
        print('似ている組（上から順。★自動判定はしない。画像を見て決めること）')
        for _, c, e, a, b in rows:
            print(f'   {a+1:>2}番（{a*cut:>4.0f}秒）と {b+1:>2}番（{b*cut:>4.0f}秒）  明度差 {c:5.1f} 輪郭差 {e:5.1f}')

        CW, CH, PAD, LAB = 320, 180, 8, 26
        sheet = Image.new('RGB', (CW * 2 + PAD * 3, (CH + LAB + PAD) * len(rows) + PAD), (22, 25, 24))
        d = ImageDraw.Draw(sheet)
        f = font(14)
        for i, (_, c, e, a, b) in enumerate(rows):
            y = PAD + i * (CH + LAB + PAD)
            sheet.paste(ims[a], (PAD, y))
            sheet.paste(ims[b], (PAD * 2 + CW, y))
            d.text((PAD, y + CH + 4), f'{a+1}番 {a*cut:.0f}秒', fill=(233, 236, 234), font=f)
            d.text((PAD * 2 + CW, y + CH + 4),
                   f'{b+1}番 {b*cut:.0f}秒   明度差 {c:.1f} / 輪郭差 {e:.1f}', fill=(233, 236, 234), font=f)
        out = '/tmp/reel_similar.png'
        sheet.save(out)
        print(f'→ 上位{len(rows)}組を {out} に並べた。これを見て重複を判断すること')

        stray = stray_frames(src)
        if stray:
            print('⚠️ 1コマだけ浮いているコマ（画で確かめること）:')
            for i, t in stray:
                print(f'   {i}コマ目（{t:.2f}秒）')
            return 1
        print('1コマだけ浮いているコマ：なし')
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
