"""マーケティング部の毎日の数字（YouTube Analytics API ＋ Data API ＋ StudioのCSV）。

使い方:
  python3 scripts/analytics_daily.py            # 今日（日本時間）の日付で記録
  python3 scripts/analytics_daily.py 2026-11-14 # 日付を指定

出力:
  departments/analytics/daily/YYYY-MM-DD.md          要約（AIはこれだけ読む）
  departments/analytics/daily/csv/YYYY-MM-DD_videos.csv       動画別の累計
  departments/analytics/daily/csv/YYYY-MM-DD_video_daily.csv  動画別・日別
  departments/analytics/daily/csv/YYYY-MM-DD_traffic.csv      動画別・日別・流入元

- Analytics API の「日」は米国太平洋時間。48時間・7日・28日の区切りも太平洋時間の公開日から数える（表の「公開」は日本時間）。
- 長尺とショートは長さで分ける（180秒以下＝ショート）。
- 収益化の4,000時間に数えるのは長尺だけ（直近365日の長尺の総再生時間）。
- 表示回数・クリック率はAPIに無いので、departments/analytics/studio/ の最新のCEO書き出しCSVから読む。
- Analytics API が使えないときは、Data API の累計再生数とStudioのCSVだけで要約を作り、冒頭に止まっている理由を書く（終了コード2）。
- トークンの値は画面にもファイルにも出さない。
"""
import csv, json, re, sys, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from youtube_auth import access_token

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "departments" / "analytics" / "daily"
STUDIO = ROOT / "departments" / "analytics" / "studio"
DATA = "https://www.googleapis.com/youtube/v3/"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
SHORT_MAX_SEC = 180
GOAL_HOURS, GOAL_DATE = 4000, date(2027, 1, 31)
METRICS = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
           "subscribersGained", "subscribersLost"]
SOURCE_JA = {"SHORTS": "ショートフィード", "RELATED_VIDEO": "関連動画", "SUBSCRIBER": "登録者（ホーム等）",
             "YT_SEARCH": "YouTube検索", "BROWSE": "ブラウジング（ホーム）", "EXT_URL": "外部サイト",
             "NO_LINK_OTHER": "直接・不明", "PLAYLIST": "再生リスト", "YT_CHANNEL": "チャンネルページ",
             "YT_OTHER_PAGE": "その他のYouTube", "NOTIFICATION": "通知", "END_SCREEN": "終了画面",
             "ANNOTATION": "カード等", "HASHTAGS": "ハッシュタグ", "SOUND_PAGE": "サウンド", "SHORTS_CONTENT_LINKS": "ショートからのリンク（ショート→長尺）", "CAMPAIGN_CARD": "キャンペーン"}


class ApiError(Exception):
    def __init__(self, code, reason, message):
        super().__init__(f"{code} {reason}: {message}")
        self.code, self.reason, self.message = code, reason, message


def get(token, url, **q):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(q), headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read() or b"{}").get("error", {})
        except ValueError:
            err = {}
        reason = (err.get("errors") or [{}])[0].get("reason", "")
        raise ApiError(e.code, reason, err.get("message", "")[:200]) from None


# ---------- Data API：動画の一覧 ----------
def iso_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def short_name(title):
    m = re.search(r"（([^）]+?)(?:・[^）]*)?）", title)
    if "#Shorts" in title and m:
        return m.group(1)
    parts = [p for p in title.split("｜") if p]
    name = parts[1] if len(parts) > 1 else title
    return re.sub(r"のイラスト.*", "", name).strip()[:20]


def list_videos(token):
    ch = get(token, DATA + "channels", part="contentDetails,statistics", mine="true")["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        q = dict(part="contentDetails", playlistId=uploads, maxResults=50)
        if page:
            q["pageToken"] = page
        r = get(token, DATA + "playlistItems", **q)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        page = r.get("nextPageToken")
        if not page:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = get(token, DATA + "videos", part="snippet,contentDetails,statistics,status", id=",".join(ids[i:i + 50]))
        for v in r.get("items", []):
            sec = iso_seconds(v["contentDetails"]["duration"])
            pub = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Tokyo"))
            videos.append({"id": v["id"], "title": v["snippet"]["title"], "name": short_name(v["snippet"]["title"]),
                           "type": "ショート" if sec <= SHORT_MAX_SEC else "長尺", "seconds": sec,
                           "published": pub.date(), "published_pt": pub.astimezone(ZoneInfo("America/Los_Angeles")).date(),
                           "privacy": v["status"]["privacyStatus"],
                           "data_views": int(v["statistics"].get("viewCount", 0))})
    return ch["statistics"], sorted(videos, key=lambda v: (v["type"], v["published"]))


# ---------- Analytics API ----------
def analytics(token, start, end, dims, metrics, video):
    r = get(token, ANALYTICS, ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
            dimensions=dims, metrics=",".join(metrics), filters="video==" + video, sort="day")
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in r.get("rows", [])]


def collect(token, videos, end):
    start = end - timedelta(days=364)  # 4,000時間の判定期間（直近12か月）
    daily, traffic = [], []
    for v in videos:
        for row in analytics(token, max(start, v["published_pt"]), end, "day", METRICS, v["id"]):
            daily.append({"video": v["id"], "type": v["type"], **row})
        for row in analytics(token, max(start, v["published_pt"]), end, "day,insightTrafficSourceType",
                             ["views", "estimatedMinutesWatched"], v["id"]):
            traffic.append({"video": v["id"], "type": v["type"], **row})
    return daily, traffic


# ---------- StudioのCSV（表示回数・クリック率） ----------
def studio_latest():
    for d in sorted((p for p in STUDIO.iterdir() if p.is_dir()), reverse=True):
        for name in ("table.csv", "content.csv", "表データ.csv"):
            f = d / name
            if f.exists():
                out = {}
                with f.open(encoding="utf-8-sig") as fh:
                    for row in csv.DictReader(fh):
                        vid = row.get("コンテンツ", "")
                        if vid and vid != "合計":
                            out[vid] = {"imp": row.get("サムネイルのインプレッション", ""),
                                        "ctr": row.get("サムネイルのクリック率 (%)", "")}
                return f.relative_to(ROOT), out
    return None, {}


# ---------- 集計 ----------
def summarize(rows):
    views = sum(r["views"] for r in rows)
    minutes = sum(r["estimatedMinutesWatched"] for r in rows)
    wsum = lambda k: sum(r[k] * r["views"] for r in rows)
    return {"views": views, "hours": minutes / 60,
            "avd": wsum("averageViewDuration") / views if views else 0,
            "avp": wsum("averageViewPercentage") / views if views else 0,
            "subs": sum(r["subscribersGained"] - r["subscribersLost"] for r in rows)}


def checkpoint(rows, published, days):
    """公開日を1日目として days 日分の再生数（48時間≒2日、7日、28日）。期間に満たなければ None。"""
    last = published + timedelta(days=days - 1)
    if not rows or max(date.fromisoformat(r["day"]) for r in rows) < last:
        return None
    return sum(r["views"] for r in rows if date.fromisoformat(r["day"]) <= last)


def mmss(sec):
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def fmt(n, d=0):
    return "—" if n is None else f"{n:,.{d}f}"


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(ZoneInfo("Asia/Tokyo")).date()
    token = access_token()
    ch_stats, all_videos = list_videos(token)
    videos = [v for v in all_videos if v["privacy"] == "public"]
    hidden = len(all_videos) - len(videos)
    studio_file, studio = studio_latest()

    blocked = None
    daily, traffic = [], []
    try:
        daily, traffic = collect(token, videos, today)
    except ApiError as e:
        blocked = e

    by_video = defaultdict(list)
    for r in daily:
        by_video[r["video"]].append(r)
    last_day = max((r["day"] for r in daily if r["views"]), default=None)

    rows = []
    for v in videos:
        rs = by_video[v["id"]]
        s = summarize(rs) if rs else None
        st = studio.get(v["id"], {})
        rows.append({"video": v["id"], "type": v["type"], "name": v["name"], "published": v["published"].isoformat(),
                     "age_days": (today - v["published"]).days + 1, "seconds": v["seconds"],
                     "views": s["views"] if s else v["data_views"], "views_source": "analytics" if s else "data_api",
                     "hours": round(s["hours"], 3) if s else "", "avg_view_sec": round(s["avd"]) if s else "",
                     "avg_view_pct": round(s["avp"], 1) if s else "", "subs_net": s["subs"] if s else "",
                     "views_48h": checkpoint(rs, v["published_pt"], 2), "views_7d": checkpoint(rs, v["published_pt"], 7),
                     "views_28d": checkpoint(rs, v["published_pt"], 28),
                     "impressions": st.get("imp", ""), "ctr_pct": st.get("ctr", ""), "title": v["title"]})

    csvdir = OUT / "csv"
    write_csv(csvdir / f"{today}_videos.csv", rows, list(rows[0].keys()) if rows else ["video"])
    write_csv(csvdir / f"{today}_video_daily.csv", daily, ["day", "video", "type"] + METRICS)
    write_csv(csvdir / f"{today}_traffic.csv", traffic,
              ["day", "video", "type", "insightTrafficSourceType", "views", "estimatedMinutesWatched"])

    # ---- 要約 ----
    L = [f"# 毎日の数字 {today}（scripts/analytics_daily.py が自動作成）", ""]
    L.append(f"- 出典：YouTube Analytics API（{'取得できず' if blocked else f'直近365日・データのある最終日 {last_day}'}）"
             f"／YouTube Data API（チャンネル全体・累計）／表示回数・クリック率は `{studio_file}`（CEOの書き出し）")
    L.append(f"- チャンネル全体（Data API）：登録者 {ch_stats.get('subscriberCount')}人、総再生 {int(ch_stats.get('viewCount', 0)):,}。"
             f"公開中の動画 {len(videos)}本" + (f"（ほかに非公開・限定公開 {hidden}本）" if hidden else ""))
    L.append("- Analytics API の数字は1〜2日遅れて確定する。今日・昨日の分は少なめに出る。")
    if blocked:
        L += ["", "> **⚠ Analytics API が使えないため、再生時間・平均視聴・登録・流入元は空欄です。**",
              f"> 理由：{blocked.code} {blocked.reason}。"
              + ("Google Cloud のプロジェクトで「YouTube Analytics API」が有効になっていません（CEOの作業：Cloud Console →「APIとサービス」→「ライブラリ」→ YouTube Analytics API →「有効にする」。無料）。"
                 if blocked.reason == "accessNotConfigured" or "has not been used" in blocked.message else blocked.message),
              "> 再生数は Data API の累計で代わりに出しています。"]

    L += ["", "## 長尺とショート（直近365日）", "| 区分 | 本数 | 再生 | 総再生時間 | 平均視聴時間 | 平均視聴率 | 登録の増減 | 最終日の再生 |",
          "|---|---|---|---|---|---|---|---|"]
    long_hours = 0.0
    for t in ("長尺", "ショート"):
        vs = [v for v in videos if v["type"] == t]
        rs = [r for r in daily if r["type"] == t]
        if rs:
            s = summarize(rs)
            day_views = sum(r["views"] for r in rs if r["day"] == last_day)
            L.append(f"| {t} | {len(vs)} | {s['views']:,} | {s['hours']:.1f}時間 | {mmss(s['avd'])} | {s['avp']:.1f}% | {s['subs']:+d} | {day_views:,} |")
            if t == "長尺":
                long_hours = s["hours"]
        else:
            L.append(f"| {t} | {len(vs)} | {sum(v['data_views'] for v in vs):,}（Data API） | — | — | — | — | — |")

    pending = [v["name"] for v in videos if not by_video[v["id"]]]
    if daily and pending:
        L.append(f"\n上の表は Analytics API にデータが出ている分だけ。まだ出ていない動画（{'、'.join(pending)}）は入っていない（動画別の表に Data API の累計あり）。")
    if not blocked:
        weeks = max((GOAL_DATE - today).days / 7, 1)
        L += ["", "## 収益化の4,000時間（長尺だけ・直近12か月）",
              f"- 累計 **{long_hours:.1f}時間 / 4,000時間（{long_hours / GOAL_HOURS * 100:.2f}%）**",
              f"- {GOAL_DATE}までに届くには、残り {GOAL_HOURS - long_hours:,.0f}時間 ÷ {weeks:.1f}週 ＝ **週 {(GOAL_HOURS - long_hours) / weeks:,.0f}時間**",
              "- ショートの再生時間は4,000時間に入らない（上の表のショート分は別扱い）。"]

    L += ["", "## 動画別", "| 区分 | 動画 | 公開 | 経過日 | 再生 | 48時間 | 7日 | 28日 | 再生時間 | 平均視聴 | 平均視聴率 | 登録 | 表示回数※ | クリック率※ |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        an = r["views_source"] == "analytics"
        views = f"{r['views']:,}" + ("" if an else "（Data API）")
        hours = f"{r['hours']:.2f}時間" if an else "—"
        avd = mmss(r["avg_view_sec"]) if an else "—"
        avp = f"{r['avg_view_pct']}%" if an else "—"
        subs = f"{r['subs_net']:+d}" if an else "—"
        ctr = r["ctr_pct"] + "%" if r["ctr_pct"] else "—"
        L.append(f"| {r['type']} | {r['name']} | {r['published'][5:].replace('-', '/')} | {r['age_days']} | {views} "
                 f"| {fmt(r['views_48h'])} | {fmt(r['views_7d'])} | {fmt(r['views_28d'])} "
                 f"| {hours} | {avd} | {avp} | {subs} | {r['impressions'] or '—'} | {ctr} |")
    L.append(f"\n※表示回数・クリック率はAPIに無いため `{studio_file}` の値（CEO書き出し時点・期間はその書き出しの設定どおり）。空欄はその書き出しに無い動画。"
             "「48時間」は公開日と翌日の2日分、まだその日数に届いていない動画は「—」。")

    if traffic:
        agg = defaultdict(lambda: [0, 0.0])
        for r in traffic:
            a = agg[(r["type"], r["insightTrafficSourceType"])]
            a[0] += r["views"]; a[1] += r["estimatedMinutesWatched"]
        L += ["", "## 流入元（直近365日）", "| 区分 | 流入元 | 再生 | 割合 | 再生時間 |", "|---|---|---|---|---|"]
        for t in ("長尺", "ショート"):
            total = sum(v[0] for (tt, _), v in agg.items() if tt == t) or 1
            for (tt, src), (vw, mins) in sorted(agg.items(), key=lambda x: -x[1][0]):
                if tt == t and vw:
                    L.append(f"| {t} | {SOURCE_JA.get(src, src)} | {vw:,} | {vw / total * 100:.0f}% | {mins / 60:.1f}時間 |")

    L += ["", f"数字のCSV：`departments/analytics/daily/csv/{today}_*.csv`（videos・video_daily・traffic）"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{today}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"書きました: departments/analytics/daily/{today}.md")
    if blocked:
        print(f"注意: Analytics API が使えません（{blocked.code} {blocked.reason}）。要約は一部だけです。")
        sys.exit(2)


if __name__ == "__main__":
    main()
