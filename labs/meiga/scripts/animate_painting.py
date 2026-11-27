"""名画を「筆のタッチのまま」動かす試作（費用ゼロ・コードのみ）。

方法:
1. 絵の筆の向き（ストロークの方向）を構造テンソルで推定する。
2. 各場所を、その筆の向きに沿って数ピクセルだけ前後に揺らす（位相はなめらかなノイズ）。
   → 絵の具そのものが筆の流れに沿って脈打つ。新しい絵は描き足さないので画風が崩れない。
3. 明るい黄色の点（星・月）は光をゆっくり明滅させる。
4. 縦長（9:16）でゆっくり横に移動し、最初と最後に字幕を出す。
使い方: python3 animate_painting.py <入力画像> <出力mp4>
"""
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
FPS, SEC = 24, 10
N = FPS * SEC
OUT_W, OUT_H = 720, 1280

img = cv2.imread(src).astype(np.float32) / 255.0
H, W = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 1. 筆の向き（構造テンソル）
g = cv2.GaussianBlur(gray, (0, 0), 1.5)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
s = 6.0
jxx = cv2.GaussianBlur(gx * gx, (0, 0), s)
jyy = cv2.GaussianBlur(gy * gy, (0, 0), s)
jxy = cv2.GaussianBlur(gx * gy, (0, 0), s)
theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)  # 勾配の主方向
vx, vy = -np.sin(theta), np.cos(theta)  # それに直交＝筆の流れ
lam = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
coh = lam / (jxx + jyy + 1e-6)  # 向きのはっきり度（0〜1）
coh = cv2.GaussianBlur(coh, (0, 0), 3)

# 動きの大きさ：空を大きく、下の村は小さく
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
sky = np.clip((0.75 * H - yy) / (0.25 * H), 0.25, 1.0)
amp = 3.2 * sky * np.clip(coh * 1.4, 0.2, 1.0)

# なめらかな位相ノイズ
rng = np.random.default_rng(7)
noise = rng.random((H // 16 + 2, W // 16 + 2)).astype(np.float32)
noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_CUBIC)
noise = cv2.GaussianBlur(noise, (0, 0), 12)
noise = (noise - noise.min()) / (noise.max() - noise.min())
phase0 = noise * 4 * np.pi

# 3. 星・月（明るい黄色）を検出
hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
star = ((hsv[..., 2] > 200) & (hsv[..., 1] > 60) & (hsv[..., 0] > 15) & (hsv[..., 0] < 40)).astype(np.float32)
star *= (yy < 0.6 * H)
star = cv2.GaussianBlur(star, (0, 0), 5)
star_phase = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 20)
star_phase = (star_phase - star_phase.min()) / (np.ptp(star_phase) + 1e-6) * 2 * np.pi
glow_col = np.array([0.55, 0.95, 1.0], np.float32)  # BGR：やわらかい黄

# 4. 縦長の画面へ
scale = OUT_H / H
SW = int(W * scale)
font_b = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 46, index=0)
font_s = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 30, index=0)
for f in ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"]:
    pass

def caption(frame_bgr, t):
    im = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(im, "RGBA")
    def fade(a, b):
        return float(np.clip(min(t - a, b - t) / 0.6, 0, 1))
    a1 = fade(0.3, 4.5)
    if a1 > 0:
        d.rectangle([0, 120, OUT_W, 300], fill=(10, 15, 40, int(150 * a1)))
        d.text((OUT_W // 2, 175), "動き出す名画", font=font_s, fill=(240, 220, 150, int(255 * a1)), anchor="mm")
        d.text((OUT_W // 2, 240), "ゴッホ《星月夜》1889年", font=font_b, fill=(255, 255, 255, int(255 * a1)), anchor="mm")
    a2 = fade(6.0, 10.5)
    if a2 > 0:
        d.rectangle([0, 1000, OUT_W, 1130], fill=(10, 15, 40, int(150 * a2)))
        d.text((OUT_W // 2, 1065), "この空の“うねり”には、理由がある", font=font_s, fill=(255, 255, 255, int(255 * a2)), anchor="mm")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

vw = cv2.VideoWriter("/tmp/_raw.mp4", cv2.VideoWriter_fourcc(*"mp4v"), FPS, (OUT_W, OUT_H))
for i in range(N):
    t = i / FPS
    w = 2 * np.pi * t / 3.0  # 3秒で1往復
    d = amp * np.sin(phase0 + w)
    mx = (xx + d * vx).astype(np.float32)
    my = (yy + d * vy).astype(np.float32)
    fr = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    tw = 0.5 + 0.5 * np.sin(star_phase + 2 * np.pi * t / 2.2)
    gl = (star * tw * 0.18)[..., None] * glow_col
    fr = 1 - (1 - fr) * (1 - gl)  # スクリーン合成で白飛びを防ぐ
    fr = np.clip(fr, 0, 1)
    big = cv2.resize(fr, (SW, OUT_H), interpolation=cv2.INTER_CUBIC)
    # ゆっくり左→右へ（イーズ）
    p = 0.5 - 0.5 * np.cos(np.pi * t / SEC)
    x0 = int(p * (SW - OUT_W))
    crop = (np.clip(big[:, x0:x0 + OUT_W], 0, 1) * 255).astype(np.uint8)
    vw.write(caption(crop, t))
vw.release()
