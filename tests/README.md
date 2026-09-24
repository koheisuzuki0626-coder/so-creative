# テスト

サイトの「決めごと」を実行可能な形で固定してある。
料金・工数・納期・文言・配色は複数箇所に散らばっているので、
片方だけ直すとここが落ちる。

## 走らせ方

```
node tests/run.mjs
```

**配信サーバーは run.mjs が自分で立てて、終わったら落とす**（2026-09-24）。
それまでは手で立てる前提で、立てっぱなしのサーバーが毎回残っていた。
すでに 8899 が応答していればそちらを使い、**横から落とさない**
（手で立てて開発している最中のため）。

個別に走らせるときは、サーバーが要る。

```
python3 -m http.server 8899 --directory . &
node tests/pricing.mjs
```

配信先を変えるなら `BASE=https://... node tests/run.mjs`。
外のホストを指したときは run.mjs は立てない。

Playwright は既定で `/opt/node22/lib/node_modules/playwright` を見る。
別の場所にあるときは `PW=/path/to/playwright/index.js node tests/run.mjs`。
Mac では `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright@<venvのplaywrightと同じ版>` を
どこかに入れて、その `index.js` を `PW` で指す（ブラウザは `~/Library/Caches/ms-playwright` の共用）。

## 何を見ているか

| ファイル | 内容 |
|----------|------|
| `pricing.mjs` | 全102通りをクリックして金額・納期・時間単価を検証。**採算の担保はここ** |
| `header.mjs` | 広い画面の並び、狭い画面の横スクロール、黒帯の境目のコントラスト |
| `content.mjs` | 画面と構造化データ・会社概要・プライバシーポリシーの突き合わせ |
| `funnel.mjs` | 料金計算機の段差と `funnel.html` |
| `a11y.mjs` | 全テキストのコントラスト（AA）と日本語の折り返し |

## どのページに何があるか（2026-09-23 に動かした）

トップが 100,000字 を超えていて、`title` を1つしか持てなかったので分けた。

| ページ | 中身 | テストの主担当 |
|---|---|---|
| `index.html` | 事業内容・撮影しない理由・ジャンルの索引・写真1枚から・制作の流れ・料金の要約・FAQ | `content` `header` |
| `pricing.html` | **料金の計算機**・尺ごとの実額の表・段の違い・支払条件 | `pricing` `funnel` |
| `works.html` | **ジャンル9枚とサンプル動画**・実測した仕様 | `content` |
| `about.html` `privacy.html` | 会社概要・プライバシーポリシー | `content` |

計算機とジャンルのカードは**トップには無い**。二重に持つと式や文言が
食い違うので、それぞれ1か所にしてある。テストを足すときは、
その要素がどのページにあるかを先に確かめること。

JSも分かれている。`assets/funnel.js`（通過率の計測。`track` はここだけ）、
`assets/pricing.js`（計算機。即時関数で包んである）、
`assets/sample.js`（サンプルの音声切り替え）。

## 置き場所について

**一時ディレクトリに置かないこと。**
以前このテスト群を作業用の一時ディレクトリに置いていて、
セッションの途中で消えて失われた。リポジトリに入れておけば残る。
