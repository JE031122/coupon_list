import os
import re
import requests
import html
from datetime import datetime, timezone, timedelta

# ===== 設定：チャンネルはここで管理します =====
CHANNELS = [
    "@YAMASAWA",
    "@KanekinFitness",
    "@SAIYAMAN-OverWork",
    "@yoshinori-yamamoto",
    "@protein1214",
    "@naasuke",
    "@METVLO",
    "@MarinaTakewaki",
    "@edward_kato",
    "@yokokawa_naotaka",
    "@JOUEZATO",
    "@junpeitaguchi",
    "@ryoterashima",
    "@themuscletv29",
    "@mametama",
    "@takutofitness",
    "@musclearuaru",
    "@vmmtkk",
    "@d-sun",
    "@jintomo",
    "@ShoImakoga",
    "@hagaseven",
    "@shintaro0105",
    "@musclegrille",
    "@jessesfitvlog",
    "@Hacogym_channel",
    "@noga",
    "@bazooka_okada",
]
MAX_VIDEOS = 10
# ==========================================

# ===== ブランド辞書：新しいブランドはここに足します =====
# 形式: "表示名": {"keys": [表記ゆれ], "url": "購入先URL（空欄""ならリンク非表示）"}
BRANDS = {
    "マイプロテイン":     {"keys": ["マイプロテイン", "myprotein"], "url": "https://www.myprotein.jp/"},
    "VALX":              {"keys": ["valx", "バルクス"], "url": "https://valx.jp/"},
    "REYS":              {"keys": ["reys", "レイズ"], "url": ""},
    "FIXIT":             {"keys": ["fixit"], "url": "https://store.fix-it.jp/"},
    "LYFT":              {"keys": ["lyft", "リフト"], "url": "https://lyft-fit.com/"},
    "エクスプロージョン":  {"keys": ["エクスプロージョン", "x-plosion", "explosion"], "url": "https://store.x-plosion.jp/"},
    "ビーレジェンド":      {"keys": ["ビーレジェンド", "be legend", "belegend"], "url": "https://store.belegend.jp/"},
    "グロング":           {"keys": ["グロング", "grong"], "url": "https://shop.grong.jp/"},
    "ザバス":             {"keys": ["ザバス", "savas"], "url": "https://www.meiji.co.jp/sports/savas/"},
    "DNS":               {"keys": ["dns"], "url": "https://shop.dnszone.jp/shop/default.aspx"},
    "ハレオ":             {"keys": ["ハレオ", "haleo"], "url": "https://haleo.jp/"},
    "マッスルデリ":        {"keys": ["マッスルデリ", "muscle deli"], "url": "https://muscledeli.jp/"},
    "ネイチャーカン":      {"keys": ["naturecan", "ネイチャーカン"], "url": "https://www.naturecan.jp/"},
    "バイタス":           {"keys": ["バイタス", "vitas"], "url": "https://vitas.fitness/"},
    "ALL OUT":           {"keys": ["all out", "allout", "オールアウト"], "url": "https://allout-official.com/"},
    "ペコダックチキン":    {"keys": ["ペコダックチキン"], "url": "https://pekodak.com/"},
    "Over Work":         {"keys": ["over work", "overwork", "オーバーワーク"], "url": "https://overwork.official.ec/"},
    "SUPLINX":           {"keys": ["SUPLINX", "サプリンクス"], "url": "https://www.suplinx.com/shop/"},
    "キョクヨー":           {"keys": ["キョクヨー", "キョクヨーのさば"], "url": "https://store.kyokuyo.co.jp/collections/naasuke"},
    "AMBiQUE":    {"keys": ["AMBiQUE", "アンビーク"], "url": "https://www.alo-organic.com/shop/product_categories/ambique?p=solia_top_amb"},
    "DELIPICKS":    {"keys": ["DELIPICKS", "デリピックス"], "url": "https://sb.deli-picks.com/ab/Creator_ad24"},
    }
# ====================================================

# ブランド名・表記ゆれそのものはコードとして扱わない（誤検出防止）
BRAND_WORDS = ({b.lower() for b in BRANDS}
               | {k.lower() for info in BRANDS.values() for k in info["keys"]})

API_KEY = os.environ.get("YOUTUBE_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"
KEYWORDS = ["クーポン", "コード", "割引", "紹介", "オフ", "OFF", "code", "%off", "限定"]

CODE_AFTER = re.compile(
    r"(?:クーポン|割引|紹介)?\s*(?:コード|code)\s*(?:は|が|で|:|：|>|＞)?\s*"
    r"[「『\"']?([A-Za-z0-9][A-Za-z0-9_\-]{1,19})",
    re.IGNORECASE,
)
CODE_QUOTED = re.compile(r"[「『\"']([A-Za-z0-9][A-Za-z0-9_\-]{1,19})[」』\"']")
CODE_COUPON = re.compile(
    r"(?:クーポン|coupon)\s*(?:は|が|:|：|>|＞)?\s*"
    r"[「『\"']?([A-Za-z0-9][A-Za-z0-9_\-]{1,19})",
    re.IGNORECASE,
)
STANDALONE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_\-]{2,19})\s*$")
IGNORE = {"https", "http", "www", "youtube", "com", "amazon",
          "code", "coupon", "off", "get", "sale"}

# 概要欄からURLを拾うパターンと、購入先として採用しないドメイン（SNS等）
URL_PATTERN = re.compile(r"https?://[^\s)）（(」』「『>＞、。！？\"']+")
SKIP_URL_DOMAINS = ("youtube.com", "youtu.be", "instagram.com",
                    "twitter.com", "x.com", "tiktok.com", "lin.ee", "line.me")


def get_json(endpoint, params):
    params["key"] = API_KEY
    data = requests.get(f"{BASE}/{endpoint}", params=params).json()
    if "error" in data:
        print("APIエラー:", data["error"].get("message", data))
        return None
    return data


# 短縮リンク（amzn.to / bit.ly 等）を展開するための仕組み。
# 同じURLは1回だけアクセスするようキャッシュする。失敗したら元のURLをそのまま使う。
RESOLVE_CACHE = {}

def resolve_url(url):
    if not url:
        return ""
    if url in RESOLVE_CACHE:
        return RESOLVE_CACHE[url]
    final = url
    try:
        res = requests.get(url, allow_redirects=True, timeout=8, stream=True,
                           headers={"User-Agent": "Mozilla/5.0"})
        final = res.url
        res.close()
    except requests.RequestException:
        pass
    RESOLVE_CACHE[url] = final
    return final


def brands_in_text(text):
    text = text.lower()
    return [b for b, info in BRANDS.items()
            if any(k.lower() in text for k in info["keys"])]


def find_brand(lines, idx, window=2):
    """コード行から距離の近い順にブランドを探す（同じ行→1行→2行）。
    窓内に無ければ、概要欄全体でブランドが1つだけのときに採用する。"""
    for dist in range(window + 1):
        targets = [idx] if dist == 0 else [idx - dist, idx + dist]
        for i in targets:
            if 0 <= i < len(lines):
                hits = brands_in_text(lines[i])
                if hits:
                    return hits[0]
    whole = brands_in_text(" ".join(lines))
    return whole[0] if len(whole) == 1 else None


def find_dest_url(lines, idx):
    """コード行の近くから購入先URLを探す（同じ行→1行上→1行下→2行上→2行下の順）。
    SNS等のリンクは購入先とみなさずスキップする。"""
    order = [idx, idx - 1, idx + 1, idx - 2, idx + 2]
    for i in order:
        if 0 <= i < len(lines):
            m = URL_PATTERN.search(lines[i])
            if m:
                url = m.group(0).rstrip(".,")
                if not any(s in url for s in SKIP_URL_DOMAINS):
                    return url
    return ""


def has_keyword(line):
    return any(kw.lower() in line.lower() for kw in KEYWORDS)


def valid_code(token, line):
    """コードとして妥当か。ブランド名そのものは除外。
    数字だけのコードは『コード』という単語が同じ行にある場合のみ許可"""
    if token.lower() in IGNORE:
        return False
    if token.lower() in BRAND_WORDS:
        return False
    if re.search(r"[A-Za-z]", token):
        return True
    return ("コード" in line or "code" in line.lower()) and 3 <= len(token) <= 12


def codes_in_description(description):
    """概要欄から (コード, ブランド, 購入先URL) のリストを返す。
    同じコードが複数ブランドで使われている場合は、それぞれ別の1件として返す。"""
    lines = description.splitlines()
    found = {}  # キー: (コード, ブランド) -> 購入先URL
    for idx, line in enumerate(lines):
        cands = []
        if has_keyword(line):
            cands += CODE_AFTER.findall(line) + CODE_QUOTED.findall(line) + CODE_COUPON.findall(line)
        # クーポン行の隣に「コード単体の行」があるパターン（例: ALL OUTクーポン↵SAIYAMAN5）
        m = STANDALONE.match(line)
        if m:
            prev_kw = idx > 0 and has_keyword(lines[idx - 1])
            next_kw = idx + 1 < len(lines) and has_keyword(lines[idx + 1])
            if prev_kw or next_kw:
                cands.append(m.group(1))
        for c in cands:
            if valid_code(c, line):
                key = (c, find_brand(lines, idx))
                if key not in found or not found[key]:
                    found[key] = find_dest_url(lines, idx)
    # 同じコードにブランド判明済みの組があるなら、ブランド不明(None)の組は除外
    has_brand = {c for (c, b) in found if b}
    return [(c, b, d) for (c, b), d in found.items() if b or c not in has_brand]


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

    # (コード, ブランド) の組み合わせごとに、動画URLと購入先URLを集計する
    summary = {}
    for v in vids.get("items", []):
        for code, brand, dest in codes_in_description(v["snippet"]["description"]):
            key = (code, brand)
            entry = summary.setdefault(key, {"urls": [], "dest": ""})
            entry["urls"].append(f"https://www.youtube.com/watch?v={v['id']}")
            if not entry["dest"] and dest:
                entry["dest"] = dest

    # チャンネル全体でも、ブランド判明済みのコードのブランド不明行は除外
    has_brand = {code for (code, brand) in summary if brand}
    codes = [(code, brand, len(e["urls"]), e["urls"][0], e["dest"])
             for (code, brand), e in summary.items()
             if brand or code not in has_brand]
    codes.sort(key=lambda x: x[2], reverse=True)
    return title, codes


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


def build_html(all_results, updated_at):
    parts = [HTML_HEAD, f'<div class="updated">最終更新: {updated_at}（毎朝6時に自動更新）</div>']
    for title, codes in all_results:
        if not codes:
            continue
        parts.append(f'<section class="channel"><h2>{html.escape(title)}</h2>')
        for code, brand, count, url, dest in codes:
            esc_code = html.escape(code)
            if brand:
                brand_tag = f'<span class="brand">{html.escape(brand)}</span>'
            else:
                brand_tag = '<span class="brand unknown">ブランド確認中</span>'
            links = ""
            if dest:
                links += f'<a class="link" href="{html.escape(dest)}" target="_blank" rel="noopener">購入ページ</a>'
            else:
                buy_url = BRANDS.get(brand, {}).get("url", "") if brand else ""
                if buy_url:
                    links += f'<a class="link" href="{html.escape(buy_url)}" target="_blank" rel="noopener">公式サイトで使う</a>'
            links += f'<a class="link" href="{html.escape(url)}" target="_blank" rel="noopener">動画例</a>'
            parts.append(
                f'<div class="code-row">'
                f'{brand_tag}'
                f'<span class="code">{esc_code}</span>'
                f'<button class="copy" onclick="copyCode(this, \'{esc_code}\')">コピー</button>'
                f'<span class="count">{count}本の動画で言及</span>'
                f'<span class="links">{links}</span>'
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

    # 集まった購入先URLの短縮リンクを展開する（同じURLは1回だけアクセス）
    resolved_results = []
    for title, codes in all_results:
        new_codes = [(code, brand, count, vurl, resolve_url(dest))
                     for code, brand, count, vurl, dest in codes]
        resolved_results.append((title, new_codes))
    print(f"購入先URLの展開: {len(RESOLVE_CACHE)}件を処理")

    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    page = build_html(resolved_results, updated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"index.html を生成しました（{len(resolved_results)}チャンネル）")


if __name__ == "__main__":
    main()
