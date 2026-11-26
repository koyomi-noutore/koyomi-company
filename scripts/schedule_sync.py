"""投稿予定表（Googleスプレッドシート）と YouTube の照合（2026-11-23 CEO指示）。

予定と在庫の正はこのシート。CEOが予約するときに「予定日・枠」を入力し、重複と空き枠はシートの計算式で
その場で分かる。このスクリプトは毎朝 YouTube の実際（非公開・予約・公開済み）を読み、自動の列だけを書き換える。

  タブ「動画一覧」 A 動画ID / B 種類 / C 回 / D タイトル / E【入力】予定日 / F【入力】枠 / G 重複(式)
                   H YouTubeの状態 / I YouTubeの予約・公開時刻 / J 照合(式) / K Studioリンク / L キー(式・非表示)
  タブ「カレンダー」 今日から60日 × 8:30・14:30・18:30。動画一覧の入力から式で出す（プログラムを待たない）。
  タブ「在庫」     予定日が空の非公開の動画を、種類ごとに式で並べる。

決まり：
  - CEOが入力する E・F 列は絶対に書き換えない。例外は、タブを作った初回だけ、予約・公開済みの動画を YouTube の時刻で埋める。
  - B 種類・C 回は空のときだけ埋める（CEOが直したら尊重）。A は新しい行だけ。D・H・I・K は毎回書き換える。
  - G・J・L は見出し行の ARRAYFORMULA なので、行ごとの式は書かない。

認証：Sheets は VERTEX_SA_KEY_B64 のサービスアカウント、YouTube は今のOAuth（youtube_upload.access_token）。

使い方:
  python3 scripts/schedule_sync.py --sheet '<シートのURLかID>'   # 初回（IDを scripts/schedule_sheet.json に保存）
  python3 scripts/schedule_sync.py                                # 2回目以降（毎朝 6:47）
  python3 scripts/schedule_sync.py --dry-run                      # YouTube を読んで表示するだけ（シートに触らない）
  python3 scripts/schedule_sync.py --mark-deleted <動画ID> ...     # その行の枠を「削除」に（作り直して不要になった動画。CEOの指示のときだけ）

枠の「削除」（2026-11-24）：カレンダー・在庫・注意から外れ、行が灰色の取り消し線になる。
"""
import argparse
import base64
import datetime as dt
import glob
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from credentials import vertex_service_account, rs256_sign  # noqa: E402

CONF = Path(__file__).parent / "schedule_sheet.json"
LIST, CAL, STOCK = "動画一覧", "カレンダー", "在庫"
SLOTS = ["8:30", "14:30", "18:30"]
DELETE = "削除"
USED10 = "10問版"   # 2026-11-26 CEO：10問の長尺に使った5問の回。単独では出さない（削除と同じく在庫・カレンダー・注意から外す）   # 枠の選択肢。作り直して不要になった動画などに付ける（カレンダー・在庫・注意から外す。2026-11-24 CEO）
JST = dt.timezone(dt.timedelta(hours=9))
EPOCH = dt.datetime(1899, 12, 30, tzinfo=JST)  # スプレッドシートの日付の起点
HEAD = ["動画ID", "種類", "回", "タイトル", "【入力】予定日", "【入力】枠", None,
        "YouTubeの状態", "YouTubeの予約・公開時刻", None, "Studioリンク", None]
KINDS = ["長尺", "間違い探しショート", "文字の脳トレ", "ちがうのどーれだ"]
CAL_DAYS = 60

# 見出し行に置く式（下の行すべてに効く）
F_KEY = ('={"キー";ARRAYFORMULA(IF((E2:E="")+(F2:F=""),"",'
         'IF(ISNUMBER(E2:E),TEXT(E2:E,"yyyymmdd"),E2:E&"")&"_"&IF(ISNUMBER(F2:F),TEXT(F2:F,"h:mm"),F2:F&"")))}')
F_DUP = '={"重複";ARRAYFORMULA(IF(L2:L="","",IF(COUNTIF(L2:L,L2:L)>1,"⚠重複","")))}'
F_CHK = ('={"照合";ARRAYFORMULA(IF(A2:A="","",IF(I2:I="",IF(L2:L="","","⚠ずれ（未予約）"),'
         'IF(L2:L="","⚠未入力",IF(L2:L=TEXT(I2:I,"yyyymmdd")&"_"&TEXT(I2:I,"h:mm"),"","⚠ずれ")))))}')


def cal_cell(row, col):
    s = f"IF(ISNUMBER({col}$1),TEXT({col}$1,\"h:mm\"),{col}$1)"
    return (f"=IFERROR(TEXTJOIN(\" ／ \",TRUE,FILTER('{LIST}'!$B$2:$B&\"：\"&"
            f"IF('{LIST}'!$D$2:$D=\"\",'{LIST}'!$A$2:$A,'{LIST}'!$D$2:$D),"
            f"'{LIST}'!$L$2:$L=TEXT($A{row},\"yyyymmdd\")&\"_\"&{s})),\"\")")


# ---------- 認証 ----------
def sheets_token():
    sa = vertex_service_account()
    b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=")
    now = int(time.time())
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = b64(json.dumps({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
                            "aud": sa["token_uri"], "iat": now, "exp": now + 3600}).encode())
    sig = b64(rs256_sign(sa["private_key"], head + b"." + claim))
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": (head + b"." + claim + b"." + sig).decode()}).encode()
    with urllib.request.urlopen(urllib.request.Request(sa["token_uri"], data=data), timeout=60) as r:
        return json.load(r)["access_token"]


def call(url, token, body=None, method=None):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
        sys.exit(f"APIエラー {e.code}: {msg[:300]}")


# ---------- YouTube ----------
def youtube_videos(extra_ids=()):
    """チャンネルの全動画。uploads 再生リストはページが重なって数本抜けることがある（2026-11-23 zcAY1FhNMm0 が抜けた）ので、
    search(forMine) と、シートに既にある動画ID も合わせて、videos.list で直接読む。"""
    from youtube_upload import access_token
    tok = access_token()
    g = lambda p: call("https://www.googleapis.com/youtube/v3/" + p, tok)

    def pages(path, pick):
        got, page, total = [], "", 0
        while True:
            r = g(path + (f"&pageToken={page}" if page else ""))
            got += [pick(i) for i in r["items"]]
            total = r.get("pageInfo", {}).get("totalResults", total)
            page = r.get("nextPageToken")
            if not page:
                return got, total

    up = g("channels?part=contentDetails&mine=true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    a, total = pages(f"playlistItems?part=contentDetails&maxResults=50&playlistId={up}", lambda i: i["contentDetails"]["videoId"])
    b, _ = pages("search?part=id&forMine=true&type=video&maxResults=50", lambda i: i["id"]["videoId"])
    ids = list(dict.fromkeys(a + b + [x for x in extra_ids if x]))
    out = {}
    for i in range(0, len(ids), 50):
        for v in g("videos?part=snippet,status,contentDetails&id=" + ",".join(ids[i:i + 50]))["items"]:
            out[v["id"]] = v
    if len(out) < total:
        print(f"注意：YouTubeの動画数 {total} 本のうち {len(out)} 本しか読めませんでした")
    return out


def parse_time(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST) if s else None


def seconds(iso):
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def kind(v):
    t = v["snippet"]["title"]
    if seconds(v["contentDetails"].get("duration")) > 180:
        return "長尺"
    if "ちがう" in t and "どれ" in t:
        return "ちがうのどーれだ"
    if "1問" in t or "見つけられる" in t or t.startswith("シニアの間違い探し"):
        return "間違い探しショート"
    return "文字の脳トレ"


def state(v):
    """(状態, JSTの時刻 or None)"""
    st = v["status"]
    if st["privacyStatus"] == "public":
        return "公開済み", parse_time(v["snippet"]["publishedAt"])
    if st["privacyStatus"] == "private" and st.get("publishAt"):
        return "予約", parse_time(st["publishAt"])
    return {"private": "非公開", "unlisted": "限定公開"}.get(st["privacyStatus"], st["privacyStatus"]), None


def episode_map():
    """outputs/*/upload.json から 動画ID → 回 の対応を作る。"""
    m = {}
    for f in glob.glob(str(ROOT / "outputs" / "**" / "upload.json"), recursive=True):
        rel = Path(f).relative_to(ROOT / "outputs").parts
        try:
            vid = json.load(open(f, encoding="utf-8")).get("video_id")
        except Exception:
            continue
        if not vid or "prototypes" in rel[0] or "old" in "/".join(rel):
            continue
        n = re.search(r"_(text_)?(\d+)", rel[0])
        if not n:
            continue
        w = re.search(r"_w10_(\d+)$", rel[0])   # 2回分をつないだ全10問の回（combine_episodes.py）
        label = (f"10問版{int(w.group(1))}" if w else f"文字{int(n.group(2))}" if n.group(1) else f"第{int(n.group(2))}回")
        if len(rel) > 2:
            label += {"short": " ショート1", "short2": " ショート2"}.get(rel[1], " " + rel[1])
        m[vid] = label
    return m


def serial(t):
    return round((t - EPOCH).total_seconds() / 86400, 6)


def hm(t):
    return f"{t.hour}:{t.minute:02d}"


# ---------- シート ----------
def color(h):
    h = h.lstrip("#")
    return {k: int(h[i:i + 2], 16) / 255 for k, i in zip(("red", "green", "blue"), (0, 2, 4))}


def stock_formulas():
    """在庫タブ 2〜3行目の式（予定日が空・非公開・枠が「削除」でない動画を種類ごとに）。"""
    q = f"'{LIST}'!"
    cond = f"{q}$B$2:$B=A$1,{q}$E$2:$E=\"\",{q}$H$2:$H=\"非公開\",{q}$F$2:$F<>\"{DELETE}\",{q}$F$2:$F<>\"{USED10}\""
    return [[f'=IFERROR(ROWS(FILTER({q}$A$2:$A,{cond.replace("A$1", c + "$1")})),0)&"本"' for c in "ABCD"],
            [f'=IFERROR(FILTER(IF({q}$C$2:$C="",{q}$D$2:$D,{q}$C$2:$C&"｜"&{q}$D$2:$D),{cond.replace("A$1", c + "$1")}),"（なし）")'
             for c in "ABCD"]]


def slot_rule(sheet):
    """枠（F列）の選択肢：8:30・14:30・18:30・削除。"""
    return {"setDataValidation": {"range": {"sheetId": sheet, "startRowIndex": 1, "endRowIndex": 1000,
                                            "startColumnIndex": 5, "endColumnIndex": 6}, "rule": {
        "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in SLOTS + [DELETE, USED10]]},
        "strict": False, "showCustomUi": True}}}


def upgrade(sid, tok):
    """作成済みのシートに、あとから足した決まりを入れる（何度実行しても同じ）。
    2026-11-24：枠の選択肢に「削除」。削除の行は在庫から外し、行を灰色にする。"""
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
    meta = call(base + "?fields=sheets(properties(title,sheetId),conditionalFormats)", tok)
    sh = {s["properties"]["title"]: s for s in meta["sheets"]}
    L = sh[LIST]["properties"]["sheetId"]
    reqs = [slot_rule(L)]
    gray = f'=OR($F2="{DELETE}",$F2="{USED10}")'
    if not any(gray == v.get("userEnteredValue") for r in sh[LIST].get("conditionalFormats", [])
               for v in r.get("booleanRule", {}).get("condition", {}).get("values", [])):
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [{"sheetId": L, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": 12}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": gray}]},
                            "format": {"backgroundColor": color("#D9D9D9"),
                                       "textFormat": {"strikethrough": True, "foregroundColor": color("#666666")}}}}}})
    call(base + ":batchUpdate", tok, {"requests": reqs})
    if STOCK in sh:
        call(base + "/values:batchUpdate", tok, {"valueInputOption": "USER_ENTERED",
                                                 "data": [{"range": f"'{STOCK}'!A2:D3", "values": stock_formulas()}]})


def mark_deleted(sid, tok, ids, value=None):
    """指定した動画の行の枠を「削除」にする（CEOの指示があったときだけ使う。予定日が入っている行は変えない）。"""
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
    cur = call(base + f"/values/{urllib.parse.quote(LIST)}!A2:F", tok).get("values", [])
    data, done = [], []
    for i, r in enumerate(cur):
        r = r + [""] * (6 - len(r))
        if r[0] in ids:
            if r[4]:
                print("予定日が入っているので変えない：", r[0], r[4], r[5])
                continue
            data.append({"range": f"'{LIST}'!F{i + 2}", "values": [[value or DELETE]]})
            done.append(r[0])
    if data:
        call(base + "/values:batchUpdate", tok, {"valueInputOption": "RAW", "data": data})
    return done


def setup(sid, tok):
    """タブがなければ作る。動画一覧を新しく作ったら True（＝初回）。"""
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
    meta = call(base + "?fields=sheets.properties", tok)
    have = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    first = LIST not in have
    add = [{"addSheet": {"properties": {"title": t}}} for t in (LIST, CAL, STOCK) if t not in have]
    if not add:
        return False
    if first:  # 日付・TODAY() を日本時間で計算させる
        add.append({"updateSpreadsheetProperties": {"properties": {"locale": "ja_JP", "timeZone": "Asia/Tokyo"},
                                                    "fields": "locale,timeZone"}})
    r = call(base + ":batchUpdate", tok, {"requests": add})
    for rep in r["replies"]:
        if "addSheet" in rep:
            p = rep["addSheet"]["properties"]
            have[p["title"]] = p["sheetId"]
    reqs, vals = [], []
    red_bg, red_fg = color("#F4CCCC"), color("#CC0000")
    rng = lambda sh, r0, r1, c0, c1: {"sheetId": sh, "startRowIndex": r0, "endRowIndex": r1,
                                       "startColumnIndex": c0, "endColumnIndex": c1}
    fmt = lambda r, f, fields: {"repeatCell": {"range": r, "cell": {"userEnteredFormat": f}, "fields": fields}}
    if first:
        L = have[LIST]
        head = [h if h else "" for h in HEAD]
        head[6], head[9], head[11] = F_DUP, F_CHK, F_KEY
        vals.append({"range": f"'{LIST}'!A1:L1", "values": [head]})
        reqs += [
            {"updateSheetProperties": {"properties": {"sheetId": L, "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}},
                                       "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
            fmt(rng(L, 0, 1, 0, 13), {"textFormat": {"bold": True}, "backgroundColor": color("#E8EAED")},
                "userEnteredFormat(textFormat,backgroundColor)"),
            # 入力する所（E・F）は黄色、見出しはオレンジ
            fmt(rng(L, 0, 1, 4, 6), {"textFormat": {"bold": True}, "backgroundColor": color("#F6B26B")},
                "userEnteredFormat(textFormat,backgroundColor)"),
            fmt(rng(L, 1, 1000, 4, 5), {"backgroundColor": color("#FFF2CC"),
                                         "numberFormat": {"type": "DATE", "pattern": "yyyy/mm/dd(ddd)"}},
                "userEnteredFormat(backgroundColor,numberFormat)"),
            fmt(rng(L, 1, 1000, 5, 6), {"backgroundColor": color("#FFF2CC"), "numberFormat": {"type": "TEXT"},
                                         "horizontalAlignment": "CENTER"},
                "userEnteredFormat(backgroundColor,numberFormat,horizontalAlignment)"),
            fmt(rng(L, 1, 1000, 8, 9), {"numberFormat": {"type": "DATE_TIME", "pattern": "yyyy/mm/dd(ddd) h:mm"}},
                "userEnteredFormat.numberFormat"),
            {"setDataValidation": {"range": rng(L, 1, 1000, 4, 5), "rule": {
                "condition": {"type": "DATE_IS_VALID"}, "strict": True, "inputMessage": "公開する日（例 11/24）"}}},
            slot_rule(L),
            {"setDataValidation": {"range": rng(L, 1, 1000, 1, 2), "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in KINDS]},
                "strict": False, "showCustomUi": True}}},
            {"updateDimensionProperties": {"range": {"sheetId": L, "dimension": "COLUMNS", "startIndex": 11, "endIndex": 12},
                                           "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}},
        ]
        for c0, c1, w in [(0, 1, 110), (1, 2, 140), (2, 3, 120), (3, 4, 380), (4, 5, 130), (5, 6, 70),
                          (6, 7, 70), (7, 8, 90), (8, 9, 170), (9, 10, 120), (10, 11, 300)]:
            reqs.append({"updateDimensionProperties": {"range": {"sheetId": L, "dimension": "COLUMNS", "startIndex": c0,
                                                                 "endIndex": c1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
        for col, letter in ((6, "G"), (9, "J")):
            reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [rng(L, 1, 1000, col, col + 1), rng(L, 1, 1000, 0, 1)],
                "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f"=${letter}2<>\"\""}]},
                                "format": {"backgroundColor": red_bg, "textFormat": {"bold": True, "foregroundColor": red_fg}}}}}})
    if CAL in [a["addSheet"]["properties"]["title"] for a in add if "addSheet" in a]:
        C = have[CAL]
        rows = [["日付"] + SLOTS]
        rows.append([f"=ARRAYFORMULA(TODAY()+SEQUENCE({CAL_DAYS})-1)"] + [cal_cell(2, c) for c in "BCD"])
        rows += [[None] + [cal_cell(r, c) for c in "BCD"] for r in range(3, CAL_DAYS + 2)]
        vals.append({"range": f"'{CAL}'!A1:D1", "values": [rows[0]], "_raw": True})
        vals.append({"range": f"'{CAL}'!A2:D{CAL_DAYS + 1}", "values": [[x if x is not None else "" for x in r] for r in rows[1:]]})
        body = rng(C, 1, CAL_DAYS + 1, 1, 4)
        reqs += [
            {"updateSheetProperties": {"properties": {"sheetId": C, "gridProperties": {"frozenRowCount": 1}},
                                       "fields": "gridProperties.frozenRowCount"}},
            fmt(rng(C, 0, 1, 0, 4), {"textFormat": {"bold": True}, "backgroundColor": color("#E8EAED"),
                                      "horizontalAlignment": "CENTER", "numberFormat": {"type": "TEXT"}},
                "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,numberFormat)"),
            fmt(rng(C, 1, CAL_DAYS + 1, 0, 1), {"numberFormat": {"type": "DATE", "pattern": "m/d(ddd)"},
                                                 "textFormat": {"bold": True}},
                "userEnteredFormat(numberFormat,textFormat)"),
            fmt(body, {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"},
                "userEnteredFormat(wrapStrategy,verticalAlignment)"),
            {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [body], "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": '=REGEXMATCH(B2," ／ ")'}]},
                "format": {"backgroundColor": red_bg, "textFormat": {"bold": True, "foregroundColor": red_fg}}}}}},
            {"addConditionalFormatRule": {"index": 1, "rule": {"ranges": [body], "booleanRule": {
                "condition": {"type": "BLANK"}, "format": {"backgroundColor": color("#EFEFEF")}}}}},
            {"addConditionalFormatRule": {"index": 2, "rule": {"ranges": [rng(C, 1, CAL_DAYS + 1, 0, 1)], "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=WEEKDAY($A2,2)>5"}]},
                "format": {"textFormat": {"foregroundColor": red_fg}}}}}},
        ]
        for c0, c1, w in [(0, 1, 90), (1, 4, 300)]:
            reqs.append({"updateDimensionProperties": {"range": {"sheetId": C, "dimension": "COLUMNS", "startIndex": c0,
                                                                 "endIndex": c1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    if STOCK in [a["addSheet"]["properties"]["title"] for a in add if "addSheet" in a]:
        S = have[STOCK]
        q = f"'{LIST}'!"
        vals.append({"range": f"'{STOCK}'!A1:D1", "values": [KINDS], "_raw": True})
        vals.append({"range": f"'{STOCK}'!A2:D3", "values": stock_formulas()})
        reqs += [
            {"updateSheetProperties": {"properties": {"sheetId": S, "gridProperties": {"frozenRowCount": 2}},
                                       "fields": "gridProperties.frozenRowCount"}},
            fmt(rng(S, 0, 2, 0, 4), {"textFormat": {"bold": True}, "backgroundColor": color("#E8EAED"),
                                      "horizontalAlignment": "CENTER"},
                "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)"),
            {"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 4},
                                           "properties": {"pixelSize": 330}, "fields": "pixelSize"}},
        ]
    if reqs:
        call(base + ":batchUpdate", tok, {"requests": reqs})
    raw = [v for v in vals if v.pop("_raw", False)]
    if raw:  # 枠の見出しは文字のまま入れる（時刻に変換させない）
        call(base + "/values:batchUpdate", tok, {"valueInputOption": "RAW", "data": raw})
    rest = [v for v in vals if v not in raw]
    if rest:
        call(base + "/values:batchUpdate", tok, {"valueInputOption": "USER_ENTERED", "data": rest})
    return first


def sync(sid, tok, videos, first):
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
    cur = call(base + f"/values/{urllib.parse.quote(LIST)}!A2:K?valueRenderOption=UNFORMATTED_VALUE", tok).get("values", [])
    cur = [r + [""] * (11 - len(r)) for r in cur]
    rows = {r[0]: i + 2 for i, r in enumerate(cur) if r[0]}
    eps = episode_map()
    ep = lambda v: (eps.get(v["id"], "").replace("文字", "ちがう", 1) if kind(v) == "ちがうのどーれだ"
                    else eps.get(v["id"], ""))
    data, added = [], 0
    put = lambda a1, vals: data.append({"range": f"'{LIST}'!{a1}", "values": [vals]})
    for vid, r in rows.items():  # 既存の行：自動の列だけ
        old = cur[r - 2]
        v = videos.get(vid)
        if not v:
            put(f"H{r}:I{r}", ["YouTubeになし", ""])
            continue
        st, t = state(v)
        put(f"B{r}:D{r}", [old[1] or kind(v), old[2] or ep(v), v["snippet"]["title"]])
        put(f"H{r}:I{r}", [st, serial(t) if t else ""])
        put(f"K{r}", [f"https://studio.youtube.com/video/{vid}/edit"])
    new = [v for vid, v in videos.items() if vid not in rows]
    new.sort(key=lambda v: state(v)[1] or parse_time(v["snippet"]["publishedAt"]))
    nxt = (max(rows.values()) if rows else 1) + 1
    for v in new:  # 新しい行
        st, t = state(v)
        e = f = ""
        if first and t:  # 初回だけ：予約・公開済みを YouTube の時刻で埋める
            e, f = int(serial(t.replace(hour=0, minute=0, second=0, microsecond=0))), hm(t)
        put(f"A{nxt}:F{nxt}", [v["id"], kind(v), ep(v), v["snippet"]["title"], e, f])
        put(f"H{nxt}:I{nxt}", [st, serial(t) if t else ""])
        put(f"K{nxt}", [f"https://studio.youtube.com/video/{v['id']}/edit"])
        nxt += 1
        added += 1
    put("M1", ["最終同期 " + dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M")])
    call(base + "/values:batchUpdate", tok, {"valueInputOption": "RAW", "data": data})
    return added


def report(sid, tok):
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
    rows = call(base + f"/values/{urllib.parse.quote(LIST)}!A2:J", tok).get("values", [])
    warn = []
    for r in rows:
        r = r + [""] * (10 - len(r))
        flag = "" if r[5] in (DELETE, USED10) else " ".join(x for x in (r[6], r[9]) if x)
        if flag:
            warn.append(f"{flag}\t{r[0]}\t{r[1]}\t入力 {r[4] or '—'} {r[5] or ''}\tYouTube {r[7]} {r[8] or '—'}\t{r[3][:30]}")
    print(f"動画 {len(rows)} 本。注意 {len(warn)} 件")
    for w in warn:
        print(w)
    return warn


def sheet_id(arg):
    if arg:
        m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", arg)
        sid = m.group(1) if m else arg.strip()
        CONF.write_text(json.dumps({"spreadsheet_id": sid}, ensure_ascii=False, indent=1) + "\n")
        return sid
    if CONF.exists():
        return json.loads(CONF.read_text())["spreadsheet_id"]
    sys.exit("シートが未設定です。--sheet '<URL>' で1回指定してください。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mark-deleted", nargs="+", metavar="動画ID", help="その動画の行の枠を「削除」にする（CEOの指示のときだけ）")
    ap.add_argument("--mark-used10", nargs="+", metavar="動画ID", help="その動画の行の枠を「10問版」にする（10問の長尺に使った5問の回。単独で出さない）")
    ap.add_argument("--fill-new", action="store_true",
                    help="今回足す新しい行だけ、予約・公開済みなら予定日・枠をYouTubeの時刻で埋める（既存の行には触らない）")
    a = ap.parse_args()
    if a.dry_run:
        videos = youtube_videos()
        for v in sorted(videos.values(), key=lambda v: state(v)[1] or parse_time(v["snippet"]["publishedAt"])):
            st, t = state(v)
            print(v["id"], kind(v), episode_map().get(v["id"], "-"), st, t.strftime("%m/%d %H:%M") if t else "-",
                  v["snippet"]["title"][:28], sep="\t")
        return
    sid = sheet_id(a.sheet)
    tok = sheets_token()
    first = setup(sid, tok)
    upgrade(sid, tok)
    if a.mark_deleted:
        print("「削除」にした行：", mark_deleted(sid, tok, set(a.mark_deleted)))
    if a.mark_used10:
        print("「10問版」にした行：", mark_deleted(sid, tok, set(a.mark_used10), USED10))
    have = call(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{urllib.parse.quote(LIST)}!A2:A", tok).get("values", [])
    videos = youtube_videos([r[0] for r in have if r])
    added = sync(sid, tok, videos, first or a.fill_new)
    print(f"{'初回の作成・' if first else ''}同期しました。新しい行 {added} 本。")
    report(sid, tok)


if __name__ == "__main__":
    main()
