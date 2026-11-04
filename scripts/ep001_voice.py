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

# 声に渡す文字（字幕とは別）。監査の差し戻し(3)：「山道」が「サンドウ」と読まれたため、かなにする。
VOICE_TEXT = {
    "q3_card": "第3問、中級。やまみちです。",
    # うんちくは plan.md 4-7 の「声に渡す文（かっこなし）」そのもの。実際の読みは下の VOICE_KANA で指定する
    "u2": "もみじは、葉の色が変わることをあらわす、むかしのことば、もみつから生まれたといわれます。",
    "u3": "万葉集のころは、黄色い葉と書いて、もみちと読むのが、ふつうだったそうです。",
    "u4": "紅葉と書くことがふえたのは、平安時代からだそうです。",
}
# うんちくは、かぎかっこで声が切れ、「もみつ」「もみち」も途中で切れて読まれたので、
# かっこを外したうえで、アクセントつきのカナ（AquesTalk記法。' はアクセント核、/ は区切り、、は短い間）で渡す。
VOICE_KANA = {
    "u2": "モ'ミジワ、ハノ'/イロ'ガ/カワル'/コト'ヲ/アラワ'ス、ムカシノ'/コトバ'、モミツカラ'/ウマレタト'/イワレマ'ス",
    "u3": "マンヨ'オシュウノ/コ'ロワ、キイロイ'/ハ'ト/カ'イテ、モミチト'/ヨ'ムノガ、フツウダッタ'/ソ'オデス",
    # 再審査の差し戻し：「紅葉」が「コオヨオ」と読まれた。plan.md 4-7 の指定どおり「もみじ」と読ませる
    "u4": "モ'ミジト/カ'ク/コト'ガ/フエ'タノワ、ヘエアンジダ'イカラダ/ソ'オデス",
}


def query(text, kana=None):
    q = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{ENGINE}/audio_query?speaker={SPEAKER}&text={urllib.parse.quote(text)}", method="POST"), timeout=60))
    if kana:
        q["accent_phrases"] = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{ENGINE}/accent_phrases?speaker={SPEAKER}&is_kana=true&text={urllib.parse.quote(kana)}", method="POST"), timeout=60))
    return q


def kana_of(q):
    """確認用：区切り（/）と間（、）つきのカナ"""
    return "".join("".join(m["text"] for m in ap["moras"]) + ("、" if ap.get("pause_mora") else "/") for ap in q["accent_phrases"])


def synth(text, out, kana=None):
    q = query(text, kana)

    q.update(speedScale=SPEED, outputSamplingRate=48000, outputStereo=False,
                 prePhonemeLength=0.05, postPhonemeLength=0.15, volumeScale=1.0)
    req = urllib.request.Request(f"{ENGINE}/synthesis?speaker={SPEAKER}", data=json.dumps(q).encode(),
                                 headers={"Content-Type": "application/json"})
    Path(out).write_bytes(urllib.request.urlopen(req, timeout=120).read())
    with wave.open(str(out)) as w:
        return w.getnframes() / w.getframerate(), kana_of(q)


if __name__ == "__main__":
    work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
    res = []
    for lid, t0, text, face, t_end in lines():
        vt = VOICE_TEXT.get(lid, text).replace("「", "").replace("」", "")
        dur, kana = synth(vt, work / f"voice_{lid}.wav", VOICE_KANA.get(lid))
        res.append({"id": lid, "start": t0, "dur": round(dur, 2), "slot": round(t_end - t0, 2), "fits": t0 + dur <= t_end,
                    "voice_text": vt, "kana": kana})
        print(f"{lid:9s} {t0:7.1f}s  {dur:5.2f}s / slot {t_end - t0:5.2f}s  {'OK' if res[-1]['fits'] else 'OVER'}  {text}  ->  {kana}")
    (work / "voice.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
