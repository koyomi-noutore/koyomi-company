"""第22回 第5問①「切り株のカップの持ち手が反対」を、画像APIを使わずにプログラムで作る（ファイル名は最初に小鳥で作った名残り）。
元の絵（q5_a.png）のカップの形のマスクを GrabCut で作り、カップ本体の中心 x=276 を軸にカップだけを左右反転して同じ場所に戻す。
元のカップの跡（持ち手があった所など）は、まわりの切り株と葉で埋める（OpenCV inpaint, Telea法）。
使い方: python3 scripts/custom/ep022_flip_sparrow.py <作業フォルダ>   → <作業>/edit_5_flip.png（opencv-python-headless が必要）"""
import sys
from pathlib import Path
import numpy as np, cv2
w = Path(sys.argv[1])
a = cv2.imread(str(w / "q5_a.png"))
AX = 276
X0, Y0, X1, Y1 = 100, 800, 460, 1060
c = a[Y0:Y1, X0:X1].copy()
m = np.zeros(c.shape[:2], np.uint8)
bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(c, m, (60, 30, 290, 200), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)   # (x, y, 幅, 高さ)：カップのまわり
fg = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
fg = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8) * 255
fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
fg = cv2.dilate(fg, np.ones((5, 5), np.uint8))
full = np.zeros(a.shape[:2], np.uint8); full[Y0:Y1, X0:X1] = fg
base = cv2.inpaint(a, cv2.dilate(full, np.ones((7, 7), np.uint8)), 7, cv2.INPAINT_TELEA)
out = base.copy()
H, W = full.shape
for x in range(X0, X1):
    sx = 2 * AX - x
    if 0 <= sx < W:
        col = full[:, sx] > 0
        out[col, x] = a[col, sx]
cv2.imwrite(str(w / "edit_5_flip.png"), out)
