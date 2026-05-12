"""Интерактивный цикл ввода (консоль)."""

from __future__ import annotations

import os

import pandas as pd

import recommender as rec
import reviews_store as rev

CSV_PATH = os.path.join(os.path.dirname(__file__), "Pokemon.csv")


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    print("Загружено покемонов:", len(df))
    while True:
        print(
            "\nМеню:\n"
            "  1 — рекомендация по текстовому запросу (топ-N)\n"
            "  2 — поиск по имени\n"
            "  3 — топ слабых по сумме характеристик\n"
            "  4 — фильтр по диапазону характеристики\n"
            "  5 — добавить отзыв\n"
            "  6 — статистика отзывов и выгрузка CSV\n"
            "  0 — выход"
        )
        choice = input("Выбор: ").strip()
        if choice == "0":
            break
        if choice == "1":
            q = input("Запрос (напр. «огонь быстрый сильный»): ")
            n = int(input("Сколько показать (N): ") or "5")
            variant = input("Вариант весов default/strict/generous [default]: ").strip() or "default"
            cfg = rec.scoring_config_variant(variant)
            top = rec.rank_pokemon(df, q, top_n=n, cfg=cfg)
            _print_table(top)
        elif choice == "2":
            sub = input("Подстрока имени: ")
            hits = rec.filter_by_name(df, sub)
            print(f"Найдено: {len(hits)}")
            print(hits.head(20).to_string(index=False))
        elif choice == "3":
            n = int(input("Сколько показать: ") or "5")
            w = rec.weak_rank(df, top_n=n)
            print(w[["name", "type1", "type2", "total", "hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]].to_string(index=False))
        elif choice == "4":
            stat = input("Характеристика (attack, hp, total, ...): ")
            lo = float(input("От: "))
            hi = float(input("До: "))
            r = rec.filter_by_stat_range(df, stat, lo, hi)
            print(f"Найдено: {len(r)}")
            print(r.head(30).to_string(index=False))
        elif choice == "5":
            name = input("Имя покемона (как в базе): ")
            rating = int(input("Оценка 1-5: "))
            text = input("Текст отзыва: ")
            rev.add_review(name, rating, text)
            print("Отзыв сохранён.")
        elif choice == "6":
            st = rev.stats_by_pokemon()
            print(pd.DataFrame(st).to_string(index=False))
            path = input("Сохранить CSV (Enter = pokemon_review_stats.csv): ").strip() or "pokemon_review_stats.csv"
            pd.DataFrame(st).to_csv(path, index=False, encoding="utf-8-sig")
            print("Сохранено:", path)
        else:
            print("Неизвестный пункт.")


def _print_table(top: pd.DataFrame) -> None:
    cols = [
        "name",
        "type1",
        "type2",
        "score",
        "max_score",
        "compatibility_pct",
        "hp",
        "attack",
        "defense",
        "sp_attack",
        "sp_defense",
        "speed",
    ]
    c = [c for c in cols if c in top.columns]
    print(top[c].to_string(index=False, float_format=lambda x: f"{x:.1f}"))


if __name__ == "__main__":
    main()
