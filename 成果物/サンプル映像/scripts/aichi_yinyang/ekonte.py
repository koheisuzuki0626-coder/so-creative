"""絵コンテ（A4縦・1ページ6コマ）を PDF にする。"""
import sys, pathlib, html as H
from playwright.sync_api import sync_playwright
FR = pathlib.Path("/tmp/aichi_map/frames"); OUT = pathlib.Path(sys.argv[1])
CUTS = [
 (1, "0:00–0:05", 5, "地図", "和紙の上に、愛知県の輪郭が製図ペンで描かれていく（線が伸びていく）。<br>音：ペン先の擦れる音、尺八が一音。", "愛知県の地図に、円をひとつ描く。", ""),
 (2, "0:05–0:11", 6, "地図", "名古屋城と岡崎城に点。中点から金の円がコンパスのように描かれ、寸法線が伸びる。", "半径は、名古屋城と岡崎城のあいだ、34.7キロ。", "R34.7km"),
 (3, "0:11–0:17", 6, "地図", "S字が引かれ、尾張に墨が広がって黒、三河は白に。二つの目が城の上にポンと落ちる。右に題字。", "S字で分けると、二つの目は、ふたつの城の上に落ちる。", "題「ふたつの目／愛知の陰陽図」"),
 (4, "0:17–0:19", 2, "地図", "岡崎城の黒い目へ寄る（2倍）。章題が縦書きで出る。", "", "章題「一　白の中の黒」"),
 (5, "0:19–0:26", 7, "AI画", "雪の夜明けの岡崎の城（1543年当時の砦で、天守はまだない）。ゆっくり寄る。<br>音：雪の静けさ、遠い産声。", "1543年の冬。岡崎城で竹千代、のちの徳川家康が生まれる。", "1543年　岡崎城"),
 (6, "0:26–0:32", 6, "AI画", "夕暮れの松並木。輿で運ばれる幼い子の後ろ姿。左へゆっくりパン。<br>音：足音、輿のきしみ。", "数え6歳。人質として送られた先は、尾張の織田家だった。", "尾張・熱田へ"),
 (7, "0:32–0:36", 4, "地図", "三河（白）の中の黒い目が、金の輪を広げて一度だけ脈打つ。<br>音：太鼓を一打。", "白の中に、黒がひとつ宿った。", ""),
 (8, "0:36–0:38", 2, "地図", "尾張と三河の境の線が金色に光る。章題。", "", "章題「二　境の川」"),
 (9, "0:38–0:43", 5, "AI画", "霧の境川。手前の葦から川へ、ゆっくり寄る。<br>音：水の流れ、葦の擦れ。", "尾張と三河のあいだには、その名も「境川」が流れている。", ""),
 (10, "0:43–0:51", 8, "AI画", "豪雨の桶狭間。雨に打たれる旗と陣幕、稲光。人が死ぬ場面は描かない。わずかに揺らす（手持ち風）。<br>音：豪雨、雷鳴、法螺貝。", "1560年、境に近い桶狭間で今川義元が討たれ、家康は岡崎へ戻る。", "1560年　桶狭間"),
 (11, "0:51–0:56", 5, "AI画→地図", "向かい合う二人の武将の手元（黒の袖と白の袖）。後半、地図の黒と白の勾玉が組み合う形へ溶けて替わる。", "2年後、信長と手を結ぶ。黒と白が、組み合った。", "1562年　清洲同盟"),
 (12, "0:56–0:58", 2, "地図", "名古屋城の白い目へ寄る（2倍）。章題。", "", "章題「三　黒の中の白」"),
 (13, "0:58–1:04", 6, "AI画", "石垣を積む大勢の人々、足場に囲まれた天守（天下普請）。左から右へパン。<br>音：槌の音、掛け声。", "1610年、家康は尾張の真ん中に、名古屋城を建てさせる。", "1610年　名古屋城"),
 (14, "1:04–1:09", 5, "既存画", "金鯱の陰陽図（作成済みの日本画）へ、ゆっくり寄る。", "三河の男が、尾張の黒に打ち込んだ、白い点。", ""),
 (15, "1:09–1:12", 3, "地図", "尾張（黒）の中の白い目が、金の輪を広げて脈打つ。ナレーションなしの間。<br>音：太鼓を一打。", "（間）", ""),
 (16, "1:12–1:14", 2, "地図", "地図全体へ引く。章題。", "", "章題「四　三百年後」"),
 (17, "1:14–1:20", 6, "AI画", "大正期のレンガ造りの紡績工場、並ぶ織機に差す光。奥へゆっくり寄る。<br>音：織機の規則的な音。", "1918年、豊田佐吉は名古屋で紡績の会社を興す。", "1918年　名古屋・栄生"),
 (18, "1:20–1:27", 7, "AI画", "昭和初期の自動車の組み立てから、右側の現代の工場の光へパン。ロゴ・車名は出さない。<br>音：溶接の火花、機械の音が現代の音へ。", "事業はやがて三河へ。そこで自動車が生まれた。尾張の種が、三河で育つ。", "刈谷 → 挙母（いまの豊田市）"),
 (19, "1:27–1:33", 6, "地図", "製図の画面。金のS字と灰色の直線が重なり、二つの数字が並ぶ。", "確かめると、S字は直線と変わらなかった。境の形に、秘密はない。", "S字 89.5%／直線 89.6%"),
 (20, "1:33–1:39", 6, "地図", "塗りと線が薄れていき、二つの目だけが残る。", "この土地をひとつの円にしているのは、互いの中にいる、相手のほうだ。", ""),
 (21, "1:39–1:43", 4, "地図", "引きの太極図に題字。暗転。<br>音：尺八の余韻。", "", "題「ふたつの目／愛知の陰陽図」"),
]
PER = 6; pages = [CUTS[i:i + PER] for i in range(0, len(CUTS), PER)]
css = """
@page{size:A4;margin:0}
*{box-sizing:border-box} body{margin:0;font-family:'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;color:#161616}
.page{width:210mm;height:297mm;padding:9mm 10mm 8mm;page-break-after:always;position:relative}
.hd{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:0.6mm solid #161616;padding-bottom:1.6mm;margin-bottom:1.8mm}
.ttl{font-family:'Hiragino Mincho ProN',serif;font-weight:600;font-size:5.2mm;letter-spacing:.3mm}
.ttl small{font-family:'Hiragino Sans',sans-serif;font-weight:400;font-size:3mm;color:#8a6a24;margin-left:3mm}
.meta{font-size:2.6mm;color:#444;text-align:right;line-height:1.5}
table{width:190mm;border-collapse:collapse;table-layout:fixed}
th{font-size:2.5mm;font-weight:700;background:#efe8da;border:0.25mm solid #161616;padding:1mm}
td{border:0.25mm solid #161616;vertical-align:top;padding:1.3mm;font-size:2.65mm;line-height:1.5}
td.c{text-align:center;vertical-align:middle;font-weight:700;font-size:4mm}
td.c span{display:block;font-size:2.2mm;font-weight:400;color:#555;margin-top:1mm}
td.p{padding:0.8mm;position:relative} td.p img{display:block;width:100%;height:auto}
td.p .kind{position:absolute;left:1.8mm;top:1.8mm;font-size:2.2mm;color:#8a6a24;background:rgba(255,255,255,.88);padding:0.2mm 1.1mm;border-radius:0.6mm}
td.s{text-align:center;vertical-align:middle;font-weight:700;font-size:3.6mm}
.na{font-weight:700} .tx{color:#8a6a24;margin-top:1.2mm}
.ft{position:absolute;bottom:6mm;left:10mm;right:10mm;font-size:2.3mm;color:#666;display:flex;justify-content:space-between}
"""
body = []
for pi, pg in enumerate(pages, 1):
    rows = []
    for n, tc, sec, kind, act, na, tx in pg:
        img = (FR / f"C{n:02d}.png").as_uri()
        na_html = f'<div class="na">{H.escape(na)}</div>' if na else '<div style="color:#999">—</div>'
        tx_html = f'<div class="tx">文字：{H.escape(tx)}</div>' if tx else ""
        rows.append(f'<tr><td class="c">{n}<span>{tc}</span></td>'
                    f'<td class="p"><img src="{img}"><div class="kind">{kind}</div></td>'
                    f'<td>{act}</td><td>{na_html}{tx_html}</td><td class="s">{sec}″</td></tr>')
    body.append(f'''<div class="page"><div class="hd"><div class="ttl">ふたつの目 ― 愛知の陰陽図<small>絵コンテ</small></div>
<div class="meta">16:9 ／ 尺 1分43秒 ／ 21カット<br>2026-10-29</div></div>
<table><colgroup><col style="width:13mm"><col style="width:66mm"><col style="width:55mm"><col style="width:44mm"><col style="width:12mm"></colgroup>
<tr><th>カット</th><th>画面</th><th>内容（動き・音）</th><th>ナレーション・文字</th><th>秒</th></tr>
{"".join(rows)}</table>
<div class="ft"><span>地図＝国土数値情報（行政区域・2021年）を加工／AI画＝Nano Banana Pro（日本画風）</span><span>{pi} / {len(pages)}</span></div></div>''')
html = OUT / "ekonte.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(body)}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
    pg.goto(html.as_uri()); pg.wait_for_timeout(800)
    pg.pdf(path=str(OUT / "ekonte.pdf"), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    pg.screenshot(path=str(OUT / "ekonte_p1.png"), clip={"x": 0, "y": 0, "width": 794, "height": 1123})
    pg.screenshot(path=str(OUT / "ekonte_all.png"), full_page=True)
    b.close()
print("pages", len(pages))
