import os
import re
import requests
import html
from datetime import datetime, timezone, timedelta

# ===== 設定:チャンネルはここで管理します =====
CHANNELS = [
    "@ここに1つ目のハンドル",
    "@ここに2つ目のハンドル",
    "@ここに3つ目のハンドル",
]
MAX_VIDEOS = 15
# ==========================================

# ===== ブランド辞書:新しいブランドはここに足します =====
# 形式: "表示名": [概要欄に出てきそうな表記のリスト]
BRANDS = {
    "マイプロテイン":     ["マイプロテイン", "myprotein"],
    "VALX":              ["valx", "バルクス"],
    "REYS":              ["reys", "レイズ"],
    "FIXIT":             ["fixit"],
    "LYFT":              ["lyft", "リフト"],
    "エクスプロージョン":  ["エクスプロージョン", "x-plosion", "explosion"],
    "ビーレジェンド":      ["ビーレジェンド", "be legend", "belegend"],
    "グロング":           ["グロング", "grong"],
    "ザバス":             ["ザバス", "savas"],
    "DNS":               ["dns"],
    "ハレオ":             ["ハレオ", "haleo"],
    "マッスルデリ":        ["マッスルデリ", "muscle deli"],
    "ナチュラカン":        ["naturecan", "ナチュラカン"],
}
# ====================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"
KEYWORDS = ["クーポン", "コード", "割引", "紹介", "オフ", "OFF", "code", "%off", "限定"]

CODE_AFTER = re.compile(
    r"(?:クーポン|割引|紹介)?\s*(?:コード|code)\s*(?:は|が|で|:|：|>|＞)?\s*"
    r"[「『\"']?([A-Za-z0-9][A-Za-z0-9_\-]{1,19})",
    re.IGNORECASE,
)
CODE_QUOTED = re.compile(r"[「『\"']([A-Za-z0-9][A-Za-z0-9_\-]{1,19})[」』\"']")
IGNORE = {"https", "http", "www", "youtube", "com", "amazon"}


def get_json(endpoint, params):
    params["key"] = API_KEY
    data = requests.get(f"{BASE}/{endpoint}", params=params).json()
    if "error" in data:
        print("APIエラー:", data["error"].get("message", data))
        return None
    return data


def brands_in_text(text):
    text = text.lower()
    return [b for b, keys in BRANDS.items() if any(k.lower() in text for k in keys)]


def find_brand(lines, idx, window=2):
    """コードが見つかった行の前後からブランドを推定する(2段構え)"""
    start, end = max(0, idx - window), min(len(lines), idx + window + 1)
    near = brands_in_text(" ".join(lines[start:end]))
    if near:
        return near[0]
    whole = brands_in_text(" ".join(lines))
    if len(whole) == 1:
        return whole[0]
    return None


def codes_in_description(description):
    """概要欄から (コード, ブランド) のリストを返す(コードの重複なし)"""
    lines = description.splitlines()
    found = {}
    for idx, line in enumerate(lines):
        if not any(kw.lower() in line.lower() for kw in KEYWORDS):
            continue
        codes = CODE_AFTER.findall(line) + CODE_QUOTED.findall(line)
        codes = [c for c in codes
                 if c.lower() not in IGNORE and re.search(r"[A-Za-z]", c)]
        for c in codes:
            if c not in found:
                found[c] = find_brand(lines, idx)
            elif found[c] is None:
                found[c] = find_brand(lines, idx)
    return list(found.items())


def get_channel_codes(handle):
    ch = get_json("channels", {"part": "contentDetails,snippet", "forHandle": handle})
    if ch is None or not ch.get("items"):
        print(f"  ! チャンネルが見つかりませんでした: {handle}")
        return None
    info = ch["items"][0]
    uploads = info["contentDetails"]["relatedPlaylists"]["uploads"]
    title = info["snippet"]["title"]

    pl = get_json("playlistItems",
                  {"part": "contentDetails", "playlistId": uploads, "maxResults": MAX_VIDEOS})
    if pl is None:
        return None
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not ids:
        return title, []

    vids = get_json("videos", {"part": "snippet", "id": ",".join(ids)})
    if vids is None:
        return None

    summary = {}
    for v in vids.get("items", []):
        for code, brand in codes_in_description(v["snippet"]["description"]):
            entry = summary.setdefault(code, {"brand": None, "urls": []})
            entry["urls"].append(f"https://www.youtube.com/watch?v={v['id']}")
            if entry["brand"] is None and brand:
                entry["brand"] = brand

    codes = [(code, e["brand"], len(e["urls"]), e["urls"][0])
             for code, e in summary.items()]
    codes.sort(key=lambda x: x[2], reverse=True)
    return title, codes


HTML_HEAD = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>クーポンコード一覧(プロテイン・サプリ系)</title>
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
  .link { color:#2563eb; font-size:13px; text-decoration:none; margin-left:auto; }
</style>
</head>
<body>
<div class="wrap">
<h1>クーポンコード一覧(プロテイン・サプリ系)</h1>
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


def build_html(all_results, updated_at):
    parts = [HTML_HEAD, f'<div class="updated">最終更新: {updated_at}(毎朝6時に自動更新)</div>']
    for title, codes in all_results:
        if not codes:
            continue
        parts.append(f'<section class="channel"><h2>{html.escape(title)}</h2>')
        for code, brand, count, url in codes:
            esc_code = html.escape(code)
            if brand:
                brand_tag = f'<span class="brand">{html.escape(brand)}</span>'
            else:
                brand_tag = '<span class="brand unknown">ブランド確認中</span>'
            parts.append(
                f'<div class="code-row">'
                f'{brand_tag}'
                f'<span class="code">{esc_code}</span>'
                f'<button class="copy" onclick="copyCode(this, \'{esc_code}\')">コピー</button>'
                f'<span class="count">{count}本の動画で言及</span>'
                f'<a class="link" href="{html.escape(url)}" target="_blank">動画例</a>'
                f'</div>'
            )
        parts.append('</section>')
    parts.append(HTML_TAIL)
    return "".join(parts)


def main():
    if not API_KEY:
        print("YOUTUBE_API_KEY が見つかりません。Secretの設定を確認してください。")
        raise SystemExit(1)

    targets = [h for h in CHANNELS if "ここに" not in h]
    if not targets:
        print("CHANNELS にチャンネルのハンドルを入れてください。")
        raise SystemExit(1)

    all_results = []
    for handle in targets:
        result = get_channel_codes(handle)
        if result is not None:
            all_results.append(result)

    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    page = build_html(all_results, updated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"index.html を生成しました({len(all_results)}チャンネル)")


if __name__ == "__main__":
    main()
