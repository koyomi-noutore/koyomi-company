"""再生リスト（2026-11-20 CEO決定）。IDは scripts/playlists.json に記録する。認証は youtube_upload.access_token()。

  python3 scripts/youtube_playlists.py create     … 再生リストを公開で作る（あるものは作らない）
  python3 scripts/youtube_playlists.py backfill   … これまでの動画（outputs/*/upload.json）を、新しい回が上になるよう入れる
  python3 scripts/youtube_playlists.py category   … チャンネルの全動画のカテゴリを「教育」(27) にそろえる（違うものだけ変える）
アップロード時は youtube_upload.upload() が add_for_upload() を呼び、該当するリストの一番上に自動で入れる。
"""
import json, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parent.parent
IDS = Path(__file__).parent / "playlists.json"
API = "https://www.googleapis.com/youtube/v3/"
EDUCATION = "27"

PLAYLISTS = {
    "long": ("間違い探し｜毎日の脳トレ",
             "シニアの方のための間違い探しを、新しい順にまとめました。季節のイラストで、ひとりで毎日楽しく脳トレ・頭の体操ができます。\n"
             "60代・70代の方の毎日の習慣に、介護施設のレクリエーションにもどうぞ。"),
    "short": ("1分間違い探し｜毎日1分脳トレ",
              "1分で解ける、シニアの方のための間違い探し（ショート）をまとめました。違いは3つ、見つけられますか？\n"
              "すきま時間の脳トレ・頭の体操に。続きは長い動画の間違い探しでどうぞ。"),
    "autumn": ("秋の間違い探し",
               "秋のイラスト（柿・栗・紅葉・きのこなど）で遊ぶ、シニアの方のための間違い探しです。\n"
               "季節を感じながら、毎日の脳トレ・頭の体操にどうぞ。"),
    "text": ("文字の脳トレ｜毎日1分",
             "都道府県の穴埋め、ひらがなの十字、漢字の間違い探しなど、文字で遊ぶシニアの方のための脳トレ（ショート）をまとめました。\n"
             "1分でできる頭の体操に。高齢者のレクリエーションやデイサービスでも、みんなで楽しめます。"),
    "mushi": ("虫めがねクイズ｜この○○なーんだ？",
              "黒くおおった絵を虫めがねでのぞいて、何の絵かを当てるクイズ（ショート）をまとめました。野菜・動物・食べ物など、シニアの方の脳トレ・頭の体操に。\n"
              "高齢者のレクリエーションやデイサービスでも、みんなで楽しめます。"),
    "winter": ("冬の間違い探し",
               "冬のイラスト（雪・こたつ・お正月など）で遊ぶ、シニアの方のための間違い探しです。\n"
               "季節を感じながら、毎日の脳トレ・頭の体操にどうぞ。"),
}
SEASON = {9: "autumn", 10: "autumn", 11: "autumn", 12: "winter", 1: "winter", 2: "winter"}   # plan.json に season が無いときだけ、フォルダ名の月で決める


def _req(method, path, tok, body=None):
    r = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(), method=method,
                               headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8"})
    with urllib.request.urlopen(r, timeout=60) as res:
        return json.load(res)


def ids():
    return json.loads(IDS.read_text(encoding="utf-8")) if IDS.exists() else {}


def create(tok):
    have = ids()
    for key, (title, desc) in PLAYLISTS.items():
        if key in have:
            continue
        r = _req("POST", "playlists?part=snippet,status", tok,
                 {"snippet": {"title": title, "description": desc, "defaultLanguage": "ja"}, "status": {"privacyStatus": "public"}})
        have[key] = {"id": r["id"], "title": title, "url": f"https://www.youtube.com/playlist?list={r['id']}"}
        IDS.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
        print("作成", key, r["id"], title)
    return have


def items(pid, tok):
    out, page = [], ""
    while True:
        r = _req("GET", f"playlistItems?part=contentDetails&maxResults=50&playlistId={pid}" + (f"&pageToken={page}" if page else ""), tok)
        out += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            return out


def add(pid, vid, tok, top=True):
    """入っていなければ入れる。top=True は一番上（新しい順）。"""
    if vid in items(pid, tok):
        return False
    sn = {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}
    if top:
        sn["position"] = 0
    _req("POST", "playlistItems?part=snippet", tok, {"snippet": sn})
    return True


def targets(folder, short):
    """その動画が入る再生リストの key。folder は outputs/<日付_回>/ または その下の short*/。間違い探しの回だけ。"""
    ep = Path(folder).resolve()
    if ep.name.startswith("short"):
        ep = ep.parent
    if re.match(r"\d{4}-\d{2}-\d{2}_mushi_\d+$", ep.name):   # 虫めがねクイズのショート（2026-11-25 CEO：専用の再生リスト）
        return ["mushi"]
    if re.match(r"\d{4}-\d{2}-\d{2}_(text|tlong)_\d+$", ep.name):   # 文字の脳トレのショート・長尺（2026-11-25 CEO：長尺も同じ再生リスト）
        return ["text"]
    if re.match(r"\d{4}-\d{2}-\d{2}_w10_\d+$", ep.name):   # 2回分をつないだ全10問の長尺（2026-11-26 CEO：長尺と季節の再生リスト。季節は plan.json の season）
        keys = ["short"] if short else ["long"]
        pj = ep / "plan.json"
        s_ = json.loads(pj.read_text(encoding="utf-8")).get("season") if pj.exists() else None
        if s_ in ("秋", "冬") and not short:
            keys.append({"秋": "autumn", "冬": "winter"}[s_])
        return keys
    m = re.match(r"(\d{4})-(\d{2})-\d{2}_\d+$", ep.name)
    if not m:
        return []
    keys = ["short"] if short else ["long"]
    season = SEASON.get(int(m.group(2)))
    pj = ep / "plan.json"      # 季節は題材で決める（2026-11-22 CEO：作った月ではなく題材の季節）。plan.json の season があればそれを使う
    if pj.exists():
        s_ = json.loads(pj.read_text(encoding="utf-8")).get("season")
        season = {"秋": "autumn", "冬": "winter"}.get(s_, season)
    if season and not short:
        keys.append(season)
    return keys


def add_for_upload(folder, vid, short, tok):
    pl = ids()
    done = []
    for k in targets(folder, short):
        if k in pl and add(pl[k]["id"], vid, tok):
            done.append(pl[k]["title"])
    return done


def backfill(tok):
    pl = ids()
    ups = []
    for f in sorted(ROOT.glob("outputs/*/upload.json")) + sorted(ROOT.glob("outputs/*/short*/upload.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ups.append((f.parent, d["video_id"], bool(d.get("short"))))
    # 古い回から順に一番上へ入れる → 新しい回が上になる（同じ回のショートは short → short2 の順）
    ups.sort(key=lambda u: (u[0].parent.name if u[0].name.startswith("short") else u[0].name, u[0].name))
    count = {k: 0 for k in pl}
    for folder, vid, short in ups:
        for k in targets(folder, short):
            if add(pl[k]["id"], vid, tok):
                count[k] += 1
    for k, v in pl.items():
        print(v["title"], "追加", count.get(k, 0), "本／合計", len(items(v["id"], tok)), "本", v["url"])


def category(tok):
    up = _req("GET", "channels?part=contentDetails&mine=true", tok)["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    vids = items(up, tok)
    changed = []
    for k in range(0, len(vids), 50):
        for v in _req("GET", "videos?part=snippet&id=" + ",".join(vids[k:k + 50]), tok)["items"]:
            sn = v["snippet"]
            if sn["categoryId"] == EDUCATION:
                continue
            body = {"id": v["id"], "snippet": {x: sn[x] for x in ("title", "description", "tags", "defaultLanguage", "defaultAudioLanguage") if x in sn}}
            body["snippet"]["categoryId"] = EDUCATION      # タイトル・説明欄・タグはそのまま送る
            _req("PUT", "videos?part=snippet", tok, body)
            changed.append(v["id"])
    print(f"全{len(vids)}本のうち、カテゴリを教育に変えたもの：{changed or 'なし（すべて教育）'}")


if __name__ == "__main__":
    import youtube_upload as U
    t = U.access_token()
    {"create": create, "backfill": backfill, "category": category}[sys.argv[1]](t)
