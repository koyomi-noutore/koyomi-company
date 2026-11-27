"""Vertex AI（画像生成・Veo）の共通部品。費用を labs/meiga/cost_log.md に自動で記録し、上限を超える前に止める。
認証：環境変数 VERTEX_SA_KEY_B64（サービスアカウントの鍵をbase64にしたもの）をメモリ上でだけ読む。ファイルには書かない。
"""
import os, json, base64, time, datetime, re
import requests
from google.oauth2 import service_account
import google.auth.transport.requests as gar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COST_LOG = os.path.join(ROOT, "cost_log.md")
BUDGET_JPY = 3000          # Ichiro承認（2026-11-27）：最初の試作の上限
USD_JPY = 150
PRICE = {                  # 2026-11 時点の調べ（USD）
    "gemini-3-pro-image": 0.134,        # 1K/2K 1枚
    "veo-3.1-fast-generate-001": 0.10,  # 720p・音あり 1秒
}
_info = json.loads(base64.b64decode(os.environ["VERTEX_SA_KEY_B64"]))
PROJECT = _info["project_id"]
_cred = service_account.Credentials.from_service_account_info(
    _info, scopes=["https://www.googleapis.com/auth/cloud-platform"])

def _h():
    if not _cred.valid:
        _cred.refresh(gar.Request())
    return {"Authorization": "Bearer " + _cred.token}

def spent_jpy():
    if not os.path.exists(COST_LOG):
        return 0
    return sum(int(m) for m in re.findall(r"\|\s*(\d+)円\s*\|\s*$", open(COST_LOG).read(), re.M))

def _check(usd):
    jpy = round(usd * USD_JPY)
    if spent_jpy() + jpy > BUDGET_JPY:
        raise SystemExit(f"予算の上限 {BUDGET_JPY}円 を超えるので止めます（使用済み {spent_jpy()}円、今回 {jpy}円）")
    return jpy

def _log(what, model, qty, jpy, note=""):
    new = not os.path.exists(COST_LOG)
    with open(COST_LOG, "a") as f:
        if new:
            f.write("# 名画試作の費用記録\n\n上限 3,000円（2026-11-27 Ichiro承認）。1ドル=150円で換算。単価は調べた値の見込みで、正式な金額はGoogle Cloudの請求で確認する。\n\n")
            f.write("| 日時 | 内容 | モデル | 量 | 金額 |\n|---|---|---|---|---|\n")
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
        f.write(f"| {now} | {what}{('（' + note + '）') if note else ''} | {model} | {qty} | {jpy}円 |\n")

def image(prompt, out_path, refs=(), aspect="9:16", what="画像"):
    """Gemini 3 Pro Image で1枚作る。refs は参考画像（画風の手本）のパス。"""
    m = "gemini-3-pro-image"; jpy = _check(PRICE[m])
    parts = [{"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(open(p, "rb").read()).decode()}} for p in refs]
    parts.append({"text": prompt})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}}
    url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{m}:generateContent"
    for wait in (20, 40, 80, 160, 0):  # 429（共有の枠が混んでいる）は待って再試行
        r = requests.post(url, headers=_h(), json=body, timeout=300)
        if r.status_code != 429 or not wait:
            break
        print("429: 待って再試行", wait, "秒"); time.sleep(wait)
    if r.status_code != 200:
        raise RuntimeError(f"image {r.status_code}: {r.text[:300]}")
    for c in r.json().get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if "inlineData" in p:
                open(out_path, "wb").write(base64.b64decode(p["inlineData"]["data"]))
                _log(what, m, "1枚", jpy)
                return out_path
    _log(what, m, "1枚", jpy, "画像が返らず")
    raise RuntimeError("画像が返らなかった: " + r.text[:300])

def video(prompt, first_frame, out_path, sec=8, aspect="9:16", audio=True, what="動画", last_frame=None):
    """Veo 3.1 Fast（720p）で、静止画を1コマ目にした動画を作る。"""
    m = "veo-3.1-fast-generate-001"; jpy = _check(PRICE[m] * sec)
    b64 = lambda p: base64.b64encode(open(p, "rb").read()).decode()
    mime = lambda p: "image/png" if p.endswith(".png") else "image/jpeg"
    inst = {"prompt": prompt, "image": {"bytesBase64Encoded": b64(first_frame), "mimeType": mime(first_frame)}}
    if last_frame:
        inst["lastFrame"] = {"bytesBase64Encoded": b64(last_frame), "mimeType": mime(last_frame)}
    body = {"instances": [inst], "parameters": {"durationSeconds": sec, "aspectRatio": aspect, "resolution": "720p",
            "generateAudio": audio, "sampleCount": 1, "personGeneration": "allow_adult"}}
    base = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/us-central1/publishers/google/models/{m}"
    r = requests.post(base + ":predictLongRunning", headers=_h(), json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"veo {r.status_code}: {r.text[:300]}")
    op = r.json()["name"]
    for _ in range(60):
        time.sleep(10)
        x = requests.post(base + ":fetchPredictOperation", headers=_h(), json={"operationName": op}, timeout=120).json()
        if x.get("done"):
            break
    if "error" in x:
        raise RuntimeError("veo error（失敗した生成は課金されない想定なので記録しない）: " + json.dumps(x["error"])[:300])
    vids = x.get("response", {}).get("videos", [])
    if not vids:
        _log(what, m, f"{sec}秒", jpy, "動画が返らず（安全フィルタなど）")
        raise RuntimeError("動画が返らなかった: " + json.dumps(x)[:300])
    open(out_path, "wb").write(base64.b64decode(vids[0]["bytesBase64Encoded"]))
    _log(what, m, f"{sec}秒", jpy)
    return out_path
