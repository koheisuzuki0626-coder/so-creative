#!/usr/bin/env python3
"""sitemap.xml の <lastmod> を git の最終コミット日で書き直す。

    python3 scripts/update-dates.py

lastmod は、実際の更新日と合っていないと検索エンジンに無視される（合っていない
サイトが多いので、そもそも信用されにくい）。手で書くと必ずずれるので、git から取る。
公開に切り替える前と、中身をまとめて直したあとに走らせる。
"""
import re, subprocess, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITEMAP = ROOT / 'sitemap.xml'

def last_commit_date(path):
    out = subprocess.run(['git', 'log', '--format=%cs', '-1', '--', path],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.strip()

def main():
    xml = SITEMAP.read_text(encoding='utf-8')
    changed = []
    def fix(m):
        url, rest = m.group(1), m.group(2)
        name = url.rsplit('/', 1)[-1] or 'index.html'   # 末尾が / のトップは index.html
        if not (ROOT / name).exists():
            sys.exit(f'sitemap に {name} があるがファイルが無い')
        d = last_commit_date(name)
        if not d:
            sys.exit(f'{name} のコミット日が取れない')
        old = re.search(r'<lastmod>([^<]*)</lastmod>', rest)
        if old and old.group(1) == d:
            return m.group(0)
        changed.append((name, old.group(1) if old else '(無し)', d))
        rest = re.sub(r'\s*<lastmod>[^<]*</lastmod>', '', rest)
        return f'<url><loc>{url}</loc>{rest}<lastmod>{d}</lastmod>'
    new = re.sub(r'<url>\s*<loc>([^<]+)</loc>(.*?)(?=</url>)', fix, xml, flags=re.S)
    if changed:
        SITEMAP.write_text(new, encoding='utf-8')
        for name, a, b in changed:
            print(f'{name:24} {a} → {b}')
    else:
        print('変更なし')

if __name__ == '__main__':
    main()
