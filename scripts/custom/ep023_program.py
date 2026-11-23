"""第23回：画像APIを使わず、プログラムで作る違い2つ（元の絵 q{N}_a.png から）。
使い方：python3 scripts/custom/ep023_program.py <作業フォルダ>   → <作業>/edit_1_stool.png と <作業>/edit_2_flip.png を書く
  第1問③ 腰かけ（木）を青い色にする：木の色（橙〜茶・彩度高め）の一番大きなかたまりだけを色相だけ青へ回す（輪郭線・明るさはそのまま）
  第2問① 右のクーラーボックスを左右反転する（持ち手が反対側）：クーラーボックスを囲む四角を左右反転して同じ場所に戻す（範囲の外は元の絵と同じ）
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

work = Path(sys.argv[1])

# --- 第1問③ 腰かけを青く
A = Image.open(work / "q1_a.png").convert("RGB")
box = (1440, 940, 1800, 1270)
hsv = np.asarray(A.crop(box).convert("HSV")).astype(float)
H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
m = (H > 10) & (H < 50) & (S > 0.38) & (V > 0.4)
lab, n = ndi.label(ndi.binary_closing(m, iterations=3))
big = lab == (1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1)))))
big = ndi.binary_fill_holes(ndi.binary_closing(big, iterations=2))
# 腰かけの脚の中（線の内側）の木の色だけを対象にするため、元のマスク ∩ 大きなかたまりの近く
near = ndi.binary_dilation(big, iterations=3)
sel = m & near
alpha = Image.fromarray((ndi.binary_dilation(sel, iterations=1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
c = A.crop(box).convert("HSV")
ch, cs, cv = c.split()
blue = Image.new("L", c.size, int(215 / 360 * 255))
cs2 = cs.point(lambda x: int(min(255, x * 0.85)))
rec = Image.merge("HSV", (blue, cs2, cv)).convert("RGB")
out = A.crop(box)
out = Image.composite(rec, out, alpha)
E1 = A.copy()
E1.paste(out, box[:2])
E1.save(work / "edit_1_stool.png")

# --- 第2問① クーラーボックスの左右反転（箱の形だけを反転して同じ場所へ。まわりの地面は元の絵のまま）
A2 = Image.open(work / "q2_a.png").convert("RGB")
fb = (1430, 1020, 1800, 1390)
crop = A2.crop(fb)
arr = np.asarray(crop).astype(int)
white = (arr.min(-1) > 150) & ((arr.max(-1) - arr.min(-1)) < 22)   # 白〜灰色の箱のからだ（ベージュの地面は彩度があるので入らない）
dark = arr.sum(-1) < 230                      # 黒い輪郭線
body = ndi.binary_closing(white, iterations=4)
lab, n = ndi.label(body)
big = lab == (1 + int(np.argmax(ndi.sum(body, lab, range(1, n + 1)))))
sil = ndi.binary_fill_holes(ndi.binary_dilation(big, iterations=13))   # 輪郭線・持ち手・足もとの影まで広げる
flipped = crop.transpose(Image.FLIP_LEFT_RIGHT)
sil_f = sil[:, ::-1]
union = ndi.binary_dilation(sil | sil_f, iterations=4)
alpha = Image.fromarray((union * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
out = Image.composite(flipped, crop, alpha)
E2 = A2.copy()
E2.paste(out, fb[:2])
E2.save(work / "edit_2_flip.png")
