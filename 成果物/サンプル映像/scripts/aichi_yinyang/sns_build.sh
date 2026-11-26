#!/bin/bash
# 縦型SNS版（20秒・1080x1920・24fps）を作り直す。使い方: sns_build.sh [作業場所]（既定 /tmp/aichi_map/sns）
# 作業場所に、Drive の元素材4本をこの名前で置いておく（所在は 素材元_台帳.md の「縦型SNS版」）：
#   油絵の人物_動画.mp4 / 尾張と三河_動画.mp4 / 融合_金鯱×地図_動画.mp4 / C21_絵地図_高画質.mp4
# 要るもの：ffmpeg・python3（numpy）・Playwright（sns_render.mjs の冒頭を参照）
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
W=$(mkdir -p "${1:-/tmp/aichi_map/sns}" && cd "${1:-/tmp/aichi_map/sns}" && pwd)

for pair in "油絵の人物_動画.mp4 oil" "尾張と三河_動画.mp4 yin" "融合_金鯱×地図_動画.mp4 kin" "C21_絵地図_高画質.mp4 ezu"; do
  set -- $pair
  [ -f "$W/$1" ] || { echo "元素材が無い: $W/$1" >&2; exit 1; }
  mkdir -p "$W/fr/$2" && ffmpeg -v error -y -i "$W/$1" -q:v 2 -start_number 0 "$W/fr/$2/%04d.jpg"
done
cp "$HERE/sns_scene.html" "$W/"; cp "$ROOT/assets/logo-word.svg" "$W/"

node "$HERE/sns_render.mjs" "$W"
# BGM：尺八は冒頭(0.3s)と「互いの中にいる」(13.4s)、締めの3音は題字が出る16.45s
python3 "$HERE/one_bgm.py" "$W/bgm.wav" 20.0 0.3 99 13.4 16.45
python3 "$HERE/sns_se.py" "$W/bgm.wav" "$W/mix.wav"

# 映像は bt709 で変換してタグも付ける。音は −0.5dB だけ（−14.4 LUFS・線形。圧縮はかけない）
ffmpeg -v error -y -framerate 24 -i "$W/frames/f%05d.jpg" -i "$W/mix.wav" -map 0:v -map 1:a \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -x264-params aq-mode=3 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -af "volume=-0.5dB" -c:a aac -b:a 192k -shortest -movflags +faststart "$W/ふたつの目_縦型SNS版.mp4"
echo "→ $W/ふたつの目_縦型SNS版.mp4"
