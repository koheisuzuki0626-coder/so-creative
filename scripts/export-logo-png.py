"""動画・印刷で使うロゴを透過PNGで書き出す。

    python3 scripts/export-logo-png.py        # 成果物/ロゴ/ へ書き出す

ブラウザ（Playwright）で assets/site.css と同じ組み方を描いて撮る。
**サイトと必ず同じ形になる**のが狙い。CSS の数値を変えたらここも自動で付いてくる
（.logo / .logo-dash / .logo-tail を site.css から読んで使う）。

⚠️ PNG から作らないこと。元は SVG とフォント（Inter）で、PNG を拡大すると粗くなる。
⚠️ 書き出した PNG は【その時点の形】で固まる。ロゴを直したら必ず流し直すこと。
   サイトだけ直して動画用を流し忘れると、名刺と動画が古い形のまま残る。
"""
import base64, io, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
# 書き出し先は配布用の置き場（成果物/ロゴ/）。assets/ には置かない
# ——サイトから読む必要が無く、置くと同じものが2か所に増えるため。
# ⚠️ 書類のレターヘッドは 成果物/書類ひな形/_書式/logo-lockup.png が実体。
#    ここを更新したら、そちらにもコピーすること（test_routing.py が
#    「書類のロゴが配布用と同じ」で突き合わせている）。
OUT = ROOT / "成果物" / "ロゴ"
OUT.mkdir(parents=True, exist_ok=True)

CSS = (A / "site.css").read_text(encoding="utf-8")


def css_val(selector, prop, default):
    """site.css から 1つの宣言を読む。見つからなければ default。"""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    if not m:
        return default
    m2 = re.search(re.escape(prop) + r"\s*:\s*([^;]+);", m.group(1))
    return m2.group(1).strip() if m2 else default


# サイトと同じ値（site.css から読む。書き換えたらここも変わる）
GAP = css_val("#nav .logo, .f-logo", "gap", "0.42em")
MARK_H = css_val(".logo-mark", "height", "1.62em")
MARK_SHIFT = css_val(".logo-mark", "transform", "translateY(0.02em)")
TAIL_GAP = css_val(".logo-tail", "margin-left", "0.04em")
TAIL_TRACK = css_val(".logo-tail", "letter-spacing", "0.005em")
DASH_W = css_val(".logo-dash", "width", "0.30em")
DASH_H = css_val(".logo-dash", "height", "0.075em")
DASH_M = css_val(".logo-dash", "margin", "0 0.06em")
DASH_LIFT = css_val(".logo-dash", "transform", "translateY(-0.20em)")

ACCENT = "#1c5c45"          # 深緑（site.css の --accent）
ACCENT_ON_DARK = "#79c2a1"  # 暗い地では明るい緑（#nav.on-dark .logo-dash）


def mark_svg(color):
    """マークの SVG を、指定の色で返す。輪・花びら・中心は同じ形のまま色だけ差し替える。"""
    s = (A / "logo-mark.svg").read_text(encoding="utf-8")
    return s.replace('stroke="#1d1d1f"', f'stroke="{color}"')


def page(ink, accent, font_px):
    mark = base64.b64encode(mark_svg(ink).encode()).decode()
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  html,body{{margin:0;padding:0;background:transparent}}
  .logo{{display:inline-flex;align-items:center;gap:{GAP};
        font-family:Inter,sans-serif;font-size:{font_px}px;font-weight:500;
        letter-spacing:0.01em;color:{ink};line-height:1}}
  .logo-mark{{flex:none;width:auto;height:{MARK_H};transform:{MARK_SHIFT}}}
  .logo-word{{display:inline-flex;align-items:baseline}}
  .logo-tail{{flex:none;margin-left:{TAIL_GAP};letter-spacing:{TAIL_TRACK}}}
  .logo-dash{{flex:none;width:{DASH_W};height:{DASH_H};margin:{DASH_M};
             border-radius:1px;background:{accent};transform:{DASH_LIFT}}}
  #wrap{{display:inline-block;padding:0}}
</style></head><body><div id="wrap"><span class="logo">
<img class="logo-mark" src="data:image/svg+xml;base64,{mark}" alt="">
<span class="logo-word">so<i class="logo-dash"></i><span class="logo-tail">creative</span></span>
</span></div></body></html>"""


def main():
    from playwright.sync_api import sync_playwright
    # (名前, 文字と線の色, 区切りの色)
    VARIANTS = [
        ("on-light", "#1d1d1f", ACCENT),          # 明るい背景に置く（濃い色のロゴ）
        ("on-dark", "#f5f5f7", ACCENT_ON_DARK),   # 暗い背景に置く（明るい色のロゴ）
        ("accent", ACCENT, ACCENT),               # 深緑一色
    ]
    # 横組みとマークで必要な大きさが違うので、別々に撮る。
    # 横組み 280px → 約4,200px幅（4K で画面いっぱいに出しても足りる）
    # マーク 340px → 約1,100px角（4K の隅に置く透かしで十分）
    JOBS = [("lockup", 280, "#wrap"), ("mark", 340, ".logo-mark")]
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, ink, acc in VARIANTS:
            for kind, font_px, sel in JOBS:
                pg = b.new_page(viewport={"width": 3000, "height": 1200},
                                device_scale_factor=2)
                pg.set_content(page(ink, acc, font_px), wait_until="load")
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(700)
                f = OUT / f"logo-{kind}-{name}.png"
                pg.locator(sel).screenshot(path=str(f), omit_background=True)
                made.append(f)
                pg.close()
        b.close()
    from PIL import Image
    print(f"{'ファイル':34} {'寸法':>13}  透過")
    for f in made:
        im = Image.open(f)
        alpha = "あり" if im.mode in ("RGBA", "LA") else "なし"
        print(f"  {f.name:32} {f'{im.width}x{im.height}':>13}  {alpha}")
    print(f"\n書き出し先: {OUT}")


if __name__ == "__main__":
    main()
