from playwright.sync_api import sync_playwright
css = """html,body{margin:0;width:1920px;height:1080px;background:transparent}
.t{position:absolute;writing-mode:vertical-rl;font-family:'Hiragino Mincho ProN',serif;font-weight:600}
.a{left:1700px;top:130px;font-size:96px;color:#161616;letter-spacing:14px;text-shadow:0 0 18px rgba(239,232,218,.95),0 0 6px rgba(239,232,218,.95)}
.b{left:1590px;top:190px;font-size:44px;color:#b8892d;letter-spacing:10px;text-shadow:0 0 14px rgba(239,232,218,.95)}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.set_content(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><div class='t a'>ふたつの目</div><div class='t b'>愛知の陰陽図</div></body></html>")
    pg.wait_for_timeout(200); pg.screenshot(path="/tmp/aichi_map/v4/title.png", omit_background=True); b.close()
print("ok")
