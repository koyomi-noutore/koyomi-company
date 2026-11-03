"""認証情報の読み込み（正式な仕組み）。値は環境変数からだけ読み、画面・ログ・ファイルに出さない。

YOUTUBE_CLIENT_SECRET_JSON について（2026-11-03 CEO決定）:
  登録されている値は、Google Cloud からダウンロードしたJSONの {"installed": の直後の "{" が欠けた形
  （{"installed":"client_id":...}} ）になっている。CEOの判断で値はこのままとし、読み込み時に補う。
  正しい形のJSONが登録された場合も、そのまま読める。
"""
import json
import os
import sys

_TOP_KEYS = ("installed", "web")


def _repair_missing_inner_brace(raw):
    """{"installed":"client_id":...}} → {"installed":{"client_id":...}} に補う。
    この形の崩れだけを直す。ほかの崩れは直さずにエラーにする（推測で直さない）。"""
    s = raw.strip()
    for key in _TOP_KEYS:
        head = '{"%s":' % key
        if s.startswith(head) and not s[len(head):].lstrip().startswith("{"):
            return head + "{" + s[len(head):]
    return None


def youtube_client(env="YOUTUBE_CLIENT_SECRET_JSON"):
    """OAuthクライアント情報（client_id, client_secret, auth_uri, token_uri …）を返す。"""
    raw = os.environ.get(env)
    if not raw:
        raise SystemExit(f"{env} が設定されていません")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        fixed = _repair_missing_inner_brace(raw)
        if fixed is None:
            raise SystemExit(f"{env} をJSONとして読めません（既知の崩れ方とも違います）") from None
        try:
            data = json.loads(fixed)
        except json.JSONDecodeError:
            raise SystemExit(f"{env} を補っても読めません") from None
    for key in _TOP_KEYS:
        if isinstance(data.get(key), dict):
            info = data[key]
            break
    else:
        raise SystemExit(f"{env} に installed / web がありません")
    missing = [k for k in ("client_id", "client_secret", "token_uri", "auth_uri") if not info.get(k)]
    if missing:
        raise SystemExit(f"{env} に必要な項目がありません: {', '.join(missing)}")
    return info


def youtube_refresh_token(token_file=None):
    """環境変数 YOUTUBE_REFRESH_TOKEN を優先し、なければログイン時に保存したファイルを読む。"""
    v = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if v:
        return v.strip()
    if token_file and os.path.exists(token_file):
        with open(token_file, encoding="utf-8") as f:
            return json.load(f)["refresh_token"]
    return None


def gemini_key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise SystemExit("GEMINI_API_KEY が設定されていません")
    return k
