"""「ふたつの目」と、その前の絵画・地図・図面までを1ページにまとめる（Mac用HTMLと、スマホ用PDF）。"""
import re, subprocess, pathlib, html as H
D = pathlib.Path.home() / "Desktop/絵画_2026-10-27"; T = D / "一覧用"
ledger = pathlib.Path("/Users/suzukikohei/so-portfolio/成果物/サンプル映像/素材元_台帳.md").read_text(encoding="utf-8")
def ledger_link(cut, word):
    for ln in ledger.splitlines():
        if f"ふたつの目 {cut} " in ln and word in ln:
            m = re.search(r"\((https://drive\.google\.com/[^)]+)\)", ln)
            if m: return m.group(1)
    return None
SITE = "https://koheisuzuki0626-coder.github.io/so-creative/works.html#original"
LINK = {
 "hd": "https://drive.google.com/file/d/1Tm5Q3CeCRbNt1XQdtvaleEo-4l5De-ns/view",
 "oil": "https://drive.google.com/file/d/1ijF0F2vJq1T7eeVfJ-PUIpDCtuAdWVcy/view",
 "yin1": "https://drive.google.com/file/d/1SciMm8-DVr4tV7dtBguIplpDM8gOTS_M/view",
 "yin2": "https://drive.google.com/file/d/1R7mhRDmIF_NqV8-m-g4tW9bPoomnDeyv/view",
 "map": "https://drive.google.com/file/d/1LqMtfo9Yd4hcouXyYkIyo80l6sjcEmq-/view",
 "hyp": "https://drive.google.com/file/d/1y5rNc4k0S2BOVTsQGfoSOdJjz_JPsiyK/view",
 "zumen": "https://drive.google.com/file/d/1VdOGOfP2J9IMrTdwa0ynejJ5JwGnL9yF/view",
 "ekonte": "https://drive.google.com/file/d/13RijXLQnWfWiXFVoPoMnZByCU6JLTsXH/view",
 "v1": "https://drive.google.com/file/d/1BKcpWnEhhSmZnmAti1sNO3emAvkjG136/view",
 "v2": "https://drive.google.com/file/d/1uhb0GqmNT5ZzJe2aBKl8yjTmQ00nt3EJ/view",
 "v3": "https://drive.google.com/file/d/1dk7GwSDiV4r8-Sj1EFjBAWol5IG33drD/view",
 "taro": "https://drive.google.com/file/d/1o7cqOankjXuyVlG8uO6XZ2U2edxhVp_n/view",
 "yin2b": "https://drive.google.com/file/d/1I6nek8xQDnvSKdKGyiG2PvYKopd1VsoB/view",
 "yin1b": "https://drive.google.com/file/d/12ObkQ_l5k7MZcOj8Y6Ee0ajPjaWehXM6/view",
 "fk": "https://drive.google.com/file/d/1TfL-7p68XsdW3ItJG3stDXLHNaRcYNov/view",
 "ezu": "https://drive.google.com/file/d/1h6A1mUU5E5QPWkRMBrkA1G3UfLjNvKT_/view",
 "fo": "https://drive.google.com/file/d/1dfl0e9FLHD2VCeoc6xWHTqVFWlechDDV/view",
 "fkv": "https://drive.google.com/file/d/1wWYasgPsa66oUvLsaJ_DC-Xo8ZbfASMI/view",
}
def poster(video, name, t=2.0):
    out = T / f"{name}.jpg"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "4", str(out)], check=True)
    return out
KL = [("C05", "雪の岡崎城（撮り直し版）"), ("C06", "輿の一行"), ("C09", "霧の境川"), ("C10", "豪雨の桶狭間"), ("C11", "扇の手元"),
      ("C13", "名古屋城の築城"), ("C14", "金鯱の陰陽図"), ("C17", "紡績工場"), ("C18", "自動車の組み立て")]
posters = {"final": poster(D / "ふたつの目_完成版_v4.mp4", "p_final", 113.0)}
for c, _ in KL: posters[c] = poster(D / "Kling素材/高画質版" / f"{c}.mp4", f"p_{c}", 2.5)
posters["ng"] = poster(D / "Kling素材/C05_1回目_没.mp4", "p_C05ng", 6.0)
posters["fkv"] = poster(D / "融合_金鯱×地図_動画.mp4", "p_fkv", 3.5)
for k, f, t in (("v1", "ふたつの目_ビデオコンテ_仮.mp4", 9.0), ("v2", "ふたつの目_ビデオコンテ_v2_太郎.mp4", 47.0), ("v3", "ふたつの目_v3_Kling7カット.mp4", 59.0)):
    posters[k] = poster(D / f, f"p_{k}", t)

def thumb(path, w):
    out = T / ("t_" + pathlib.Path(path).stem + ".jpg")
    if not out.exists():
        subprocess.run(["sips", "-Z", str(w), "-s", "format", "jpeg", "-s", "formatOptions", "70", str(path), "--out", str(out)], capture_output=True, check=True)
    return out
def build(pdf):
    rel = (lambda p: pathlib.Path(p).as_uri())
    def vid(path, key, link, label, small=False):
        if pdf:
            a = f'<a href="{link}">' if link else ""; b = "</a>" if link else ""
            return f'<figure class="{"s" if small else "v"}">{a}<img src="{rel(posters[key])}"><span class="play">▶ 再生</span>{b}<figcaption>{label}</figcaption></figure>'
        attrs = 'muted loop autoplay playsinline' if small else 'controls playsinline preload="metadata"'
        return f'<figure class="{"s" if small else "v"}"><video src="{rel(path)}" poster="{rel(posters[key])}" {attrs}></video><figcaption>{label}{f" ／ <a href={chr(34)}{link}{chr(34)}>Drive</a>" if link else ""}</figcaption></figure>'
    def img(path, label, link=None, cls="i"):
        a = f'<a href="{link}">' if link else ""; b = "</a>" if link else ""
        src = thumb(path, 520 if cls == "f" else 1100) if pdf else path
        return f'<figure class="{cls}">{a}<img src="{rel(src)}">{b}<figcaption>{label}</figcaption></figure>'
    frames = "".join(img(D / "絵コンテ_コマ" / f"C{i:02d}.png", f"C{i:02d}", cls="f") for i in range(1, 22))
    kl = "".join(vid(D / "Kling素材/高画質版" / f"{c}.mp4", c, ledger_link(c, "高画質版"), f"{c} {n}", small=True) for c, n in KL)
    css = """body{margin:0;background:#f4efe4;color:#1a1a1a;font-family:'Hiragino Sans',sans-serif}
.w{max-width:1100px;margin:0 auto;padding:36px 28px 60px}
h1{font-family:'Hiragino Mincho ProN',serif;font-size:40px;margin:0 0 6px} .sub{color:#8a6a24;margin:0 0 28px}
h2{font-family:'Hiragino Mincho ProN',serif;font-size:24px;border-bottom:2px solid #1a1a1a;padding-bottom:6px;margin:44px 0 16px}
p.n{color:#444;line-height:1.8;margin:6px 0 14px} a{color:#7a5a14}
figure{margin:0} figcaption{font-size:13px;color:#333;margin-top:6px;line-height:1.5}
.v video,.v img{width:100%;border-radius:6px;display:block;background:#000}
.v figure img{background:none}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px} .g3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.g7{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
.i img{width:100%;border-radius:4px;display:block;border:1px solid #d6cdb8} .f img{width:100%;display:block;border:1px solid #d6cdb8}
.s video,.s img{width:100%;border-radius:4px;display:block} .s,.v{position:relative}
.play{position:absolute;left:10px;top:10px;background:rgba(0,0,0,.6);color:#fff;font-size:12px;padding:3px 8px;border-radius:3px}
table{border-collapse:collapse;width:100%;font-size:14px} td,th{border:1px solid #bfb5a0;padding:6px 10px;text-align:left} th{background:#e9e1cf}
@media print{.w{padding:14mm 12mm} h2{break-after:avoid} figure{break-inside:avoid} .g3{grid-template-columns:repeat(3,1fr)}}"""
    body = f'''<div class="w">
<h1>ふたつの目 ― 愛知の陰陽図</h1><p class="sub">2026-10-27〜30 に作ったもの、ぜんぶ（{"スマホ用：画像を押すとDriveで開きます" if pdf else "Mac用：動画はその場で再生できます"}）</p>
<h2>1. 完成版（ホームページ掲載・高画質版）</h2>
{vid(D / "ふたつの目_完成版_v4.mp4", "final", LINK["hd"], "1分55秒・1920×1080・24fps（115.0秒）・新しい金鯱と絵地図の締めを入れた v4")}
<p class="n">ホームページ：<a href="{SITE}">{SITE}</a></p>
<h2>2. はじまり：AIで描いた絵画</h2>
<div class="g3">{img(D / "A_古典.png", "油絵の人物（A 古典・Nano Banana Pro）", LINK["oil"])}{img(D / "陰陽_案1_金鯱.png", "陰陽図 案1 金鯱（日本画）", LINK["yin1"])}{img(D / "陰陽_案2_尾張と三河.png", "陰陽図 案2 尾張と三河（油絵・1回目）", LINK["yin2"])}</div>
<p class="n">10/29 の追加：太極図の型紙を参考画像として渡して作り直した案2と、名古屋城の金鯱どおりの姿（虎の頭・うろこ・反った尾）に寄せた案1。</p>
<div class="g3">{img(D / "陰陽_案2_尾張と三河_v2.png", "陰陽図 案2 尾張と三河（作り直し）", LINK["yin2b"])}{img(D / "陰陽_案1_金鯱_本物の形.png", "陰陽図 案1 金鯱（本物の形に寄せた版）", LINK["yin1b"])}</div>
<h2>2.5 絵と地図の融合</h2>
<p class="n"><b>絵地図</b>：正確な地図に、尾張（夜）・三河（昼）の塗り分けと名所の位置の印を入れた下絵をAIに渡して描かせた。県の形は本当の輪郭と重なる。金の点が城の本当の位置。</p>
<div class="v">{img(D / "絵地図_愛知の陰陽図.png", "絵地図：愛知の陰陽図（名所を本当の位置に）", LINK["ezu"])}</div>
<p class="n" style="margin-top:18px">金鯱×地図：金の玉＝名古屋城、黒い玉＝岡崎城に合わせて重ねたもの。尾張と三河を流し込んだ版は、絵の中の城が本当の位置から約60km外れていたので没。</p>
<div class="g2">{img(D / "融合_金鯱×地図.png", "融合：金鯱 × 地図", LINK["fk"])}{vid(D / "融合_金鯱×地図_動画.mp4", "fkv", LINK["fkv"], "動画：金鯱 × 地図（7秒・ループ）", small=True)}</div>
<p class="n">動画（10/30）：玉を2つの城に合わせたまま、金鯱だけを動かした（カメラ固定の Kling → 1080p 高画質化）。Kling は 3.6秒目から黒い鯱の鱗に金が滲んだので、最初の 3.5秒を順に流してから逆に戻し、7秒の切れ目のないループにした。</p>
<h2>3. 地図と仮説</h2>
<p class="n">国土数値情報（行政区域・2021年）から正確な県の形を描き、名古屋城と岡崎城を目にした太極図を重ねた。「境はS字に沿う」という仮説は、測ると等距離の直線と同じ（89.5%／89.6%）で、支持されなかった。</p>
<div class="g3">{img(D / "愛知の陰陽図_地図.png", "地図の上の陰陽図", LINK["map"])}{img(D / "愛知の陰陽図_仮説図.png", "仮説図（検証つき）", LINK["hyp"])}{img(D / "愛知の陰陽図_図面_A3.png", "A3の図面（1:400,000・PDFはDrive）", LINK["zumen"])}</div>
<h2>4. 絵コンテ（21カット）</h2>
<p class="n">PDF：<a href="{LINK["ekonte"]}">ふたつの目_絵コンテ.pdf</a></p>
<div class="g7">{frames}</div>
<h2>5. 動く場面（Kling 3.0 → 1080p 高画質化・9本）</h2>
<div class="g3">{kl}</div>
<p class="n">没テイク：C05 の1回目（写真のような霧が絵から浮いたので撮り直し）</p>
<div class="g3">{vid(D / "Kling素材/C05_1回目_没.mp4", "ng", None, "C05 1回目（没）", small=True)}</div>
<h2>6. 途中の版</h2>
<div class="g3">{vid(D / "ふたつの目_ビデオコンテ_仮.mp4", "v1", LINK["v1"], "ビデオコンテ（仮の読み上げ・静止画）", small=False)}{vid(D / "ふたつの目_ビデオコンテ_v2_太郎.mp4", "v2", LINK["v2"], "v2（太郎の声）", small=False)}{vid(D / "ふたつの目_v3_Kling7カット.mp4", "v3", LINK["v3"], "v3（Kling 7カット）", small=False)}</div>
<h2>7. ナレーション</h2>
<p class="n">声：Seed Audio「太郎」（日本語・低めの男性）。15本を録り、声の尺に合わせて映像を延ばした。試し録り：<a href="{LINK["taro"]}">ナレーション試し_太郎.wav</a></p>
<h2>8. クレジット</h2>
<table><tr><th>用途</th><th>クレジット</th></tr>
<tr><td>陰陽図の絵 2枚</td><td>4</td></tr><tr><td>絵コンテのAI画 8枚</td><td>16</td></tr><tr><td>ナレーション（試し＋15本）</td><td>3.3</td></tr>
<tr><td>Kling 8カット＋撮り直し1本</td><td>96</td></tr><tr><td>金鯱の動画化＋高画質化 9本</td><td>約20</td></tr><tr><td>陰陽図 案2の作り直し・金鯱の本物の形</td><td>4</td></tr><tr><td>絵地図（生成と印消し）</td><td>4</td></tr><tr><td>v4：新しい金鯱と絵地図の動画化＋高画質化</td><td>約17</td></tr><tr><td>金鯱×地図の動画（カメラ固定＋高画質化）</td><td>8.5</td></tr>
<tr><th>合計</th><th>約173（残り 52.8）</th></tr></table>
</div>'''
    return f"<html><head><meta charset='utf-8'><title>ふたつの目 一覧</title><style>{css}</style></head><body>{body}</body></html>"
(D / "ふたつの目_一覧.html").write_text(build(False), encoding="utf-8")
(T / "print.html").write_text(build(True), encoding="utf-8")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto((T / "print.html").as_uri()); pg.wait_for_timeout(1500)
    pg.pdf(path=str(D / "ふたつの目_一覧.pdf"), format="A4", print_background=True, margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"})
    b.close()
print("ok")
