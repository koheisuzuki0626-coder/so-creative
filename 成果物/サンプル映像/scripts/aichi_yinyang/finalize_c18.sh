#!/bin/bash
# C18 が届いたら：落として確認用のコマを作り、完成版を組む。使い方: finalize_c18.sh <URL>
set -e
python3 /tmp/scripts_map/kling_qc.py "C18=$1"
cp /tmp/aichi_map/kling/C18_raw.mp4 /tmp/aichi_map/kling_use/C18.mp4
rm -rf /tmp/aichi_map/edit/seg
cd /tmp && KLING_DIR=/tmp/aichi_map/kling_use python3 /tmp/scripts_map/assemble.py /tmp/aichi_map/audio/mix_taro.wav /tmp/aichi_map/edit/final.mp4
