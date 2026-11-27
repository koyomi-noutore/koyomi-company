"""アップロードした動画を、空いている枠に予約する（2026-11-27 CEO決定：今後はアップロードのときに予約まで済ませる）。

youtube_upload.upload() がアップロードの直後に book() を呼ぶ。手で呼ぶとき：
  python3 scripts/auto_schedule.py <フォルダ>           # そのフォルダの upload.json の動画を予約
  python3 scripts/auto_schedule.py <フォルダ> --dry-run  # 入れる枠を表示するだけ

決まり（knowledge/schedule.md 2026-11-27）：
  - 枠は 長尺 7:30／ショート 13:00・17:00（schedule_sync.SLOTS が正）。毎日。
  - 長尺：いちばん後ろの長尺の次の日の 7:30（あいだに空きがあればそこ）。明日より前には入れない。
  - ショート：空いている 13:00・17:00 のうち一番早い枠。ただし
      ・間違い探しのショートは、元の長尺（と、その回を使った10問版）の公開日か、それより後
      ・前後の枠と同じ種類にならない枠を先に選ぶ（無ければ一番早い空き）
  - 予約は YouTube の status.publishAt（非公開のまま。時刻になると公開）。予定表の E・F 列は schedule_sync が YouTube の時刻で埋める。
  - 環境変数 KOYOMI_NO_SCHEDULE=1 のときは予約しない（作り直しの差し替え用など）。
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import schedule_sync as SS   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
JST = SS.JST
LONG_SLOT, SHORT_SLOTS = SS.SLOTS[0], SS.SLOTS[1:]
HORIZON = 120


def at(day, slot):
    h, m = map(int, slot.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)


def taken(videos, skip=None):
    """予約・公開済みの (日時 → 種類)。"""
    out = {}
    for vid, v in videos.items():
        if vid == skip:
            continue
        st, t = SS.state(v)
        if st in ("予約", "公開済み") and t:
            out[t.replace(second=0, microsecond=0)] = SS.kind(v)
    return out


def earliest_for_short(folder, videos):
    """間違い探しのショート：元の長尺と、その回を使った10問版の、予約・公開の日（遅いほう）。"""
    ep = folder.parent
    ids = []
    up = ep / "upload.json"
    if up.exists():
        ids.append(json.loads(up.read_text(encoding="utf-8"))["video_id"])
    for p in ROOT.glob("outputs/*/plan.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8")).get("combined") or {}
        except Exception:
            continue
        if ep.name in c.get("sources", []) and (p.parent / "upload.json").exists():
            ids.append(json.loads((p.parent / "upload.json").read_text(encoding="utf-8"))["video_id"])
    days = []
    for i in ids:
        v = videos.get(i)
        if v:
            st, t = SS.state(v)
            if t:
                days.append(t.date())
    return max(days) if days else None


def choose(vid, short, folder, videos, now=None):
    now = now or dt.datetime.now(JST)
    start = now.date() + dt.timedelta(days=1)   # 明日から
    busy = taken(videos, skip=vid)
    me = SS.kind(videos[vid])
    if not short:
        longs = sorted(t.date() for t, k in busy.items() if k == "長尺")
        last = max([d for d in longs] + [start - dt.timedelta(days=1)])
        d = start
        while d <= last + dt.timedelta(days=1):
            if at(d, LONG_SLOT) not in busy:
                return at(d, LONG_SLOT)
            d += dt.timedelta(days=1)
        raise SystemExit("長尺の空き枠が見つからない")
    lo = earliest_for_short(folder, videos) if me == "間違い探しショート" else None
    d0 = max(start, lo) if lo else start
    seq = [at(d0 + dt.timedelta(days=i), s) for i in range(HORIZON) for s in SHORT_SLOTS]
    free = [t for t in seq if t not in busy]
    if not free:
        raise SystemExit("ショートの空き枠が見つからない")

    def neighbors(t):
        i = seq.index(t)
        return [busy.get(seq[j]) for j in (i - 1, i + 1) if 0 <= j < len(seq)]
    good = [t for t in free if me not in neighbors(t)]
    return (good or free)[0]


def book(vid, short, folder, dry=False):
    import os
    if os.environ.get("KOYOMI_NO_SCHEDULE") == "1":
        return None
    from youtube_upload import access_token
    videos = SS.youtube_videos([vid])
    t = choose(vid, short, Path(folder), videos)
    if dry:
        return t.isoformat()
    tok = access_token()
    st = videos[vid]["status"]
    if st["privacyStatus"] != "private":
        raise SystemExit(f"非公開ではないので予約しない：{vid} {st['privacyStatus']}")
    body = {"id": vid, "status": {k: st[k] for k in ("embeddable", "license", "publicStatsViewable", "selfDeclaredMadeForKids", "containsSyntheticMedia") if k in st}}
    body["status"].update(privacyStatus="private", publishAt=t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    r = SS.call("https://www.googleapis.com/youtube/v3/videos?part=status", tok, body, "PUT")
    return r["status"].get("publishAt") and t.isoformat()


if __name__ == "__main__":
    f = Path(sys.argv[1]).resolve()
    j = json.loads((f / "upload.json").read_text(encoding="utf-8"))
    print(book(j["video_id"], bool(j.get("short")), f, dry="--dry-run" in sys.argv))
