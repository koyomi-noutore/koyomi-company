"""第5問③「右のハトが反対を向く」を、画像APIを使わずにプログラムで作る（AIの描き直しを3回試してできなかったため。事業部長の指示）。
元の絵（q5_a.png）から、ハトの形に沿ったマスクを色で作り、ハトだけを左右反転して、同じ外接枠（同じ場所）に戻す。
反転で見えるようになった元のハトの跡は、まわりの地面で埋める（OpenCV の inpaint、Telea法）。足もとの影は元の絵のまま。
使い方: python3 scripts/ep001_flip_pigeon.py <作業フォルダ>   → <作業>/edit_5_flip.png を書く（範囲の外は元の絵と同じ）
"""
import sys
from pathlib import Path
import numpy as np, cv2

REGION = (880, 1440, 1260, 1730)   # ハトのまわり（元の絵のピクセル）
# 石の道のふちの線（元の絵のピクセル）。(1043,1558) から、ハトの背中の後ろを通って左下 (963,1640) へ続いていた
EDGE_LINE = [(1048, 1548), (1036, 1564), (1018, 1584), (995, 1608), (963, 1640)]
EDGE_BGR = (55, 75, 100)           # ふちの線の色（元の線の中くらいの濃さに合わせた）
EDGE_ALPHA = 0.0                   # 線を描き足すと棒のように目立ったので、描かずに、石と地面の境目だけで見せる
STONE_FROM = (0, -75)              # 石の側を埋めるときに写す元（上へ75px）
GROUND_FROM = (80, 0)              # 黄色い地面の側を埋めるときに写す元（右へ80px）


def pigeon_mask(c, rect=(78, 82, 210, 175), legs=(120, 200, 200, 265)):
    """ハトの形のマスク。ハトを囲む枠（x, y, 幅, 高さ）から GrabCut で前景を取り、穴を埋めて、白いふちどりまで少し広げる。"""
    m = np.zeros(c.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(c, m, rect, bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    fg = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    one = cv2.morphologyEx((lab == i).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    cs, _ = cv2.findContours(one, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs = [max(cs, key=cv2.contourArea)]
    full = np.zeros(fg.shape, np.uint8); cv2.drawContours(full, cs, -1, 255, -1)
    full = cv2.dilate(full, np.ones((7, 7), np.uint8))
    # 細い足は GrabCut で取れないので、足のあたり（legs）の黒い線を少し太らせて足す（足の中のピンクまで入る）
    lx0, ly0, lx1, ly1 = legs
    sub = c[ly0:ly1, lx0:lx1].astype(int).sum(-1) < 400
    leg = np.zeros(fg.shape, np.uint8); leg[ly0:ly1, lx0:lx1] = sub * 255
    leg = cv2.dilate(leg, np.ones((9, 9), np.uint8))
    full = cv2.bitwise_or(full, leg)
    ys, xs = np.nonzero(full)
    return full, (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


def main(work):
    w = Path(work)
    a = cv2.imread(str(w / "q5_a.png"))
    x0, y0, x1, y1 = REGION
    c = a[y0:y1, x0:x1].copy()
    m, st = pigeon_mask(c)
    bx, bw = int(st[0]), int(st[2])
    # 外接枠の中心で左右反転（ハトの外接枠は元と同じ）
    M = np.float32([[-1, 0, 2 * bx + bw - 1], [0, 1, 0]])
    fc = cv2.warpAffine(c, M, (c.shape[1], c.shape[0]))
    fm = cv2.warpAffine(m, M, (c.shape[1], c.shape[0]))
    hole = cv2.bitwise_and(m, cv2.bitwise_not(cv2.erode(fm, np.ones((5, 5), np.uint8))))  # 反転したハトで隠れない、元のハトの跡
    bg = cv2.inpaint(c, m, 4, cv2.INPAINT_TELEA)              # まず、ぼんやり埋める
    # 跡は、石の道のふちの線（元の絵でハトの背中の後ろに消えていた線）の左が石、右が黄色い地面。
    # それぞれ、近くの同じ地面を写して埋め、最後にふちの線を描き足す（のっぺりしたにじみを残さないため）
    H, Wd = c.shape[:2]
    side = np.zeros((H, Wd), np.uint8)                         # 255＝線の左（石の側）
    p, q = EDGE_LINE[0], EDGE_LINE[-1]
    poly = np.array([[0, 0], [p[0] - x0, 0], [p[0] - x0, p[1] - y0], [q[0] - x0, q[1] - y0], [q[0] - x0, H], [0, H]], np.int32)
    cv2.fillPoly(side, [poly], 255)
    for sel, (dx, dy) in ((side, STONE_FROM), (cv2.bitwise_not(side), GROUND_FROM)):
        mk = cv2.bitwise_and(hole, sel)
        src = np.roll(np.roll(c, -dy, axis=0), -dx, axis=1)    # (dx, dy) だけずらした所の地面
        a_ = (cv2.GaussianBlur(cv2.dilate(mk, np.ones((7, 7), np.uint8)), (0, 0), 3).astype(np.float32) / 255)[..., None]
        bg = (src * a_ + bg * (1 - a_)).astype(np.uint8)
    pts = np.array([(x - x0, y - y0) for x, y in EDGE_LINE], np.int32)
    ln = np.zeros((H, Wd), np.uint8)
    cv2.polylines(ln, [pts], False, 255, 3, cv2.LINE_AA)
    ln = cv2.GaussianBlur(ln, (0, 0), 0.8)
    la = (ln.astype(np.float32) / 255 * EDGE_ALPHA)[..., None]  # 線の濃さ（0＝描かない）
    bg = (np.array(EDGE_BGR, np.float32) * la + bg * (1 - la)).astype(np.uint8)
    alpha = cv2.GaussianBlur(fm, (0, 0), 1.5).astype(np.float32)[..., None] / 255
    out = (fc * alpha + bg * (1 - alpha)).astype(np.uint8)
    ed = a.copy(); ed[y0:y1, x0:x1] = out
    cv2.imwrite(str(w / "edit_5_flip.png"), ed)
    cv2.imwrite(str(w / "pigeon_mask.png"), m)
    print("pigeon bbox in region:", [int(v) for v in st[:4]])


if __name__ == "__main__":
    main(sys.argv[1])
