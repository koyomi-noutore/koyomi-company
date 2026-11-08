"""YouTubeへ「非公開」でアップロードする（社則：公開ボタンはCEOが押す）。
タイトル・説明・タグは outputs/<回>/description.md の確定版（コードブロック）から読む。
認証情報は環境変数（scripts/credentials.py）からだけ読み、画面・ログに出さない。

使い方:
  python3 scripts/youtube_upload.py <outputs/回のフォルダ>
  → 動画ID・URLを <フォルダ>/upload.json に記録する
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from credentials import youtube_client, youtube_refresh_token

TOKEN_FILE = Path.home() / ".config" / "koyomi-noutore" / "youtube_token.json"
CHUNK = 16 * 1024 * 1024


def access_token():
    c = youtube_client()
    rt = youtube_refresh_token(str(TOKEN_FILE))
    if not rt:
        sys.exit("ログイン情報がありません（scripts/youtube_auth.py で初回ログイン）")
    data = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "refresh_token": rt, "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen(urllib.request.Request(c["token_uri"], data=data), timeout=60) as r:
        return json.load(r)["access_token"]


def read_metadata(desc_md):
    text = Path(desc_md).read_text(encoding="utf-8")

    def block(heading):
        m = re.search(r"^## " + re.escape(heading) + r".*?\n```\n(.*?)\n```", text, re.S | re.M)
        if not m:
            sys.exit(f"description.md に「{heading}」のコードブロックがありません")
        return m.group(1).strip()

    title = block("タイトル")
    desc = block("説明欄")
    tags = [t.strip() for t in block("タグ").split(",") if t.strip()]
    if len(title) > 100:
        sys.exit("タイトルが100文字を超えています")
    if re.search(r"[○〇]時|記入）", desc):
        sys.exit("説明欄に仮置き（○時・記入）が残っています")
    return title, desc, tags


def set_thumbnail(video_id, path, tok):
    """サムネを設定する（thumbnails.set）。"""
    data = Path(path).read_bytes()
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media",
        data=data, method="POST", headers={"Authorization": "Bearer " + tok, "Content-Type": "image/jpeg"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"サムネの設定に失敗: HTTP {e.code} {e.read()[:400]!r}")


def upload(folder, thumbnail=None, short=False):
    """short=True はショート（<回>/short/）。ショートはサムネを設定しない（ショートの画面ではサムネが出ないため）。"""
    folder = Path(folder)
    if not short and (thumbnail is None or not Path(thumbnail).exists()):
        sys.exit("サムネがありません（サムネなしでアップロードしない：.claude/agents/production.md）")
    video = folder / "video.mp4"
    title, desc, tags = read_metadata(folder / "description.md")
    body = {
        "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "27",
                    "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True},
    }
    assert body["status"]["privacyStatus"] == "private"  # 社則：必ず非公開
    tok = access_token()
    size = video.stat().st_size
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    with urllib.request.urlopen(init, timeout=60) as r:
        session = r.headers["Location"]
    sent, result = 0, None
    with open(video, "rb") as f:
        while sent < size:
            chunk = f.read(CHUNK)
            end = sent + len(chunk) - 1
            req = urllib.request.Request(session, data=chunk, method="PUT", headers={
                "Authorization": "Bearer " + tok, "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {sent}-{end}/{size}"})
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    result = json.load(r)
                    sent = size
            except urllib.error.HTTPError as e:
                if e.code != 308:
                    sys.exit(f"アップロード失敗: HTTP {e.code} {e.read()[:300]!r}")
                rng = e.headers.get("Range")
                sent = int(rng.split("-")[1]) + 1 if rng else 0
                f.seek(sent)
            print(f"  {sent * 100 // size}%", flush=True)
    vid = result["id"]
    th = set_thumbnail(vid, thumbnail, access_token()) if not short else {}
    rec = {"video_id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
           "privacy": result["status"]["privacyStatus"], "title": result["snippet"]["title"],
           "thumbnail": bool(th.get("items")), "short": short}
    (folder / "upload.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit("scripts/make_episode.py <回> upload を使ってください（監査の合格とサムネを確かめてから送る）")
