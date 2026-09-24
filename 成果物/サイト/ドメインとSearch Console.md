# 独自ドメインと Search Console（2026-09-24 調べ）

SEOの土台であり、**主軸の営業経路（28社へのアウトバウンド）の信用**でもある。
サイトのURLとメールアドレスが、いま両方とも借り物になっている。

| | いま | 問題 |
|---|---|---|
| サイト | `koheisuzuki0626-coder.github.io/so-creative/` | GitHubのユーザー名が入る。B2Bの初回メールに貼るには弱い |
| メール | `bonvoyage.ti@icloud.com` | 280名規模の会社の採用担当に、iCloudのアドレスから送ることになる |

**両方、独自ドメインで同時に解決する。**

---

## 1. どのドメインを取るか

**2026-09-24 に RDAP で実際に確認した結果**（whois は IANA に落ちて判定にならないので RDAP を使った）。

| ドメイン | 状態 |
|---|---|
| **so-creative.jp** | **空き** ← 推す |
| socreative.jp | 空き |
| so-creative.video | 空き |
| so-creative.work | 空き |
| so-creative.com | 登録済み |
| socreative.com | 登録済み |
| so-creative.net | 登録済み |
| so-creative.studio | 登録済み |

**`so-creative.jp` を推す理由**

- `.com` が取れない以上、日本の中小企業を相手にするなら `.jp` が自然
- **`.co.jp` は法人登記が要る**ので、個人事業主では取れない。開業後も同じ
- 社名の表記（ハイフン入りの `so-creative`）とURLが一致する。
  ロゴも `so-creative` なので、`socreative.jp` だと表記が割れる

費用は年 **¥3,000〜4,000** 程度（レジストラによる。**取る前に実額を確認すること**）。
月¥57,835 のツール代に対して誤差。

---

## 2. 順番が重要（いま移すのが一番安い）

**noindex を外す前に移す。**公開して検索に載ってから移すと、
評価の引き継ぎとリダイレクトの手間が出る。いまは全ページ noindex なので、
**移行コストが一番低い瞬間**にいる。

そして**営業文面Dに貼るURLも、送る前に確定させたい**。
28社に送ったあとでドメインを変えると、送った側のリンクが古いままになる。

```
いま（noindex）→ ドメイン移行 → 開業 → noindex を外す → 送る
```

---

## 3. 移行の手順

**URLの書き換えスクリプトは既にある。**`scripts/set-site-url.mjs` が
canonical / og:url / og:image / 構造化データ / sitemap.xml / robots.txt を
まとめて書き換え、CNAME も書き出す。手で17か所直す必要はない。

1. **ドメインを取る**（レジストラはどこでもよい。お名前.com / Xserver / Cloudflare など）
2. **DNSを設定する**
   - apex（`so-creative.jp`）… A レコード 4本
     `185.199.108.153` / `185.199.109.153` / `185.199.110.153` / `185.199.111.153`
     ※**GitHubの公式ドキュメントで最新のIPを確認してから入れること**
   - `www.so-creative.jp` … CNAME → `koheisuzuki0626-coder.github.io`
3. **GitHub の Settings → Pages → Custom domain** に `so-creative.jp` を入れる
4. **Enforce HTTPS** にチェック（証明書の発行に数分〜1時間かかる）
5. **URLを書き換える**
   ```
   node scripts/set-site-url.mjs https://so-creative.jp/
   ```
   `--show` で現在の設定を確認できる。CNAME ファイルも自動で作られる
6. **テストを通す**
   ```
   python3 -m http.server 8899 --directory . &
   PW=<playwrightのindex.js> BASE=http://127.0.0.1:8899 node tests/run.mjs
   ```
   ※Playwright は **venv と同じ 1.60.0** を使うこと。版が違うとブラウザが見つからない
7. **`成果物/_テンプレート/営業文面.md` と `差し込み文_◎10社.md` のURLを差し替える**
8. **メールを作る**（`suzuki@so-creative.jp` など）。
   レジストラの転送機能で足りるか、Google Workspace を入れるかは費用次第

---

## 4. Search Console（noindex のままでもできる）

**所有権の確認は「サイトを検索に出す」ことではない。**所有者であることを
証明するだけで、noindex は外れない。先に済ませておけば、
**開業日に noindex を外した瞬間からクロールが走る。**

### いまやること

1. Search Console でプロパティを追加
2. 所有権の確認
   - **ドメインを取ったなら DNS の TXT レコード**（`so-creative.jp` 配下すべてを一度でカバーできる）
   - まだなら HTML ファイルをリポジトリ直下に置く方式
3. Bing Webmaster Tools も同様に（Search Console からインポートできる）

### 開業日にやること（この順番で）

1. 公開6ページの `<meta name="robots">` から `noindex, nofollow` を外す
   （index / pricing / works / company-video / **recruit-video** / about / privacy）
2. `funnel.html` / `roadmap.html` / `record.html` は**社内用なので noindex のまま**
3. `robots.txt` の `# Sitemap:` のコメントを外す
4. Search Console で sitemap を送信
5. 主要ページを URL 検査 → インデックス登録をリクエスト
6. **GA4 から自分のアクセスを除外する**（ロードマップの宿題）

※1〜3を別々にやると「sitemap では出しているのに中身は拒否」という食い違いが残る。
`tests/content.mjs` がこの足並みを検査しているので、**必ず一度にやってテストを通す。**

---

## やらないこと

- **被リンクを買わない。**短期の順位より、ペナルティの方が高くつく
- **記事を量産しない。**主軸はアウトバウンドで、SEOは補助。
  「AI動画制作 名古屋」のような語で上位を取るには時間がかかる。
  現実的なのはロングテール（「会社紹介動画 撮影なし 費用」など）と指名検索
- **ドメインを何度も変えない。**変えるなら公開前の一度だけ
