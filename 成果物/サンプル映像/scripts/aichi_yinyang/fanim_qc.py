"""合成した動画のコマに、城の本当の位置（P1=名古屋城, P2=岡崎城）の印を描いて並べる"""
import json, sys
from PIL import Image, ImageDraw
p = json.load(open("/tmp/aichi_map/fanim/params.json"))
outs = []
for f in sys.argv[2:]:
    im = Image.open(f).convert("RGB"); d = ImageDraw.Draw(im)
    for (x, y) in (p["P1"], p["P2"]):
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(255, 0, 0), width=2)
        d.line([x - 24, y, x + 24, y], fill=(255, 0, 0), width=1); d.line([x, y - 24, x, y + 24], fill=(255, 0, 0), width=1)
    outs.append(im)
# 全体（縮小）と、城まわりの拡大を並べる
W = 960; rows = []
for im in outs:
    a = im.resize((W, 540))
    c1 = im.crop((int(p["P1"][0]) - 90, int(p["P1"][1]) - 90, int(p["P1"][0]) + 90, int(p["P1"][1]) + 90)).resize((270, 270), Image.NEAREST)
    c2 = im.crop((int(p["P2"][0]) - 90, int(p["P2"][1]) - 90, int(p["P2"][0]) + 90, int(p["P2"][1]) + 90)).resize((270, 270), Image.NEAREST)
    row = Image.new("RGB", (W + 560, 540), "white"); row.paste(a, (0, 0)); row.paste(c1, (W + 10, 0)); row.paste(c2, (W + 290 - 10 + 10, 0))
    rows.append(row)
sheet = Image.new("RGB", (W + 560, 540 * len(rows)), "white")
for i, r in enumerate(rows): sheet.paste(r, (0, 540 * i))
sheet.save(sys.argv[1]); print(sys.argv[1], sheet.size)
