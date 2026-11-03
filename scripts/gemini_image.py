"""Gemini画像APIの小さなラッパー。キーは環境変数 GEMINI_API_KEY からだけ読む。"""
import base64, io, json, os, sys, urllib.request
from PIL import Image

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3-pro-image"


def generate(prompt, images=(), model=DEFAULT_MODEL, aspect="16:9", size="2K"):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY が設定されていません")
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
    for p in res["candidates"][0]["content"]["parts"]:
        d = p.get("inlineData") or p.get("inline_data")
        if d:
            return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
    raise RuntimeError("画像が返りませんでした: " + json.dumps(res)[:500])
