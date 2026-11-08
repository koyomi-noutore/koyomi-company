"""ショート動画（knowledge/shorts.md 2026-11-08 CEO決定）。長尺の1問を、縦1080×1920に作り直す。追加の画像費用はゼロ。
make_episode.py の short（作る）・short-check（数値チェック）・short-upload（非公開アップロード）から呼ぶ。

画面（上から）：
  上の帯（0〜200px）  … 「3つ見つけられる？」と問題の情報。セリフがある間は字幕に替わる。帯の下に残り時間のバー
  上の絵（205〜1015）  … 元の絵（a）720×810
  下の絵（1025〜1835）… 違いのある絵（b）720×810
  左右に180pxずつのすき間を空ける（ショートの画面の右側のボタンが絵にかからないように）
流れ（plan.json の short で変えられる）：
  0秒から出題（冒頭で声の問いかけ）→ solve 秒で時間切れ →「答えです」→ 赤丸を1つずつ（上下の絵の両方）→ 長尺への案内（こよみ先生が小さく登場）
成果物：<回>/short/video.mp4（git管理外）・timeline.json・description.md、作業：<作業>/short/
"""
import json, math, subprocess, sys, wave
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from episode_plan import plan

W, H, FPS = 1080, 1920, 30
BG = (246, 236, 216)
INK = (59, 47, 37)
RED = (220, 30, 30)
PW, PH = 720, 810
PX = (W - PW) // 2
YS = {"a": 205, "b": 1025}
BAND_H = 200
LEVEL_COLOR = {"初級": (96, 150, 90), "中級": (214, 128, 48), "上級": (176, 62, 52)}
SR = 48000

DEFAULT = {"solve": 25.0, "intro_at": 0.3, "answer_gap": 3.2, "end_len": 6.0,
           "intro": "上と下の絵で、違いが3つあります。見つけられますか。",
           "end": "続きは、長い動画で。ほかにも問題がありますよ。",
           "end_title": "続きは 長い動画で", "end_sub": "全5問・1問90秒"}


def cfg():
    c = dict(DEFAULT)
    c.update(plan().get("short", {}))
    return c


def lines(ep):
    """ショートのセリフ：(id, 開始秒, 字幕, 声に渡す文)。答えのセリフは長尺と同じ文を使う。"""
    import ep_timeline as T
    c = cfg()
    q = c["question"]
    Q = {x["q"]: x for x in plan()["questions"]}[q]
    L = [("s_intro", c["intro_at"], c["intro"])]
    a0 = c["solve"]
    L.append(("s_ans0", a0, Q.get("answers_intro", "答えです。")))
    for i, d in enumerate(Q["diffs"]):
        L.append((f"s_ans{i + 1}", a0 + 1.6 + c["answer_gap"] * i, d["line"]))
    end_at = a0 + 1.6 + c["answer_gap"] * len(Q["diffs"]) + 0.4
    L.append(("s_end", end_at + 0.4, c["end"]))
    total = round(end_at + c["end_len"], 1)
    return [(lid, t, s, T.to_voice(lid, s)) for lid, t, s in L], end_at, total


# ---------- 声 ----------
def voice(ep, work):
    import ep_voice as V
    vd = Path(work) / "short"; vd.mkdir(parents=True, exist_ok=True)
    vj = vd / "voice.json"
    old = {v["id"]: v for v in json.loads(vj.read_text(encoding="utf-8"))} if vj.exists() else {}
    L, end_at, total = lines(ep)
    res = []
    for i, (lid, t0, sub, vt) in enumerate(L):
        wav = vd / f"voice_{lid}.wav"
        if wav.exists() and old.get(lid, {}).get("voice_text") == vt:
            dur = old[lid]["dur"]
        else:
            dur = V.tts(vt, wav)
            import datetime
            with open(vd / "usage.jsonl", "a", encoding="utf-8") as f:   # 声の費用の記録（cost.md 用）
                f.write(json.dumps({"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                    "id": lid, "chars": len(vt)}, ensure_ascii=False) + "\n")
        nxt = L[i + 1][1] if i + 1 < len(L) else total
        if lid == "s_intro":
            nxt = cfg()["solve"]
        res.append({"id": lid, "start": t0, "dur": round(dur, 2), "slot": round(nxt - t0, 2), "fits": t0 + dur <= nxt,
                    "subtitle": sub, "voice_text": vt})
    vj.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ---------- 音 ----------
VOICE_RMS_DB = -16.0   # セリフごとにそろえる声の大きさ（話している所の平均）


def voice_stats(work):
    """声のファイルごとの、割れ（最大振幅に近いサンプル数）と大きさ。第1回ショートで1セリフだけ割れて大きかった反省（2026-11-08）。"""
    import ep_audio as A
    vd = Path(work) / "short"
    out = {}
    for v in json.loads((vd / "voice.json").read_text(encoding="utf-8")):
        x = A.read_wav(vd / f"voice_{v['id']}.wav")
        sp = x[np.abs(x) > 0.01]
        out[v["id"]] = {"clipped": int((np.abs(x) >= 0.976).sum()), "rms_db": round(float(20 * np.log10(np.sqrt(np.mean(sp ** 2)) + 1e-12)), 1)}
    return out


def remux(ep, work):
    """絵はそのままで、音だけを作り直した mix.wav に入れ替える（動画の映像は再エンコードしない）。"""
    out = Path(ep) / "short"
    tmp = out / "video_newaudio.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "video.mp4"), "-i", str(Path(work) / "short" / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(tmp)], check=True)
    tmp.replace(out / "video.mp4")
    return out / "video.mp4"


def audio(ep, work):
    import ep_audio as A
    vd = Path(work) / "short"
    vs = json.loads((vd / "voice.json").read_text(encoding="utf-8"))
    _, end_at, total = lines(ep)
    n = int(total * SR)
    tt = np.arange(n) / SR
    def put(track, x, at):
        s = int(at * SR); e = min(n, s + len(x)); track[s:e] += x[:e - s]
    vo = np.zeros(n)
    for v in vs:
        x = A.read_wav(vd / f"voice_{v['id']}.wav")
        x = x * (10 ** (VOICE_RMS_DB / 20) / (np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) + 1e-9))   # セリフごとに声の大きさをそろえる
        put(vo, np.clip(x, -0.9, 0.9), v["start"])
    vo *= 0.6 / max(np.abs(vo).max(), 1e-9)
    sfx = np.zeros(n)
    c = cfg()
    put(sfx, A.chime((79, 84, 88), 0.18), 0.0)
    for k in range(5):                                  # 残り5秒〜1秒
        put(sfx, A.tick(), c["solve"] - 5 + k)
    put(sfx, A.chime((84, 79), 0.25), c["solve"])
    for v in vs:
        if v["id"].startswith("s_ans") and v["id"] != "s_ans0":
            put(sfx, A.pon(), v["start"])
    put(sfx, A.chime((84, 88), 0.25, 0.16), end_at)
    music = A.bgm()[:n]
    act = np.convolve((np.abs(vo) > 0.01).astype(float), np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same") > 0.02
    duck = np.convolve(np.where(act, 0.45, 1.0), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    gain = np.where(tt < c["solve"], 0.7, 1.0)
    fade = np.clip(np.minimum(tt / 0.3, (total - tt) / 1.5), 0, 1)
    mix = vo + sfx + music * gain * duck * fade
    mix *= min(1.0, 0.95 / np.abs(mix).max())
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(vd / "mix.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


# ---------- 画面 ----------
CTX = {}


@lru_cache(maxsize=64)
def font(size):
    return ImageFont.truetype(CTX["font"], size)


def setup(ep, work, fontp):
    CTX.update(ep=Path(ep), work=Path(work), font=str(fontp))
    c = cfg()
    q = c["question"]
    ans = {Q["q"]: Q for Q in json.loads((Path(ep) / "answers.json").read_text(encoding="utf-8"))["questions"]}[q]
    CTX["Q"] = ans
    CTX["voice"] = json.loads((Path(work) / "short" / "voice.json").read_text(encoding="utf-8"))
    CTX["lines"], CTX["end_at"], CTX["total"] = lines(ep)
    pics = {}
    for side in "ab":
        im = Image.open(Path(ep) / f"q{q}_{side}.png").convert("RGB").crop(tuple(ans["content_px"]))
        pics[side] = im.resize((PW, PH), Image.LANCZOS)
    base = Image.new("RGB", (W, H), BG)
    for side, y in YS.items():
        base.paste(pics[side], (PX, y))
        ImageDraw.Draw(base).rectangle((PX - 4, y - 4, PX + PW + 3, y + PH + 3), outline=(255, 250, 238), width=4)
    CTX["base"] = base
    owl = Path(work) / "owl" / "koyomi_smile.png"
    CTX["owl"] = Image.open(owl).convert("RGBA").resize((300, 300), Image.LANCZOS) if owl.exists() else None
    CTX["owl_s"] = CTX["owl"].resize((150, 150), Image.LANCZOS) if CTX["owl"] else None


def circle_box(a, side):
    """answers.json の画面座標（960×1080の絵の上）を、ショートの絵（720×810）の上の座標にする。"""
    k = PW / 960
    x0, y0, x1, y1 = a[f"circle_{side}_screen"]
    return PX + x0 * k, YS[side] + y0 * k, PX + x1 * k, YS[side] + y1 * k


def wrap2(s, maxc):
    """2行までに分ける。句読点の後ろを優先し、なければ助詞の後ろ。行の頭に句読点が来ないようにする。"""
    if len(s) <= maxc:
        return [s]
    for marks in ("。", "、", "がはをにのとで"):
        best = None
        for k in range(1, len(s)):
            if s[k - 1] in marks and s[k] not in "、。" and len(s[:k]) <= maxc and len(s[k:]) <= maxc:
                sc = abs(len(s[:k]) - len(s[k:]))
                if best is None or sc < best[0]:
                    best = (sc, [s[:k], s[k:]])
        if best:
            return best[1]
    return [s[:maxc], s[maxc:]]


def current_sub(t):
    for v in CTX["voice"]:
        end = v["start"] + v["dur"] + 0.5
        if v["start"] <= t < min(end, v["start"] + v["slot"]):
            return v["subtitle"]
    return None


def render(t):
    c = cfg()
    Q = CTX["Q"]
    im = CTX["base"].copy()
    d = ImageDraw.Draw(im)
    # 上の帯
    d.rectangle((0, 0, W, BAND_H), fill=(52, 40, 30))
    sub = current_sub(t) if t < CTX["end_at"] else None
    if sub:
        ls = wrap2(sub, 17)
        size = 64 if len(ls) == 1 else 58
        for i, l in enumerate(ls):
            y = BAND_H / 2 + (i - (len(ls) - 1) / 2) * (size + 14)
            d.text((W / 2, y), l, font=font(size), fill=(255, 255, 255), anchor="mm")
    else:
        d.text((W / 2, 78), "3つ見つけられる？", font=font(84), fill=(255, 214, 0), anchor="mm", stroke_width=3, stroke_fill=(30, 20, 10))
        col = LEVEL_COLOR[Q["level"]]
        d.rounded_rectangle((W / 2 - 250, 138, W / 2 - 90, 186), 16, fill=col)
        d.text((W / 2 - 170, 162), Q["level"], font=font(36), fill=(255, 255, 255), anchor="mm")
        d.text((W / 2 - 70, 162), f"秋の間違いさがし・{Q['scene']}", font=font(36), fill=(255, 240, 200), anchor="lm")
    # 残り時間のバー（帯の下）
    if t < c["solve"]:
        frac = max(0.0, 1 - t / c["solve"])
        rem = c["solve"] - t
        col = (110, 180, 100) if rem > 10 else (236, 170, 50) if rem > 5 else (230, 70, 60)
        d.rectangle((0, BAND_H, W, BAND_H + 5), fill=(225, 212, 188))
        d.rectangle((0, BAND_H, int(W * frac), BAND_H + 5), fill=col)
        if rem <= 5:
            d.text((PX + PW - 20, YS["a"] + 20), str(math.ceil(rem - 1e-6)), font=font(96), fill=(230, 70, 60), anchor="ra",
                   stroke_width=5, stroke_fill=(255, 255, 255))
    # 答え合わせ（上下の絵の両方に赤丸、番号札）
    shown = [i for i, v in enumerate(v for v in CTX["voice"] if v["id"].startswith("s_ans") and v["id"] != "s_ans0")
             if t >= [v for v in CTX["voice"] if v["id"] == f"s_ans{i + 1}"][0]["start"]]
    for i in shown:
        a = Q["answers"][i]
        for side in "ab":
            x0, y0, x1, y1 = circle_box(a, side)
            d.ellipse((x0 - 9, y0 - 9, x1 + 9, y1 + 9), outline=(255, 255, 255), width=10)
            d.ellipse((x0 - 6, y0 - 6, x1 + 6, y1 + 6), outline=RED, width=6)
    for i in shown:
        a = Q["answers"][i]
        for side in "ab":
            x0, y0, x1, y1 = circle_box(a, side)
            bx, by = min(max(x1 + 4, PX + 22), PX + PW - 22), min(max(y0 - 4, YS[side] + 22), YS[side] + PH - 22)
            d.ellipse((bx - 22, by - 22, bx + 22, by + 22), fill=RED, outline=(255, 255, 255), width=3)
            d.text((bx, by + 1), str(i + 1), font=font(30), fill=(255, 255, 255), anchor="mm")
    # こよみ先生（冒頭に小さく）
    if CTX["owl_s"] is not None and t < 3.0:
        o = CTX["owl_s"]
        bob = int(6 * math.sin(2 * math.pi * t / 1.6))
        im.paste(o, ((PX - o.width) // 2, YS["a"] + 30 + bob), o)    # 左のすき間に
    # 長尺への案内
    e0 = CTX["end_at"]
    if t >= e0:
        k = min(1.0, (t - e0) / 0.5)
        layer = Image.new("RGBA", (W, H), (246, 236, 216, int(235 * k)))
        ld = ImageDraw.Draw(layer)
        a = int(255 * k)
        ld.text((W / 2, 640), c["end_title"], font=font(96), fill=INK + (a,), anchor="mm")
        ld.text((W / 2, 780), c["end_sub"], font=font(64), fill=(176, 62, 52, a), anchor="mm")
        ld.text((W / 2, 880), "こよみ先生のまいにち脳トレ", font=font(48), fill=(110, 84, 60, a), anchor="mm")
        ld.polygon([(W / 2 - 60, 960), (W / 2 + 60, 960), (W / 2, 1040)], fill=(214, 128, 48, a))
        im.paste(layer, (0, 0), layer)
        if CTX["owl"] is not None:
            o = CTX["owl"].copy(); o.putalpha(o.getchannel("A").point(lambda v: int(v * k)))
            bob = int(8 * math.sin(2 * math.pi * t / 1.6))
            im.paste(o, ((W - o.width) // 2, 1120 + bob), o)
    return im


def video(ep, work, fontp):
    setup(ep, work, fontp)
    out = Path(ep) / "short"; out.mkdir(exist_ok=True)
    total = CTX["total"]
    tmp = Path(work) / "short" / "video_noaudio.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "animation", "-pix_fmt", "yuv420p", str(tmp)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close(); assert p.wait() == 0
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(Path(work) / "short" / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(out / "video.mp4")], check=True)
    tmp.unlink()
    (out / "timeline.json").write_text(json.dumps({
        "size": [W, H], "fps": FPS, "total_sec": total, "question": cfg()["question"], "solve_sec": cfg()["solve"],
        "end_card_at": CTX["end_at"], "pictures": {"a": [PX, YS["a"], PX + PW, YS["a"] + PH], "b": [PX, YS["b"], PX + PW, YS["b"] + PH]},
        "lines": CTX["voice"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return out / "video.mp4"


def contact_sheet(ep, work, fontp, path):
    """目で見る確認用：冒頭・出題中・残り3秒・答え合わせ・案内の5枚を縮小して1枚に。"""
    setup(ep, work, fontp)
    c = cfg()
    ts = [0.5, 12.0, c["solve"] - 2.5, CTX["end_at"] - 0.3, CTX["total"] - 1.0]
    sheet = Image.new("RGB", (5 * 360 + 40, 640 + 50), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(ts):
        sheet.paste(render(t).resize((360, 640), Image.LANCZOS), (i * 370, 40))
        d.text((i * 370 + 4, 4), f"{t:.1f}s", font=font(30), fill=(0, 0, 0))
    sheet.save(path)
    return path


def check(ep, work):
    """数値チェック：大きさ・長さ（15〜45秒）・声が枠に収まるか。"""
    out = Path(ep) / "short"
    problems = []
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json",
                        str(out / "video.mp4")], capture_output=True, text=True, check=True)
    pr = json.loads(r.stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    dur = float(pr["format"]["duration"])
    if (v["width"], v["height"]) != (W, H):
        problems.append(f"大きさが {v['width']}×{v['height']}")
    if not 15 <= dur <= 45:
        problems.append(f"長さ {dur:.1f}秒 が15〜45秒の外")
    vs = json.loads((Path(work) / "short" / "voice.json").read_text(encoding="utf-8"))
    over = [x["id"] for x in vs if not x["fits"]]
    if over:
        problems.append(f"声が枠に収まらない：{over}")
    st = voice_stats(work)
    clipped = [k for k, v in st.items() if v["clipped"] > 0]
    if clipped:
        problems.append(f"声が割れている（元の声のファイル）：{clipped}")
    lv = [v["rms_db"] for v in st.values()]
    if max(lv) - min(lv) > 6:
        problems.append(f"セリフごとの声の大きさの差が6dBを超える（元の声のファイル）：{st}")
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    res = {"voice": st, "duration": round(dur, 2), "size": [v["width"], v["height"]], "question": tl["question"], "problems": problems}
    (out / "check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def description(ep):
    """<回>/short/description.md を書く（長尺のタイトル・URLは <回>/upload.json から）。タイトル・説明欄は youtube_upload が読む。"""
    c = cfg()
    up = json.loads((Path(ep) / "upload.json").read_text(encoding="utf-8"))
    Q = {x["q"]: x for x in plan()["questions"]}[c["question"]]
    title = c.get("title") or f"3つ見つけられる？秋の間違いさがし（{Q['scene']}・{Q['level']}）#Shorts"
    desc = (f"上と下の絵で、違いを3つ探してください。{Q['level']}の1問です。\n\n"
            f"続きは長い動画で（全5問・1問90秒）\n{up['title']}\n{up['url']}\n\n"
            "こよみ先生のまいにち脳トレ：平日の朝6時に新しい問題をお届けします。\n\n"
            "【クレジット】\n音声：Fish Audio（AIで合成した音声です）\nBGM・効果音：オリジナル（プログラムで作成）\n\n"
            "#Shorts #間違い探し #脳トレ #頭の体操")
    tags = "脳トレ, 間違い探し, 頭の体操, 秋の間違い探し, シニア 脳トレ, ショート, こよみ先生"
    md = (f"# {plan()['episode']} ショート 投稿用メタデータ\n\n- 長尺：{up['url']}（関連動画はCEOがStudioで設定する。APIでは設定できない）\n\n"
          f"## タイトル\n```\n{title}\n```\n\n## 説明欄\n```\n{desc}\n```\n\n## タグ\n```\n{tags}\n```\n")
    (Path(ep) / "short" / "description.md").write_text(md, encoding="utf-8")
