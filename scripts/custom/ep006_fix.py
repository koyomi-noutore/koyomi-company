"""第6回 第5問：元の絵の茶筒に、文字のような筆の線（「茶」の字に見える）が描かれていた（社則：絵に文字を入れない）。
ラベルの白い地の中の暗い線（文字）を、まわりの白でうめる。ラベルのふちと、筒の筆のむらは残す（画像APIは使わない）。元の絵（q5_a）を直接直す。
python3 ep006_fix.py <作業フォルダ>"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

w = Path(sys.argv[1])
p = w / "q5_a.png"
im = Image.open(p).convert("RGB")
A = np.asarray(im).astype(float)
def fill(A, mask, iters=200):
    """mask の所を、まわりの色から少しずつぼかしてうめる。"""
    B = A.copy()
    B[mask] = A[~mask].mean(0)
    for _ in range(iters):
        bl = np.asarray(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
        B[mask] = bl[mask]
    return B


# ラベルの内側（黒いふち x137–140・209–217 の間、上のふち y≈1698 の下から、湯のみのふち y≈1762 の上まで）を、紙の色でうめる
x0, y0, x1, y1 = 142, 1703, 208, 1760
C = A[y0:y1, x0:x1]
L = C.mean(2)
paper = np.median(C[L > 215], 0)
rng = np.random.default_rng(6)
noise = rng.normal(0, 2.0, C.shape)
noise = np.asarray(Image.fromarray(np.clip(128 + noise * 4, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))).astype(float) - 128
A[y0:y1, x0:x1] = np.clip(paper + noise / 4, 0, 255)
Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).save(p)
