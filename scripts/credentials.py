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


def vertex_service_account(env="VERTEX_SA_KEY_B64"):
    """Vertex AI 用サービスアカウント鍵（JSONをBase64にしたもの）をメモリ上でだけデコードして返す。
    中身は表示・保存・ログ出力しない。エラー文にも値を含めない。"""
    import base64
    raw = os.environ.get(env)
    if not raw:
        raise SystemExit(f"{env} が設定されていません")
    try:
        info = json.loads(base64.b64decode("".join(raw.split())))
    except Exception:
        raise SystemExit(f"{env} をBase64のJSONとして読めません") from None
    missing = [k for k in ("client_email", "private_key", "project_id") if not info.get(k)]
    if missing:
        raise SystemExit(f"{env} に必要な項目がありません: {', '.join(missing)}")
    return info


def rs256_sign(private_key_pem, message):
    """サービスアカウントのJWT署名（RS256）。2026-11-24：一部の作業環境で cryptography の読み込みが
    pyo3 の PanicException で落ちたため、純Pythonの rsa ライブラリを先に使う（無ければ自動で入れる）。
    rsa が使えないときだけ cryptography を使う。鍵はメモリ上だけで扱う。"""
    try:
        import rsa
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "rsa"],
                       check=False, capture_output=True)
        try:
            import rsa
        except ImportError:
            rsa = None
    if rsa is not None:
        try:
            key = rsa.PrivateKey.load_pkcs1(private_key_pem.encode(), "PEM")
        except Exception:
            from rsa import pem as _pem  # PKCS#8（-----BEGIN PRIVATE KEY-----）を PKCS#1 に
            from pyasn1.codec.der import decoder
            der = _pem.load_pem(private_key_pem.encode(), "PRIVATE KEY")
            inner, _ = decoder.decode(der)
            key = rsa.PrivateKey.load_pkcs1(bytes(inner[2]), "DER")
        return rsa.sign(message, key, "SHA-256")
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    k = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    return k.sign(message, padding.PKCS1v15(), hashes.SHA256())
