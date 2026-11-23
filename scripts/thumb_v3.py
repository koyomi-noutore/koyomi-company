"""サムネ標準形（案3・2026-11-12 CEO決定）を作る。
使い方: python3 scripts/thumb_v3.py <回のフォルダ> <問番号> <出力パス> [上の文字]
上：黒帯に挑戦の言葉（既定「3つ見つけたら天才！」）。下：特大の「間違い探し」。キャラなし。
絵は answers.json の違いの範囲を囲むように切り出して拡大し、色とコントラストを強める。"""
import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

import os, subprocess
from pathlib import Path
# 書体は太い角ゴシック（Noto Sans CJK JP Black＝npm の Noto Sans JP Black, OFL）。第9回のサムネと同じ（2026-11-18 夜 CEO：第10回の丸ゴシックから第9回の書体に戻す）。
# 丸ゴシックには替えない。無ければ npm から取り、それでも無ければ止める。
FONT_DIR = Path.home() / ".cache/koyomi/fonts"
FONT_CANDIDATES = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', str(FONT_DIR / "package/900Black/NotoSansJP_900Black.ttf")]


def font_path():
    f = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    if not f:
        FONT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["npm", "pack", "--silent", "@expo-google-fonts/noto-sans-jp@0.4.4"], cwd=FONT_DIR, stdout=subprocess.DEVNULL)
        for t in FONT_DIR.glob("*.tgz"):
            subprocess.run(["tar", "xzf", t.name], cwd=FONT_DIR)
        f = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    if not f:
        raise SystemExit("サムネの書体（Noto Sans CJK JP Black）が見つからない。丸ゴシックには替えずに止める。")
    return f


F = font_path()

def make(ep, q, out, top_text=("3つ", "見つけたら", "天才！"), bottom=("^秋の", "間違い探し")):
    a = Image.open(f'{ep}/q{q}_a.png').convert('RGB'); b = Image.open(f'{ep}/q{q}_b.png').convert('RGB')
    ans = json.load(open(f'{ep}/answers.json', encoding='utf-8'))
    Q = [x for x in ans['questions'] if x['q'] == q][0]
    W, H = a.size
    bx = [x['box_px'] for x in Q['answers']]
    x0 = min(v[0] for v in bx); y0 = min(v[1] for v in bx); x1 = max(v[2] for v in bx); y1 = max(v[3] for v in bx)
    top = 170; ph = 720 - top; pw = 636; r = pw / ph
    w = max(x1 - x0, (y1 - y0) * r) * 1.3; h = w / r
    if w > W: w, h = W, W / r
    if h > H: h, w = H, H * r
    cx = min(max((x0 + x1) / 2, w / 2), W - w / 2); cy = min(max((y0 + y1) / 2 + h * 0.08, h / 2), H - h / 2)
    box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
    def prep(im):
        im = im.crop(box).resize((pw, ph), Image.LANCZOS)
        im = ImageEnhance.Color(im).enhance(1.5); im = ImageEnhance.Contrast(im).enhance(1.3)
        return im.filter(ImageFilter.UnsharpMask(2, 130, 2))
    T = Image.new('RGB', (1280, 720), (255, 255, 255))
    T.paste(prep(a), (0, top)); T.paste(prep(a), (644, top))  # 2026-11-23：左右とも元の絵（違いゼロ）
    d = ImageDraw.Draw(T)
    d.rectangle([636, top, 644, 720], fill=(25, 25, 25)); d.rectangle([0, 0, 1280, top], fill=(0, 0, 0))
    f = ImageFont.truetype(F, 150)   # 上の文字は大きく、帯いっぱいに（2026-11-18）
    cols = [(255, 221, 0), (255, 255, 255), (255, 45, 45)]
    # 色は意味のまとまりごと（2026-11-14 CEO指摘）：先頭が * なら赤（一番大事な語だけ）、^ なら黄、印がなければ白
    if any(t[:1] in "*^" for t in top_text):
        cmap = {"*": (255, 45, 45), "^": (255, 221, 0)}
        cols = [cmap.get(t[:1], (255, 255, 255)) for t in top_text]
        top_text = [t[1:] if t[:1] in "*^" else t for t in top_text]
    tw = sum(d.textlength(s, font=f) for s in top_text)
    if tw > 1250:                                   # 帯からはみ出すときは小さく
        f = ImageFont.truetype(F, int(150 * 1250 / tw)); tw = sum(d.textlength(s, font=f) for s in top_text)
    x = (1280 - tw) / 2
    for s, c in zip(top_text, cols):
        d.text((x, top / 2 + 4), s, font=f, fill=c, anchor='lm', stroke_width=2, stroke_fill=(0, 0, 0)); x += d.textlength(s, font=f)
    g = Image.new('L', (1280, 220), 0); gd = ImageDraw.Draw(g)
    for i in range(220): gd.line([(0, i), (1280, i)], fill=int(170 * i / 220))
    T.paste(Image.new('RGB', (1280, 220), (0, 0, 0)), (0, 500), g)
    # 下の文字：見やすい2色（黄・白）＋黒の縁取りだけ（2026-11-18：黄＋赤＋黒の重ねは見にくい）。^ で始まる語は黄、ほかは白
    bcol = [(255, 214, 0) if t[:1] == "^" else (255, 255, 255) for t in bottom]
    bottom = [t[1:] if t[:1] == "^" else t for t in bottom]
    f2 = ImageFont.truetype(F, 158)
    bw = sum(d.textlength(s, font=f2) for s in bottom)
    if bw > 1150:
        f2 = ImageFont.truetype(F, int(158 * 1150 / bw)); bw = sum(d.textlength(s, font=f2) for s in bottom)
    x = (1280 - bw) / 2
    for s, c in zip(bottom, bcol):
        d.text((x, 618), s, font=f2, fill=c, anchor='lm', stroke_width=14, stroke_fill=(0, 0, 0)); x += d.textlength(s, font=f2)
    T.save(out, quality=92)

if __name__ == '__main__':
    # 上の文字は意味のまとまりで | に分け、色の印を付ける（例：^3つ|見つけたら|*天才！ ＝黄・白・赤）。印なしの3つは黄・白・赤
    # 下の文字も | で分け、^ の語を黄にする（既定 ^秋の|間違い探し）
    make(sys.argv[1], int(sys.argv[2]), sys.argv[3], tuple(sys.argv[4].split('|')) if len(sys.argv) > 4 else ("3つ", "見つけたら", "天才！"),
         tuple(sys.argv[5].split('|')) if len(sys.argv) > 5 else ("^秋の", "間違い探し"))
