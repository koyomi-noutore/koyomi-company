"""第24回：画像APIを使わず、プログラムで作る違い（元の絵 q{N}_a.png から）。
使い方：python3 scripts/custom/ep024_program.py <作業フォルダ>   → <作業>/edit_1_duck.png を書く
  第1問③ アヒルのおもちゃを左右反転する：アヒル（黄色と黄色の輪郭）の中心で切り出しを左右反転し、
  反転前と反転後のアヒルの形の和だけをぼかして貼る（範囲の外は元の絵と同じ。まわりの床・タイルの線は元のまま）。
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

work = Path(sys.argv[1])
A = Image.open(work / "q1_a.png").convert("RGB")
region = (1480, 975, 1800, 1270)
arr = np.asarray(A.crop(region)).astype(int)
R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
body = ((R > 200) & (G > 150) & (B < 140)) | ((R > 200) & (G > 90) & (G < 170) & (B < 90))     # 黄色い体・オレンジのくちばし
body = ndi.binary_opening(body, iterations=2)
lab, n = ndi.label(ndi.binary_closing(body, iterations=3))
big = lab == (1 + int(np.argmax(ndi.sum(body, lab, range(1, n + 1)))))
sil = ndi.binary_fill_holes(ndi.binary_dilation(big, iterations=9))     # 黒い輪郭線まで
ys, xs = np.nonzero(sil)
cx = (xs.min() + xs.max()) / 2
x0 = int(round(cx - 150)); x1 = int(round(cx + 150))                    # アヒルの中心を軸に反転する切り出し
x0, x1 = max(0, x0), min(arr.shape[1], x1)
w = min(int(cx) - x0, x1 - int(cx))
x0, x1 = int(cx) - w, int(cx) + w
crop = A.crop((region[0] + x0, region[1], region[0] + x1, region[3]))
flipped = crop.transpose(Image.FLIP_LEFT_RIGHT)
s = sil[:, x0:x1]
sf = s[:, ::-1]
import cv2
base = np.asarray(crop).copy()
full = (ndi.binary_dilation(ndi.binary_dilation(s, iterations=10), iterations=1)).astype(np.uint8) * 255                # 元のアヒル全体を消して、まわりの床だけで埋める（黄色を引き込まない）
hole = (ndi.binary_dilation(ndi.binary_dilation(s, iterations=10) & ~ndi.binary_erosion(sf, iterations=1), iterations=2)).astype(np.uint8) * 255          # そのうち、反転後のアヒルが覆わない所（くちばし・しっぽの跡）だけを使う
filled = cv2.inpaint(np.ascontiguousarray(base), full, 9, cv2.INPAINT_TELEA)
alpha = np.asarray(Image.fromarray((sf * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(float) / 255.0
out = np.where(hole[..., None] > 0, filled, base).astype(float)
out = out * (1 - alpha[..., None]) + np.asarray(flipped).astype(float) * alpha[..., None]
E1 = A.copy()
E1.paste(Image.fromarray(out.astype(np.uint8)), (region[0] + x0, region[1]))
E1.save(work / "edit_1_duck.png")
print("duck bbox", xs.min() + region[0], ys.min() + region[1], xs.max() + region[0], ys.max() + region[1])
