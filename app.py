"""Flask-интерфейс рекомендательной системы по покемонам."""

from __future__ import annotations

import io
import os

import pandas as pd
from flask import Flask, redirect, render_template, request, send_file, url_for

import recommender as rec
import reviews_store as rev

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(APP_DIR, "Pokemon.csv")

app = Flask(__name__)


def load_df() -> pd.DataFrame:
    if not os.path.isfile(CSV_PATH):
        raise FileNotFoundError(f"Нет файла {CSV_PATH}")
    return pd.read_csv(CSV_PATH)


@app.route("/", methods=["GET", "POST"])
def index():
    df = load_df()
    results = None
    weak = None
    name_hits = None
    range_hits = None
    error = None
    variant = request.values.get("variant", "default")

    if request.method == "POST":
        action = request.form.get("action", "recommend")
        cfg = rec.scoring_config_variant(variant)
        try:
            if action == "recommend":
                q = request.form.get("query", "")
                top_n = int(request.form.get("top_n", 5))
                scored = rec.rank_pokemon(df, q, top_n=top_n, cfg=cfg)
                results = scored
            elif action == "weak":
                top_n = int(request.form.get("top_n", 5))
                weak = rec.weak_rank(df, top_n=top_n)
            elif action == "name":
                sub = request.form.get("name_sub", "")
                name_hits = rec.filter_by_name(df, sub).head(50)
            elif action == "range":
                stat = request.form.get("stat", "attack")
                lo = float(request.form.get("low", 0))
                hi = float(request.form.get("high", 9999))
                range_hits = rec.filter_by_stat_range(df, stat, lo, hi).head(200)
            elif action == "review":
                rev.add_review(
                    request.form.get("pokemon_name", ""),
                    int(request.form.get("rating", 5)),
                    request.form.get("review_text", ""),
                )
                return redirect(url_for("index"))
        except Exception as e:  # noqa: BLE001 — показ пользователю
            error = str(e)

    stats = rev.stats_by_pokemon()

    def as_records(frame):
        if frame is None:
            return None
        return frame.to_dict(orient="records")

    return render_template(
        "index.html",
        results=as_records(results),
        weak=as_records(weak),
        name_hits=as_records(name_hits),
        range_hits=as_records(range_hits),
        stats=stats,
        error=error,
        variant=variant,
    )


@app.route("/export/stats.csv")
def export_stats():
    rows = rev.stats_by_pokemon()
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="pokemon_review_stats.csv",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
