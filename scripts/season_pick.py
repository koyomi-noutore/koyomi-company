"""ショートの季節の色を season_theme.json から引く共通の部品（2026-11-24 CEO厳守：ショートの背景は長尺と同じ季節の色）。

    from season_pick import pick
    name, theme = pick(season="冬")        # name＝"winter_A"、theme＝その色の辞書（bg・ink・panel・accent・edge・alert・hit など。RGBの組）

季節の決め方（先に見つかったものを使う）：
  1. 環境変数 KOYOMI_THEME（テーマ名。長尺と同じ）
  2. 引数 theme（テーマ名。例 "winter_B"）
  3. 引数 season（"冬" などの季節、またはテーマ名。季節は season_default を通す。冬なら winter_A）
  4. どちらも無ければ「冬」（今は全部冬。season_default["冬"]）
"""
import json
import os
from pathlib import Path

THEME_FILE = Path(__file__).parent / "season_theme.json"
DEFAULT_SEASON = "冬"


def pick(season=None, theme=None):
    cfg = json.loads(THEME_FILE.read_text(encoding="utf-8"))
    themes, default = cfg["themes"], cfg["season_default"]
    name = os.environ.get("KOYOMI_THEME") or theme
    if not name and season:
        name = season if season in themes and season not in default else default.get(season, season)
    name = name or default[DEFAULT_SEASON]
    if name not in themes:
        raise SystemExit(f"季節の見た目 {name!r} が season_theme.json にありません")
    return name, {k: (tuple(v) if isinstance(v, list) and k != "particles" else v) for k, v in themes[name].items() if not k.startswith("_")}
