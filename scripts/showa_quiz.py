"""昭和なつかしクイズ（試作。2026-11-18 CEO指示）：昭和の暮らしの道具の水彩画を1枚ずつ見せ、名前を当てる。
1問の流れ：絵を見せて「これは何でしょう？」→ 考える時間（plan.json の think_sec）→ ヒント（最初の1文字）→ 答え＋豆知識1文。

使い方：python3 scripts/showa_quiz.py <フォルダ> <工程>
  工程：voice（声）・audio（音）・long（長尺の動画）・short [番号]（ショート1問）・thumb（サムネ）・sheet（絵の一覧）・all
フォルダ：outputs/prototypes/showa_quiz_001 など（plan.json がある所）。作業フォルダは ~/.cache/koyomi/<フォルダ名>/。
絵：作業フォルダの item<番号>.png（4:3）。声のキーは環境変数 FISH_AUDIO_API_KEY だけから読む。
声に渡す文は plan.json の voice（ひらがな）を使い、漢字が残っていたら止める。字幕との対照表を readings_check.md に出す。
工程ごとの時間は <フォルダ>/timing.json に足す。
"""
import json, math, os, re, subprocess, sys, time, urllib.request, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SR, FPS = 48000, 30
BG, INK, RED = (246, 236, 216), (59, 47, 37), (200, 50, 40)
KANJI = re.compile(r"[㐀-鿿々〆ヶ]")
BOLD = str(Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf")   # 太い角ゴシック（サムネ・大きな文字）
ROUND = next(iter(sorted(Path.home().glob(".cache/koyomi/*/fontpkg/package/700Bold/ZenMaruGothic_700Bold.ttf"))), None)  # 字幕（今の長尺と同じ）
OWL = next(iter(sorted(Path.home().glob(".cache/koyomi/*/owl/koyomi_smile.png"))), None)


def f_bold(s):
    return ImageFont.truetype(BOLD, s)


def f_round(s):
    return ImageFont.truetype(str(ROUND or BOLD), s)


# ---------- 台本 ----------
def script(P):
    """セリフの一覧：[(id, 字幕, 声に渡す文, 種類)]。種類で画面を切り替える。"""
    L = [("op1", "こよみ先生です。今日は、昭和のなつかしい道具クイズ、全5問です。",
          "こよみせんせいです。きょうは、しょうわの、なつかしいどうぐクイズ、ぜんごもんです。", "op"),
         ("op2", "絵を見て、道具の名前を当ててくださいね。", "えをみて、どうぐのなまえを、あててくださいね。", "op")]
    for it in P["items"]:
        n = it["id"]
        L += [(f"q{n}_card", f"第{n}問", "だい" + {1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご"}[n] + "もん。", "card"),
              (f"q{n}_ask", "これは何でしょう？", "これは、なんでしょう？", "ask"),
              (f"q{n}_hint", f"ヒント。最初の文字は「{it['hint']}」です。", f"ヒント。さいしょのもじは、{it['hint_voice']}、です。", "hint"),
              (f"q{n}_ans", f"答えは、{it['name']}。", f"こたえは、{it['name_voice']}。", "ans"),
              (f"q{n}_trivia", it["trivia"], it["trivia_voice"], "trivia")]
    L += [("ed1", "5問、おしまいです。いくつわかりましたか。", "ごもん、おしまいです。いくつ、わかりましたか。", "ed"),
          ("ed2", "なつかしい道具のお話、また一緒にしましょうね。", "なつかしいどうぐのおはなし、また、いっしょにしましょうね。", "ed")]
    return L


def readings_check(P, out):
    rows = ["# 読みの対照表（字幕 → 声に渡す文）", "", "| id | 字幕 | 声に渡す文 |", "|---|---|---|"]
    bad = []
    for lid, sub, vt, _ in script(P):
        rows.append(f"| {lid} | {sub} | {vt} |")
        if KANJI.search(vt):
            bad.append(f"{lid}：{''.join(KANJI.findall(vt))}")
    (out / "readings_check.md").write_text("\n".join(([f"問題：漢字が残っている {bad}", ""] if bad else ["問題：なし（声に渡す文に漢字なし）", ""]) + rows) + "\n",
                                           encoding="utf-8")
    if bad:
        raise SystemExit(f"声に渡す文に漢字が残っている：{bad}")


# ---------- 声（Fish Audio。ep_voice.py と同じ設定） ----------
def tts(P, text, out_wav):
    key = os.environ.get("FISH_AUDIO_API_KEY")
    if not key:
        raise SystemExit("FISH_AUDIO_API_KEY が設定されていません")
    V = P["voice"]
    body = {"text": text, "reference_id": V["reference_id"], "format": "wav", "prosody": {"speed": V["speed"]}}
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "model": V.get("model", "s1"), "Content-Type": "application/json"})
    raw = Path(str(out_wav) + ".raw.wav")
    raw.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ac", "1", "-ar", str(SR), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,adelay=50,apad=pad_dur=0.15",
                    str(out_wav)], check=True)
    raw.unlink()


def voice(P, out, work):
    readings_check(P, out)
    vd = work / "voice"; vd.mkdir(parents=True, exist_ok=True)
    vj = vd / "voice.json"
    old = {v["id"]: v for v in json.loads(vj.read_text(encoding="utf-8"))} if vj.exists() else {}
    res = []
    for lid, sub, vt, kind in script(P):
        wav = vd / f"{lid}.wav"
        if not wav.exists() or old.get(lid, {}).get("voice_text") != vt:
            tts(P, vt, wav)
        with wave.open(str(wav)) as w_:
            dur = w_.getnframes() / w_.getframerate()
        res.append({"id": lid, "subtitle": sub, "voice_text": vt, "kind": kind, "dur": round(dur, 2)})
    vj.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def read_wav(p):
    with wave.open(str(p)) as w_:
        return np.frombuffer(w_.readframes(w_.getnframes()), dtype=np.int16).astype(np.float32) / 32768


# ---------- 段取り（各セリフの開始秒と、画面の状態） ----------
def timeline(P, work, items=None, short=False):
    V = {v["id"]: v for v in json.loads((work / "voice" / "voice.json").read_text(encoding="utf-8"))}
    T, t = [], 0.3       # (開始秒, id, 状態)
    states = []          # (開始秒, 終わり秒, 状態dict)

    def say(lid, st, after=0.5):
        nonlocal t
        T.append((t, lid)); s0 = t; t += V[lid]["dur"] + after
        states.append((s0, t, st))

    if not short:
        say("op1", {"k": "op"}); say("op2", {"k": "op"}, 0.8)
    for it in (items or P["items"]):
        n = it["id"]
        if not short:
            say(f"q{n}_card", {"k": "card", "n": n}, 0.6)
        say(f"q{n}_ask", {"k": "ask", "n": n}, 0.2)
        s0 = t; t += P["think_sec"]
        states.append((s0, t, {"k": "think", "n": n, "t0": s0}))
        say(f"q{n}_hint", {"k": "hint", "n": n}, 0.3)
        s0 = t; t += 3.0
        states.append((s0, t, {"k": "hint", "n": n}))
        say(f"q{n}_ans", {"k": "ans", "n": n}, 0.3)
        say(f"q{n}_trivia", {"k": "trivia", "n": n}, 1.2)
    if not short:
        say("ed1", {"k": "ed"}); say("ed2", {"k": "ed"}, 1.5)
    return T, states, t


# ---------- 音（BGMと効果音は numpy で合成したオリジナル） ----------
def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def bgm(n):
    tt = np.arange(int(8 * SR)) / SR
    loop = np.zeros(len(tt))
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    for ci, ch in enumerate(chords):
        s = int(ci * 2 * SR); seg = np.arange(int(2 * SR)) / SR
        pad = sum(np.sin(2 * np.pi * midi(m - 12) * seg) for m in ch) * 0.02 * np.minimum(1, seg * 3) * np.minimum(1, (2 - seg) * 3)
        loop[s:s + len(seg)] += pad
    return np.tile(loop, n // len(loop) + 1)[:n]


def tone(f, dur, decay, amp):
    tt = np.arange(int(dur * SR)) / SR
    return amp * np.sin(2 * np.pi * f * tt) * np.exp(-tt * decay)


def mix(P, work, T, total, events, out_wav):
    n = int(total * SR) + SR
    track = bgm(n)
    vd = work / "voice"

    def put(x, at):
        s = int(at * SR); e = min(n, s + len(x)); track[s:e] += x[:e - s]
    for at, lid in T:
        put(read_wav(vd / f"{lid}.wav") * 0.9, at)
    for at, kind in events:
        if kind == "tick":
            put(tone(1600, 0.08, 40, 0.12), at)
        elif kind == "chime":
            put(tone(midi(84), 0.6, 4, 0.18), at); put(tone(midi(88), 0.8, 4, 0.18), at + 0.18)
        elif kind == "hint":
            for k, m in enumerate((88, 91, 96)):
                put(tone(midi(m), 0.4, 8, 0.10), at + k * 0.08)
    track = np.clip(track / max(1e-6, np.abs(track).max()) * 0.9, -1, 1)
    with wave.open(str(out_wav), "w") as w_:
        w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR)
        w_.writeframes((track * 32767).astype(np.int16).tobytes())


# ---------- 画面 ----------
def load_pic(work, n):
    return Image.open(work / f"item{n}.png").convert("RGB")


def draw_center(d, xy, s, f, fill, stroke=0):
    d.text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(30, 20, 10))


def frame_long(P, work, st, t, cache):
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    k = st["k"]
    if k in ("op", "ed"):
        draw_center(d, (W / 2, 330), "昭和なつかしクイズ", f_bold(130), (180, 70, 40))
        draw_center(d, (W / 2, 500), "道具の名前、わかりますか？" if k == "op" else "おつかれさまでした", f_bold(80), INK)
        if OWL:
            o = Image.open(OWL).convert("RGBA").resize((300, 300)); im.paste(o, (W // 2 - 150, 640), o)
        return im
    n = st["n"]; it = {x["id"]: x for x in P["items"]}[n]
    if k == "card":
        draw_center(d, (W / 2, H / 2 - 40), f"第{n}問", f_bold(200), (180, 70, 40))
        draw_center(d, (W / 2, H / 2 + 140), "これは何でしょう？", f_bold(70), INK)
        return im
    pic = cache.setdefault(n, load_pic(work, n).resize((1240, 930), Image.LANCZOS))
    im.paste(pic, (50, 75)); d.rectangle((46, 71, 1293, 1008), outline=(255, 250, 238), width=6)
    px = 1610       # 右の欄の中央
    draw_center(d, (px, 120), f"第{n}問", f_bold(64), (180, 70, 40))
    if k in ("ask", "think", "hint"):
        draw_center(d, (px, 260), "これは", f_bold(90), INK); draw_center(d, (px, 370), "何でしょう？", f_bold(90), INK)
    if k == "think":
        rem = max(1, math.ceil(P["think_sec"] - (t - st["t0"]) - 1e-6))
        d.ellipse((px - 120, 520, px + 120, 760), fill=(255, 250, 238), outline=(214, 128, 48), width=12)
        draw_center(d, (px, 640), str(rem), f_bold(150), (214, 128, 48))
    if k == "hint":
        d.rounded_rectangle((px - 270, 520, px + 270, 900), 30, fill=(255, 245, 210), outline=(214, 128, 48), width=6)
        draw_center(d, (px, 590), "ヒント", f_bold(60), (214, 128, 48))
        draw_center(d, (px, 670), "最初の文字は", f_bold(50), INK)
        draw_center(d, (px, 800), f"「{it['hint']}」", f_bold(130), (180, 70, 40))
    if k in ("ans", "trivia"):
        draw_center(d, (px, 260), "答え", f_bold(64), (180, 70, 40))
        name = it["name"]; sz = 130 if len(name) <= 4 else 96
        draw_center(d, (px, 420), name, f_bold(sz), INK)
        draw_center(d, (px, 540), f"（{it['reading']}）", f_round(44), (110, 84, 60))
        if k == "trivia":       # 右の欄（x 1310〜1910）の中に収める
            fz = 50
            lines = wrap_px(it["trivia"], f_round(fz), 560)
            while len(lines) > 4:
                fz -= 4; lines = wrap_px(it["trivia"], f_round(fz), 560)
            for i, l in enumerate(lines):
                draw_center(d, (px, 680 + i * (fz + 18)), l, f_round(fz), INK)
    return im


def wrap(s, n):
    out, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= n and ch in "、。をにがはでと":
            out.append(cur); cur = ""
    if cur:
        out.append(cur)
    res = []
    for l in out:
        while len(l) > n + 3:
            res.append(l[:n]); l = l[n:]
        res.append(l)
    return res


def wrap_px(s, f, maxw):
    """文を、実際の文字幅（px）で maxw に収まるように改行する。読点・句点・助詞のあとを優先して切る（2026-11-18 監査 M-2）。"""
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines, cur, last_break = [], "", -1
    for ch in s:
        if d.textlength(cur + ch, font=f) > maxw and cur and ch not in "、。」）":   # 句読点は行の頭に置かない（前の行の終わりにぶら下げる）
            if last_break > 0 and last_break >= len(cur) // 2:
                lines.append(cur[:last_break]); cur = cur[last_break:]
            else:
                lines.append(cur); cur = ""
            last_break = -1
        cur += ch
        if ch in "、。」）":
            last_break = len(cur)
    if cur:
        lines.append(cur)
    for l in lines:     # 念のため：枠をはみ出す行があれば止める
        if d.textlength(l.rstrip("、。」）"), font=f) > maxw + 1:
            raise SystemExit(f"文字が枠に収まらない：{l}")
    return lines


def subtitle(im, sub, W, H, y, size):
    d = ImageDraw.Draw(im)
    for i, l in enumerate(wrap(sub, 22)[:2]):
        draw_center(d, (W / 2, y + i * (size + 14)), l, f_round(size), (255, 255, 255), stroke=5)


def frame_short(P, work, st, t, cache, end=False, t_end=0):
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    k = st["k"]; n = st["n"]; it = {x["id"]: x for x in P["items"]}[n]
    pic = cache.setdefault(("s", n), load_pic(work, n).resize((1008, 756), Image.LANCZOS))
    im.paste(pic, (36, 300))
    draw_center(d, (W / 2, 200), "昭和なつかしクイズ", f_bold(76), (180, 70, 40))
    if k in ("ask", "think"):
        draw_center(d, (W / 2, 1180), "これは何でしょう？", f_bold(96), INK)
    if k == "think":
        rem = max(1, math.ceil(P["think_sec"] - (t - st["t0"]) - 1e-6))
        d.ellipse((W / 2 - 110, 1290, W / 2 + 110, 1510), fill=(255, 250, 238), outline=(214, 128, 48), width=12)
        draw_center(d, (W / 2, 1400), str(rem), f_bold(140), (214, 128, 48))
    if k == "hint":
        draw_center(d, (W / 2, 1180), "ヒント：最初の文字は", f_bold(70), INK)
        draw_center(d, (W / 2, 1340), f"「{it['hint']}」", f_bold(150), (180, 70, 40))
    if k in ("ans", "trivia"):
        draw_center(d, (W / 2, 1150), "答え", f_bold(64), (180, 70, 40))
        draw_center(d, (W / 2, 1270), it["name"], f_bold(130 if len(it["name"]) <= 4 else 100), INK)
        if k == "trivia":       # 左右36pxより内側（幅 900px まで）に収める
            for i, l in enumerate(wrap_px(it["trivia"], f_round(54), 900)[:3]):
                draw_center(d, (W / 2, 1410 + i * 66), l, f_round(54), INK)
    # 最初：暗い幕と大きな文字（ショートの形 2026-11-18 夜）
    if st.get("intro"):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 140)); ld = ImageDraw.Draw(layer)
        ld.text((W / 2, 860), "昭和の道具", font=f_bold(130), fill=(255, 214, 0), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        ld.text((W / 2, 1020), "名前、わかりますか？", font=f_bold(96), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    if end:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 140)); ld = ImageDraw.Draw(layer)
        ld.text((W / 2, 860), "続きは長い動画で", font=f_bold(100), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        ld.text((W / 2, 1010), "左下をクリック", font=f_bold(110), fill=(255, 214, 0), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        im = Image.alpha_composite(im.convert("RGBA"), layer)
        d2 = ImageDraw.Draw(im)
        wig = 14 * math.sin(2 * math.pi * t_end)
        tx, ty, sx, sy = 240 + wig * 0.7, 1720 + wig * 0.7, 560, 1280
        ang = math.atan2(ty - sy, tx - sx); hx, hy = tx - 90 * math.cos(ang), ty - 90 * math.sin(ang); px, py = -math.sin(ang), math.cos(ang)
        for wdt, col in ((46, (255, 255, 255)), (30, (230, 60, 30))):
            d2.line((sx, sy, hx, hy), fill=col, width=wdt); e = wdt / 30
            d2.polygon([(tx, ty), (hx + 54 * e * px, hy + 54 * e * py), (hx - 54 * e * px, hy - 54 * e * py)], fill=col)
        im = im.convert("RGB")
    return im


def render(frames_fn, total, size, wav, out):
    W, H = size
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    last_key, last = None, None
    for i in range(int(total * FPS)):
        t = i / FPS
        key, fn = frames_fn(t)
        if key != last_key:
            last, last_key = fn().tobytes(), key
        p.stdin.write(last)
    p.stdin.close(); p.wait()


def state_at(states, t):
    for s0, s1, st in states:
        if s0 <= t < s1:
            return st
    return states[-1][2]


def current_sub(work, T, t):
    V = {v["id"]: v for v in json.loads((work / "voice" / "voice.json").read_text(encoding="utf-8"))}
    for at, lid in T:
        if at <= t < at + V[lid]["dur"] + 0.4:
            return V[lid]["subtitle"]
    return None


def long_video(P, out, work):
    T, states, total = timeline(P, work)
    ev = []
    for s0, s1, st in states:
        if st["k"] == "think":
            ev += [(s0 + i, "tick") for i in range(P["think_sec"])]
        if st["k"] == "hint" and (s0, "hint") not in ev:
            ev.append((s0, "hint"))
        if st["k"] == "ans":
            ev.append((s0, "chime"))
    mix(P, work, T, total, ev, work / "long.wav")
    cache = {}

    def fr(t):
        st = state_at(states, t); sub = current_sub(work, T, t)
        key = (id(st), int(t) if st["k"] == "think" else 0, sub)

        def f():
            im = frame_long(P, work, st, t, cache)
            if sub and st["k"] in ("op", "ed", "card", "ask", "hint", "ans"):
                ImageDraw.Draw(im).rectangle((0, 1012, 1920, 1080), fill=(52, 40, 30))
                draw_center(ImageDraw.Draw(im), (960, 1046), sub, f_round(44), (255, 255, 255))
            return im
        return key, f
    render(fr, total, (1920, 1080), work / "long.wav", out / "long.mp4")
    (out / "long_timeline.json").write_text(json.dumps({"total": round(total, 2), "lines": T}, ensure_ascii=False, indent=1), encoding="utf-8")
    return total


def short_video(P, out, work, n):
    it = [x for x in P["items"] if x["id"] == n]
    T, states, total = timeline(P, work, items=it, short=True)
    # 最初の2.6秒は暗い幕（効果音のあと「これは何でしょう？」）、最後は「続きは長い動画で」
    T = [(a + 2.6, lid) for a, lid in T]
    states = [(0, 2.6, dict(states[0][2], intro=True))] + [(a + 2.6, b + 2.6, st) for a, b, st in states]
    total += 2.6
    end_at = total
    end_v = "つづきは、ながいどうがで。ひだりしたをクリックして、ちょうせんしてみてくださいね。"
    vd = work / "voice"
    if not (vd / "s_end.wav").exists():
        tts(P, end_v, vd / "s_end.wav")
    end_dur = len(read_wav(vd / "s_end.wav")) / SR
    T.append((end_at + 0.3, "s_end"))
    total = end_at + end_dur + 1.2
    ev = [(0.1, "hint")]
    for s0, s1, st in states:
        if st["k"] == "think":
            ev += [(s0 + i, "tick") for i in range(P["think_sec"])]
        if st["k"] == "ans":
            ev.append((s0, "chime"))
    vj = json.loads((vd / "voice.json").read_text(encoding="utf-8"))
    if not any(v["id"] == "s_end" for v in vj):
        vj.append({"id": "s_end", "subtitle": "続きは長い動画で。左下をクリックして、挑戦してみてくださいね。", "voice_text": end_v, "kind": "end", "dur": round(end_dur, 2)})
        (vd / "voice.json").write_text(json.dumps(vj, ensure_ascii=False, indent=1), encoding="utf-8")
    mix(P, work, T, total, ev, work / f"short{n}.wav")
    cache = {}

    def fr(t):
        if t >= end_at:
            return ("end", round((t - end_at) * 10)), (lambda: frame_short(P, work, states[-1][2], t, cache, end=True, t_end=t - end_at))
        st = state_at(states, t)
        key = (id(st), int(t) if st["k"] == "think" else 0)
        return key, (lambda: frame_short(P, work, st, t, cache))
    render(fr, total, (1080, 1920), work / f"short{n}.wav", out / f"short{n}.mp4")
    return total


def thumb(P, out, work, n=2):
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), (30, 22, 16))
    pic = load_pic(work, n).resize((800, 600), Image.LANCZOS)
    im.paste(pic, (20, 100))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 96), fill=(0, 0, 0))
    d.text((W / 2, 50), "昭和なつかしクイズ", font=f_bold(76), fill=(255, 214, 0), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((1050, 300), "これ", font=f_bold(150), fill=(255, 255, 255), anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))
    d.text((1050, 470), "なに？", font=f_bold(150), fill=(255, 214, 0), anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))
    d.text((1050, 640), "全5問", font=f_bold(70), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
    im.save(out / "thumbnail.jpg", quality=92)


def sheet(P, out, work):
    tiles = []
    for it in P["items"]:
        t = Image.new("RGB", (560, 480), "white")
        t.paste(load_pic(work, it["id"]).resize((560, 420)), (0, 0))
        ImageDraw.Draw(t).text((280, 450), f"第{it['id']}問 {it['name']}（{it['era']}）", font=f_round(26), fill=INK, anchor="mm")
        tiles.append(t)
    S = Image.new("RGB", (570 * 3, 490 * 2), (220, 220, 220))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % 3) * 570, (i // 3) * 490))
    S.save(out / "items_sheet.png")


def record_time(out, step, sec):
    p = out / "timing.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"total_sec_by_step": {}}
    tot = data["total_sec_by_step"]; tot[step] = round(tot.get(step, 0) + sec, 1)
    data["total_sec_all"] = round(sum(tot.values()), 1)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    out = Path(sys.argv[1]).resolve(); step = sys.argv[2]
    P = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    work = Path.home() / ".cache/koyomi" / out.name; work.mkdir(parents=True, exist_ok=True)
    steps = ["voice", "long", "short", "thumb", "sheet"] if step == "all" else [step]
    for s in steps:
        t0 = time.time()
        if s == "voice":
            voice(P, out, work)
        elif s == "long":
            print("長尺", long_video(P, out, work), "秒")
        elif s == "short":
            n = int(sys.argv[3]) if len(sys.argv) > 3 else P.get("short_item", 2)
            print("ショート", short_video(P, out, work, n), "秒")
        elif s == "thumb":
            thumb(P, out, work, P.get("thumb_item", 2))
        elif s == "sheet":
            sheet(P, out, work)
        record_time(out, {"voice": "音声", "long": "書き出し（長尺）", "short": "書き出し（ショート）", "thumb": "サムネ", "sheet": "確認画像"}[s], time.time() - t0)


if __name__ == "__main__":
    main()
