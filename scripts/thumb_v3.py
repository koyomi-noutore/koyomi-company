"""サムネ標準形（案3・2026-11-12 CEO決定）を作る。
使い方: python3 scripts/thumb_v3.py <回のフォルダ> <問番号> <出力パス> [上の文字]
上：黒帯に挑戦の言葉（既定「3つ見つけたら天才！」）。下：特大の「間違い探し」。キャラなし。
絵は answers.json の違いの範囲を囲むように切り出して拡大し、色とコントラストを強める。"""
import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

F = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

def make(ep, q, out, top_text=("3つ", "見つけたら", "天才！")):
    a = Image.open(f'{ep}/q{q}_a.png').convert('RGB'); b = Image.open(f'{ep}/q{q}_b.png').convert('RGB')
    ans = json.load(open(f'{ep}/answers.json', encoding='utf-8'))
    Q = [x for x in ans['questions'] if x['q'] == q][0]
    W, H = a.size
    bx = [x['box_px'] for x in Q['answers']]
    x0 = min(v[0] for v in bx); y0 = min(v[1] for v in bx); x1 = max(v[2] for v in bx); y1 = max(v[3] for v in bx)
    top = 140; ph = 720 - top; pw = 636; r = pw / ph
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
    T.paste(prep(a), (0, top)); T.paste(prep(b), (644, top))
    d = ImageDraw.Draw(T)
    d.rectangle([636, top, 644, 720], fill=(25, 25, 25)); d.rectangle([0, 0, 1280, top], fill=(0, 0, 0))
    f = ImageFont.truetype(F, 112, index=0)
    cols = [(255, 221, 0), (255, 255, 255), (255, 45, 45)]
    tw = sum(d.textlength(s, font=f) for s in top_text); x = (1280 - tw) / 2
    for s, c in zip(top_text, cols):
        d.text((x, top / 2 + 4), s, font=f, fill=c, anchor='lm', stroke_width=3, stroke_fill=(0, 0, 0)); x += d.textlength(s, font=f)
    g = Image.new('L', (1280, 220), 0); gd = ImageDraw.Draw(g)
    for i in range(220): gd.line([(0, i), (1280, i)], fill=int(170 * i / 220))
    T.paste(Image.new('RGB', (1280, 220), (0, 0, 0)), (0, 500), g)
    f2 = ImageFont.truetype(F, 190, index=0)
    d.text((640, 612), "間違い探し", font=f2, fill=(0, 0, 0), anchor='mm', stroke_width=26, stroke_fill=(0, 0, 0))
    d.text((640, 612), "間違い探し", font=f2, fill=(255, 230, 0), anchor='mm', stroke_width=14, stroke_fill=(215, 25, 25))
    T.save(out, quality=92)

if __name__ == '__main__':
    make(sys.argv[1], int(sys.argv[2]), sys.argv[3])
