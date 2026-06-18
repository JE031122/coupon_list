import json
import html
import os

# data.json を読んで index.html を生成する。
# タブ（チャンネル別/ブランド別）＋検索（候補表示・ひらがなカタカナ吸収）。
# ブランド別では、ブランドの表記ゆれ（keys。カナ読み含む）も検索・候補の対象にする。
# さらに overrides.json があれば、自動抽出結果に手動の補正を上書き適用する。

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
  .searchbox { position:relative; margin-bottom:14px; }
  .search { width:100%; box-sizing:border-box; padding:11px 14px; font-size:15px;
            border:1px solid #d0d5dd; border-radius:10px; }
  .search:focus { outline:none; border-color:#1a56db; }
  .suggest { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
  .suggest button { border:1px solid #cfe0ff; background:#f3f8ff; color:#1a56db;
                    border-radius:999px; padding:6px 14px; font-size:13px; cursor:pointer; }
  .suggest button:active { background:#e3eeff; }
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
// 候補は [表示ラベル, マッチ用テキスト] のペア。マッチ用にカナ読み等を含める。
var SUGGEST = { channel: __SUGGEST_CHANNEL__, brand: __SUGGEST_BRAND__ };

function copyCode(btn, code) {
  navigator.clipboard.writeText(code).then(function () {
    var old = btn.textContent;
    btn.textContent = "コピーしました!";
    setTimeout(function () { btn.textContent = old; }, 1500);
  });
}

function kanaNorm(s) {
  var out = "";
  for (var i = 0; i < s.length; i++) {
    var o = s.charCodeAt(i);
    if (o >= 0x3041 && o <= 0x3096) out += String.fromCharCode(o + 0x60);
    else out += s[i];
  }
  return out.toLowerCase();
}

function currentView() {
  return document.querySelector('#view-channel:not(.hidden), #view-brand:not(.hidden)');
}

function showView(name) {
  document.getElementById('view-channel').classList.toggle('hidden', name !== 'channel');
  document.getElementById('view-brand').classList.toggle('hidden', name !== 'brand');
  document.getElementById('tab-channel').classList.toggle('active', name === 'channel');
  document.getElementById('tab-brand').classList.toggle('active', name === 'brand');
  applySearch();
}

function pickSuggest(word) {
  document.getElementById('search').value = word;
  applySearch();
}

function renderSuggest(query) {
  var box = document.getElementById('suggest');
  box.innerHTML = "";
  var q = kanaNorm(query.trim());
  if (!q) return;
  var view = currentView();
  var key = (view && view.id === 'view-brand') ? 'brand' : 'channel';
  var terms = q.split(/\\s+/);
  var hits = SUGGEST[key].filter(function (item) {
    var cn = kanaNorm(item[1]);
    return terms.every(function (t) { return cn.indexOf(t) !== -1; });
  });
  hits.sort(function (a, b) {
    var an = kanaNorm(a[1]), bn = kanaNorm(b[1]);
    var as = an.indexOf(terms[0]) === 0 ? 0 : 1;
    var bs = bn.indexOf(terms[0]) === 0 ? 0 : 1;
    if (as !== bs) return as - bs;
    return a[0].length - b[0].length;
  });
  hits.slice(0, 6).forEach(function (item) {
    var btn = document.createElement('button');
    btn.textContent = item[0];
    btn.onclick = function () { pickSuggest(item[0]); };
    box.appendChild(btn);
  });
}

function applySearch() {
  var raw = document.getElementById('search').value;
  renderSuggest(raw);
  var q = kanaNorm(raw.trim());
  var terms = q ? q.split(/\\s+/) : [];
  var view = currentView();
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


def kana_norm(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0x3041 <= o <= 0x3096:
            out.append(chr(o + 0x60))
        else:
            out.append(ch)
    return "".join(out).lower()


def apply_overrides(data, overrides):
    """data.json の構造に overrides（手動補正）を適用する。
    - 識別: code + channel（channelは前後空白を無視した完全一致）
    - 同名コードが複数あるとき → ブランド確認中(null)を優先して上書き
    - brand / url は指定された方だけ上書き（常にoverridesが勝つ）
    - 上書きしたブランドのURLが brand_urls に無ければ登録（購入リンク表示のため）
    戻り値: (適用件数, 未マッチのoverridesリスト)
    """
    brand_urls = data.setdefault("brand_urls", {})
    applied = 0
    unmatched = []

    for ov in overrides:
        code = (ov.get("code") or "").strip()
        ch_name = (ov.get("channel") or "").strip()
        ov_brand = ov.get("brand")
        ov_url = ov.get("url")
        if not code or not ch_name:
            unmatched.append(ov)
            continue

        target_codes = []
        for ch in data.get("channels", []):
            if (ch.get("channel") or "").strip() == ch_name:
                target_codes = ch.get("codes", [])
                break

        matches = [c for c in target_codes if c.get("code") == code]
        if not matches:
            unmatched.append(ov)
            continue

        null_matches = [c for c in matches if c.get("brand") is None]
        targets = null_matches if null_matches else matches

        for c in targets:
            if ov_brand:
                c["brand"] = ov_brand
            if ov_url:
                c["dest"] = ov_url
            applied += 1

        if ov_brand and ov_url and not brand_urls.get(ov_brand):
            brand_urls[ov_brand] = ov_url

    return applied, unmatched


def load_overrides(path="overrides.json"):
    """overrides.json を読む。無ければ空リスト。壊れていても落とさず空扱い。"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        print(f"  ! overrides.json はリスト形式である必要があります。無視します。")
        return []
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! overrides.json の読み込みに失敗（{e}）。無視して続行します。")
        return []


def search_attr(code, name, extra_terms=None):
    """行に埋め込む検索対象。コード＋名前（チャンネル名orブランド名）＋追加語（ブランドの表記ゆれ）。"""
    parts = [code, name]
    if extra_terms:
        parts.extend(extra_terms)
    text = " ".join(x for x in parts if x)
    return html.escape(kana_norm(text), quote=True)


def render_code_row(c, badge_html, brand_urls, search_name, extra_terms=None):
    esc_code = html.escape(c["code"])
    buy = c.get("dest") or (brand_urls.get(c["brand"], "") if c["brand"] else "")
    links = ""
    if buy:
        links += f'<a class="link" href="{html.escape(buy)}" target="_blank" rel="noopener">購入ページに移動する</a>'
    links += f'<a class="link" href="{html.escape(c["video_url"])}" target="_blank" rel="noopener">動画先</a>'
    hay = search_attr(c["code"], search_name, extra_terms)
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
    """チャンネル別。左バッジ＝ブランド名。検索対象＝コード＋チャンネル名。"""
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
    """ブランド別。左バッジ＝チャンネル名。検索対象＝コード＋ブランド名＋表記ゆれ。投稿日の新しい順。"""
    brand_urls = data.get("brand_urls", {})
    brand_keys = data.get("brand_keys", {})
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
        extra = brand_keys.get(label, [])
        for r in rows:
            badge = f'<span class="badge channel">{html.escape(r["from_channel"])}</span>'
            parts.append(render_code_row(r, badge, brand_urls, label, extra))
        parts.append('</section>')
    parts.append('<div class="noresult hidden">該当するクーポンが見つかりませんでした。</div>')
    parts.append('</div>')
    return "".join(parts)


def collect_suggest_lists(data):
    """候補に出す語。チャンネル別タブ＝チャンネル名、ブランド別タブ＝ブランド表示名。
    各候補は [表示ラベル, マッチ用テキスト]。ブランドはマッチ用に表記ゆれ（カナ読み等）を含める。
    コードは候補に出さない（打って探すものではないため）。"""
    brand_keys = data.get("brand_keys", {})
    channels = list(dict.fromkeys(ch["channel"] for ch in data["channels"] if ch["codes"]))
    brands = []
    for ch in data["channels"]:
        for c in ch["codes"]:
            b = c["brand"] if c["brand"] else "ブランド確認中"
            if b not in brands:
                brands.append(b)
    channel_items = [[name, name] for name in channels]
    brand_items = [[b, " ".join([b] + brand_keys.get(b, []))] for b in brands]
    return channel_items, brand_items


def build_html(data):
    parts = [HTML_HEAD]
    parts.append(f'<div class="updated">最終更新: {data["updated_at"]}（毎朝6時に自動更新）</div>')
    parts.append(
        '<div class="searchbox">'
        '<input id="search" class="search" type="search" '
        'placeholder="コード・ブランド・YouTuber名で検索" oninput="applySearch()">'
        '<div id="suggest" class="suggest"></div>'
        '</div>'
    )
    parts.append(
        '<div class="tabs">'
        '<button id="tab-channel" class="tab active" onclick="showView(\'channel\')">チャンネル別</button>'
        '<button id="tab-brand" class="tab" onclick="showView(\'brand\')">ブランド別</button>'
        '</div>'
    )
    parts.append(build_channel_view(data))
    parts.append(build_brand_view(data))

    sug_channel, sug_brand = collect_suggest_lists(data)
    tail = HTML_TAIL.replace("__SUGGEST_CHANNEL__", json.dumps(sug_channel, ensure_ascii=False))
    tail = tail.replace("__SUGGEST_BRAND__", json.dumps(sug_brand, ensure_ascii=False))
    parts.append(tail)
    return "".join(parts)


def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    # 手動補正（overrides.json）を適用：自動抽出の結果を上書き
    overrides = load_overrides("overrides.json")
    if overrides:
        applied, unmatched = apply_overrides(data, overrides)
        print(f"overrides を適用しました（{applied}件）")
        for ov in unmatched:
            print(f"  ! 未マッチのoverride: code={ov.get('code')} / channel={ov.get('channel')}")

    page = build_html(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    n = sum(1 for ch in data["channels"] if ch["codes"])
    print(f"index.html を生成しました（表示チャンネル {n}）")


if __name__ == "__main__":
    main()
