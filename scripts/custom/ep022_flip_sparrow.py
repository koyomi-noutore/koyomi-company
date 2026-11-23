"""第22回 第5問①「小鳥の向きが反対」を、画像APIを使わずにプログラムで作る（AIの描き直しは小鳥を別の杭へ動かしたため）。
元の絵（q5_a.png）から小鳥の形のマスクを作り（空の色との差）、杭の中心 x=276 を軸に小鳥だけを左右反転して同じ場所に戻す。
元の小鳥の跡は、その行の空の色（左右の外側の中央値）で埋める。杭の上に立ったまま向きだけ変わる。
使い方: python3 scripts/custom/ep022_flip_sparrow.py <作業フォルダ>   → <作業>/edit_5_flip.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
w = Path(sys.argv[1])
a = np.asarray(Image.open(w / "q5_a.png").convert("RGB")).astype(int)
AX = 276
x0, x1, y0, y1 = 121, 431, 55, 199
reg = a[y0:y1, x0:x1]
ref = np.median(np.concatenate([a[y0:y1, 90:118], a[y0:y1, 440:470]], axis=1), axis=1)   # 行ごとの空の色
m = np.abs(reg - ref[:, None, :]).sum(axis=2) > 45
lab, n = ndi.label(m)
sizes = ndi.sum(m, lab, range(1, n + 1))
m = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 150])
m = ndi.binary_dilation(m, iterations=3)
full = np.zeros(a.shape[:2], bool); full[y0:y1, x0:x1] = m
out = a.copy()
fill = full.copy(); pass
sky = np.broadcast_to(np.concatenate([ref, ref[-1:]])[: y1 - y0][:, None, :], (y1 - y0, x1 - x0, 3))
sub = out[y0:y1, x0:x1]; sub[fill[y0:y1, x0:x1]] = sky[fill[y0:y1, x0:x1]]
for x in range(x0, x1):
    sx = 2 * AX - x
    col = full[y0:y1, sx]
    out[y0:y1, x][col] = a[y0:y1, sx][col]
Image.fromarray(out.astype(np.uint8)).save(w / "edit_5_flip.png")
