"""第38回：q4_b・q10_b の消し跡（監査 K-2・K-3）を雪の色で塗る。pictures の後に実行する（冪等）。
使い方：python3 scripts/custom/ep038_erase.py outputs/2026-11-28_038"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ep = Path(sys.argv[1])
FIX = {4: [(497, 1915, 545, 2035)], 10: [(195, 1770, 330, 1830), (330, 1855, 370, 1895)]}


def bg_color(im, box):
    x0, y0, x1, y1 = box
    px = [im.getpixel((x, y)) for x in range(x0 - 25, x1 + 25, 6) for y in (y0 - 20, y1 + 20) if 0 <= y < im.height]
    px = [p for p in px if sum(p) > 700]
    return tuple(sorted(c)[len(c) // 2] for c in zip(*px)) if px else (252, 252, 250)


for q, boxes in FIX.items():
    im = Image.open(ep / f"q{q}_b.png").convert("RGB")
    for box in boxes:
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rectangle(box, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(4))
        im.paste(Image.new("RGB", im.size, bg_color(im, box)), (0, 0), m)
    im.save(ep / f"q{q}_b.png")
