"""サムネの型（試作）。scripts/thumb_band.py と同じ見た目（帯・書体・赤の強調・下の段のグラデーション・左右とも元の絵＝違いゼロ）。
違いは、絵の切り出しが「主役（人物＋物）を大きく」になっていること。使い方：python3 make_thumbs.py（この フォルダで）"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from thumb_band import neutral, F, K, WT, Y, R

HERE = Path(__file__).resolve().parent
CROP_Y0 = {"X": 230, "Y": 150}       # 縦の切り出しの上端（元の絵 1856×2088 のピクセル）。幅は絵いっぱい


def pic(style, sat=1.15):
    a = Image.open(HERE / f"{style}_a.png").convert("RGB")
    top = 170; ph = 720 - top; pw = 636
    W = a.size[0]; h = round(W * ph / pw); y0 = CROP_Y0[style]
    im = neutral(a).crop((0, y0, W, y0 + h)).resize((pw, ph), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Contrast(im).enhance(1.15)
    return im.filter(ImageFilter.UnsharpMask(2, 130, 2)), top


def make(out, style, band, top_txt, bottom):
    p, top = pic(style)
    T = Image.new("RGB", (1280, 720), WT); T.paste(p, (0, top)); T.paste(p, (644, top))   # 左右とも同じ絵（違いゼロ）
    d = ImageDraw.Draw(T); d.rectangle([636, top, 644, 720], fill=(25, 25, 25)); d.rectangle([0, 0, 1280, top], fill=band)
    emph, rest = top_txt
    parts = [(emph, R, 10, WT), (rest, WT if band == K else K, 2 if band == K else 0, K)]
    f = ImageFont.truetype(F, 150)
    tw = sum(d.textlength(s, font=f) for s, *_ in parts)
    if tw > 1240:
        f = ImageFont.truetype(F, int(150 * 1240 / tw)); tw = sum(d.textlength(s, font=f) for s, *_ in parts)
    x = (1280 - tw) / 2
    for s, fill, sw, sc in parts:
        d.text((x, top / 2 + 4), s, font=f, fill=fill, anchor="lm", stroke_width=sw, stroke_fill=sc); x += d.textlength(s, font=f)
    g = Image.new("L", (1280, 220), 0); gd = ImageDraw.Draw(g)
    for i in range(220):
        gd.line([(0, i), (1280, i)], fill=int(170 * i / 220))
    T.paste(Image.new("RGB", (1280, 220), K), (0, 500), g)
    f2 = ImageFont.truetype(F, 158)
    bw = sum(d.textlength(s, font=f2) for s in bottom)
    if bw > 1080:
        f2 = ImageFont.truetype(F, int(158 * 1080 / bw)); bw = sum(d.textlength(s, font=f2) for s in bottom)
    x = (1280 - bw) / 2 - 40 if bw > 900 else (1280 - bw) / 2      # 右下の動画の長さを避けて少し左へ
    for i, s in enumerate(bottom):
        c = Y if (len(bottom) > 1 and i == 0) else WT
        d.text((x, 618), s, font=f2, fill=c, anchor="lm", stroke_width=14, stroke_fill=K); x += d.textlength(s, font=f2)
    T.save(out, quality=92)


for st in "XY":
    make(HERE / f"thumb_{st}_1.jpg", st, Y, ("60代70代", " 全部見つけられる？"), ("間違いさがし", " 全10問"))
    make(HERE / f"thumb_{st}_2.jpg", st, K, ("こよみ先生", "の間違いさがし"), ("見つけたら天才！", " 全10問"))
