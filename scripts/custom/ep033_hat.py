"""第33回 第5問②「壁の毛糸の帽子が緑色の小さい帽子になる」をプログラムで作る（AIでは大きさが変わらず、緑が暗かったため）。
元の絵（q5_a.png）の帽子を縮め（約72%・上のふちの中心をとめたまま）、明るい緑にして、はみ出した元の帽子の跡は壁の色でうめる。
使い方: python3 scripts/custom/ep033_hat.py <作業フォルダ> → <作業>/edit_5_2.png"""
import sys
from pathlib import Path
import numpy as np, cv2
w = Path(sys.argv[1])
a = cv2.imread(str(w / "q5_a.png"))
x0, y0, x1, y1 = 1530, 660, 1800, 1020
c = a[y0:y1, x0:x1].copy()
b, g, r = [c[..., i].astype(int) for i in range(3)]
dark = ((c.max(2) < 120) & ((b > r + 8) | (g > r + 8))).astype(np.uint8) * 255
dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(dark)
i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
hat = (lab == i).astype(np.uint8) * 255
cs, _ = cv2.findContours(hat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
M = np.zeros_like(hat); cv2.drawContours(M, [max(cs, key=cv2.contourArea)], -1, 255, -1)
M = cv2.dilate(M, np.ones((5, 5), np.uint8))
ys, xs = np.nonzero(M); top = ys.min(); cx = (xs.min() + xs.max()) / 2.0
# 帽子の影（壁の上の灰色）も、帽子と同じ比で縮める
gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(float)
wall = np.percentile(gray[170:, :], 90)
sh = ((gray < wall - 10) & (np.arange(c.shape[0])[:, None] > 150)).astype(np.uint8) * 255
sh = cv2.morphologyEx(sh, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
sh = cv2.dilate(M, np.ones((9, 9), np.uint8)) | sh
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(sh)
j = lab2[int(np.nonzero(M)[0].mean()), int(np.nonzero(M)[1].mean())]
F = ((lab2 == j) * 255).astype(np.uint8)
F = cv2.morphologyEx(F, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
# 緑にする（色相を緑へ・彩度と明るさを上げる）
hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV).astype(float)
G = hsv.copy(); G[..., 0] = 58; G[..., 1] = np.clip(hsv[..., 1] * 0.8 + 45, 0, 255); G[..., 2] = np.clip(hsv[..., 2] * 1.35 + 40, 0, 255)
green = cv2.cvtColor(G.astype(np.uint8), cv2.COLOR_HSV2BGR)
# 元の帽子の跡を壁の色でうめる
fill = cv2.inpaint(c, cv2.dilate(F, np.ones((15, 15), np.uint8)), 9, cv2.INPAINT_TELEA)
C2 = c.copy(); C2[M > 0] = green[M > 0]
k = 0.72
H, W = c.shape[:2]
A = np.array([[k, 0, cx - k * cx], [0, k, top - k * top]], float)
gs = cv2.warpAffine(C2, A, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
ms = cv2.warpAffine(F, A, (W, H), flags=cv2.INTER_LINEAR)
ms = cv2.GaussianBlur(ms, (3, 3), 0).astype(float)[..., None] / 255
out = (gs * ms + fill * (1 - ms)).astype(np.uint8)
e = a.copy(); e[y0:y1, x0:x1] = out
cv2.imwrite(str(w / "edit_5_2.png"), e)
