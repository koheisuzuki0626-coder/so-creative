#!/usr/bin/env python3
"""CSS・JS の参照に、中身から出した版（?v=ハッシュ）を打つ。

なぜ要るか：GitHub Pages は assets に cache-control: max-age=600 を付ける。
版の指定が無いと、CSSを直しても最大10分は古いものが使われ続ける。
実際に「3列に直したのに2列のまま」という報告が出た（2026-10-06）。
URLが変われば必ず取り直されるので、中身が変わった時だけ版を変える。

使い方：  python3 tools/stamp_assets.py        （書き換える）
          python3 tools/stamp_assets.py --check （ずれていたら終了コード1）
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# ⚠️ CSS だけを対象にする。JS に版を打つと、生成スクリプト
# （scripts/make-genre-pages.py）が script タグを完全一致で書き換えている所と、
# テスト6か所の正規表現が一斉に壊れる。実際に一度やって落ちた。
# JS は中身が滅多に変わらないので、割に合わない。
PAT = re.compile(r'((?:href)=")(assets/[\w./-]+\.css)(?:\?v=[0-9a-f]+)?(")')


def stamp(path: pathlib.Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


def main() -> int:
    check = '--check' in sys.argv
    cache: dict[str, str] = {}
    stale: list[str] = []
    changed = 0

    for html in sorted(ROOT.glob('*.html')):
        src = html.read_text(encoding='utf-8')

        def sub(m: re.Match) -> str:
            asset = m.group(2)
            if asset not in cache:
                f = ROOT / asset
                cache[asset] = stamp(f) if f.exists() else ''
            v = cache[asset]
            if not v:                       # 実体が無い参照はそのまま
                return m.group(0)
            want = f'{m.group(1)}{asset}?v={v}{m.group(3)}'
            if check and m.group(0) != want:
                stale.append(f'{html.name}: {asset}')
            return want

        out = PAT.sub(sub, src)
        if out != src:
            changed += 1
            if not check:
                html.write_text(out, encoding='utf-8')

    if check:
        if stale:
            print(f'⚠️ 版がずれている参照 {len(stale)}件:')
            for s in stale[:10]:
                print(f'   {s}')
            print('   → python3 tools/stamp_assets.py を実行すること')
            return 1
        print('✅ すべての参照が最新の版を指している')
        return 0

    print(f'{changed} ページを書き換えた')
    for a, v in sorted(cache.items()):
        print(f'   {a}  ?v={v}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
