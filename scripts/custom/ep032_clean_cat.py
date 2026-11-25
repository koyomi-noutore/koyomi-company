"""第32回 第1問③「ねこがいない」：ねこを消した後に残る薄いかげ（舗道の上）を、範囲だけ強いメディアンでならす。
使い方: python3 scripts/custom/ep032_clean_cat.py <回のフォルダ> → <回>/q1_b.png の範囲 [150,1880,480,2050] だけを書き換える（compose のあとに1回）。"""
import sys
import cv2
import numpy as np
from pathlib import Path
ep = Path(sys.argv[1])
im = cv2.imread(str(ep / "q1_b.png"))
x0, y0, x1, y1 = 150, 1880, 480, 2050
r = im[y0:y1, x0:x1].copy()
m = cv2.medianBlur(r, 61)
w = np.zeros(r.shape[:2], np.float32); w[15:-15, 15:-15] = 1; w = cv2.GaussianBlur(w, (0, 0), 12)[..., None]
im[y0:y1, x0:x1] = (m * w + r * (1 - w)).astype(np.uint8)
cv2.imwrite(str(ep / "q1_b.png"), im)
