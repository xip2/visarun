#!/usr/bin/env python3
"""Генерирует флаги и карточки стран для всех slug'ов из БД.

Источники (интернет не используется):
  - main/data/country_map.json — code -> slug / alpha_2 / name (выгрузка из psql)
  - country-cards/flag-icon-css/flags/4x3/<alpha2>.svg — флаги
  - country-cards/data.json — реальные визовые данные для 24 стран

Результат:
  - main/static/main/flags/<slug>.svg
  - main/data/cards_auto.json — карточки, которые views.py подмешивает к ручным.
"""

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "main" / "data"
FLAGS_SRC = ROOT / "country-cards" / "flag-icon-css" / "flags" / "4x3"
FLAGS_DST = ROOT / "main" / "static" / "main" / "flags"
DATA_JSON = ROOT / "country-cards" / "data.json"

DASH = "\u2014"  # —


def fmt_date(value):
    if not value:
        return None
    parts = value.split("-")
    if len(parts) == 3:
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    return value


def fallback_card(slug, alpha2, name):
    return {
        "flag": f"main/flags/{slug}.svg",
        "status": DASH,
        "status_key": "unknown",
        "rule": "Визовые правила ещё не внесены",
        "signed": DASH,
        "from": DASH,
        "until": DASH,
        "stay": DASH,
        "stay_note": "визовые данные пока не внесены",
        "capital": DASH,
        "religion": DASH,
        "religion_share": "",
        "cities": [],
        "people_note": "",
        "note": "Карточка подключена: визовые данные, население и источники будут добавлены позже.",
        "source_label": DASH,
        "source_url": "",
    }


def card_from_data_json(item, slug):
    until = item.get("until")
    card = {
        "flag": f"main/flags/{slug}.svg",
        "status": "действует",
        "status_key": "active",
        "rule": item.get("rule") or DASH,
        "signed": fmt_date(item.get("signed")) or DASH,
        "from": fmt_date(item.get("from")) or DASH,
        "until": fmt_date(until) if until else "срок не ограничен",
        "stay": item.get("stay") or DASH,
        "stay_note": item.get("stayNote") or "",
        "capital": item.get("capital") or DASH,
        "religion": item.get("religion") or DASH,
        "religion_share": item.get("religionShare") or "",
        "cities": item.get("cities") or [],
        "people_note": "",
        "note": item.get("note") or "",
        "source_label": (item.get("source") or {}).get("label") or DASH,
        "source_url": (item.get("source") or {}).get("url") or "",
    }
    return card


def main():
    country_map = json.loads((DATA / "country_map.json").read_text(encoding="utf-8"))
    data_by_alpha2 = {
        item["id"].lower(): item
        for item in json.loads(DATA_JSON.read_text(encoding="utf-8"))
    }

    cards = {}
    copied = 0
    missing_svg = []
    for row in country_map:
        slug = row["slug"]
        alpha2 = (row.get("alpha2") or "").strip()
        if not alpha2:
            # Абхазия, Южная Осетия, Нормандские острова — без ISO-кода, флага нет.
            missing_svg.append(f"{slug} (no alpha2)")
            continue
        src = FLAGS_SRC / f"{alpha2.lower()}.svg"
        if not src.exists():
            missing_svg.append(slug)
            continue
        FLAGS_DST.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, FLAGS_DST / f"{slug}.svg")
        copied += 1

        if alpha2.lower() in data_by_alpha2:
            card = card_from_data_json(data_by_alpha2[alpha2.lower()], slug)
        else:
            card = fallback_card(slug, alpha2, row.get("name") or slug)
        cards[slug] = card

    out = DATA / "cards_auto.json"
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flags copied: {copied}, cards: {len(cards)}, skipped: {missing_svg}")


if __name__ == "__main__":
    main()
