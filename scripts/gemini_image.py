"""Gemini画像APIの小さなラッパー。キーは環境変数 GEMINI_API_KEY からだけ読む。"""
import base64, io, json, os, sys, urllib.request
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from credentials import gemini_key

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3-pro-image"


USAGE_LOG = os.environ.get("KOYOMI_IMAGE_USAGE_LOG")  # 例：outputs/<回>/image_usage.jsonl（費用の記録用）


def _log_usage(model, size, usage):
    """1回の呼び出しごとに、モデル・サイズ・トークン数を記録する（キーは書かない）。"""
    if not USAGE_LOG:
        return
    import datetime
    rec = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "model": model, "size": size,
           "prompt_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount"),
           "total_tokens": usage.get("totalTokenCount")}
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def generate(prompt, images=(), model=DEFAULT_MODEL, aspect="16:9", size="2K"):
    key = gemini_key()
    parts = [{"text": prompt}]
    for im in images:
        buf = io.BytesIO(); im.convert("RGB").save(buf, "PNG")
        parts.append({"inline_data": {"mime_type": "image/png",
                                      "data": base64.b64encode(buf.getvalue()).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": aspect, "imageSize": size}}}
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    _log_usage(model, size, res.get("usageMetadata", {}))
    for p in res["candidates"][0]["content"]["parts"]:
        d = p.get("inlineData") or p.get("inline_data")
        if d:
            return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
    raise RuntimeError("画像が返りませんでした: " + json.dumps(res)[:500])
