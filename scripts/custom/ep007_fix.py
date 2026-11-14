"""第7回：プログラムで作る違い（画像APIは使わない）。
- 第5問：石灯籠の左上の、小さいだいだい色のもみじを1枚消す（無地の地面なので、まわりの地からうめる）→ edit_5_leaf.png
python3 ep007_fix.py <作業フォルダ>"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

w = Path(sys.argv[1])


def fill(A, mask, iters=250):
    B = A.copy()
    B[mask] = A[~mask].mean(0)
    for _ in range(iters):
        bl = np.asarray(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
        B[mask] = bl[mask]
    return B


im = Image.open(w / "q5_a.png").convert("RGB")
A = np.asarray(im).astype(float)
x0, y0, x1, y1 = 100, 1130, 215, 1230
C = A[y0:y1, x0:x1]
L = C.mean(2)
leaf = ((C[..., 0] - C[..., 2]) > 50) | (L < 120)                  # だいだい色の葉と、その黒い輪郭
leaf = ndimage.binary_dilation(leaf, iterations=3)
B = fill(C, leaf)
grain = np.random.default_rng(7).normal(0, 1.8, B.shape)
B[leaf] = np.clip(B[leaf] + grain[leaf], 0, 255)
A[y0:y1, x0:x1] = B
Image.fromarray(A.astype(np.uint8)).save(w / "edit_5_leaf.png")
