"""「ちがうのどーれだ？」絵版（2026-11-25）。1本につき画像API（Vertex）1枚。違う1つは、同じ絵の一部の「色」をプログラムで変えたもの（左右反転は使わない）。
使い方：python3 scripts/chigau_pic_shorts.py <出力フォルダ> <problem.json> ...   problem.json の kind は "pic"。
  src（元の絵）が ~/.cache/koyomi/chigau/<id>_src.png に無いときだけ画像APIを1回使う。
  recolor：{"hue":[下,上]（色相0-360）, "sat_min":, "val_min":, "to":（色相の移動量。度）, "region":[x0,y0,x1,y1]（元の絵の割合0-1。省略可）}
  chigau_shorts の台紙・流れ・声・音・こよみ先生・矢印をそのまま使う。"""
import functools, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import chigau_shorts as C
import text_shorts as T
import numpy as np
from PIL import Image

WORK = C.WORK


def _hsv(a):
    return np.array(Image.fromarray(a).convert("HSV")).astype(int)


def recolor_mask(a, rc):
    h, s, v = [x.astype(float) for x in np.moveaxis(_hsv(a), 2, 0)]
    h = h * 360 / 255
    lo, hi = rc["hue"]
    m = ((h >= lo) & (h <= hi)) if lo <= hi else ((h >= lo) | (h <= hi))
    m &= (s >= rc.get("sat_min", 80)) & (v >= rc.get("val_min", 60))
    if rc.get("region"):
        x0, y0, x1, y1 = rc["region"]; H_, W_ = m.shape
        r = np.zeros_like(m); r[int(y0 * H_):int(y1 * H_), int(x0 * W_):int(x1 * W_)] = True; m &= r
    return m


def recolor(a, rc):
    m = recolor_mask(a, rc)
    hsv = np.array(Image.fromarray(a).convert("HSV"))
    hsv[..., 0] = np.where(m, ((hsv[..., 0].astype(int) + int(rc["to"] * 255 / 360)) % 256), hsv[..., 0]).astype(np.uint8)
    if rc.get("sat_mul"):
        hsv[..., 1] = np.where(m, np.clip(hsv[..., 1] * rc["sat_mul"], 0, 255), hsv[..., 1]).astype(np.uint8)
    return np.array(Image.fromarray(hsv, "HSV").convert("RGB")), m


def make_pics(P):
    src = WORK / f"{P['id']}_src.png"
    if not src.exists():
        import gemini_image as G
        G.generate(P["prompt"], aspect="1:1", size="1K").save(src)
    a = np.array(Image.open(src).convert("RGB"))
    a[(a > 236).all(axis=2)] = 255
    o, m = recolor(a, P["recolor"])
    bb = Image.fromarray(255 - a.min(axis=2)).point(lambda v: 255 if v > 40 else 0).getbbox()
    out = []
    for arr in (a, o):
        im = Image.fromarray(arr).crop(bb)
        h = P["pic_h"]; out.append(im.resize((round(im.width * h / im.height), h), Image.LANCZOS))
    return out, m, bb


def load_problem(path):
    P = json.loads(Path(path).read_text(encoding="utf-8"))
    key = P["id"]
    T.set_season(P.get("season"), P.get("theme")) if (P.get("season") or P.get("theme")) and not T.SEASON_ARG else None
    pics = {}

    def frame(state, remain=None):
        if "p" not in pics:
            pics["p"] = make_pics(P)[0]
        pic, odd = pics["p"]
        im, d = C.base(P["what"], bg=(255, 255, 255))
        x0, y0, x1, y1 = C.INNER
        cols, rows = P["cols"], P["rows"]; cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
        for r in range(rows):
            for c in range(cols):
                is_odd = (r, c) == tuple(P["odd_at"]); p = odd if is_odd else pic
                cx, cy = x0 + cw * (c + .5), y0 + ch * (r + .5)
                im.paste(p, (int(cx - p.width / 2), int(cy - p.height / 2)))
                if is_odd and state:
                    C.circle(d, cx, cy, int(max(p.width, p.height) * 0.62))
        return im
    T.KINDS[key] = ({"think": P["think"], "veil": C.VEIL_TXT, "intro_lines": C.INTRO_LINES}, frame, 1)
    T.LINES[key] = {"intro": tuple(P["lines"]["intro"]), "ans": [tuple(x) for x in P["lines"]["ans"]]}
    T.PROBLEM_ID = key
    C.PIC_FRAMES = getattr(C, "PIC_FRAMES", {}); C.PIC_FRAMES[key] = (P, pics)
    return key


if __name__ == "__main__":
    T.take_season(sys.argv)
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    import time
    for f in sys.argv[2:]:
        k = load_problem(f); t = time.time(); sec = C.build(k, out)
        print(k, sec, "秒（作業", round(time.time() - t), "秒）", flush=True)
