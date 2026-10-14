#!/usr/bin/env python3
"""Higgsfield でいま使えるモデルIDをカタログから引く。

    python3 tools/hf_models.py            # 全件
    python3 tools/hf_models.py kling      # 絞り込み

⚠️ 2026-10-15：`hf_wrapper.py` の既定ID3つが全部 model_not_found になっていた
（提供側で消えた）。決め打ちのIDは黙って腐るので、生成が通らない時はまずここを見る。
`model_not_found` ならID切れ、`not_enough_credits` なら残高切れで、別の話。
"""
import asyncio, os, pathlib, re, sys

BASE = pathlib.Path(__file__).resolve().parent.parent
env = BASE / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def main(q):
    import aiohttp
    h = {"hf-api-key": os.getenv("HIGGSFIELD_API_KEY", ""),
         "hf-secret": os.getenv("HIGGSFIELD_API_SECRET", "")}
    async with aiohttp.ClientSession() as s:
        async with s.get("https://platform.higgsfield.ai/models", headers=h) as r:
            if r.status != 200:
                print(f"カタログが引けない（HTTP {r.status}）"); return 1
            t = await r.text()
    ids = sorted(set(re.findall(
        r'"(?:id|name|application|slug)"\s*:\s*"([\w\-./]{3,60})"', t)))
    ids = [i for i in ids if "/" in i]
    if q:
        ids = [i for i in ids if q.lower() in i.lower()]
    for i in ids:
        print(" ", i)
    print(f"{len(ids)}件")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "")))
