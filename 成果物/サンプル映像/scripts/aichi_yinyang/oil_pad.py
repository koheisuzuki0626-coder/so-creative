"""油絵（3:4）を Kling の 9:16 に載せるための開始画像。上下は絵を鏡写しにしてぼかした帯（完成時に切り落とす）。"""
from PIL import Image, ImageFilter, ImageOps
import json, pathlib
D = pathlib.Path.home() / "Desktop/絵画_2026-10-27"; OUT = pathlib.Path("/tmp/aichi_map/rest")
im = Image.open(D / "A_古典.png").convert("RGB"); W, H = im.size
TH = round(W * 16 / 9); pad = (TH - H) // 2
top = ImageOps.flip(im.crop((0, 0, W, pad))).filter(ImageFilter.GaussianBlur(40))
bot = ImageOps.flip(im.crop((0, H - (TH - H - pad), W, H))).filter(ImageFilter.GaussianBlur(40))
c = Image.new("RGB", (W, TH)); c.paste(top, (0, 0)); c.paste(im, (0, pad)); c.paste(bot, (0, pad + H))
c.resize((1440, 2560), Image.LANCZOS).save(OUT / "oil_9x16.png")
json.dump({"W": W, "H": H, "TH": TH, "pad": pad}, open(OUT / "oil_pad.json", "w")); print(W, H, TH, pad)
