"""Archiviert die monatlichen Puenktlichkeitswerte der Deutschen Bahn.

Die DB zeigt auf ihrer Seite nur ein gleitendes Fenster von ca. 14 Monaten.
Aeltere Werte verschwinden ersatzlos. Dieses Skript liest die Tabelle aus und
fuehrt sie in ein wachsendes Archiv zusammen.

Quelle: https://www.deutschebahn.com/de/konzern/konzernprofil/zahlen_fakten/
"""

import csv
import datetime as dt
import pathlib
import re
import sys

import lxml.html
import requests

URL = (
    "https://www.deutschebahn.com/de/konzern/konzernprofil/zahlen_fakten/"
    "puenktlichkeitswerte-6878476"
)
ROOT = pathlib.Path(__file__).parent
ARCHIVE = ROOT / "data" / "db_punctuality.csv"
RAW_DIR = ROOT / "data" / "raw"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "mae": 3, "mrz": 3, "apr": 4,
    "mai": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "okt": 10, "nov": 11, "dez": 12,
}


def month_num(cell):
    """'Mär' -> 3. Gibt None zurueck, wenn die Zelle kein Monat ist."""
    key = cell.strip().lower().replace("ä", "ae").replace("\xe4", "ae")[:3]
    return MONTHS.get(key)


def fetch(url=URL):
    resp = requests.get(url, headers={"User-Agent": "bahnpuls/1.0"}, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def parse(html):
    """Liefert [(YYYY-MM, metrik, wert), ...] aus der Puenktlichkeitstabelle."""
    doc = lxml.html.fromstring(html)
    tables = doc.xpath("//table")
    if not tables:
        raise ValueError("Keine Tabelle auf der Seite gefunden")

    rows = [
        [" ".join(c.text_content().split()) for c in tr.xpath("./th|./td")]
        for tr in tables[0].xpath(".//tr")
    ]

    # Monatszeile: die Zeile mit den meisten erkannten Monatsnamen.
    month_idx = max(range(len(rows)), key=lambda i: sum(month_num(c) is not None for c in rows[i]))
    month_row = rows[month_idx]
    months = [(pos, month_num(c)) for pos, c in enumerate(month_row) if month_num(c)]
    if len(months) < 2:
        raise ValueError("Monatszeile nicht erkannt")

    # Jahre stehen in einer Zeile oberhalb der Monate.
    years = []
    for r in rows[:month_idx]:
        years += [int(y) for c in r for y in re.findall(r"\b(20\d{2})\b", c)]
    years = sorted(set(years))
    if not years:
        raise ValueError("Keine Jahreszahl im Tabellenkopf gefunden")

    # Jahr pro Spalte: beim Rueckwaertssprung (Dez -> Jan) ins naechste Jahr.
    col_period, yi = [], 0
    prev = None
    for _, m in months:
        if prev is not None and m < prev:
            yi += 1
        if yi >= len(years):
            raise ValueError("Mehr Jahreswechsel als Jahre im Kopf")
        col_period.append(f"{years[yi]}-{m:02d}")
        prev = m
    if years[yi] != years[-1]:
        raise ValueError(f"Jahreszuordnung inkonsistent: endet {years[yi]}, erwartet {years[-1]}")

    positions = [pos for pos, _ in months]
    out = []
    for r in rows[month_idx + 1:]:
        name = r[0].strip() if r else ""
        if not name:
            continue
        for period, pos in zip(col_period, positions):
            if pos >= len(r):
                continue
            raw = r[pos].strip().replace("%", "").strip()
            if not re.fullmatch(r"\d{1,3},\d+", raw):
                continue
            out.append((period, name, float(raw.replace(",", "."))))
    if not out:
        raise ValueError("Keine Messwerte extrahiert")
    return out


def merge(records, today):
    """Fuehrt neue Werte ins Archiv. Bestehende Zeilen bleiben erhalten."""
    archive = {}
    if ARCHIVE.exists():
        with ARCHIVE.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                archive[(row["period"], row["metric"])] = row

    added = changed = 0
    for period, metric, value in records:
        key = (period, metric)
        existing = archive.get(key)
        if existing is None:
            archive[key] = {
                "period": period, "metric": metric, "value_pct": f"{value}",
                "first_seen": today, "last_seen": today, "source_url": URL,
            }
            added += 1
        else:
            if float(existing["value_pct"]) != value:
                existing["value_pct"] = f"{value}"
                changed += 1
            existing["last_seen"] = today

    fields = ["period", "metric", "value_pct", "first_seen", "last_seen", "source_url"]
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for key in sorted(archive):
            writer.writerow(archive[key])
    return added, changed, len(archive)


def main():
    today = dt.date.today().isoformat()
    html = fetch()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = RAW_DIR / f"db_punctuality_{today}.html"
    snapshot.write_text(html, encoding="utf-8")

    records = parse(html)
    added, changed, total = merge(records, today)

    print(f"Seite gelesen:   {len(html):,} Zeichen -> {snapshot.name}")
    print(f"Extrahiert:      {len(records)} Werte")
    print(f"Neu:             {added}")
    print(f"Revidiert:       {changed}")
    print(f"Archiv gesamt:   {total} Zeilen -> {ARCHIVE.relative_to(ROOT)}")
    if changed:
        print("Hinweis: Die DB hat Werte nachtraeglich korrigiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
