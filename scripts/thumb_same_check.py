"""サムネの左右が同じ絵か（違いゼロか）を確かめる（2026-11-24 CEO厳守ルール）。
使い方：python3 scripts/thumb_same_check.py <サムネ画像> [...]
上の帯と下の文字を除いた中央の帯（縦 25〜65%）で、左半分と右半分の差を比べる。差があれば「不合格」で終了コード1。
make_episode.py が thumbnail の直後と upload・retitle・short-upload の前に自動で呼ぶ（thumb_guard）。
ショート自身のサムネは0:00の画面で、絵を左右に並べたものではないので、この確認の対象外（長尺のサムネが合格でないとショートも上げない）。"""
import sys
from PIL import Image, ImageChops, ImageStat


def check(path, limit=4.0):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    y0, y1 = int(H * 0.25), int(H * 0.65)
    # 左の絵は x=0〜636、右の絵は x=644〜1280（thumb_band.py の並べ方。幅1280の比で合わせる）
    s = W / 1280
    L = im.crop((0, y0, int(636 * s), y1))
    R = im.crop((int(644 * s), y0, int(644 * s) + L.width, y1))
    d = sum(ImageStat.Stat(ImageChops.difference(L, R)).mean) / 3
    return d <= limit, round(d, 2)


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        ok, d = check(f)
        print(("合格 " if ok else "不合格（左右がちがう） ") + f + f"  差={d}")
        bad += not ok
    sys.exit(1 if bad else 0)
