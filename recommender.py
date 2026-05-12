"""
Рекомендательная система: взвешенный перебор с настраиваемыми весами.
Легко расширяется новыми стратегиями через ScoringConfig и функции keyword_scorers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

# Русские названия типов → английские идентификаторы в CSV (как в veekun: Fire, Water...)
TYPE_RU_TO_EN: Dict[str, str] = {
    "огонь": "Fire",
    "вода": "Water",
    "трава": "Grass",
    "электричество": "Electric",
    "электрик": "Electric",
    "псих": "Psychic",
    "психический": "Psychic",
    "дракон": "Dragon",
}

KEYWORDS = ("сильный", "быстрый", "живучий", "умный")

StatRow = pd.Series


def _norm_series(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


@dataclass
class ScoringConfig:
    """Веса для расширения и сравнения подходов."""

    type_match_min: float = 40.0
    type_match_max: float = 50.0
    keyword_caps: Dict[str, float] = field(
        default_factory=lambda: {
            "сильный": 35.0,
            "быстрый": 35.0,
            "живучий": 35.0,
            "умный": 35.0,
        }
    )
    # Хеш от id для стабильного «случайного» числа в диапазоне очков за тип
    use_id_jitter_for_type: bool = True


def type_match_points(pokemon_id: int, cfg: ScoringConfig) -> float:
    if not cfg.use_id_jitter_for_type:
        return (cfg.type_match_min + cfg.type_match_max) / 2
    span = cfg.type_match_max - cfg.type_match_min
    jitter = (abs(hash(str(pokemon_id))) % 1000) / 1000.0 * span
    return cfg.type_match_min + jitter


def keyword_scorers(df: pd.DataFrame) -> Dict[str, Callable[[StatRow], float]]:
    """Нормализация по всему датасету; возвращает вклад 0..1 для ключевого слова."""
    n_attack = _norm_series(df["attack"])
    n_sp_atk = _norm_series(df["sp_attack"])
    n_speed = _norm_series(df["speed"])
    n_hp = _norm_series(df["hp"])
    n_def = _norm_series(df["defense"])
    n_sp_def = _norm_series(df["sp_defense"])
    n_total = _norm_series(df["total"])
    idx = df.index

    def strong(row: StatRow) -> float:
        i = row.name
        return float(0.35 * n_attack.loc[i] + 0.35 * n_sp_atk.loc[i] + 0.30 * n_total.loc[i])

    def fast(row: StatRow) -> float:
        i = row.name
        return float(n_speed.loc[i])

    def sturdy(row: StatRow) -> float:
        i = row.name
        return float(0.4 * n_hp.loc[i] + 0.3 * n_def.loc[i] + 0.3 * n_sp_def.loc[i])

    def smart(row: StatRow) -> float:
        i = row.name
        return float(0.55 * n_sp_atk.loc[i] + 0.45 * n_sp_def.loc[i])

    return {
        "сильный": strong,
        "быстрый": fast,
        "живучий": sturdy,
        "умный": smart,
    }


def parse_query_types(query_lower: str) -> List[str]:
    found: List[str] = []
    for ru, en in TYPE_RU_TO_EN.items():
        if ru in query_lower:
            if en not in found:
                found.append(en)
    return found


def parse_query_keywords(query_lower: str) -> List[str]:
    return [k for k in KEYWORDS if k in query_lower]


def theoretical_max_score(
    types_mentioned: List[str], keywords: List[str], cfg: ScoringConfig
) -> float:
    total = 0.0
    if types_mentioned:
        total += len(types_mentioned) * cfg.type_match_max
    for kw in keywords:
        total += cfg.keyword_caps.get(kw, 0.0)
    if total <= 0:
        return 1.0
    return total


def score_dataframe(
    df: pd.DataFrame, query: str, cfg: Optional[ScoringConfig] = None
) -> pd.DataFrame:
    """
    Взвешенный перебор: для каждой строки считаем сумму весов.
    Возвращает копию с колонками score, max_score, compatibility_pct.
    """
    cfg = cfg or ScoringConfig()
    q = query.lower().strip()
    types_en = parse_query_types(q)
    kws = parse_query_keywords(q)
    scorers = keyword_scorers(df)
    max_score = theoretical_max_score(types_en, kws, cfg)

    scores = []
    for _, row in df.iterrows():
        s = 0.0
        t1 = str(row["type1"])
        t2 = "" if pd.isna(row.get("type2")) else str(row["type2"])
        pid = int(row["id"])
        for t in types_en:
            if t == t1 or t == t2:
                s += type_match_points(pid, cfg)
        for kw in kws:
            cap = cfg.keyword_caps.get(kw, 0.0)
            fn = scorers.get(kw)
            if fn and cap > 0:
                s += cap * float(fn(row))
        scores.append(s)

    out = df.copy()
    out["score"] = scores
    out["max_score"] = max_score
    out["compatibility_pct"] = (out["score"] / out["max_score"] * 100.0).clip(0, 100)
    return out


def rank_pokemon(
    df: pd.DataFrame,
    query: str,
    top_n: int = 5,
    ascending: bool = False,
    cfg: Optional[ScoringConfig] = None,
) -> pd.DataFrame:
    scored = score_dataframe(df, query, cfg)
    scored = scored.sort_values("score", ascending=ascending).head(top_n)
    return scored


def filter_by_name(df: pd.DataFrame, name_sub: str) -> pd.DataFrame:
    sub = name_sub.strip().lower()
    if not sub:
        return df.iloc[0:0]
    mask = df["name"].str.lower().str.contains(re.escape(sub), regex=True)
    return df.loc[mask].copy()


def filter_by_stat_range(
    df: pd.DataFrame, stat: str, low: float, high: float
) -> pd.DataFrame:
    stat = stat.strip().lower()
    col_map = {
        "hp": "hp",
        "атака": "attack",
        "attack": "attack",
        "защита": "defense",
        "defense": "defense",
        "спец. атака": "sp_attack",
        "спец атака": "sp_attack",
        "sp_attack": "sp_attack",
        "спец. защита": "sp_defense",
        "sp_defense": "sp_defense",
        "скорость": "speed",
        "speed": "speed",
        "сумма": "total",
        "total": "total",
    }
    col = col_map.get(stat)
    if col is None or col not in df.columns:
        raise ValueError(f"Неизвестная характеристика: {stat}")
    m = df[col].between(low, high, inclusive="both")
    return df.loc[m].copy()


def weak_rank(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Топ «слабых» по сумме базовых характеристик (минимальный total)."""
    return df.sort_values("total", ascending=True).head(top_n).copy()


def scoring_config_variant(variant: str) -> ScoringConfig:
    """Два дополнительных набора весов для сравнения подходов."""
    v = (variant or "default").lower()
    if v == "strict":
        return ScoringConfig(
            type_match_min=40.0,
            type_match_max=42.0,
            keyword_caps={"сильный": 25.0, "быстрый": 25.0, "живучий": 25.0, "умный": 25.0},
        )
    if v == "generous":
        return ScoringConfig(
            type_match_min=48.0,
            type_match_max=50.0,
            keyword_caps={"сильный": 45.0, "быстрый": 45.0, "живучий": 45.0, "умный": 45.0},
        )
    return ScoringConfig()
