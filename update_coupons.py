import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote

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
    "@samgetitright",
]
# 長尺・ショートそれぞれの最新何本を調べるか（合計で最大この2倍を確認）
MAX_VIDEOS = 10
# ==========================================

# ===== ブランド辞書：新しいブランドはここに足します =====
# 形式: "表示名": {"keys": [表記ゆれ], "url": "購入先URL（空欄""ならリンク非表示）"}
BRANDS = {
    "マイプロテイン":     {"keys": ["マイプロテイン", "マイプロ", "myprotein"], "url": "https://www.myprotein.jp/"},
    "VALX":              {"keys": ["valx", "バルクス"], "url": "https://valx.jp/"},
    "REYS":              {"keys": ["reys", "レイズ"], "url": "https://reizupurotein.com/"},
    "FIXIT":             {"keys": ["fixit", "フィックスイット"], "url": "https://store.fix-it.jp/"},
    "LYFT":              {"keys": ["lyft", "リフト"], "url": "https://lyft-fit.com/"},
    "エクスプロージョン":  {"keys": ["エクスプロージョン", "x-plosion", "explosion"], "url": "https://store.x-plosion.jp/"},
    "ビーレジェンド":      {"keys": ["ビーレジェンド", "be legend", "belegend"], "url": "https://store.belegend.jp/"},
    "グロング":           {"keys": ["グロング", "grong"], "url": "https://shop.grong.jp/"},
    "ザバス":             {"keys": ["ザバス", "savas"], "url": "https://www.meiji.co.jp/sports/savas/"},
    "DNS":               {"keys": ["dns", "ディーエヌエス"], "url": "https://shop.dnszone.jp/shop/default.aspx"},
    "ハレオ":             {"keys": ["ハレオ", "haleo"], "url": "https://haleo.jp/"},
    "マッスルデリ":        {"keys": ["マッスルデリ", "muscle deli"], "url": "https://muscledeli.jp/"},
    "ネイチャーカン":      {"keys": ["naturecan", "ネイチャーカン"], "url": "https://www.naturecan.jp/"},
    "バイタス":           {"keys": ["バイタス", "vitas"], "url": "https://vitas.fitness/"},
    "ALL OUT":           {"keys": ["all out", "allout", "オールアウト"], "url": "https://allout-official.com/"},
    "ペコダックチキン":    {"keys": ["ペコダックチキン", "pekodak"], "url": "https://pekodak.com/"},
    "Over Work":         {"keys": ["over work", "overwork", "オーバーワーク"], "url": "https://overwork.official.ec/"},
    "SUPLINX":           {"keys": ["SUPLINX", "サプリンクス"], "url": "https://www.suplinx.com/shop/"},
    "キョクヨー":           {"keys": ["キョクヨー", "キョクヨーのさば"], "url": "https://store.kyokuyo.co.jp/"},
    "AMBiQUE":           {"keys": ["AMBiQUE", "アンビーク"], "url": "https://www.alo-organic.com/shop/product_categories/ambique"},
    "DELIPICKS":         {"keys": ["DELIPICKS", "デリピックス"], "url": "https://sb.deli-picks.com/ab/Creator_ad24"},
    "男DAYS":            {"keys": ["男DAYS", "ダンディーズ", "オトコデイズ"], "url": "https://dan-days.jp/shop"},
    "ハルクファクター":    {"keys": ["ハルクファクター", "hulx-factor", "hulkfactor"], "url": "https://hulx-factor.jp/"},
    "FITPEAK":           {"keys": ["fitpeak", "フィットピーク"], "url": "https://fitpeak.co/"},
    "iHerb":             {"keys": ["iherb", "アイハーブ"], "url": "https://jp.iherb.com/"},
    "SAIJIRUSHI":        {"keys": ["saijirushi", "サイジルシ"], "url": "https://saijirushi.co.jp/"},
    "マクロファクター":    {"keys": ["macrofactor", "マクロファクター"], "url": "https://macrofactor.com/jp/"},
    "MBC POWER":         {"keys": ["MBCパワー", "mbcパワー", "MBC POWER", "mbc power"], "url": "https://www.mbcpower.jp/"},
    "Vanquish Fitness":  {"keys": ["Vanquish Fitness", "ヴァンキッシュフィットネス", "バンキッシュフィットネス"], "url": "https://www.vqfit.com/"},
}
# ====================================================

# ブランド名・表記ゆれそのものはコードとして扱わない（誤検出防止）
BRAND_WORDS = ({b.lower() for b in BRANDS}
               | {k.lower() for info in BRANDS.values() for k in info["keys"]})

API_KEY = os.environ.get("YOUTUBE_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"
KEYWORDS = ["クーポン", "コード", "割引", "紹介", "オフ", "OFF", "code", "%off", "限定"]

CODE_AFTER = re.compile(
    r"(?:クーポン|割引|紹介)?\s*(?:コード|code)\s*(?:は|が|で|:|：|>|＞|】|」|』|\])?\s*"
    r"[「『\"']?([A-Za-z0-9][A-Za-z0-9_\-]{1,19})",
    re.IGNORECASE,
)
CODE_QUOTED = re.compile(r"[「『【\"']([A-Za-z0-9][A-Za-z0-9_\-]{1,19})[」』】\"']")
CODE_COUPON = re.compile(
    r"(?:クーポン|coupon)\s*(?:は|が|:|：|>|＞|】|」|』|\])?\s*"
    r"[「『\"']?([A-Za-z0-9][A-Za-z0-9_\-]{1,19})",
    re.IGNORECASE,
)
STANDALONE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_\-]{2,19})\s*$")
IGNORE = {"https", "http", "www", "youtube", "com", "amazon",
          "code", "coupon", "off", "get", "sale"}

URL_PATTERN = re.compile(r"https?://[^\s)）（(」』「『>＞、。！？\"']+")
SKIP_URL_DOMAINS = ("youtube.com", "youtu.be", "instagram.com",
                    "twitter.com", "x.com", "tiktok.com", "lin.ee", "line.me")


def get_json(endpoint, params, quiet=False):
    params["key"] = API_KEY
    data = requests.get(f"{BASE}/{endpoint}", params=params).json()
    if "error" in data:
        if not quiet:
            print("APIエラー:", data["error"].get("message", data))
        return None
    return data


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


def to_date(published_at):
    """ISO8601(例: 2026-06-10T09:00:00Z) を日本時間の YYYY-MM-DD に変換"""
    if not published_at:
        return ""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def brands_in_text(text):
    text = text.lower()
    return [b for b, info in BRANDS.items()
            if any(k.lower() in text for k in info["keys"])]


def find_brand(lines, idx, window=2):
    """①前後2行を近い順 → ②同じ段落（空行区切り）内を近い順。見つからなければ None。"""
    for dist in range(window + 1):
        targets = [idx] if dist == 0 else [idx - dist, idx + dist]
        for i in targets:
            if 0 <= i < len(lines):
                hits = brands_in_text(lines[i])
                if hits:
                    return hits[0]
    top = idx
    while top > 0 and lines[top - 1].strip():
        top -= 1
    bottom = idx
    while bottom + 1 < len(lines) and lines[bottom + 1].strip():
        bottom += 1
    max_dist = max(idx - top, bottom - idx)
    for dist in range(window + 1, max_dist + 1):
        for i in (idx - dist, idx + dist):
            if top <= i <= bottom:
                hits = brands_in_text(lines[i])
                if hits:
                    return hits[0]
    return None


def find_dest_url(lines, idx):
    """コード行の近くから購入先URLを探す（同じ行→1行上→1行下→2行上→2行下の順）。"""
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
    if token.lower() in IGNORE:
        return False
    if token.lower() in BRAND_WORDS:
        return False
    if re.search(r"[A-Za-z]", token):
        return True
    return ("コード" in line or "code" in line.lower()) and 3 <= len(token) <= 12


def codes_in_description(description):
    """概要欄から (コード, ブランド, 購入先URL) のリストを返す。"""
    lines = description.splitlines()
    found = {}
    for idx, line in enumerate(lines):
        cands = []
        if has_keyword(line):
            cands += CODE_AFTER.findall(line) + CODE_QUOTED.findall(line) + CODE_COUPON.findall(line)
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
    has_brand = {c for (c, b) in found if b}
    return [(c, b, d) for (c, b), d in found.items() if b or c not in has_brand]


def get_channel_data(handle):
    """1チャンネル分のデータを辞書で返す。失敗時は None。"""
    ch = get_json("channels", {"part": "contentDetails,snippet", "forHandle": handle})
    if ch is None or not ch.get("items"):
        print(f"  ! チャンネルが見つかりませんでした: {handle}")
        return None
    info = ch["items"][0]
    uploads = info["contentDetails"]["relatedPlaylists"]["uploads"]
    title = info["snippet"]["title"]

    ids = []
    if uploads.startswith("UU"):
        for prefix in ("UULF", "UUSH"):
            pid = prefix + uploads[2:]
            sub = get_json("playlistItems",
                           {"part": "contentDetails", "playlistId": pid,
                            "maxResults": MAX_VIDEOS}, quiet=True)
            if sub:
                ids += [i["contentDetails"]["videoId"] for i in sub.get("items", [])]
    if not ids:
        pl = get_json("playlistItems",
                      {"part": "contentDetails", "playlistId": uploads,
                       "maxResults": MAX_VIDEOS})
        if pl is None:
            return None
        ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {"channel": title, "subscribers": None, "codes": []}

    vids = get_json("videos", {"part": "snippet", "id": ",".join(ids)})
    if vids is None:
        return None

    # (コード, ブランド) ごとに、動画URL・購入先・投稿日を集計
    summary = {}
    for v in vids.get("items", []):
        vid = v["id"]
        date = to_date(v["snippet"].get("publishedAt", ""))
        for code, brand, dest in codes_in_description(v["snippet"]["description"]):
            key = (code, brand)
            entry = summary.setdefault(key, {"urls": [], "dest": "", "date": ""})
            entry["urls"].append(f"https://www.youtube.com/watch?v={vid}")
            if not entry["dest"] and dest:
                entry["dest"] = dest
            if date > entry["date"]:        # 一番新しい投稿日を採用
                entry["date"] = date

    has_brand = {code for (code, brand) in summary if brand}
    codes = []
    for (code, brand), e in summary.items():
        if not (brand or code not in has_brand):
            continue
        codes.append({
            "code": code,
            "brand": brand,
            "count": len(e["urls"]),
            "video_url": e["urls"][0],
            "dest": e["dest"],
            "latest_date": e["date"],
        })
    codes.sort(key=lambda c: c["count"], reverse=True)
    return {"channel": title, "subscribers": None, "codes": codes}


def main():
    if not API_KEY:
        print("YOUTUBE_API_KEY が見つかりません。Secretの設定を確認してください。")
        raise SystemExit(1)

    targets = [h for h in CHANNELS if "ここに" not in h]
    if not targets:
        print("CHANNELS にチャンネルのハンドルを入れてください。")
        raise SystemExit(1)

    channels_data = []
    for handle in targets:
        result = get_channel_data(handle)
        if result is not None:
            channels_data.append(result)

    # 購入先URLの短縮リンクを展開し、URLからブランド不明分を補完
    refined = 0
    for ch in channels_data:
        for c in ch["codes"]:
            c["dest"] = resolve_url(c["dest"])
            if c["brand"] is None and c["dest"]:
                hits = brands_in_text(unquote(c["dest"]))
                if hits:
                    c["brand"] = hits[0]
                    refined += 1
    print(f"購入先URLの展開: {len(RESOLVE_CACHE)}件 / URLからのブランド補完: {refined}件")

    jst = timezone(timedelta(hours=9))
    data = {
        "updated_at": datetime.now(jst).strftime("%Y-%m-%d %H:%M"),
        "brand_urls": {b: info["url"] for b, info in BRANDS.items()},
        "channels": channels_data,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(c["codes"]) for c in channels_data)
    print(f"data.json を生成しました（{len(channels_data)}チャンネル / 合計{total}コード）")


if __name__ == "__main__":
    main()
