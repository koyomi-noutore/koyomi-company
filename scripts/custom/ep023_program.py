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

# --- 差し戻し後（D-1・D-2）。元の絵（neutralize 前の作業フォルダの q{N}_a.png）から作る
# 第2問③ 手前のおわん（木）を青くする：木の色（橙〜茶）の画素だけ色相を青へ。汁の具（白・緑・橙の小さな物）は彩度・色相で外す
A2 = Image.open(work / "q2_a.png").convert("RGB")
bb = (780, 1185, 1000, 1350)
c = A2.crop(bb)
hsv = np.asarray(c.convert("HSV")).astype(float)
H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
m = (H > 15) & (H < 45) & (S > 0.42) & (V > 0.3)
lab, n = ndi.label(ndi.binary_opening(m, iterations=1))
big = lab == (1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1)))))
al = Image.fromarray((ndi.binary_dilation(big, iterations=1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
ch, cs, cv = c.convert("HSV").split()
rec = Image.merge("HSV", (Image.new("L", c.size, int(215 / 360 * 255)), cs.point(lambda x: int(x * 0.85)), cv)).convert("RGB")
E3 = A2.copy()
E3.paste(Image.composite(rec, c, al), bb[:2])
E3.save(work / "edit_2_bowl.png")

# 第4問③ 青い風呂敷の結び目を左右反転する（結び目の青い布と輪郭線だけを反転。背景は周りの色で埋める）
import cv2
A4 = Image.open(work / "q4_a.png").convert("RGB")
kb = (480, 1650, 700, 1736)
cr = np.asarray(A4.crop(kb)).astype(int)
M = ((cr[..., 2] - cr[..., 0] > 18) | (cr.sum(-1) < 270))
M = ndi.binary_closing(M, iterations=2)
lab_k, n_k = ndi.label(M)
M = lab_k == (1 + int(np.argmax(ndi.sum(M, lab_k, range(1, n_k + 1)))))   # 結び目につながる一番大きなかたまりだけ
cx = (kb[2] - kb[0]) / 2
ys, xs = np.nonzero(M)
mid = (xs.min() + xs.max()) / 2          # 結び目の左右の真ん中
Mf = np.zeros_like(M)
shift = int(round(2 * mid - (M.shape[1] - 1)))
fl = M[:, ::-1]
Mf = np.roll(fl, shift, axis=1)
src = np.roll(np.asarray(A4.crop(kb))[:, ::-1], shift, axis=1)
big = np.asarray(A4).copy()
sub = big[kb[1]:kb[3], kb[0]:kb[2]]
hole = (ndi.binary_dilation(M, iterations=3)).astype(np.uint8) * 255
filled = cv2.inpaint(np.ascontiguousarray(sub), hole, 7, cv2.INPAINT_TELEA)
alpha = ndi.binary_dilation(Mf, iterations=1).astype(float)
alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
keep_orig_bottom = np.ones(M.shape, bool); keep_orig_bottom[-6:, :] = False   # 下端は元の絵のまま（布の面につなぐ）
use_fill = ndi.binary_dilation(M, iterations=3) & keep_orig_bottom
out = sub.copy()
out[use_fill] = filled[use_fill]
out = (out * (1 - alpha[..., None]) + src * alpha[..., None]).astype(np.uint8)
out[~keep_orig_bottom] = sub[~keep_orig_bottom]
big[kb[1]:kb[3], kb[0]:kb[2]] = out
Image.fromarray(big).save(work / "edit_4_knot.png")
