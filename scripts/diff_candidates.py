"""描き直しの版から、変わった所を自動で探して一覧画像にする（違いを選ぶための下見。目で見るのは1枚だけ）。
使い方：python3 scripts/diff_candidates.py <作業フォルダ/pictures> <出力.jpg> <版> [問 ...]
各候補に「問#番号 x0,y0,x1,y1 w=変わった所の幅px」を書く。box と object_w の目安にする（object_w は物そのものの幅を目で確かめて決める）。
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

FONT = Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf"


def candidates(a, e, min_area=800, top=6):
    d = ndimage.uniform_filter(np.sqrt(((a - e) ** 2).sum(2)), 9)
    lab, n = ndimage.label(ndimage.binary_closing(d > 40, iterations=6))
    objs = [(s, (lab[s] == i + 1).sum()) for i, s in enumerate(ndimage.find_objects(lab))]
    objs = sorted([o for o in objs if o[1] > min_area], key=lambda o: -o[1])[:top]
    return [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s, _ in objs]


def main(pics, out, ver, qs):
    pics = Path(pics)
    F = ImageFont.truetype(str(FONT), 22)
    tiles = []
    for q in qs:
        A = Image.open(pics / f"q{q}_a.png").convert("RGB")
        E = Image.open(pics / f"edit_{q}_{ver}.png").convert("RGB")
        for k, (x0, y0, x1, y1) in enumerate(candidates(np.asarray(A).astype(float), np.asarray(E).astype(float))):
            pad = 40
            b = (max(0, x0 - pad), max(0, y0 - pad), min(A.width, x1 + pad), min(A.height, y1 + pad))
            ca, ce = A.crop(b), E.crop(b)
            sc = 200 / max(ca.size)
            sz = (max(1, int(ca.width * sc)), max(1, int(ca.height * sc)))
            t = Image.new("RGB", (410, 230), "white")
            t.paste(ca.resize(sz), (0, 28)); t.paste(ce.resize(sz), (208, 28))
            ImageDraw.Draw(t).text((2, 0), f"{q}#{k} {x0},{y0},{x1},{y1} w={x1 - x0}", font=F, fill="black")
            tiles.append(t)
            print(q, k, (x0, y0, x1, y1))
    cols = 5
    rows = max(1, (len(tiles) + cols - 1) // cols)
    S = Image.new("RGB", (410 * cols, 230 * rows), "gray")
    for i, t in enumerate(tiles):
        S.paste(t, ((i % cols) * 410, (i // cols) * 230))
    S.save(out, quality=80)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4:]] or [1, 2, 3, 4, 5])
