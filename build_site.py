import json
import html

# data.json を読んで index.html を生成するスクリプト。
# 見た目はこれまで（チャンネル別表示）と完全に同じ。

HTML_HEAD = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>クーポンコード一覧（プロテイン・サプリ系）</title>
<style>
  body { font-family: -apple-system, "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
         background:#f5f6f8; color:#1a1a1a; margin:0; padding:24px; }
  .wrap { max-width:720px; margin:0 auto; }
  h1 { font-size:22px; margin:0 0 4px; }
  .updated { color:#888; font-size:13px; margin-bottom:24px; }
  .channel { background:#fff; border-radius:12px; padding:16px 20px;
             margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
  .channel h2 { font-size:16px; margin:0 0 8px; }
  .code-row { display:flex; align-items:center; gap:10px; padding:12px 0;
              border-top:1px solid #eee; flex-wrap:wrap; }
  .brand { background:#e8f0fe; color:#1a56db; font-size:12px; font-weight:600;
           padding:3px 10px; border-radius:999px; white-space:nowrap; }
  .brand.unknown { background:#f0f0f0; color:#888; }
  .code { font-weight:700; font-size:18px; letter-spacing:0.5px;
          background:#fff3cd; padding:3px 12px; border-radius:6px; }
  .copy { border:1px solid #d0d5dd; background:#fff; border-radius:6px;
          padding:4px 12px; font-size:13px; cursor:pointer; }
  .copy:active { background:#eef2f6; }
  .count { color:#666; font-size:13px; }
  .links { margin-left:auto; display:flex; gap:14px; }
  .link { color:#2563eb; font-size:13px; text-decoration:none; }
</style>
</head>
<body>
<div class="wrap">
<h1>クーポンコード一覧（プロテイン・サプリ系）</h1>
"""

HTML_TAIL = """</div>
<script>
function copyCode(btn, code) {
  navigator.clipboard.writeText(code).then(function () {
    var old = btn.textContent;
    btn.textContent = "コピーしました!";
    setTimeout(function () { btn.textContent = old; }, 1500);
  });
}
</script>
</body>
</html>"""


def build_html(data):
    brand_urls = data.get("brand_urls", {})
    parts = [HTML_HEAD,
             f'<div class="updated">最終更新: {data["updated_at"]}（毎朝6時に自動更新）</div>']
    for ch in data["channels"]:
        codes = ch["codes"]
        if not codes:
            continue
        parts.append(f'<section class="channel"><h2>{html.escape(ch["channel"])}</h2>')
        for c in codes:
            code, brand = c["code"], c["brand"]
            esc_code = html.escape(code)
            if brand:
                brand_tag = f'<span class="brand">{html.escape(brand)}</span>'
            else:
                brand_tag = '<span class="brand unknown">ブランド確認中</span>'
            links = ""
            buy = c.get("dest") or (brand_urls.get(brand, "") if brand else "")
            if buy:
                links += f'<a class="link" href="{html.escape(buy)}" target="_blank" rel="noopener">購入ページに移動する</a>'
            links += f'<a class="link" href="{html.escape(c["video_url"])}" target="_blank" rel="noopener">動画先</a>'
            parts.append(
                f'<div class="code-row">'
                f'{brand_tag}'
                f'<span class="code">{esc_code}</span>'
                f'<button class="copy" onclick="copyCode(this, \'{esc_code}\')">コピー</button>'
                f'<span class="count">{c["count"]}本の動画で言及</span>'
                f'<span class="links">{links}</span>'
                f'</div>'
            )
        parts.append('</section>')
    parts.append(HTML_TAIL)
    return "".join(parts)


def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)
    page = build_html(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    n = sum(1 for ch in data["channels"] if ch["codes"])
    print(f"index.html を生成しました（表示チャンネル {n}）")


if __name__ == "__main__":
    main()
