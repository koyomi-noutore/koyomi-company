"""名画の試作を、設定（パターン）ごとにまとめて作る。

1本の流れ：
  フック（名画そのもの＋ナレーション）→ 飛び込み効果 → 切り替え（白／黒／まばたき）
  → 絵の中の世界（その名画のタッチのまま）＋ナレーション
音声：Open JTalk（無料・オフライン。試作専用）。
使い方: python3 -I scripts/proto.py  （VARIANTS を全部書き出す）
"""
import os, subprocess, wave
import numpy as np
import cv2
import pyopenjtalk
_remap = cv2.remap
def _r(src, mx, my, *a, **k):
    return _remap(src, np.asarray(mx, np.float32), np.asarray(my, np.float32), *a, **k)
cv2.remap = _r
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "batch1")
TMP = os.path.join(ROOT, "work")
os.makedirs(OUT, exist_ok=True)
FPS, OW, OH, SR = 24, 720, 1280, 48000
FONT = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
F_TITLE = ImageFont.truetype(FONT, 44)
F_SUB = ImageFont.truetype(FONT, 34)
F_SMALL = ImageFont.truetype(FONT, 26)
BG = (18, 16, 20)

PAINTINGS = {
    "starry": dict(file="starry_night.jpg", title="ゴッホ《星月夜》", year="1889年"),
    "wave": dict(file="wave.jpg", title="葛飾北斎《神奈川沖浪裏》", year="1831年ごろ"),
    "scream": dict(file="the_scream.jpg", title="ムンク《叫び》", year="1893年"),
}

# ---------- 絵の読み込みと「筆の流れ」 ----------
_cache = {}
def load(key, frame=False):
    if (key, frame) in _cache:
        return _cache[(key, frame)]
    img = cv2.imread(os.path.join(ROOT, "src", PAINTINGS[key]["file"])).astype(np.float32) / 255
    if frame:  # 金の額縁と壁を足す
        h, w = img.shape[:2]
        b = int(0.07 * max(h, w)); m = int(0.35 * max(h, w))
        canvas = np.ones((h + 2 * (b + m), w + 2 * (b + m), 3), np.float32) * (np.array(BG[::-1]) / 255)
        y0, x0 = m, m
        fr = np.zeros((h + 2 * b, w + 2 * b, 3), np.float32)
        yy, xx = np.mgrid[0:h + 2 * b, 0:w + 2 * b]
        edge = np.minimum.reduce([yy, xx, h + 2 * b - 1 - yy, w + 2 * b - 1 - xx]).astype(np.float32) / b
        shade = 0.55 + 0.45 * np.cos(edge * np.pi * 2.0) ** 2
        fr[:] = np.stack([0.25 * shade, 0.62 * shade, 0.82 * shade], -1)  # BGR 金
        fr[b:b + h, b:b + w] = img
        canvas[y0:y0 + h + 2 * b, x0:x0 + w + 2 * b] = fr
        img = canvas.astype(np.float32)
    H, W = img.shape[:2]
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 1.5)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), 6); jyy = cv2.GaussianBlur(gy * gy, (0, 0), 6)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), 6)
    th = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    coh = np.clip(cv2.GaussianBlur(coh, (0, 0), 3) * 1.4, 0.15, 1)
    rng = np.random.default_rng(3)
    n = cv2.resize(rng.random((H // 16 + 2, W // 16 + 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    n = cv2.GaussianBlur(n, (0, 0), 12); n = (n - n.min()) / (np.ptp(n) + 1e-6)
    d = dict(img=img, H=H, W=W, vx=-np.sin(th), vy=np.cos(th), coh=coh, ph=n * 4 * np.pi,
             yy=np.mgrid[0:H, 0:W][0].astype(np.float32), xx=np.mgrid[0:H, 0:W][1].astype(np.float32))
    if frame:
        d["inner"] = (m + b, m + b, img.shape[1] - 2 * (m + b), img.shape[0] - 2 * (m + b))
    _cache[(key, frame)] = d
    return d

def alive(d, t, amp):
    """筆の流れに沿って絵の具を揺らした1コマ（絵の座標のまま）。"""
    if amp <= 0:
        return d["img"]
    s = amp * d["coh"] * np.sin(d["ph"] + 2 * np.pi * t / 2.6)
    return cv2.remap(d["img"], d["xx"] + s * d["vx"], d["yy"] + s * d["vy"], cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)

def view(src, cx, cy, scale):
    """絵の点(cx,cy)を画面中央に、倍率scaleで縦長画面に写す。"""
    M = np.float32([[scale, 0, OW / 2 - scale * cx], [0, scale, OH / 2 - scale * cy]])
    return cv2.warpAffine(src, M, (OW, OH), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=np.array(BG[::-1]) / 255)

# ---------- 効果 ----------
def radial_blur(fr, k):
    if k < 0.01:
        return fr
    acc = fr.copy()
    for i in range(1, 6):
        z = 1 + k * i / 5
        M = cv2.getRotationMatrix2D((OW / 2, OH / 2), 0, z)
        acc += cv2.warpAffine(fr, M, (OW, OH), borderMode=cv2.BORDER_REFLECT)
    return acc / 6

def swirl(fr, strength):
    if strength < 0.01:
        return fr
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    dx, dy = xx - OW / 2, yy - OH / 2
    r = np.sqrt(dx ** 2 + dy ** 2); R = 0.75 * OH
    a = np.arctan2(dy, dx) + strength * np.clip(1 - r / R, 0, 1) ** 2
    return cv2.remap(fr, OW / 2 + r * np.cos(a), OH / 2 + r * np.sin(a), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)

_noise = None
def dissolve(fr, p):
    """筆のタッチがほどけて飛び散る。"""
    global _noise
    if _noise is None:
        rng = np.random.default_rng(5)
        n = rng.normal(size=(OH // 6, OW // 6, 2)).astype(np.float32)
        _noise = cv2.resize(n, (OW, OH), interpolation=cv2.INTER_NEAREST)
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    k = 90 * p ** 1.5
    return cv2.remap(fr, xx + k * _noise[..., 0], yy + k * _noise[..., 1] - 40 * p, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)

def eyelid(fr, open_):
    """まばたき：0=閉じている、1=開いている。"""
    if open_ >= 0.999:
        return fr
    mask = np.zeros((OH, OW), np.float32)
    ry = max(1, int(open_ * OH * 0.75))
    cv2.ellipse(mask, (OW // 2, OH // 2), (int(OW * 0.9), ry), 0, 0, 360, 1, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 25 + 40 * (1 - open_))
    return fr * mask[..., None]

def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

# ---------- 文字 ----------
def overlay(fr, title=None, sub=None, alpha_t=0.0, alpha_s=0.0, place=None):
    im = Image.fromarray(cv2.cvtColor((np.clip(fr, 0, 1) * 255).astype(np.uint8), cv2.COLOR_BGR2RGB))
    dr = ImageDraw.Draw(im, "RGBA")
    if title and alpha_t > 0:
        a = int(255 * alpha_t)
        dr.text((OW // 2, 150), title[0], font=F_SMALL, fill=(235, 215, 150, a), anchor="mm")
        dr.text((OW // 2, 205), title[1], font=F_TITLE, fill=(255, 255, 255, a), anchor="mm",
                stroke_width=3, stroke_fill=(0, 0, 0, a))
    if place and alpha_t > 0:
        a = int(255 * alpha_t)
        dr.text((40, 90), place, font=F_SUB, fill=(255, 255, 255, a), anchor="lm", stroke_width=3,
                stroke_fill=(0, 0, 0, a))
    if sub and alpha_s > 0:
        a = int(255 * alpha_s)
        lines = sub.split("\n")
        for i, ln in enumerate(lines):
            dr.text((OW // 2, 1040 + i * 52 - 26 * (len(lines) - 1)), ln, font=F_SUB, fill=(255, 255, 255, a),
                    anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, a))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

# ---------- 音 ----------
def tts(text):
    x, sr = pyopenjtalk.tts(text.replace("\n", ""), speed=0.95, half_tone=0.0)
    x = x.astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.linspace(0, len(x), int(len(x) * SR / sr), endpoint=False), np.arange(len(x)), x)
    return x * 1.4

def whoosh(sec):
    n = int(sec * SR); rng = np.random.default_rng(1)
    x = rng.normal(size=n).astype(np.float32)
    out = np.zeros(n, np.float32); y = 0.0
    cut = np.linspace(0.02, 0.5, n) ** 2  # だんだん高く
    for i in range(n):  # 簡単なローパス
        y += cut[i] * (x[i] - y); out[i] = y
    env = np.sin(np.linspace(0, np.pi, n)) ** 2 * np.linspace(0.3, 1, n)
    return out * env * 0.25

# ---------- 1本を作る ----------
def build(v):
    name = v["name"]; key = v["painting"]; P = PAINTINGS[key]
    use_frame = v["dive"] == "frame"
    d = load(key, frame=use_frame)
    H, W = d["H"], d["W"]
    if use_frame:
        ix, iy, iw, ih = d["inner"]
    else:
        ix, iy, iw, ih = 0, 0, W, H
    fit = min(OW * 0.94 / iw, OH * 0.62 / ih)
    c0 = (ix + iw / 2, iy + ih / 2)
    tx, ty = ix + v["target"][0] * iw, iy + v["target"][1] * ih

    a1 = tts(v["hook_line"]); a2 = tts(v["inside_line"])
    t_hook = max(3.2, len(a1) / SR + 0.9)
    t_dive = 1.6
    t_trans = {"white": 0.8, "black": 0.8, "blink": 1.6}[v["trans"]]
    t_in = max(4.0, len(a2) / SR + 1.2)
    T = t_hook + t_dive + t_trans + t_in
    N = int(T * FPS)

    raw = os.path.join(TMP, f"{name}.mp4")
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (OW, OH))
    in_scale = OH / (ih * v.get("inside_span", 0.45))
    def clamp(cx, cy, sc):
        hw, hh = OW / 2 / sc, OH / 2 / sc
        cx = ix + iw / 2 if 2 * hw >= iw else min(max(cx, ix + hw), ix + iw - hw)
        cy = iy + ih / 2 if 2 * hh >= ih else min(max(cy, iy + hh), iy + ih - hh)
        return cx, cy
    for i in range(N):
        t = i / FPS
        if t < t_hook:  # フック
            if v["hook"] == "burst":  # ため → 急に動き出す
                amp = 0 if t < 0.7 else 7 * ease((t - 0.7) / 0.25)
                sc = fit * (1 + 0.05 * ease((t - 0.7) / 0.3))
            else:
                amp = 3; sc = fit * (1 + 0.02 * t / t_hook)
            fr = view(alive(d, t, amp), *c0, sc)
            fr = overlay(fr, (P["year"], P["title"]), v["hook_line"], ease(t / 0.4), ease((t - 0.3) / 0.3))
        elif t < t_hook + t_dive:  # 飛び込み
            p = (t - t_hook) / t_dive; e = p ** 2.2
            cx = c0[0] + (tx - c0[0]) * ease(p * 1.5); cy = c0[1] + (ty - c0[1]) * ease(p * 1.5)
            sc = fit * np.exp(np.log(in_scale * 2.2 / fit) * e)
            if p > 0.5:
                kx, ky = clamp(cx, cy, sc); w_ = ease((p - 0.5) / 0.3)
                cx, cy = cx + (kx - cx) * w_, cy + (ky - cy) * w_
            fr = view(alive(d, t, 5), cx, cy, sc)
            if v["dive"] in ("zoom", "frame"):
                fr = radial_blur(fr, 0.25 * e)
            elif v["dive"] == "swirl":
                fr = swirl(fr, 9 * e)
            elif v["dive"] == "dissolve":
                fr = dissolve(fr, e)
            if v["trans"] in ("white", "black"):  # 最後に白／黒へ
                col = 1.0 if v["trans"] == "white" else 0.0
                k = ease((p - 0.6) / 0.4)
                fr = fr * (1 - k) + col * k
            else:
                fr = eyelid(fr, 1 - ease((p - 0.55) / 0.45))
            fr = overlay(fr)
        else:  # 切り替え → 絵の中
            tt = t - t_hook - t_dive
            pan = (tt / (t_trans + t_in))
            cx = tx + v.get("pan", (0.06, 0))[0] * iw * (pan - 0.5)
            cy = ty + v.get("pan", (0, 0))[1] * ih * (pan - 0.5)
            sc = in_scale * (1.06 - 0.06 * pan)
            cx, cy = clamp(cx, cy, sc)
            fr = view(alive(d, t, 4), cx, cy, sc)
            if v["trans"] in ("white", "black"):
                col = 1.0 if v["trans"] == "white" else 0.0
                k = 1 - ease(tt / t_trans)
                fr = fr * (1 - k) + col * k
            else:  # 目を開く：半分→閉じる→全開
                if tt < t_trans:
                    q = tt / t_trans
                    o = 0.35 * ease(q / 0.35) if q < 0.35 else (0.35 * (1 - ease((q - 0.35) / 0.2)) if q < 0.55 else ease((q - 0.55) / 0.45))
                    fr = eyelid(fr, o)
                    blur = int(31 * (1 - q)) | 1
                    fr = cv2.GaussianBlur(fr, (blur, blur), 0)
            s_on = tt - t_trans
            fr = overlay(fr, None, v["inside_line"], ease((tt - t_trans * 0.5) / 0.5), ease(s_on / 0.3),
                         place=v.get("place"))
            if v.get("place"):
                pass
        vw.write(fr if fr.dtype == np.uint8 else (np.clip(fr, 0, 1) * 255).astype(np.uint8))
    vw.release()

    # 音を並べる
    audio = np.zeros(int(T * SR) + SR, np.float32)
    def put(x, at):
        s = int(at * SR); audio[s:s + len(x)] += x[:len(audio) - s]
    put(a1, 0.35)
    put(whoosh(t_dive + 0.3), t_hook - 0.1)
    put(a2, t_hook + t_dive + t_trans * 0.7)
    audio = np.clip(audio, -1, 1)
    wav = os.path.join(TMP, f"{name}.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    mp4 = os.path.join(OUT, f"{name}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-i", wav, "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest",
                    mp4], check=True)
    os.remove(raw); os.remove(wav)
    print("done", mp4, round(T, 1), "sec")

VARIANTS = [
    dict(name="01_星月夜_渦に吸い込まれる_白", painting="starry", hook="burst", dive="swirl", trans="white",
         target=(0.42, 0.33), inside_span=0.40, pan=(0.25, 0.9), place="1889年 南フランス・サン＝レミ",
         hook_line="この空、\nなぜうねっているか知っていますか？",
         inside_line="ゴッホは療養院の窓から、\n夜明け前の空を見ていました"),
    dict(name="02_星月夜_村へ降りる_まばたき", painting="starry", hook="subtle", dive="zoom", trans="blink",
         target=(0.57, 0.86), inside_span=0.30, pan=(0.35, 0), place="1889年 サン＝レミ",
         hook_line="名画の世界へ、\n飛び込んでみませんか？",
         inside_line="ここは、ゴッホが\n窓の外に見ていた夜です"),
    dict(name="03_北斎_波の中へ_黒", painting="wave", hook="burst", dive="zoom", trans="black",
         target=(0.40, 0.30), inside_span=0.45, pan=(0.3, 0.2), place="江戸時代 1831年ごろ",
         hook_line="この絵、\n富士山はどこにあるか分かりますか？",
         inside_line="波の向こう、いちばん小さく\n描かれているのが富士山です"),
    dict(name="04_北斎_額縁をくぐる_白", painting="wave", hook="subtle", dive="frame", trans="white",
         target=(0.65, 0.68), inside_span=0.35, pan=(0.4, 0), place="神奈川沖",
         hook_line="この絵の中に、\n入ってみましょう",
         inside_line="舟をこいでいるのは、\n魚を江戸へ急いで運ぶ人たちです"),
    dict(name="05_叫び_タッチがほどける_黒", painting="scream", hook="burst", dive="dissolve", trans="black",
         target=(0.5, 0.15), inside_span=0.35, pan=(0.6, 0), place="1893年 ノルウェー・オスロ",
         hook_line="叫んでいるのは、\nこの人ではありません",
         inside_line="ムンクは夕暮れの道で、\n自然をつらぬく叫びを感じたと書いています"),
    dict(name="06_叫び_顔へズーム_まばたき", painting="scream", hook="subtle", dive="zoom", trans="blink",
         target=(0.52, 0.46), inside_span=0.30, pan=(0, 0.3), place="オスロの夕暮れ",
         hook_line="この絵に隠された秘密、\n知っていますか？",
         inside_line="この人は、叫び声を聞いて\n耳をふさいでいるのです"),
]

if __name__ == "__main__":
    import sys
    only = sys.argv[1:]
    for v in VARIANTS:
        if not only or any(o in v["name"] for o in only):
            build(v)
