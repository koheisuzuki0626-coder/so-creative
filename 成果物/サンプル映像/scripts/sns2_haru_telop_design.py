"""SNSショート②（HARU）のステッカー型テロップを、1枚ずつ透過PNGで書き出す。
位置（中心座標）は meta.json に出る。合成は sns2_haru_telop_compose.py。
書体は macOS の筑紫B丸ゴシック（Chromium の Playwright で描く）。
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
OUT = pathlib.Path(sys.argv[1])
A8 = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
CSS = f"""
@font-face{{font-family:'TsukuB';src:url('file://{A8}60484a5d6f3fa8d51dcbeff43b7e70c9d42bcd2f.asset/AssetData/TsukushiBMaruGothic.ttc');}}
html,body{{margin:0;width:1080px;height:1920px;background:transparent;overflow:hidden}}
.w{{position:absolute;left:0;width:1080px;display:flex;justify-content:center}}
.pill{{font-family:'TsukuB','Hiragino Maru Gothic ProN';font-weight:700;color:#3b2418;background:#fffaf2;
 padding:18px 40px 22px;border-radius:999px;font-size:62px;letter-spacing:.02em;white-space:nowrap;
 box-shadow:0 8px 0 rgba(59,36,24,.85);position:relative}}
.pink{{background:#ffd3dc}}
"""
SP = '<svg width="{s}" height="{s}" viewBox="0 0 20 20" style="position:absolute;{st}"><path d="M10 0 C11 7 13 9 20 10 C13 11 11 13 10 20 C9 13 7 11 0 10 C7 9 9 7 10 0Z" fill="{c}"/></svg>'
EL = {
 "cap1": f'<div class="w" style="top:1360px"><div id="e" class="pill" style="transform:rotate(-3deg)">起きてすぐ、飲みたいやつ。{SP.format(s=54,st="right:-30px;top:-34px",c="#f2b33d")}</div></div>',
 "cap2": f'<div class="w" style="top:1360px"><div id="e" class="pill pink" style="transform:rotate(2.5deg)">これは撮るしかない。{SP.format(s=48,st="left:-28px;top:-30px",c="#fff")}{SP.format(s=30,st="left:14px;top:-50px",c="#fff")}</div></div>',
 "end1": '<div class="w" style="top:1250px"><div id="e" class="pill" style="font-size:72px;padding:26px 54px 30px;letter-spacing:.04em">HARU COFFEE STAND</div></div>',
 "end2": f'<div class="w" style="top:1420px;left:150px"><div id="e" class="pill pink" style="font-size:46px;padding:12px 34px 16px;transform:rotate(-6deg)">NEW OPEN!{SP.format(s=40,st="right:-26px;top:-26px",c="#f2b33d")}</div></div>',
 "end3": '<div class="w" style="top:1540px"><div id="e" style="font-family:TsukuB;font-weight:700;font-size:40px;color:#fff;text-shadow:0 3px 8px rgba(0,0,0,.5);padding:4px 10px">#HARUで朝活</div></div>',
}
PAD = 70
meta = {}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1080,"height":1920})
    for k, body in EL.items():
        h = OUT / f"{k}.html"
        h.write_text(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
        pg.goto(h.as_uri()); pg.wait_for_timeout(300)
        r = pg.evaluate("()=>{const r=document.getElementById('e').getBoundingClientRect();return [r.left,r.top,r.width,r.height]}")
        x, y, w, hh = r
        clip = {"x": max(0, x-PAD), "y": max(0, y-PAD), "width": min(1080, w+2*PAD), "height": hh+2*PAD}
        pg.screenshot(path=str(OUT / f"{k}.png"), omit_background=True, clip=clip)
        meta[k] = {"cx": round(clip["x"] + clip["width"]/2), "cy": round(clip["y"] + clip["height"]/2)}
    b.close()
(OUT / "meta.json").write_text(json.dumps(meta))
print(meta)
