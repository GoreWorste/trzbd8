"""JSON-хранилище отзывов и агрегированная статистика."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "reviews.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_reviews(path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_reviews(items: List[Dict[str, Any]], path: str = DEFAULT_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_review(
    pokemon_name: str,
    rating: int,
    text: str,
    path: str = DEFAULT_PATH,
) -> Dict[str, Any]:
    items = load_reviews(path)
    entry = {
        "pokemon_name": pokemon_name.strip(),
        "rating": int(rating),
        "text": text.strip(),
        "created_at": _utc_now(),
    }
    items.append(entry)
    save_reviews(items, path)
    return entry


def stats_by_pokemon(path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    items = load_reviews(path)
    by: Dict[str, Dict[str, Any]] = {}
    for r in items:
        name = r.get("pokemon_name") or ""
        if name not in by:
            by[name] = {
                "pokemon_name": name,
                "review_count": 0,
                "rating_sum": 0,
                "text_chars": 0,
            }
        by[name]["review_count"] += 1
        by[name]["rating_sum"] += int(r.get("rating") or 0)
        by[name]["text_chars"] += len(str(r.get("text") or ""))
    out = []
    for v in by.values():
        c = v["review_count"]
        v["avg_rating"] = round(v["rating_sum"] / c, 2) if c else 0.0
        del v["rating_sum"]
        out.append(v)
    return sorted(out, key=lambda x: (-x["review_count"], x["pokemon_name"]))
