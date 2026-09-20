#!/bin/sh
# テロップとパッケージで使うフォントを取ってくる。/tmp は消えるので、
# 新しい環境では最初にこれを走らせる。
set -e
D="${SO_FONTS:-/tmp/fonts}"
mkdir -p "$D"
ua='Mozilla/5.0'
get() { [ -s "$D/$1" ] || curl -sL -A "$ua" -o "$D/$1" "$2"; }

# Noto Sans JP（Google Fonts の CSS から TTF の URL を引く）
css=$(curl -sA "$ua" \
  'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;900')
for pair in "400 Regular" "500 Medium" "600 SemiBold" "900 Black"; do
  w=${pair%% *}; name=${pair##* }
  url=$(printf '%s\n' "$css" | awk -v w="$w" '
    /font-weight:/ { cur=$2 }
    /src: url\(/ && cur == w":" { gsub(/.*url\(|\).*/, ""); print; exit }')
  [ -n "$url" ] && get "NotoSansJP-$name.ttf" "$url"
done
ls -l "$D"
