"""サムネの標準（thumbnail-title.md「サムネの標準（2026-11-23）」）で、テストと比較の3案を作る。
見本 outputs/prototypes/thumb_band_001/proto.py と同じ作り方（CEOが選んだ CEO_黒帯.png・CEO_黄帯.png）。

  A＝黒帯×上①×下①、B＝黄帯×上①×下①
  C＝黄帯で、奇数の回は上②×下①、偶数の回は上①×下②（回の番号はフォルダ名の末尾）

使い方：python3 scripts/thumb_band.py <回のフォルダ> <問> <上①の強調語> <上①の残り> <C用：上②の強調語,上②の残り  または  下②（例：難問！,間違いさがし）> [出力フォルダ名=ab]
  例：python3 scripts/thumb_band.py outputs/2026-11-22_017 1 70代 の認知症予防 10分で,頭の体操
"""
import json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat

F = str(Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf")
K, WT, Y, R = (0, 0, 0), (255, 255, 255), (255, 214, 0), (230, 30, 30)
BADGE_W, BADGE_H = 0.25, 0.20   # 右下の角（動画の長さの表示）。ここに文字を置かない（2026-11-28 CEO決定）


def neutral(im, target=1.45):
    """赤みを抑える（赤÷青が target を超えたら、赤を下げ青を上げて半分ずつ寄せる）。"""
    r, g, b = ImageStat.Stat(im.resize((100, 100))).mean
    ratio = r / max(b, 1)
    if ratio <= target:
        return im
    k = (target / ratio) ** 0.5
    R_, G_, B_ = im.split()
    return Image.merge("RGB", (R_.point(lambda v: min(255, int(v * k))), G_, B_.point(lambda v: min(255, int(v / k)))))


def pics(ep, q, sat=1.15):
    a = Image.open(ep / f"q{q}_a.png").convert("RGB"); b = Image.open(ep / f"q{q}_b.png").convert("RGB")
    ans = json.loads((ep / "answers.json").read_text(encoding="utf-8"))
    A = next(x for x in ans["questions"] if x["q"] == q); W, H = a.size
    bx = [x["box_px"] for x in A["answers"]]
    x0 = min(v[0] for v in bx); y0 = min(v[1] for v in bx); x1 = max(v[2] for v in bx); y1 = max(v[3] for v in bx)
    top = 170; ph = 720 - top; pw = 636; r = pw / ph
    w = max(x1 - x0, (y1 - y0) * r) * 1.3; h = w / r
    if w > W: w, h = W, W / r
    if h > H: h, w = H, H * r
    cx = min(max((x0 + x1) / 2, w / 2), W - w / 2); cy = min(max((y0 + y1) / 2 + h * 0.08, h / 2), H - h / 2)
    box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))

    def prep(im):
        im = neutral(im).crop(box).resize((pw, ph), Image.LANCZOS)
        im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Contrast(im).enhance(1.15)
        return im.filter(ImageFilter.UnsharpMask(2, 130, 2))
    return prep(a), prep(a), top   # 2026-11-23 CEO決定：サムネは左右とも元の絵（違いゼロ）。サムネで答えが見つからないように


def make(out, ep, q, band, top_txt, bottom=("間違いさがし",)):
    pa, pb, top = pics(ep, q)
    T = Image.new("RGB", (1280, 720), WT); T.paste(pa, (0, top)); T.paste(pb, (644, top))
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
    # 下の段：右下の角（右25%×下20%＝動画の長さの表示）に文字を置かない（2026-11-28 CEO決定。scripts/thumb_badge_check.py で確かめる）。
    # 文字は左から 75% の幅の中に、縁取りを含めて収める。
    BL, BR = 30, int(1280 * (1 - BADGE_W)) - 30
    f2 = ImageFont.truetype(F, 158)
    bw = sum(d.textlength(s, font=f2) for s in bottom)
    if bw > BR - BL - 28:
        f2 = ImageFont.truetype(F, int(158 * (BR - BL - 28) / bw)); bw = sum(d.textlength(s, font=f2) for s in bottom)
    x = BL + 14 + (BR - BL - 28 - bw) / 2
    boxes = []
    for i, s in enumerate(bottom):
        c = Y if (len(bottom) > 1 and i == 0) else WT
        d.text((x, 618), s, font=f2, fill=c, anchor="lm", stroke_width=14, stroke_fill=K)
        bb = d.textbbox((x, 618), s, font=f2, anchor="lm", stroke_width=14); boxes.append([int(v) for v in bb])
        x += d.textlength(s, font=f2)
    T.save(out, quality=92)
    Path(str(out) + ".text.json").write_text(json.dumps({"size": [1280, 720], "boxes": boxes}, ensure_ascii=False))   # 文字の位置の記録（thumb_badge_check.py が読む）


# サムネの型1（2026-11-28 CEO決定・標準）：上の黄帯「60代70代 全部見つけられる？」（60代70代を赤）、下の段は「間違いさがし」だけ。
# チャンネル名・キャラ名は入れない。右下の角に文字を置かない。
TYPE1_TOP = ("60代70代", " 全部見つけられる？")
TYPE1_BOTTOM = ("間違いさがし",)


def make_type1(out, ep, q):
    """型1のサムネを1枚作る（左右とも元の絵）。作ったあと thumb_same_check と thumb_badge_check で確かめるのは呼んだ側（make_episode.thumb_guard）。"""
    make(out, ep, q, Y, TYPE1_TOP, TYPE1_BOTTOM)


def main(E, q, emph, rest, c_arg, sub="ab"):
    ep = Path(E); n = int(re.search(r"_(\d+)$", ep.name).group(1)); q = int(q)
    out = ep / sub; out.mkdir(exist_ok=True)
    c = tuple(c_arg.split(","))
    top1 = (emph, rest)
    make(out / "thumb_A.jpg", ep, q, K, top1)
    make(out / "thumb_B.jpg", ep, q, Y, top1)
    if n % 2:   # 奇数の回：上の文字を比べる
        make(out / "thumb_C.jpg", ep, q, Y, c); cdesc = ("".join(c), "間違いさがし", "上の文字（BとC）")
    else:       # 偶数の回：下の段を比べる
        make(out / "thumb_C.jpg", ep, q, Y, top1, c); cdesc = (emph + rest, "".join(c), "下の段（BとC）")
    rows = [("A", "黒帯", emph + rest, "間違いさがし", "帯の色（AとB）"), ("B", "黄帯", emph + rest, "間違いさがし", "帯の色（AとB）"),
            ("C", "黄帯") + cdesc]
    md = [f"# 第{n}回 サムネ テストと比較の3案（サムネの標準 2026-11-23）", "",
          f"scripts/thumb_band.py で作成。絵は第{q}問（左右とも元の絵＝違いゼロ）、赤みを抑え、色の強め1.15倍、書体 Noto Sans JP Black。"
          f"強調語は赤＋白の縁取り。第{n}回は{'奇数' if n % 2 else '偶数'}の回なので、Cは{'上の文字' if n % 2 else '下の段'}を変える。", "",
          "| 案 | 帯 | 上の文字 | 下の段 | 比べるもの |", "|---|---|---|---|---|"] + [f"| {a} | {b} | {c_} | {d} | {e} |" for a, b, c_, d, e in rows]
    (out / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
