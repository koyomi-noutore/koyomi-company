"""YouTubeの初回ログイン（OAuth、デスクトップアプリ方式＋PKCE）。
認証情報は環境変数 YOUTUBE_CLIENT_SECRET_JSON からだけ読む。トークンはリポジトリの外
（~/.config/koyomi-noutore/youtube_token.json、権限600）に保存し、画面やログには出さない。

使い方:
  python3 scripts/youtube_auth.py url              # 許可ページのURLを出す
  python3 scripts/youtube_auth.py exchange '<URL>' # 許可後に飛んだ http://localhost/?code=... を渡す
  python3 scripts/youtube_auth.py check            # ログイン中のチャンネルを確認
"""
import base64, hashlib, json, os, secrets, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from credentials import youtube_client, youtube_refresh_token

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",      # 非公開アップロード
          "https://www.googleapis.com/auth/youtube.readonly",    # 自分のチャンネル・動画の確認
          "https://www.googleapis.com/auth/yt-analytics.readonly"]  # 分析部用
REDIRECT = "http://localhost"
DIR = Path.home() / ".config" / "koyomi-noutore"
STATE, TOKEN = DIR / "oauth_state.json", DIR / "youtube_token.json"


def client():
    return youtube_client()


def save(path, data):
    DIR.mkdir(parents=True, exist_ok=True); os.chmod(DIR, 0o700)
    path.write_text(json.dumps(data)); os.chmod(path, 0o600)


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = json.loads(e.read() or b"{}")
        sys.exit(f"エラー: {body.get('error')} {body.get('error_description', '')}")


def access_token():
    rt = youtube_refresh_token(str(TOKEN))
    if not rt:
        sys.exit("まだログインしていません（url → exchange を先に）")
    c = client()
    return post(c["token_uri"], {"client_id": c["client_id"], "client_secret": c["client_secret"],
                                 "refresh_token": rt, "grant_type": "refresh_token"})["access_token"]


def cmd_url():
    c = client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    save(STATE, {"verifier": verifier, "state": state})
    q = {"client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code",
         "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent",
         "code_challenge": challenge, "code_challenge_method": "S256", "state": state}
    print(c["auth_uri"] + "?" + urllib.parse.urlencode(q))


def cmd_exchange(redirected):
    c = client(); st = json.loads(STATE.read_text())
    q = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
    if q.get("state", [""])[0] != st["state"]:
        sys.exit("state が一致しません。url からやり直してください。")
    if "error" in q:
        sys.exit("許可されませんでした: " + q["error"][0])
    tok = post(c["token_uri"], {"code": q["code"][0], "client_id": c["client_id"], "client_secret": c["client_secret"],
                                "redirect_uri": REDIRECT, "grant_type": "authorization_code", "code_verifier": st["verifier"]})
    if "refresh_token" not in tok:
        sys.exit("refresh_token が返りませんでした。url からやり直してください。")
    save(TOKEN, {"refresh_token": tok["refresh_token"], "scope": tok.get("scope")})
    STATE.unlink()
    print("ログインできました。トークンは", TOKEN, "に保存しました（中身は表示しません）。")
    cmd_check()


def cmd_check():
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
                                 headers={"Authorization": "Bearer " + access_token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.load(r).get("items", [])
    if not items:
        print("このアカウントにはチャンネルがありません。ブランドアカウントを選び直してください。")
    for it in items:
        s = it["snippet"]
        print(f"チャンネル: {s['title']} / ハンドル: {s.get('customUrl')} / 登録者: {it['statistics'].get('subscriberCount')}")


if __name__ == "__main__":
    {"url": lambda: cmd_url(), "exchange": lambda: cmd_exchange(sys.argv[2]), "check": lambda: cmd_check()}[sys.argv[1]]()
