"""Gemini画像APIの小さなラッパー。キーは環境変数 GEMINI_API_KEY からだけ読む。"""
import base64, io, json, os, sys, urllib.request
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from credentials import gemini_key

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3-pro-image"


USAGE_LOG = os.environ.get("KOYOMI_IMAGE_USAGE_LOG")  # 例：outputs/<回>/image_usage.jsonl（費用の記録用）


def _log_usage(model, size, usage, batch=False, key=None):
    """1回の呼び出しごとに、モデル・サイズ・トークン数を記録する（キーは書かない）。バッチは batch: true（約半額）。"""
    if not USAGE_LOG:
        return
    import datetime
    rec = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "model": model, "size": size,
           "prompt_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount"),
           "total_tokens": usage.get("totalTokenCount")}
    if batch:
        rec.update(batch=True, key=key)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _request(prompt, images, aspect, size, fmt="PNG"):
    parts = [{"text": prompt}]
    for im in images:
        buf = io.BytesIO()
        if fmt == "JPEG":
            im.convert("RGB").save(buf, "JPEG", quality=95)
        else:
            im.convert("RGB").save(buf, "PNG")
        parts.append({"inline_data": {"mime_type": f"image/{fmt.lower()}",
                                      "data": base64.b64encode(buf.getvalue()).decode()}})
    return {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": aspect, "imageSize": size}}}


def _image_of(res):
    for p in res["candidates"][0]["content"]["parts"]:
        d = p.get("inlineData") or p.get("inline_data")
        if d:
            return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
    raise RuntimeError("画像が返りませんでした: " + json.dumps(res)[:500])


def _call(method, url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": gemini_key()})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


BATCH_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchGenerateContent"
ROOT = "https://generativelanguage.googleapis.com/v1beta/"


def generate_batch(jobs, model=DEFAULT_MODEL, poll=30, max_wait=6 * 3600, name="koyomi"):
    """急がない生成をまとめてバッチ（約半額）で頼む。jobs = {key: {"prompt", "images", "aspect", "size"}}。
    結果が出るまで待ち、{key: Image} を返す（失敗した key は入らない）。入力の絵は容量を抑えるため JPEG（品質95）で送る。"""
    import time
    reqs = [{"request": _request(j["prompt"], j.get("images", ()), j.get("aspect", "16:9"), j.get("size", "2K"), "JPEG"),
             "metadata": {"key": str(k)}} for k, j in jobs.items()]
    op = _call("POST", BATCH_API.format(model=model),
               {"batch": {"display_name": name, "input_config": {"requests": {"requests": reqs}}}})
    bname = op["name"]
    print(f"[gemini] バッチ {bname} を送った（{len(reqs)}件）", flush=True)
    t0 = time.time()
    while True:
        st = _call("GET", ROOT + bname)
        state = st.get("metadata", {}).get("state") or st.get("state")
        if st.get("done") or state in ("BATCH_STATE_SUCCEEDED", "BATCH_STATE_FAILED", "BATCH_STATE_CANCELLED", "BATCH_STATE_EXPIRED"):
            break
        if time.time() - t0 > max_wait:
            raise TimeoutError(f"バッチ {bname} が {max_wait} 秒で終わらない（state={state}）。あとで同じ名前を取りにいける")
        time.sleep(poll)
    if state not in (None, "BATCH_STATE_SUCCEEDED") and not st.get("response"):
        raise RuntimeError(f"バッチ {bname} が失敗：{state} {json.dumps(st.get('error', {}))[:300]}")
    resp = st.get("response") or st.get("metadata", {}).get("output") or {}
    inl = resp.get("inlinedResponses", {})
    items = inl.get("inlinedResponses", inl) if isinstance(inl, dict) else inl
    jobs = {str(k): j for k, j in jobs.items()}
    keys = list(jobs)
    out = {}
    for i, it in enumerate(items):
        k = (it.get("metadata") or {}).get("key", keys[i] if i < len(keys) else str(i))
        if "response" not in it:
            print(f"[gemini] バッチの {k} は失敗：{json.dumps(it.get('error', {}))[:200]}", flush=True)
            continue
        _log_usage(model, jobs.get(k, {}).get("size", "2K"), it["response"].get("usageMetadata", {}), batch=True, key=k)
        try:
            out[k] = _image_of(it["response"])
        except RuntimeError as e:
            print(f"[gemini] バッチの {k}：{e}", flush=True)
    return out


def generate(prompt, images=(), model=DEFAULT_MODEL, aspect="16:9", size="2K"):
    key = gemini_key()
    body = _request(prompt, images, aspect, size)
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    _log_usage(model, size, res.get("usageMetadata", {}))
    return _image_of(res)
