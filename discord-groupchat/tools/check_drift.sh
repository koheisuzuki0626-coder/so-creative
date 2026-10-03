#!/usr/bin/env bash
# 成果物/ が main と作業ブランチで食い違っていないかを見る。
#
# なぜ要るか（2026-10-03 に3ファイルでやった）：
#   成果物/ は main と作業ブランチの両方にあり、放っておくと片方だけ新しくなる。
#   目の前にある写しを編集して main へ押すと、main の新しい内容を黙って消す。
#   実際に起きたこと：
#     ・業務委託契約書.md …… 作業ブランチが古く、支払条件・意図しない類似・
#       楽曲特約を消しかけた（cherry-pick の衝突が止めた）
#     ・_書式/業務委託契約書.html …… 「意図しない類似」が入っておらず、
#       9/24 に書いた免責がお客様に一度も届いていなかった
#     ・営業文面.md …… 古い写しに書き足して main へ上書きし、
#       「2か所に置かない」「東北新社」「（税込）」を消した（テストが止めた）
#
# 使い方：成果物/ を編集する【前】に実行する。
#   bash discord-groupchat/tools/check_drift.sh
set -u
cd "$(dirname "$0")/../.." || exit 1
git fetch origin main --quiet 2>/dev/null
# ⚠️ core.quotepath=false が無いと、日本語のパスが "\346\210\220..." に
# エスケープされて返り、git show に渡せず全部「片方にしか無い」に見える
# （2026-10-03 に実際にそうなった）。
echo "■ 成果物/ の食い違い（HEAD ↔ origin/main）"
n=0
while IFS= read -r f; do
    [ -z "$f" ] && continue
    n=$((n + 1))
    a=$(git show "HEAD:$f" 2>/dev/null | wc -c | tr -d ' ')
    b=$(git show "origin/main:$f" 2>/dev/null | wc -c | tr -d ' ')
    if [ "$b" = "0" ]; then
        printf '  作業ブランチのみ  %s\n' "$f"
    elif [ "$a" = "0" ]; then
        printf '  main のみ        %s\n' "$f"
    else
        printf '  中身が違う (%s↔%s バイト)  %s\n' "$a" "$b" "$f"
    fi
done <<< "$(git -c core.quotepath=false diff --name-only HEAD origin/main -- 成果物/)"
[ "$n" = "0" ] && echo "  食い違いなし" \
  || echo "
  ⚠️ 編集する前に、どちらが新しいかを確かめること。
     新しい方を正として、もう片方へ揃える。目の前の写しに書き足してはいけない。
     差分を見る: git diff HEAD origin/main -- '<パス>'"
