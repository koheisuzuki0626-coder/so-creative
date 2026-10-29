import sys, pathlib
from playwright.sync_api import sync_playwright
OUT = pathlib.Path("/tmp/aichi_map/edit")
TEL = {"C05": "1543年　岡崎城", "C06": "尾張・熱田へ", "C10": "1560年　桶狭間", "C11": "1562年　清洲同盟",
       "C13": "1610年　名古屋城", "C17": "1918年　名古屋・栄生", "C18": "刈谷 → 挙母（いまの豊田市）"}
css = """html,body{margin:0;width:1920px;height:1080px;background:transparent}
.p{position:absolute;left:96px;bottom:86px;display:flex;align-items:center;gap:18px;
 background:rgba(239,232,218,.86);padding:14px 30px 16px 22px;border-radius:3px;box-shadow:0 2px 14px rgba(0,0,0,.18)}
.r{width:4px;height:44px;background:#b8892d}
.t{font-family:'Hiragino Mincho ProN',serif;font-weight:600;font-size:40px;color:#161616;letter-spacing:4px;white-space:nowrap}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    for k, t in TEL.items():
        pg.set_content(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><div class='p'><div class='r'></div><div class='t'>{t}</div></div></body></html>")
        pg.wait_for_timeout(150); pg.screenshot(path=str(OUT / f"tel_{k}.png"), omit_background=True)
    b.close()
print("ok", len(TEL))
