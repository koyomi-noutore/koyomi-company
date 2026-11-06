"""回ごとの企画（outputs/<回>/plan.json）を読む。make_episode.py が環境変数 KOYOMI_EPISODE_DIR に回のフォルダを入れる。"""
import json
import os
from functools import lru_cache
from pathlib import Path


def episode_dir():
    d = os.environ.get("KOYOMI_EPISODE_DIR")
    if not d:
        raise SystemExit("KOYOMI_EPISODE_DIR が設定されていません（scripts/make_episode.py から実行してください）")
    return Path(d)


@lru_cache(maxsize=1)
def plan():
    return json.loads((episode_dir() / "plan.json").read_text(encoding="utf-8"))


def questions():
    return {Q["q"]: Q for Q in plan()["questions"]}
