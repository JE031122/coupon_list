import json
import html

# data.json を読んで index.html を生成する。
# 「チャンネル別 / ブランド別」タブ切り替え＋検索ボックス（どちらもブラウザ内のJSで動く）。

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
  .updated { color:#888; font-size:13px; margin-bottom:16px; }
  .search { width:100%; box-sizing:border-box; padding:11px 14px; font-size:15px;
            border:1px solid #d0d5dd; border-radius:10px; margin-bottom:14px; }
  .search:focus { outline:none; border-color:#1a56db; }
  .tabs { display:flex; gap:8px; margin-bottom:20px; }
  .tab { border:1px solid #d0d5dd; background:#fff; color:#444; border-radius:999px;
         padding:7px 18px; font-size:14px; font-weight:600; cursor:pointer; }
  .tab.active { background:#1a56db; color:#fff; border-color:#1a56db; }
  .group { background:#fff; border-radius:12px; padding:16px 20px;
           margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
  .group h2 { font-size:16px; margin:0 0 8px; }
  .code-row { display:flex; align-items:center; gap:10px; padding:12px 0;
              border-top:1px solid #eee; flex-wrap:wrap; }
  .badge { font-size:12px; font-weight:600; padding:3px 10px; border-radius:999px;
           white-space:nowrap; }
  .badge.brand { background:#e8f0fe; color:#1a56db; }
  .badge.unknown { background:#f0f0f0; color:#888; }
  .badge.channel { background:#eef7ee; color:#2f7d32; }
  .code { font-weight:700; font-size:18px; letter-spacing:0.5px;
          background:#fff3cd; padding:3px 12px; border-radius:6px; }
  .copy { border:1px solid #d0d5dd; background:#fff; border-radius:6px;
          padding:4px 12px; font-size:13px; cursor:pointer; }
  .copy:active { background:#eef2f6; }
  .links { margin-left:auto; display:flex; gap:14px; }
  .link { color:#2563eb; font-size:13px; text-decoration:none; }
  .hidden { display:none; }
  .noresult { color:#888; font-size:14px; padding:8px 2px; }
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
function showView(name) {
  document.getElementById('view-channel').classList.toggle('hidden', name !== 'channel');
  document.getElementById('view-brand').classList.toggle('hidden', name !== 'brand');
  document.getElementById('tab-channel').classList.toggle('active', name === 'channel');
  document.getElementById('tab-brand').classList.toggle('active', name === 'brand');
  applySearch();
}
function applySearch() {
  var q = document.getElementById('search').value.toLowerCase().trim();
  var terms = q ? q.split(/\\s+/) : [];
  var view = document.querySelector('#view-channel:not(.hidden), #view-brand:not(.hidden)');
  if (!view) return;
  var anyVisible = false;
  view.querySelectorAll('.group').forEach(function (group) {
    var groupVisible = false;
    group.querySelectorAll('.code-row').forEach(function (row) {
      var hay = row.getAttribute('data-search') || '';
      var match = terms.every(function (t) { return hay.indexOf(t) !== -1; });
      row.classList.toggle('hidden', !match);
      if (match) groupVisible = true;
    });
    group.classList.toggle('hidden', !groupVisible);
    if (groupVisible) anyVisible = true;
  });
  var nr = view.querySelector('.noresult');
  if (nr) nr.classList.toggle('hidden', anyVisible);
}
</script>
</body>
</html>"""


def search_attr(code, brand, channel):
    """行に埋め込む検索対象（コード・ブランド・チャンネルを小文字で連結）"""
    text = " ".join(x for x in [code, brand, channel] if x).lower()
    return html.escape(text, quote=True)


def render_code_row(c, badge_html, brand_urls, channel_name):
    esc_code = html.escape(c["code"])
    buy = c.get("dest") or (brand_urls.get(c["brand"], "") if c["brand"] else "")
    links = ""
    if buy:
        links += f'<a class="link" href="{html.escape(buy)}" target="_blank" rel="noopener">購入ページに移動する</a>'
    links += f'<a class="link" href="{html.escape(c["video_url"])}" target="_blank" rel="noopener">動画先</a>'
    hay = search_attr(c["code"], c["brand"], channel_name)
    return (
        f'<div class="code-row" data-search="{hay}">'
        f'{badge_html}'
        f'<span class="code">{esc_code}</span>'
        f'<button class="copy" onclick="copyCode(this, \'{esc_code}\')">コピー</button>'
        f'<span class="links">{links}</span>'
        f'</div>'
    )


def brand_badge(brand):
    if brand:
        return f'<span class="badge brand">{html.escape(brand)}</span>'
    return '<span class="badge unknown">ブランド確認中</span>'


def build_channel_view(data):
    """チャンネル別。左バッジ＝ブランド名。検索対象にはチャンネル名も含める。"""
    brand_urls = data.get("brand_urls", {})
    parts = ['<div id="view-channel">']
    for ch in data["channels"]:
        if not ch["codes"]:
            continue
        parts.append(f'<section class="group"><h2>{html.escape(ch["channel"])}</h2>')
        for c in ch["codes"]:
            parts.append(render_code_row(c, brand_badge(c["brand"]), brand_urls, ch["channel"]))
        parts.append('</section>')
    parts.append('<div class="noresult hidden">該当するクーポンが見つかりませんでした。</div>')
    parts.append('</div>')
    return "".join(parts)


def build_brand_view(data):
    """ブランド別。チャンネル横断で集約し投稿日の新しい順。左バッジ＝チャンネル名。"""
    brand_urls = data.get("brand_urls", {})
    brands = {}
    for ch in data["channels"]:
        for c in ch["codes"]:
            label = c["brand"] if c["brand"] else "ブランド確認中"
            row = dict(c)
            row["from_channel"] = ch["channel"]
            brands.setdefault(label, []).append(row)
    for label in brands:
        brands[label].sort(key=lambda r: (r.get("latest_date", ""), r["count"]), reverse=True)
    ordered = sorted(brands.items(),
                     key=lambda kv: max((r.get("latest_date", "") for r in kv[1]), default=""),
                     reverse=True)

    parts = ['<div id="view-brand" class="hidden">']
    for label, rows in ordered:
        parts.append(f'<section class="group"><h2>{html.escape(label)}</h2>')
        for r in rows:
            badge = f'<span class="badge channel">{html.escape(r["from_channel"])}</span>'
            parts.append(render_code_row(r, badge, brand_urls, r["from_channel"]))
        parts.append('</section>')
    parts.append('<div class="noresult hidden">該当するクーポンが見つかりませんでした。</div>')
    parts.append('</div>')
    return "".join(parts)


def build_html(data):
    parts = [HTML_HEAD]
    parts.append(f'<div class="updated">最終更新: {data["updated_at"]}（毎朝6時に自動更新）</div>')
    parts.append(
        '<input id="search" class="search" type="search" '
        'placeholder="コード・ブランド・YouTuber名で検索" '
        'oninput="applySearch()">'
    )
    parts.append(
        '<div class="tabs">'
        '<button id="tab-channel" class="tab active" onclick="showView(\'channel\')">チャンネル別</button>'
        '<button id="tab-brand" class="tab" onclick="showView(\'brand\')">ブランド別</button>'
        '</div>'
    )
    parts.append(build_channel_view(data))
    parts.append(build_brand_view(data))
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
