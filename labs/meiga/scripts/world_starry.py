"""試作W1：星月夜。H4（いきなり絵に落ちる＋誘い）→ 白 → 目を開く → ゴッホの画風の一人称の3Dの世界。
段階ごとに実行する（できたものは作り直さない＝お金を二重に使わない）：
  python3 scripts/world_starry.py img    # 一人称の静止画（Gemini 3 Pro Image）
  python3 scripts/world_starry.py vid    # 静止画を1コマ目にした動画（Veo 3.1 Fast 720p）
  python3 scripts/world_starry.py build  # フックとつないで1本にする（無料）
"""
import os, sys, subprocess, wave
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import proto as P

W = os.path.join(P.ROOT, "work", "W1_starry"); os.makedirs(W, exist_ok=True)
OUT = os.path.join(P.ROOT, "out", "world"); os.makedirs(OUT, exist_ok=True)
REF = os.path.join(P.ROOT, "src", "starry_night.jpg")
OW, OH, FPS, SR = P.OW, P.OH, P.FPS, P.SR

STYLE = ("Painted entirely in Vincent van Gogh's late style exactly like the reference painting 'The Starry Night' (1889): "
         "thick impasto oil paint, visible short directional brushstrokes everywhere including the walls, ground and air, "
         "swirling cobalt and ultramarine sky, glowing yellow stars with halos, a crescent moon. "
         "Not photorealistic, not 3D render, not digital illustration: it must look like a real oil painting on canvas, "
         "yet with real perspective and depth as if the viewer is standing inside the painting. No text, no people, no frame.")

SHOTS = [
    dict(key="s1_window",
         img=("First-person point of view, standing in a small room of the Saint-Paul asylum in Saint-Remy at night, "
              "looking out through an open window with iron bars. Through the window: the exact view of The Starry Night - "
              "the huge swirling sky, the flame-like dark cypress on the left, the sleeping village with a church steeple "
              "and rolling blue hills. The dim room interior (window frame, stone sill, bars) frames the view. Vertical 9:16. ") + STYLE,
         vid=("First-person POV, the camera slowly and steadily moves forward toward the window and almost through it. "
              "The stars pulse and the swirls in the sky slowly turn, like paint flowing. Everything stays a thick Van Gogh "
              "oil painting with visible brushstrokes; no photorealism. Sound: quiet night wind and distant crickets only, "
              "no music, no speech.")),
    dict(key="s2_village",
         img=("First-person point of view at eye level, standing on a dirt path at the edge of the little village from "
              "The Starry Night, at night. A giant flame-shaped cypress towers on the left, small houses with warm yellow "
              "lit windows ahead, the church steeple, and above everything the enormous swirling starry sky taking up the "
              "upper half of the frame. Vertical 9:16. ") + STYLE,
         vid=("First-person POV walking slowly forward along the path, then the camera gently tilts up toward the "
              "enormous swirling sky. The swirls rotate, the stars and moon glow and shimmer, the dark green cypress "
              "sways gently in the wind (it is a tree, never on fire, no flames). Every frame keeps the same thick impasto Van Gogh brushstroke texture as the first frame, never becoming smooth "
              "or cartoon-like. Sound: soft footsteps on dirt, night wind, crickets, no music, no speech.")),
]

# ナレーション（世界に入ってから）。(開始秒, 文)  ※開始秒は世界パートの頭から
NARR = [
    (0.6, "1889年。南フランスの療養院。"),
    (3.6, "ゴッホは、この窓から\n夜明け前の空を見ていた。"),
    (8.6, "外へ出ると、\n空は燃えるように渦を巻いていた。"),
    (13.4, "これが、\nゴッホが見た夜。"),
]

def stage_img():
    import vertex as V
    for s in SHOTS:
        p = os.path.join(W, s["key"] + ".png")
        if not os.path.exists(p):
            V.image(s["img"], p, refs=[REF], what=f"W1星月夜 {s['key']} 静止画")
            print("image", p)

def stage_vid():
    import vertex as V
    for s in SHOTS:
        p = os.path.join(W, s["key"] + ".mp4")
        if not os.path.exists(p):
            V.video(s["vid"], os.path.join(W, s["key"] + ".png"), p, sec=8, what=f"W1星月夜 {s['key']} 動画")
            print("video", p)

def read_clip(path):
    cap = cv2.VideoCapture(path); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(f)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 24
    idx = np.round(np.arange(0, len(fr) / src_fps, 1 / FPS) * src_fps).astype(int)
    out = []
    for i in idx[idx < len(fr)]:
        f = fr[i]; h, w = f.shape[:2]; s = max(OW / w, OH / h)
        f = cv2.resize(f, (int(w * s + 0.5), int(h * s + 0.5)), interpolation=cv2.INTER_AREA)
        y0 = (f.shape[0] - OH) // 2; x0 = (f.shape[1] - OW) // 2
        out.append(f[y0:y0 + OH, x0:x0 + OW].astype(np.float32) / 255)
    return out

def clip_audio(path, sec):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    n = int(sec * SR)
    return np.pad(a, (0, max(0, n - len(a))))[:n]

def stage_build():
    hook = os.path.join(P.ROOT, "out", "hooks2", "H4_星月夜_いきなり落ちる_誘い.mp4")
    if not os.path.exists(hook):
        import hooks2; hooks2.render(*[h for h in hooks2.HOOKS if h[0].startswith("H4")][0])
    c1 = read_clip(os.path.join(W, "s1_window.mp4")); c2 = read_clip(os.path.join(W, "s2_village.mp4"))
    XF = int(0.8 * FPS)  # 窓→村 のつなぎ（白っぽく溶かす）
    frames = []
    for i, f in enumerate(c1):
        t = i / FPS
        # 白の中で目を開く：まぶたの外は白→だんだん消える
        m = P.eyelid(np.ones((OH, OW, 1), np.float32), P.ease((t - 0.05) / 0.9) * 0.6 + 0.4 * P.ease((t - 0.6) / 0.6))
        w = 1 - P.ease(t / 1.3)
        f = f * m + (1 - m) * w + m * w * 0.6 * (1 - P.ease(t / 0.9))
        frames.append(f)
    for j in range(XF):  # 窓の外へ抜ける：白へ寄せて次へ
        k = (j + 1) / XF; a = frames[-XF + j]; b = c2[j]
        glow = np.sin(np.pi * k) * 0.55
        frames[-XF + j] = np.clip(a * (1 - k) + b * k + glow, 0, 1)
    frames += c2[XF:]
    T = len(frames) / FPS
    for i in range(len(frames)):  # 字幕
        t = i / FPS; cur = None
        for s, line in NARR:
            if t >= s: cur = (s, line)
        a = 0.0
        if cur:
            nxt = [s for s, _ in NARR if s > cur[0]]; end = nxt[0] if nxt else T
            a = P.ease((t - cur[0]) / 0.25) * (1 - P.ease((t - (end - 0.3)) / 0.3))
        if i > len(frames) - int(0.8 * FPS):  # 最後は黒へ
            frames[i] = frames[i] * (1 - P.ease((i - (len(frames) - int(0.8 * FPS))) / (0.8 * FPS)))
        frames[i] = P.overlay(frames[i], None, cur[1] if cur else None, 0, a)
    raw = os.path.join(W, "world.mp4")
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (OW, OH))
    for f in frames:
        vw.write(f if f.dtype == np.uint8 else (np.clip(f, 0, 1) * 255).astype(np.uint8))
    vw.release()
    # 音：Veoの環境音（小さめ）＋ナレーション
    amb = np.concatenate([clip_audio(os.path.join(W, "s1_window.mp4"), len(c1) / FPS)[:int((len(c1) - XF) / FPS * SR)],
                          clip_audio(os.path.join(W, "s2_village.mp4"), len(c2) / FPS)])
    audio = np.zeros(int((T + 0.5) * SR), np.float32); audio[:len(amb)] += amb[:len(audio)] * 0.5
    for s, line in NARR:
        v = P.tts(line); st = int(s * SR); audio[st:st + len(v)] += v[:max(0, len(audio) - st)]
    wav = os.path.join(W, "world.wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    world = os.path.join(W, "world_av.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", str(SR), "-ac", "1", "-shortest", world], check=True)
    final = os.path.join(OUT, "W1_星月夜_H4落ちる_一人称の世界.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", hook, "-i", world, "-filter_complex",
                    "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "1", final], check=True)
    print("done", final, round(6 + T, 1), "sec")

if __name__ == "__main__":
    {"img": stage_img, "vid": stage_vid, "build": stage_build}[sys.argv[1]]()
