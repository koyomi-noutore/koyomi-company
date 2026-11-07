"""サムネイル（1280×720、2MB未満）を作る。knowledge/thumbnail-title.md の型に沿い、実際の問題の絵を使う。
設定は plan.json の thumbnail：
  {"question": 使う問, "big_text": 大きな文字（10字以内）, "big_color": [r,g,b], "sub_text": 小さな文字,
   "badges": [[文字, [r,g,b]], ...], "circle_hint": true/false（違いの1つに丸を付けて「違いを探す動画」と一目でわかるようにする）}
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from episode_plan import plan

TW, TH = 1280, 720


def _font(fontp, size):
    return ImageFont.truetype(str(fontp), size)


def make(out_dir, fontp):
    cfg = plan()["thumbnail"]
    out = Path(out_dir)
    q = cfg["question"]
    a = Image.open(out / f"q{q}_a.png").convert("RGB")
    b = Image.open(out / f"q{q}_b.png").convert("RGB")
    Q = next(x for x in plan()["questions"] if x["q"] == q)
    x0, y0, x1, y1 = Q["content_box"]
    pw, ph = TW // 2, TH                      # 左右に並べる（動画の出題画面と同じ並べ方）
    # 8:9 の絵を 640×720 に収める：縦を合わせ、横は中央を使う
    def fit(im):
        c = im.crop((x0, y0, x1, y1))
        s = ph / c.height
        c = c.resize((round(c.width * s), ph), Image.LANCZOS)
        left = (c.width - pw) // 2
        return c.crop((left, 0, left + pw, ph)), s, left
    fa, s, left = fit(a)
    fb, _, _ = fit(b)
    im = Image.new("RGB", (TW, TH))
    im.paste(fa, (0, 0)); im.paste(fb, (pw, 0))
    d = ImageDraw.Draw(im)
    d.line((pw, 0, pw, TH), fill=(255, 255, 255), width=8)
    fp = fontp
    # 上の帯：大きな文字（白い縁取り）
    big = cfg["big_text"]
    assert len(big.replace(" ", "").replace("　", "")) <= 10, "大きな文字は10字以内（thumbnail-title.md）"
    band_h = 190
    ov = Image.new("RGBA", (TW, band_h), tuple(cfg.get("band_color", (25, 35, 70))) + (235,))
    im.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(im)
    # 大きな文字。highlight の部分だけ別の色（例：「3つ」を黄）。縁取りは黒
    f = _font(fp, cfg.get("big_size", 132))
    hl, hl_col = cfg.get("highlight", ""), tuple(cfg.get("highlight_color", (255, 214, 0)))
    parts = [(big[:big.index(hl)], None), (hl, hl_col), (big[big.index(hl) + len(hl):], None)] if hl and hl in big else [(big, None)]
    total = sum(d.textlength(t, font=f) for t, _ in parts)
    x = (TW - total) / 2
    for t, col in parts:
        if t:
            d.text((x, band_h // 2 + 4), t, font=f, fill=col or tuple(cfg.get("big_color", (255, 255, 255))), anchor="lm",
                   stroke_width=7, stroke_fill=(0, 0, 0))
            x += d.textlength(t, font=f)
    # 下の帯：小さな文字とバッジ
    y = TH - 120
    ov = Image.new("RGBA", (TW, 120), (59, 47, 37, 215))
    im.paste(ov, (0, y), ov)
    d = ImageDraw.Draw(im)
    x = 28
    for text, col in cfg.get("badges", []):
        f = _font(fp, 64)
        w = d.textlength(text, font=f)
        d.rounded_rectangle((x, y + 18, x + w + 40, y + 102), 20, fill=tuple(col))
        d.text((x + 20, y + 60), text, font=f, fill=(255, 255, 255), anchor="lm")
        x += w + 60
    if cfg.get("sub_text"):
        d.text((TW - 28, y + 60), cfg["sub_text"], font=_font(fp, 58), fill=(255, 240, 200), anchor="rm")
    # 違いの1つに丸（右の絵）
    if cfg.get("circle_hint"):
        dd = next(x for x in Q["diffs"] if x["id"] == cfg.get("circle_diff", Q.get("hint_diff") or 1))
        bx0, by0, bx1, by1 = dd.get("circle_b", dd.get("circle", dd["box"]))
        sx = lambda v: pw + (v - x0) * s - left
        sy = lambda v: (v - y0) * s
        r = 10
        d.ellipse((sx(bx0) - r, sy(by0) - r, sx(bx1) + r, sy(by1) + r), outline=(230, 30, 30), width=9)
    path = out / "thumbnail.jpg"
    for qual in (92, 85, 75):
        im.save(path, "JPEG", quality=qual, optimize=True)
        if path.stat().st_size < 2_000_000:
            break
    assert path.stat().st_size < 2_000_000, "サムネが2MB以上"
    return path
