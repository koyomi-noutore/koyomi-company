"""第5回：AIの描き直しで消した物（第4問の飾りの三角・第5問の柿）のうすい輪郭が残ったので、
元の絵で物があった所のうち、描き直しの絵で明るい（地の）所を、まわりの地からなだらかにうめる。濃い線（ひも・枝）と残る柿は変えない。
python3 ep005_clean.py <作業フォルダ>  →  <作業>/edit_4_2c.png, edit_5_1c.png（画像APIは使わない）"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

JOBS = {(4, "2"): (70, 755, 205, 905)}

w = Path(sys.argv[1])
for (q, v), (x0, y0, x1, y1) in JOBS.items():
    a = np.asarray(Image.open(w / f"q{q}_a.png").convert("RGB").crop((x0, y0, x1, y1))).astype(float)
    ed_im = Image.open(w / f"edit_{q}_{v}.png").convert("RGB")
    e = np.asarray(ed_im.crop((x0, y0, x1, y1))).astype(float)
    La, Le = a.mean(2), e.mean(2)
    obj = ndimage.binary_dilation(np.abs(a - e).max(2) > 18, iterations=4)          # 元の物があった所（と、そのにじみ）
    keep = ndimage.binary_dilation((Le < 150) | ((e[..., 0] - e[..., 2]) > 70), iterations=3)   # 残すもの：濃い線・柿の色
    fill = obj & ~keep
    B = e.copy()
    B[fill] = e[~obj].mean(0) if (~obj).any() else 240
    for _ in range(300):
        bl = np.asarray(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
        B[fill] = bl[fill]
    noise = e - np.asarray(Image.fromarray(e.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(float)
    B[fill] = np.clip(B[fill] + np.clip(noise[fill], -2, 2), 0, 255)
    ed_im.paste(Image.fromarray(B.astype(np.uint8)), (x0, y0))
    ed_im.save(w / f"edit_{q}_{v}c.png")


# 第5問：いちばん下の柿を（へたごと）元の絵から消す。上の枝は残す。柿の実の所だけを、上と下の空の色で列ごとにつなぐ
R5 = (1622, 258, 1735, 364)
a_im = Image.open(w / "q5_a.png").convert("RGB")
A = np.asarray(a_im.crop(R5)).astype(float)
fruit = ((A[..., 0] - A[..., 2]) > 45) | (A.mean(2) < 120)
fruit[:10] = False                                  # いちばん上の10px（枝）は物に数えない
lab, n = ndimage.label(fruit)
big = max(range(1, n + 1), key=lambda i: (lab == i).sum())
fruit = ndimage.binary_dilation(ndimage.binary_fill_holes(lab == big), iterations=4)
B = A.copy()
for x in range(A.shape[1]):
    ys = np.nonzero(fruit[:, x])[0]
    if len(ys) == 0:
        continue
    y0, y1 = max(ys.min() - 1, 0), min(ys.max() + 1, A.shape[0] - 1)
    def sky(rows):                                  # その高さの、近くの列の空の色（枝・輪郭の暗い画素は使わない）
        blk = A[rows[0]:rows[1], max(0, x - 20):x + 21].reshape(-1, 3)
        ok = blk[(blk.mean(1) > 200) & ((blk[:, 0] - blk[:, 2]) < 20)]
        return np.median(ok, 0) if len(ok) else blk.mean(0)
    top, bot = sky((max(y0 - 4, 0), y0 + 1)), sky((y1, min(y1 + 4, A.shape[0])))
    t = ((np.arange(y0, y1 + 1) - y0) / max(1, y1 - y0))[:, None]
    B[y0:y1 + 1, x] = top * (1 - t) + bot * t
B = np.asarray(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0))).astype(float)
sm = np.asarray(Image.fromarray(B.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
B[fruit] = sm[fruit]
out = a_im.copy(); out.paste(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)), R5[:2])
out.save(w / "edit_5_1c.png")
