# クーポンコード一覧（プロテイン・サプリ系）

プロテイン・サプリ系YouTuberの概要欄からクーポンコードを自動収集し、一覧サイトとして毎日更新するプロジェクト。

## 🔗 リンク

| ページ | URL | 用途 |
|---|---|---|
| **サイト本体** | https://je031122.github.io/coupon_list/ | クーポン一覧（公開ページ） |
| **管理ページ** | https://je031122.github.io/coupon_list/admin.html | 要対応コードの確認（運営用） |

## 🛠 仕組み

毎朝、GitHub Actions が以下を自動実行します。

1. `update_coupons.py` … 各チャンネルの最新動画（長尺・ショート）の概要欄からクーポンを抽出 → `data.json` を生成
2. `build_site.py` … `data.json`
