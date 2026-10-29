import math, sys
sys.argv = [sys.argv[0], "/tmp/aichi_map/out"]
src = open("/tmp/scripts_map/render_map.py").read()
# 幾何とデータ読み込みの部分だけ使う（描画の手前まで）
exec(src.split("# どちら向きに置くと")[0])
dark, white = taiji(1)
def seg_side(pt):  # 等距離線：近い城の側
    return "owari" if math.dist(pt, NAGOYA) < math.dist(pt, OKAZAKI) else "mikawa"
N = 90
tot = {"owari": 0, "mikawa": 0}; tj = {"owari": 0, "mikawa": 0}; eq = {"owari": 0, "mikawa": 0}
for i in range(-N, N + 1):
    for j in range(-N, N + 1):
        pt = (C[0] + R * i / N, C[1] + R * j / N)
        if math.dist(pt, C) > R: continue
        pv = prov_at(pt)
        if pv is None: continue
        tot[pv] += 1
        in_dark = pip(pt, dark)
        tj[pv] += (pv == "owari") == in_dark
        eq[pv] += seg_side(pt) == pv
T = tot["owari"] + tot["mikawa"]
km_per_px = 110.95 / S
print(f"円内の陸地の点: {T}（尾張 {tot['owari']} / 三河 {tot['mikawa']}）")
print(f"太極図   : 全体 {100*(tj['owari']+tj['mikawa'])/T:.1f}%  尾張→黒 {100*tj['owari']/tot['owari']:.1f}%  三河→白 {100*tj['mikawa']/tot['mikawa']:.1f}%")
print(f"等距離線 : 全体 {100*(eq['owari']+eq['mikawa'])/T:.1f}%  尾張側 {100*eq['owari']/tot['owari']:.1f}%  三河側 {100*eq['mikawa']/tot['mikawa']:.1f}%")
# 名古屋城〜岡崎城の距離（球面）
lat1, lon1, lat2, lon2 = map(math.radians, (35.18515, 136.89949, 34.95625, 137.15888))
d = 2 * 6371.0 * math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2))
print(f"名古屋城〜岡崎城: {d:.1f} km（図上 R={R:.0f}px ＝ {R*km_per_px:.1f} km）")
