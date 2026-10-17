#!/usr/bin/env python3
"""ロゴマークの壁紙9枚（iPhone / iPad / Mac × 3色）を作り直す。

    ../../../discord-groupchat/venv/bin/python3 壁紙を作り直す.py

マークは ../logo-mark.svg（配布用の写し。実体は main の assets/logo-mark.svg）を
読んで色だけ差し替える。2026-10-17 までは手作りで、ここだけ 2026-09-23 の
作図（花が外円の中で下寄り・輪が細い）が残っていた。読んで作れば置いていかれない。

寸法と位置は、作り直す前の9枚を実測して写した値（下の DEVICES / STYLES）。
金（#b08733）は 2026-09-24 に深緑へ変えた前のブランド色だが、
壁紙は自分用なので金のまま残してある（2026-10-17・本人の指示）。
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MARK = HERE.parent / "logo-mark.svg"
VENV_PY = HERE.parents[2] / "discord-groupchat" / "venv" / "bin" / "python3"
HTML2PNG = HERE.parents[2] / "discord-groupchat" / "tools" / "html_to_png.py"

# (幅, 高さ, マークの枠の幅, 画面の高さに対するマークの中心)
DEVICES = {
    "iphone": (1290, 2796, 504, 0.3995),
    "ipad": (2048, 2732, 649, 0.4197),
    "mac": (3456, 2234, 839, 0.4595),
}
# (地の色, マークの色, 光の色, 光の濃さ)
STYLES = {
    "dark-gold": ("#16161a", "#b08733", "176,135,51", 0.075),
    "dark-white": ("#16161a", "#f5f5f7", "255,255,255", 0.095),
    "light-ink": ("#f5f5f7", "#1d1d1f", "29,29,31", 0.078),
}


def page(w, h, box, fy, bg, ink, glow, alpha):
    svg = MARK.read_text(encoding="utf-8").replace('stroke="#1d1d1f"', f'stroke="{ink}"')
    # 光はマークの奥にふわっと。作り直す前の9枚で、光が地の色に戻る距離を
    # 実測した（iPhone 831px / iPad 1141px / Mac 1025px以上＝上端で切れて測り切れず）。
    # 下の 2.45 と止めどころ72%で、戻る距離が 889 / 1145 / 1480px になる。
    r = round(box * 2.45)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{w}px;height:{h}px;background:{bg};overflow:hidden}}
#glow{{position:absolute;inset:0;
  background:radial-gradient(circle {r}px at 50% {fy * 100:.2f}%,
    rgba({glow},{alpha}) 0%, rgba({glow},{alpha}) 18%, rgba({glow},0) 72%)}}
#mark{{position:absolute;left:50%;top:{fy * 100:.2f}%;
  width:{box}px;height:{box}px;transform:translate(-50%,-50%)}}
#mark svg{{display:block;width:100%;height:100%}}
</style></head><body><div id="glow"></div><div id="mark">{svg}</div></body></html>"""


# 一覧（どれがどれか一目で分かるように）
LABELS = {"dark-gold": "濃い地×金", "dark-white": "濃い地×白", "light-ink": "明るい地×黒"}
DEV_LABEL = {"iphone": "iPhone", "ipad": "iPad", "mac": "Mac"}


def index_page():
    rows = ""
    for dev, (w, h, _b, _f) in DEVICES.items():
        shots = "".join(
            f'<figure><img src="壁紙_{dev}_{st}.png"><figcaption>{LABELS[st]}</figcaption></figure>'
            for st in STYLES)
        rows += (f'<div class="row"><div class="tag">{DEV_LABEL[dev]} {w}×{h}</div>'
                 f'<div class="shots">{shots}</div></div>')
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1360px;background:#fff;font-family:"Hiragino Sans",sans-serif;color:#1d1d1f;padding:34px 40px}}
h1{{font-size:21px;font-weight:600;margin-bottom:22px}}
.row{{display:flex;align-items:center;gap:28px;padding:26px 0;border-top:1px solid rgba(0,0,0,.1)}}
.tag{{flex:none;width:150px;font-size:13px;color:#8c8c92}}
.shots{{display:flex;align-items:flex-start;gap:28px}}
figure{{text-align:center}}
img{{max-height:390px;max-width:290px;display:block;box-shadow:0 2px 10px rgba(0,0,0,.14)}}
figcaption{{font-size:12px;color:#8c8c92;margin-top:9px}}
</style></head><body><h1>ロゴマークの壁紙（9枚）</h1>{rows}</body></html>"""


def main():
    if not MARK.exists():
        sys.exit(f"マークが無い: {MARK}")
    made = []
    for dev, (w, h, box, fy) in DEVICES.items():
        for style, (bg, ink, glow, alpha) in STYLES.items():
            tmp = pathlib.Path("/tmp/_壁紙.html")
            tmp.write_text(page(w, h, box, fy, bg, ink, glow, alpha), encoding="utf-8")
            out = HERE / f"壁紙_{dev}_{style}.png"
            # 端末の実寸そのものなので scale は 1。2 にすると倍の画素になる
            r = subprocess.run([str(VENV_PY), str(HTML2PNG), str(tmp), str(out),
                                str(w), str(h), "1"], capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"書き出し失敗: {out.name}\n{r.stderr}")
            made.append(out)
            print(f"  {out.name:34} {w}x{h}")
    # 一覧は壁紙を読むので、9枚を書き終えてから作る
    tmp = HERE / "_一覧.html"
    tmp.write_text(index_page(), encoding="utf-8")
    r = subprocess.run([str(VENV_PY), str(HTML2PNG), str(tmp), str(HERE / "一覧.png"),
                        "1360", "1280", "1"], capture_output=True, text=True)
    tmp.unlink()
    if r.returncode:
        sys.exit(f"一覧の書き出し失敗\n{r.stderr}")
    print(f"  {'一覧.png':34} 1360x1280")
    print(f"\n{len(made)}枚＋一覧。置き場: {HERE}")


if __name__ == "__main__":
    main()
