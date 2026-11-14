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
orig = w / "q5_a_orig.png"
if not orig.exists():
    Image.open(p).save(orig)
im = Image.open(orig).convert("RGB")
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




# 第3問③：七輪の通風口の取っ手を消す（監査の差し戻し1：左右反対では見分けられない）。無地の扉なので、扉の色でうめる → edit_3_noh.png
a3 = Image.open(w / "q3_a.png").convert("RGB")
A3 = np.asarray(a3).astype(float)
x0, y0, x1, y1 = 966, 1655, 1090, 1728
C = A3[y0:y1, x0:x1]
L = C.mean(2)
door = np.median(C[(L > np.percentile(L, 10)) & (L < np.percentile(L, 60))], 0)
handle = np.abs(L - door.mean()) > 28                                     # 扉の色と違う所（取っ手と、その黒い線）
handle = ndimage.binary_dilation(handle, iterations=3)
handle = ndimage.binary_dilation(np.abs(L - door.mean()) > 28, iterations=2)
rng3 = np.random.default_rng(9)
grain = C - np.asarray(Image.fromarray(C.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(float)
gstd = grain[~handle].std(0)
for yy in range(C.shape[0]):                       # 行ごとに、取っ手の左右の扉の色をつないでうめる
    xs = np.nonzero(handle[yy])[0]
    if len(xs) == 0:
        continue
    l, r = max(xs.min() - 1, 0), min(xs.max() + 1, C.shape[1] - 1)
    left = C[yy, max(l - 4, 0):l + 1].mean(0); right = C[yy, r:r + 5].mean(0)
    t = np.linspace(0, 1, r - l + 1)[:, None]
    seg = left * (1 - t) + right * t + rng3.normal(0, 1, (r - l + 1, 3)) * gstd
    C[yy, l:r + 1] = np.where(handle[yy, l:r + 1, None], seg, C[yy, l:r + 1])
bl = np.asarray(Image.fromarray(np.clip(C, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(float)
C = np.where(handle[..., None], bl + rng3.normal(0, 1, C.shape) * gstd * 0.8, C)      # 行のすじをならして、扉のざらつきを足す
A3[y0:y1, x0:x1] = C
Image.fromarray(np.clip(A3, 0, 255).astype(np.uint8)).save(w / "edit_3_noh.png")


# 第4問②：干したさんまを消した所に、空の輪のひもが残った（2026-11-14 CEO指摘：消し残りの切れ端）。輪を、左右の空の色で行ごとにうめる → edit_4_1c.png
e4 = Image.open(w / "edit_4_1.png").convert("RGB")
E4 = np.asarray(e4).astype(float)
x0, x1, y0, y1 = 664, 786, 816, 945
base = np.zeros((y1 - y0, x1 - x0, 3))
for yy in range(y0, y1):                       # 行ごとに、左右の空の色をつなぐ（空のグラデーション）
    def sky(xa, xb):
        px = E4[yy, xa:xb]
        ok = px[(px.mean(1) > 90) & (px[:, 2] > px[:, 0] + 45)]       # 青い空だけ（線・さおの白を除く）
        return np.median(ok, 0) if len(ok) else np.array([150., 200., 230.])
    lft, rgt = sky(x0 - 24, x0), sky(x1, x1 + 24)
    t = np.linspace(0, 1, x1 - x0)[:, None]
    base[yy - y0] = lft * (1 - t) + rgt * t
base = np.asarray(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
# 水彩のむら：すぐ下の空から切り出した模様を足す（監査の差し戻し2：平らな四角に見える）
patch = E4[y1 + 5:y1 + 5 + (y1 - y0), x0:x1].copy()        # すぐ下の、さんまを消した後の空（同じ列）の模様
tex = patch - np.asarray(Image.fromarray(patch.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(float)
fillp = base + tex
yy_, xx_ = np.mgrid[0:y1 - y0, 0:x1 - x0]
edge = np.minimum.reduce([xx_, x1 - x0 - 1 - xx_, yy_, y1 - y0 - 1 - yy_]).astype(float)
wgt = np.clip(edge / 10.0, 0, 1)[..., None]           # ふち10pxはなだらかにまぜる
E4[y0:y1, x0:x1] = E4[y0:y1, x0:x1] * (1 - wgt) + fillp * wgt
Image.fromarray(np.clip(E4, 0, 255).astype(np.uint8)).save(w / "edit_4_1c.png")


# 第4問①：灯台の新しい屋根の上に残った、とんがりの先の点を空の色でうめる → edit_4_2c.png
e42 = Image.open(w / "edit_4_2.png").convert("RGB")
E42 = np.asarray(e42).astype(float)
bx0, by0, bx1, by1 = 140, 255, 182, 312
C = E42[by0:by1, bx0:bx1]
L = C.mean(2)
cap = ndimage.binary_dilation(L < 120, iterations=3)         # 屋根の輪郭（残す）
dot = (L < np.median(L) - 6) & ~cap
E42[by0:by1, bx0:bx1] = fill(C, ndimage.binary_dilation(dot, iterations=3) & ~cap, 200)
Image.fromarray(np.clip(E42, 0, 255).astype(np.uint8)).save(w / "edit_4_2c.png")
