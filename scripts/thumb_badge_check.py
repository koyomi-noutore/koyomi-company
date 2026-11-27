"""サムネの右下の角（動画の長さの表示が重なる所）に文字が入っていないかを確かめる（2026-11-28 CEO決定）。
使い方：python3 scripts/thumb_badge_check.py <サムネ画像> [...]
  角＝横の右25%×縦の下20%（1280×720 なら x≥960・y≥576）。
  1) 作るときの記録（<画像>.text.json の文字の箱。scripts/thumb_band.py が書く）があれば、箱が角に1画素でもかかれば不合格。
  2) 記録の有無にかかわらず画像も見る：角の中で「白・黄・赤の文字の色」で、すぐ近く（4画素以内）に黒い縁取りがある画素を数え、
     LIMIT を超えたら不合格（文字の縁取りの形。絵の雪や線だけでは、ほとんど0になる）。
不合格が1枚でもあれば終了コード1。make_episode.py の thumb_guard（サムネを作った直後・アップロードの前）と
youtube_upload.upload（長尺のサムネを付けるとき）、text_long.py のサムネ作成で、thumb_same_check.py と一緒に呼ぶ。"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

BADGE_W, BADGE_H = 0.25, 0.20
LIMIT = 150      # 文字の画素の数の上限（1280×720 に直した値）


def corner(W=1280, H=720):
    return int(W * (1 - BADGE_W)), int(H * (1 - BADGE_H)), W, H


def text_pixels(im):
    a = np.asarray(im.convert("RGB").resize((1280, 720))).astype(int)
    x0, y0, x1, y1 = corner()
    c = a[y0:y1, x0:x1]
    black = c.max(axis=2) < 25
    near = ndimage.binary_dilation(black, iterations=4)
    white = c.min(axis=2) > 235
    yellow = (c[..., 0] > 230) & (c[..., 1] > 190) & (c[..., 2] < 60)
    red = (c[..., 0] > 200) & (c[..., 1] < 70) & (c[..., 2] < 70)
    return int(((white | yellow | red) & near & ~black).sum())


def check(path):
    path = Path(path)
    im = Image.open(path)
    W, H = im.size
    why = []
    rec = Path(str(path) + ".text.json")
    if rec.exists():
        r = json.loads(rec.read_text(encoding="utf-8"))
        sw, sh = r.get("size", [W, H])
        x0, y0, x1, y1 = corner(sw, sh)
        for b in r.get("boxes", []):
            if b[2] > x0 and b[3] > y0:
                why.append(f"記録の文字の箱 {b} が右下の角（x≥{x0}・y≥{y0}）にかかる")
    n = text_pixels(im)
    if n > LIMIT:
        why.append(f"右下の角に文字らしい画素が {n} 個（上限 {LIMIT}）")
    return not why, n, why


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        ok, n, why = check(f)
        print(("合格 " if ok else "不合格（右下の角に文字） ") + f + f"  文字の画素={n}" + ("" if ok else "  " + "／".join(why)))
        bad += not ok
    sys.exit(1 if bad else 0)
