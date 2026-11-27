"""フックだけの試作 第2版（各6秒前後）。
11/27のフィードバック：名画を一度見たことがある・画家の名前を知っている程度の人でも止まる強さにする。
狙い：1秒目に「絵が額縁から出てくる」ズレを起こし、言葉は問いかけをやめて
「誘い」「言い切り」「物語の一文」で比べる。最後は白く飛ばして、一人称の世界へ入る手前で終わる。
"""
import os, sys, subprocess, wave
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import proto as P

OUT = os.path.join(P.ROOT, "out", "hooks2"); os.makedirs(OUT, exist_ok=True)
OW, OH, FPS, SR = P.OW, P.OH, P.FPS, P.SR
ease = P.ease

def blob_mask(cx, cy, r, seed=0):
    """ふちがギザギザに広がる円（絵の具があふれる形）。"""
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    a = np.arctan2(yy - cy, xx - cx)
    rng = np.random.default_rng(seed); wob = np.zeros_like(a)
    for k in range(3, 9):
        wob += rng.uniform(0.02, 0.06) * np.sin(k * a + rng.uniform(0, 6.28))
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (r * (1 + wob) + 1e-3)
    return np.clip((1.0 - d) * 12, 0, 1)

def to_u8(fr):
    return fr if fr.dtype == np.uint8 else (np.clip(fr, 0, 1) * 255).astype(np.uint8)

def framed(d, t, amp, sc):
    ix, iy, iw, ih = d["inner"]
    return P.view(P.alive(d, t, amp), ix + iw / 2, iy + ih / 2, sc)

def render(name, painting, mode, line, title_top, T=6.0):
    d = P.load(painting, frame=True); dn = P.load(painting)
    ix, iy, iw, ih = d["inner"]
    fit = min(OW * 0.80 / iw, OH * 0.50 / ih)
    full = OH / dn["H"] * 1.05  # 画面いっぱいの倍率
    voice = P.tts(line); tv = len(voice) / SR
    T = max(T, tv + 2.2)
    raw = os.path.join(P.TMP, name + ".mp4")
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (OW, OH))
    for i in range(int(T * FPS)):
        t = i / FPS
        base = framed(d, t, 3, fit * (1 + 0.03 * t / T))
        if mode == "overflow":  # 絵が額縁からあふれて画面を飲み込む
            world = P.view(P.alive(dn, t, 6), dn["W"] * 0.45, dn["H"] * 0.45, full * (1.15 - 0.1 * t / T))
            r = 40 + 1400 * ease((t - 0.25) / 2.4) ** 1.3
            m = blob_mask(OW / 2, OH / 2, r) if t > 0.25 else np.zeros((OH, OW), np.float32)
            fr = base * (1 - m[..., None]) + world * m[..., None]
        elif mode == "wave_out":  # 北斎の波が額縁を突き破ってこちらへ
            img = dn["img"]; H, W = dn["H"], dn["W"]
            b, g, r_ = img[..., 0], img[..., 1], img[..., 2]
            wm = ((b >= r_ - 0.02) & (np.arange(W)[None, :] < 0.62 * W)).astype(np.float32)
            wm = cv2.GaussianBlur(wm, (0, 0), 1.2)
            k = 1 + 2.6 * ease((t - 0.3) / 1.4) ** 1.6
            ax, ay = 0.36 * W, 0.80 * H  # 波の根元を中心に大きくなる
            sc = fit * k
            M = np.float32([[sc, 0, OW / 2 - fit * (ix + iw / 2 - ix) + (ax) * (fit - sc) - 0], [0, sc, 0]])
            # 額縁内での絵の位置に合わせて、波の層だけを拡大して重ねる
            px0 = OW / 2 - fit * iw / 2; py0 = OH / 2 - fit * ih / 2
            Mx = np.float32([[sc, 0, px0 + ax * fit - ax * sc], [0, sc, py0 + ay * fit - ay * sc]])
            layer = cv2.warpAffine(P.alive(dn, t, 6), Mx, (OW, OH), flags=cv2.INTER_CUBIC)
            lm = cv2.warpAffine(wm, Mx, (OW, OH))
            fr = base * (1 - lm[..., None]) + layer * lm[..., None]
            shake = int(10 * np.exp(-((t - 1.2) / 0.25) ** 2) * np.sin(t * 90))
            fr = np.roll(fr, shake, axis=0)
        elif mode == "fall_in":  # 1コマ目から絵に落ちていく（ためなし）
            p = ease(t / (T - 0.6))
            ddd = P.load(painting)
            sc = fit * (iw / ddd["W"]) * np.exp(np.log(full * 3 / (fit * iw / ddd["W"])) * p ** 1.8)
            fr = P.view(P.alive(ddd, t, 6), ddd["W"] * 0.57, ddd["H"] * 0.86, sc)
            fr = P.radial_blur(fr, 0.2 * p ** 2)
        k = ease((t - (T - 0.7)) / 0.6)  # 最後は白へ
        fr = fr * (1 - k) + k
        fr = P.overlay(fr, title_top, line, ease(t / 0.2) * (1 - k), ease((t - 0.15) / 0.2) * (1 - k))
        vw.write(to_u8(fr))
    vw.release()
    audio = np.zeros(int((T + 1) * SR), np.float32)
    audio[int(0.15 * SR):int(0.15 * SR) + len(voice)] += voice
    w = P.whoosh(1.4); s = int(max(0.2, T - 1.6) * SR); audio[s:s + len(w)] += w
    wav = os.path.join(P.TMP, name + ".wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-i", wav, "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    os.path.join(OUT, name + ".mp4")], check=True)
    os.remove(raw); os.remove(wav); print("done", name, round(T, 1))

HOOKS = [
    ("H1_北斎_波が飛び出す_言い切り", "wave", "wave_out", "北斎の波が、\nこっちに来る。", ("葛飾北斎", "神奈川沖浪裏")),
    ("H2_叫び_絵があふれる_言い切り", "scream", "overflow", "叫んでいるのは、\nこの人じゃない。", ("ムンク", "叫び")),
    ("H3_星月夜_絵があふれる_物語", "starry", "overflow", "1889年、ゴッホは\n精神病院の窓から、この夜を見ていた。", ("ゴッホ", "星月夜")),
    ("H4_星月夜_いきなり落ちる_誘い", "starry", "fall_in", "今から、\nゴッホが見た夜に入ります。", ("ゴッホ", "星月夜")),
    ("H5_叫び_絵があふれる_誘い", "scream", "overflow", "あなたも今から、\nこの叫びを聞きます。", ("ムンク", "叫び")),
]

if __name__ == "__main__":
    only = sys.argv[1:]
    for h in HOOKS:
        if not only or any(o in h[0] for o in only):
            render(*h)
