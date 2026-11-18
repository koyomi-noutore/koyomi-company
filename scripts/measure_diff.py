"""違いの物の幅を、元の絵と描き直しの差から測る（object_w を手で書かないため。2026-11-18 監査のすすめ）。
使い方：python3 scripts/measure_diff.py <作業フォルダ/pictures> '[[問, "版", [x0,y0,x1,y1]], ...]'
出力：問・版・調べた範囲・[差のいちばん大きなかたまりの幅px, その範囲]・画面幅に対する%（ep_check の難易度の基準と同じ測り方）
描き直しの版は全体が少しずつ描き直されるので、弱い差（しきい値90未満）と細かい点は外して測る。"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

SCREEN_PCT_PER_PX = 960 / 1856 / 1920 * 100     # 絵（1856px）を画面の左半分（960px）に出したときの、1pxあたりの画面幅%


def width(pics, q, ver, b, thr=90):
    a = np.asarray(Image.open(Path(pics) / f"q{q}_a.png").convert("RGB")).astype(float)[b[1]:b[3], b[0]:b[2]]
    e = np.asarray(Image.open(Path(pics) / f"edit_{q}_{ver}.png").convert("RGB")).astype(float)[b[1]:b[3], b[0]:b[2]]
    m = ndimage.binary_opening(np.sqrt(((a - e) ** 2).sum(2)) > thr, iterations=3)
    lab, n = ndimage.label(ndimage.binary_closing(m, iterations=5))
    if n == 0:
        return None
    k = int(np.argmax(ndimage.sum(m, lab, range(1, n + 1)))) + 1
    xs = np.nonzero((lab == k).any(0))[0]; ys = np.nonzero((lab == k).any(1))[0]
    return int(xs.max() - xs.min() + 1), [int(b[0] + xs.min()), int(b[1] + ys.min()), int(b[0] + xs.max()), int(b[1] + ys.max())]


if __name__ == "__main__":
    for q, ver, b in json.loads(sys.argv[2]):
        r = width(sys.argv[1], q, ver, b)
        print(q, ver, b, r, round(r[0] * SCREEN_PCT_PER_PX, 2) if r else "")
