"""第31回 第4問②「右のポットの口が反対向き」：ポットの形だけを左右反転して同じ場所に戻す（AIでは変わらなかったため）。
反転で見えるようになった元のポットの跡は、まわりの木目で埋める（OpenCV inpaint）。
使い方: python3 scripts/custom/ep031_flip_teapot.py <作業フォルダ> → <作業>/edit_4_2.png"""
import sys
from pathlib import Path
import numpy as np, cv2
w = Path(sys.argv[1])
a = cv2.imread(str(w / "q4_a.png"))
x0, y0, x1, y1 = 1380, 930, 1740, 1220
c = a[y0:y1, x0:x1].copy()
m = np.zeros(c.shape[:2], np.uint8)
bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(c, m, (30, 20, 320, 255), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
fg = np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
fg = cv2.morphologyEx((lab == i).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
Mw = cv2.dilate(fg, np.ones((33, 33), np.uint8))   # 跡を埋める範囲（白いふちも含める）
# ポットの輪郭の黒い線だけから外形を取る（白いふちを含めない）
dark = ((c.max(2) < 75) & (cv2.dilate(fg, np.ones((3, 3), np.uint8)) > 0)).astype(np.uint8) * 255
dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
cs, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
M = np.zeros_like(fg); cv2.drawContours(M, [max(cs, key=cv2.contourArea)], -1, 255, -1)
M = cv2.dilate(M, np.ones((3, 3), np.uint8))
ys, xs = np.nonzero(M); cx = (xs.min() + xs.max()) / 2.0   # 形の左右の中心で反転
W = c.shape[1]; shift = int(round(2 * cx - (W - 1)))
def flip(img):
    f = img[:, ::-1]
    return np.roll(f, shift, axis=1)
Mf = flip(M); Cf = flip(c)
hole = Mw.copy()
filled = cv2.inpaint(c, hole, 11, cv2.INPAINT_TELEA)
out = filled.copy()
mk = cv2.GaussianBlur(Mf, (5, 5), 0).astype(float)[..., None] / 255
out = (Cf * mk + out * (1 - mk)).astype(np.uint8)
e = a.copy(); e[y0:y1, x0:x1] = out
cv2.imwrite(str(w / "edit_4_2.png"), e)
