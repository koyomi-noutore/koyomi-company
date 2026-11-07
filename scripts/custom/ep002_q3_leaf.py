"""第2回 第3問：描き直し（版2）で増えた落ち葉が字幕の場所（絵の下）に入ったので、葉だけを上へ移して貼る（画像APIは使わない）。
python3 ep002_q3_leaf.py <作業フォルダ>  →  <作業>/edit_3_leaf.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

SRC = (900, 1755, 1045, 1860)   # 版2で増えた葉のまわり（8:9の絵の座標）
DY = -150                        # 上へ動かす量（px）

w = Path(sys.argv[1])
a = Image.open(w / "q3_a.png").convert("RGB")
e = Image.open(w / "edit_3_2.png").convert("RGB")
A, E = np.asarray(a.crop(SRC)).astype(int), np.asarray(e.crop(SRC)).astype(int)
H = np.asarray(e.crop(SRC).convert("HSV")).astype(int)
leaf = ((H[..., 0] > 20) & (H[..., 0] < 50) & (H[..., 1] > 120)) | (H[..., 2] < 120)   # 葉の黄色と輪郭の線だけ（まわりの白いにじみは入れない）
m = ((np.abs(A - E).max(2) > 30) & leaf).astype(np.uint8) * 255
mask = Image.fromarray(m).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
out = a.copy()
out.paste(e.crop(SRC), (SRC[0], SRC[1] + DY), mask)
out.save(w / "edit_3_leaf.png")
