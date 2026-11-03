"""第1回のセリフを VOICEVOX（冥鳴ひまり ノーマル、speaker=14）で音声にする。
使い方: python3 scripts/ep001_voice.py <作業フォルダ>   （VOICEVOXエンジン http://localhost:50021 が必要）
作業フォルダに voice_<id>.wav（48kHz・モノラル）と voice.json（各セリフの長さと、枠に収まるか）を書く。
クレジット表記：VOICEVOX:冥鳴ひまり
"""
import json, sys, urllib.parse, urllib.request, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ep001_timeline import lines

ENGINE, SPEAKER, SPEED = "http://localhost:50021", 14, 0.88


def synth(text, out):
    q = urllib.request.urlopen(urllib.request.Request(
        f"{ENGINE}/audio_query?speaker={SPEAKER}&text={urllib.parse.quote(text)}", method="POST"), timeout=60)
    query = json.load(q)
    query.update(speedScale=SPEED, outputSamplingRate=48000, outputStereo=False,
                 prePhonemeLength=0.05, postPhonemeLength=0.15, volumeScale=1.0)
    req = urllib.request.Request(f"{ENGINE}/synthesis?speaker={SPEAKER}", data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"})
    Path(out).write_bytes(urllib.request.urlopen(req, timeout=120).read())
    with wave.open(str(out)) as w:
        return w.getnframes() / w.getframerate()


if __name__ == "__main__":
    work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
    res = []
    for lid, t0, text, face, t_end in lines():
        dur = synth(text, work / f"voice_{lid}.wav")
        res.append({"id": lid, "start": t0, "dur": round(dur, 2), "slot": round(t_end - t0, 2), "fits": t0 + dur <= t_end})
        print(f"{lid:9s} {t0:7.1f}s  {dur:5.2f}s / slot {t_end - t0:5.2f}s  {'OK' if res[-1]['fits'] else 'OVER'}  {text}")
    (work / "voice.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
