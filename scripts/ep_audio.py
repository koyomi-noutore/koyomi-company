"""音（声・BGM・効果音）を1本のWAVにまとめる（make_episode.py から呼ぶ）。BGMと効果音はすべて numpy で合成したオリジナル（外部の音源は使わない）。
時刻は plan.json（ep_timeline）から読む。
"""
import json, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import ep_timeline as T

SR = 48000
N = int(T.TOTAL * SR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(1)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sustain_end=None):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ---------- BGM：やさしい和音のループ（80BPM、1小節3秒、4小節12秒） ----------
def bgm():
    beat = 0.75
    chords = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 67]]  # Cmaj7 Am7 Fmaj7 G
    loop = np.zeros(int(12 * SR))
    for ci, ch in enumerate(chords):
        s = int(ci * 3 * SR); n = int(3.2 * SR); tt = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * midi(m - 12) * tt) + 0.25 * np.sin(2 * np.pi * midi(m) * tt) for m in ch)
        pad *= env_adsr(n, 0.6, 0.8) * 0.035
        seg = loop[s:s + n]; seg += pad[:len(seg)]
        if s + n > len(loop):  # ループのつなぎ目へ回り込ませる
            loop[:s + n - len(loop)] += pad[len(seg):]
        # 木琴ふうのアルペジオ（8分音符）
        pattern = [ch[0] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 12]
        for k, m in enumerate(pattern):
            st = s + int(k * beat / 2 * SR); nn = int(0.7 * SR); tt = np.arange(nn) / SR
            note = (np.sin(2 * np.pi * midi(m) * tt) * np.exp(-tt * 5) + 0.2 * np.sin(2 * np.pi * midi(m) * 4 * tt) * np.exp(-tt * 18))
            note *= (0.05 if k % 2 == 0 else 0.035) * env_adsr(nn, 0.004, 0.05)
            e = min(len(loop), st + nn); loop[st:e] += note[:e - st]
    reps = int(np.ceil(N / len(loop)))
    return np.tile(loop, reps)[:N]


# ---------- 効果音 ----------
def tone(f, dur, decay, partials=((1, 1.0),), amp=0.3):
    tt = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f * p * tt) for p, a in partials) * np.exp(-tt * decay)
    return x * env_adsr(len(tt), 0.003, 0.02) * amp


def pon():  # 赤丸：ポン
    tt = np.arange(int(0.35 * SR)) / SR
    f = 700 * np.exp(-tt * 3) + 520
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-tt * 12) * env_adsr(len(tt), 0.002, 0.02) * 0.45


def chime(notes=(88, 84), gap=0.22, amp=0.22):  # ピンポン
    out = np.zeros(int((gap * len(notes) + 1.5) * SR))
    for i, m in enumerate(notes):
        x = tone(midi(m), 1.4, 3.0, ((1, 1), (2.76, 0.25), (5.4, 0.08)), amp)
        s = int(i * gap * SR); out[s:s + len(x)] += x
    return out


def tick(high=False):  # カウント音
    return tone(1320 if high else 990, 0.09, 40, ((1, 1), (2, 0.2)), 0.28)


def swoosh():  # 難易度カード
    n = int(0.5 * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    k = np.exp(-np.arange(200) / 30); k /= k.sum()
    x = np.convolve(noise, k, mode="same") - np.convolve(noise, np.ones(800) / 800, mode="same")
    return x * np.sin(np.pi * tt / 0.5) ** 2 * 0.25


def sparkle():  # ヒント：キラキラ
    out = np.zeros(int(1.6 * SR))
    for i, m in enumerate([84, 88, 91, 96, 100]):
        x = tone(midi(m), 0.9, 6, ((1, 1), (3, 0.15)), 0.12)
        s = int(i * 0.08 * SR); out[s:s + len(x)] += x
    return out


def fanfare():  # エンディング
    out = np.zeros(int(3 * SR))
    for i, m in enumerate([72, 76, 79, 84]):
        x = tone(midi(m), 1.6, 2.2, ((1, 1), (2, 0.3), (3, 0.1)), 0.2)
        s = int(i * 0.14 * SR); out[s:s + len(x)] += x
    return out


def add(track, x, at):
    s = int(at * SR); e = min(N, s + len(x)); track[s:e] += x[:e - s]


def sfx_events():
    ev = [(T.OPENING[0] + 0.2, chime((79, 84, 88), 0.18)), (T.UNCHIKU[0], chime((84, 88), 0.25, 0.16)), (T.ENDING[0], fanfare())]
    for q, s in T.Q_START.items():
        ev.append((s, swoosh()))
        ev.append((s + T.CARD, chime((88, 84))))  # 出題スタート
        ev.append((s + T.CARD + T.HINT_AT, sparkle()))
        for k in range(10):  # 残り10秒〜1秒
            ev.append((s + T.CARD + T.TEN_AT + k, tick()))
        ev.append((s + T.CARD + T.SOLVE, chime((84, 79), 0.25)))  # 時間切れ
    for lid, t0, *_ in T.lines():
        if "_ans" in lid and not lid.endswith("ans0"):
            ev.append((t0, pon()))
    return ev


def read_wav(p):
    with wave.open(str(p)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768


def main(voice_dir, out):
    voice = np.zeros(N)
    for lid, t0, *_ in T.lines():
        add(voice, read_wav(Path(voice_dir) / f"voice_{lid}.wav"), t0)
    voice *= 0.6 / np.abs(voice).max()
    sfx = np.zeros(N)
    for at, x in sfx_events():
        add(sfx, x, at)
    music = bgm()
    # BGMの音量：出題中（黙って探す時間）は少し下げ、声が出ている間はさらに下げる
    gain = np.ones(N)
    for s in T.Q_START.values():
        a, b = int((s + T.CARD) * SR), int((s + T.CARD + T.SOLVE) * SR)
        gain[a:b] = 0.6
    act = (np.abs(voice) > 0.01).astype(float)
    win = int(0.3 * SR)
    act = np.convolve(act, np.ones(win) / win, mode="same") > 0.02
    duck = np.where(act, 0.45, 1.0)
    duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    fade = np.clip(np.minimum(t_all / 1.5, (T.TOTAL - t_all) / 3.0), 0, 1)
    mix = voice + sfx + music * gain * duck * fade
    peak = np.abs(mix).max()
    if peak > 0.95:
        mix *= 0.95 / peak
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    speak = act > 0
    print(json.dumps({"peak_before_norm": round(float(peak), 3),
                      "voice_rms_db_while_speaking": round(rms(voice[speak]), 1),
                      "bgm_rms_db_while_speaking": round(rms((music * gain * duck * fade)[speak]), 1),
                      "bgm_rms_db_silent_solve": round(rms((music * gain * duck)[int((T.Q_START[min(T.Q_START)] + T.CARD + 12) * SR):int((T.Q_START[min(T.Q_START)] + T.CARD + 42) * SR)]), 1)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
