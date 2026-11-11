"""かくし絵（試作）：物の輪郭線を、まわりの模様と同じ色・少し濃い線で、模様に重ねて描く（画像APIを使わない）。
knowledge/ng-list.md（2026-11-09）：物を普通の色・形のまま置かない。周りの模様・色・線に溶け込ませる。

使い方：python3 scripts/kakushie.py <元の絵> <設定json> <出力フォルダ>
設定 json：{"items": [{"name": "柿", "shape": "kaki", "center": [x, y], "size": px, "rot": 度}, ...],
           "levels": {"初級": {"alpha": 0.85, "width": 6, "darken": 0.55}, "上級": {"alpha": 0.5, "width": 4, "darken": 0.8}}}
  size は物の幅（元の絵のpx）。alpha は線の濃さ、width は線の太さ、darken は「まわりの線の色」をどれだけ暗くするか（小さいほど濃い）。
  dash は線を残す割合（1未満で線がところどころ切れ、模様に溶ける）、scale は大きさの倍率、rot_add は向きを交互に傾ける角度。
出力：<出力>/<段階>_puzzle.png（出題の絵）・<段階>_answer.png（答えの丸つき）・<段階>_screen.png（出題画面 1920×1080）・
      <段階>_answer_screen.png（答えの画面）・answers.json（物の位置と大きさ）
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 形（中心0・幅1にそろえた線の集まり。y は下向き）
def _ellipse(cx, cy, rx, ry, t0=0, t1=360, n=48):
    return [(cx + rx * math.cos(math.radians(t)), cy + ry * math.sin(math.radians(t))) for t in np.linspace(t0, t1, n)]


def shape_lines(kind):
    if kind == "kaki":        # 柿：少しつぶれた丸と、4まいのへた、軸
        L = [_ellipse(0, 0.08, 0.5, 0.42)]
        for a in (0, 90, 180, 270):
            r = math.radians(a + 45)
            tip = (0.26 * math.cos(r), -0.30 + 0.12 * math.sin(r))
            L.append([(0, -0.30), ((tip[0]) * 0.6 - 0.05, tip[1] - 0.04), tip, (tip[0] * 0.6 + 0.05, tip[1] + 0.04), (0, -0.30)])
        L.append([(0, -0.30), (0.02, -0.44)])
        return L
    if kind == "donguri":     # どんぐり：ぼうしと、とがった実
        cap = _ellipse(0, -0.12, 0.42, 0.22, 180, 360) + [(0.42, -0.12), (-0.42, -0.12)]
        body = [(-0.36, -0.10)] + _ellipse(0, -0.10, 0.36, 0.55, 180, 0, 30)[::-1][1:] + [(0, 0.5)]
        body = [(-0.36, -0.10), (-0.34, 0.12), (-0.22, 0.34), (0, 0.5), (0.22, 0.34), (0.34, 0.12), (0.36, -0.10)]
        hatch = [[(-0.3 + 0.15 * i, -0.30), (-0.22 + 0.15 * i, -0.14)] for i in range(5)]
        return [cap, body, [(0, -0.34), (0.02, -0.46)]] + hatch
    if kind == "momiji":      # もみじ：5つの葉先（上が長い）と、ふち・葉脈・軸
        lobes = [(-90, 0.50), (-38, 0.44), (-142, 0.44), (18, 0.34), (162, 0.34)]
        lobes.sort(key=lambda t: t[0])
        pts = []
        for k, (a, r) in enumerate(lobes):
            ra = math.radians(a)
            for da, rr in ((-14, 0.22), (-6, r * 0.8), (0, r), (6, r * 0.8), (14, 0.22)):
                pts.append(((rr) * math.cos(ra + math.radians(da)), rr * math.sin(ra + math.radians(da)) + 0.06))
        pts.append(pts[0])
        veins = [[(0, 0.06), (r * 0.85 * math.cos(math.radians(a)), r * 0.85 * math.sin(math.radians(a)) + 0.06)] for a, r in lobes]
        return [pts, [(0, 0.12), (0.02, 0.5)]] + veins
    if kind == "kinoko":      # きのこ：かさと、え
        cap = _ellipse(0, 0.0, 0.5, 0.42, 180, 360) + [(0.5, 0.0), (-0.5, 0.0)]
        stem = [(-0.16, 0.0), (-0.18, 0.45), (0.18, 0.45), (0.16, 0.0)]
        dots = [_ellipse(-0.2, -0.18, 0.07, 0.05), _ellipse(0.15, -0.24, 0.06, 0.05)]
        return [cap, stem] + dots
    if kind == "kuri":        # 栗：上がとがった丸と、下のおしり
        body = [(0, -0.48), (0.18, -0.34), (0.42, -0.02), (0.46, 0.22), (0.3, 0.42), (0, 0.46), (-0.3, 0.42), (-0.46, 0.22), (-0.42, -0.02), (-0.18, -0.34), (0, -0.48)]
        bottom = [(-0.4, 0.2), (-0.15, 0.27), (0.15, 0.27), (0.4, 0.2)]
        return [body, bottom]
    raise ValueError(kind)


def transform(lines, center, size, rot, wobble_seed=0):
    rng = np.random.default_rng(wobble_seed)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for ln in lines:
        pts = []
        # 線を細かく分けて、少しだけゆらす（手描きの模様に見えるように）
        for (x0, y0), (x1, y1) in zip(ln[:-1], ln[1:]):
            for t in np.linspace(0, 1, 6, endpoint=False):
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                x += rng.normal(0, 0.008); y += rng.normal(0, 0.008)
                pts.append((center[0] + size * (x * c - y * s), center[1] + size * (x * s + y * c)))
        pts.append((center[0] + size * (ln[-1][0] * c - ln[-1][1] * s), center[1] + size * (ln[-1][0] * s + ln[-1][1] * c)))
        out.append(pts)
    return out


def line_color(img, center, size, darken):
    """まわりの模様の線の色：物のまわりの暗いほうの画素の中央値を、少し暗くする。"""
    x0, y0 = int(center[0] - size), int(center[1] - size)
    blk = np.asarray(img.crop((x0, y0, x0 + 2 * size, y0 + 2 * size))).reshape(-1, 3).astype(float)
    L = blk.mean(1)
    dark = blk[L <= np.percentile(L, 25)]
    return tuple(int(v) for v in np.median(dark, 0) * darken)


def render(img, items, lv):
    base = img.convert("RGB")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, it in enumerate(items):
        col = line_color(base, it["center"], it["size"], lv["darken"])
        a = int(255 * lv["alpha"])
        rng = np.random.default_rng(100 + k)
        for pts in transform(shape_lines(it["shape"]), it["center"], it["size"] * lv.get("scale", 1.0), it.get("rot", 0) + lv.get("rot_add", 0) * (1 if k % 2 else -1), k):
            if lv.get("dash"):     # 線をところどころ切る（模様の線に見えるように）。dash＝線を残す割合
                for q0, q1 in zip(pts[:-1], pts[1:]):
                    if rng.random() < lv["dash"]:
                        d.line([q0, q1], fill=col + (a,), width=lv["width"])
            else:
                d.line(pts, fill=col + (a,), width=lv["width"], joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(lv.get("blur", 0.7)))
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def answer(img, items):
    im = img.copy()
    d = ImageDraw.Draw(im)
    for i, it in enumerate(items):
        cx, cy = it["center"]; r = it["size"] * 0.65
        d.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), outline=(255, 255, 255), width=16)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(220, 30, 30), width=10)
        bx, by = cx + r * 0.75, cy - r * 0.75
        d.ellipse((bx - 34, by - 34, bx + 34, by + 34), fill=(220, 30, 30), outline=(255, 255, 255), width=4)
    return im


def screen(pic, items, fontp, title, show_answer=False):
    """出題画面：左に絵（960×1080）、右に「かくれているもの」の一覧（物の名前と形の見本）。"""
    W, H = 1920, 1080
    sc = Image.new("RGB", (W, H), (246, 236, 216))
    p = pic.resize((960, 1080), Image.LANCZOS)
    sc.paste(p, (0, 0))
    d = ImageDraw.Draw(sc)
    f = lambda s: ImageFont.truetype(str(fontp), s)
    d.text((1440, 70), title, font=f(64), fill=(59, 47, 37), anchor="mm")
    d.text((1440, 140), "かくれているもの 5つ", font=f(46), fill=(180, 70, 40), anchor="mm")
    k = 960 / pic.width
    for i, it in enumerate(items):
        y = 250 + i * 160
        icon = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
        di = ImageDraw.Draw(icon)
        for pts in transform(shape_lines(it["shape"]), (65, 65), 110, 0, 99):
            di.line(pts, fill=(59, 47, 37, 255), width=5, joint="curve")
        sc.paste(icon, (1080, y - 65), icon)
        d.text((1240, y), f"{i + 1}. {it['name']}", font=f(60), fill=(59, 47, 37), anchor="lm")
        if show_answer:
            d.ellipse((1600, y - 30, 1660, y + 30), fill=(220, 30, 30))
            d.text((1630, y), "○", font=f(40), fill=(255, 255, 255), anchor="mm")
    return sc


def main(src, cfgp, out, fontp):
    cfg = json.loads(Path(cfgp).read_text(encoding="utf-8"))
    img = Image.open(src).convert("RGB")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    items = cfg["items"]
    for name, lv in cfg["levels"].items():
        pz = render(img, items, lv)
        pz.save(out / f"{name}_puzzle.png")
        an = answer(pz, items)
        an.save(out / f"{name}_answer.png")
        screen(pz, items, fontp, f"かくし絵（{name}）").save(out / f"{name}_screen.png")
        screen(an, items, fontp, f"答え（{name}）", True).save(out / f"{name}_answer_screen.png")
    (out / "answers.json").write_text(json.dumps({"image_size": img.size, "items": [dict(it, width_pct_of_picture=round(it["size"] / img.width * 100, 1)) for it in items],
                                                  "levels": cfg["levels"]}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:5])
