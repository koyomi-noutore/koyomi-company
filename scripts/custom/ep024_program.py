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
union = ndi.binary_dilation(s | sf, iterations=3)
alpha = Image.fromarray((union * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5))
out = Image.composite(flipped, crop, alpha)
E1 = A.copy()
E1.paste(out, (region[0] + x0, region[1]))
E1.save(work / "edit_1_duck.png")
print("duck bbox", xs.min() + region[0], ys.min() + region[1], xs.max() + region[0], ys.max() + region[1])
