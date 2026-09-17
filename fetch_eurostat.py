"""Laedt die Eurostat-Bahndatensaetze und legt sie als tidy CSV ab.

Anders als bei der DB verschwinden bei Eurostat keine Daten: die volle
Zeitreihe steht jederzeit zur Verfuegung. Es wird deshalb nicht archiviert,
sondern bei jedem Lauf komplett neu geladen. Fuer die Nachvollziehbarkeit
spaeterer Revisionen bleibt je Lauf ein Rohdaten-Snapshot liegen.

Quelle: Eurostat Dissemination API (JSON-stat 2.0), kein API-Schluessel noetig.
"""

import csv
import datetime as dt
import json
import pathlib
import sys

import requests

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# Nur laufend gepflegte Datensaetze. Eingestellte Reihen (rail_go_typeall endet
# 2016, rail_ac_catvict endet 2015) sind bewusst nicht enthalten.
DATASETS = {
    "rail_pa_total":   "Fahrgaeste gesamt",
    "rail_pa_typepas": "Fahrgaeste nach Verkehrsart",
    "rail_pa_intcmng": "Internationale Fahrgaeste nach Einstiegsland",
    "rail_go_total":   "Gueterverkehr gesamt",
    "rail_if_tracks":  "Gleislaenge nach Elektrifizierung",
    "rail_if_line_ga": "Streckenlaenge nach Spurweite",
    "rail_if_electri": "Elektrifizierte Strecken nach Stromsystem",
    "rail_eq_locon":   "Lokomotiven und Triebwagen nach Energiequelle",
    "tran_sf_railac":  "Eisenbahnunfaelle nach Unfallart",
    "tran_sf_railvi":  "Unfallopfer nach Unfallart und Personengruppe",
}

ROOT = pathlib.Path(__file__).parent
OUT_DIR = ROOT / "data" / "eurostat"
RAW_DIR = ROOT / "data" / "raw" / "eurostat"
VERSIONS = OUT_DIR / "_versions.json"


def fetch(code):
    resp = requests.get(
        f"{API}/{code}",
        params={"format": "JSON", "lang": "EN"},
        headers={"User-Agent": "bahnpuls/1.0"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def to_rows(data):
    """JSON-stat 2.0 -> Liste flacher Zeilen.

    'value' ist ein duenn besetztes Dict, dessen Schluessel ein zeilenweiser
    Flachindex ueber die Dimensionen in 'id' mit den Groessen in 'size' ist.
    """
    dims, sizes = data["id"], data["size"]
    status = data.get("status", {})

    # Position -> Code und Position -> Label, je Dimension.
    codes, labels = [], []
    for dim in dims:
        cat = data["dimension"][dim]["category"]
        index = cat["index"]
        if isinstance(index, dict):
            ordered = [None] * len(index)
            for code, pos in index.items():
                ordered[pos] = code
        else:
            ordered = list(index)
        codes.append(ordered)
        labels.append(cat.get("label", {}))

    # Dimensionen mit nur einer Auspraegung tragen keine Information.
    keep = [i for i, n in enumerate(sizes) if n > 1 or dims[i] == "time"]

    rows = []
    for flat, value in data["value"].items():
        rest, position = int(flat), [0] * len(sizes)
        for axis in range(len(sizes) - 1, -1, -1):
            rest, position[axis] = divmod(rest, sizes[axis])

        row = {}
        for axis in keep:
            code = codes[axis][position[axis]]
            name = "period" if dims[axis] == "time" else dims[axis]
            row[name] = code
            if dims[axis] != "time":
                row[f"{name}_label"] = labels[axis].get(code, code)
        row["value"] = value
        row["flag"] = status.get(flat, "")
        rows.append(row)

    if rows:
        fields = list(rows[0])
        rows.sort(key=lambda r: tuple(str(r.get(k, "")) for k in fields))
    return rows


def write_csv(path, rows):
    fields = list(rows[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    today = dt.date.today().isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = []

    # Eurostat aktualisiert nur wenige Male im Jahr. Ohne diesen Abgleich
    # schriebe jeder Lauf identische Dateien neu und blaehte das Repo auf.
    known = json.loads(VERSIONS.read_text(encoding="utf-8")) if VERSIONS.exists() else {}

    print(f"{'Datensatz':17} {'Zeilen':>7} {'Zeitraum':>13} {'Stand':>11}  Titel")
    print("-" * 96)

    for code, title in DATASETS.items():
        try:
            data = fetch(code)
            stamp = data["updated"]
            target = OUT_DIR / f"{code}.csv"
            if known.get(code) == stamp and target.exists():
                print(f"{code:17} {'-':>7} {'unveraendert':>13} {stamp[:10]:>11}  {title}")
                continue

            (RAW_DIR / f"{code}_{today}.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            rows = to_rows(data)
            if not rows:
                raise ValueError("keine Werte im Datensatz")
            write_csv(target, rows)
            known[code] = stamp

            periods = sorted({r["period"] for r in rows})
            span = f"{periods[0]}-{periods[-1]}"
            print(f"{code:17} {len(rows):>7,} {span:>13} {data['updated'][:10]:>11}  {title}")
        except Exception as exc:
            failures.append((code, exc))
            print(f"{code:17} {'FEHLER':>7} {type(exc).__name__}: {exc}")

    VERSIONS.write_text(json.dumps(known, indent=2, sort_keys=True), encoding="utf-8")

    print("-" * 96)
    print(f"{len(DATASETS) - len(failures)} von {len(DATASETS)} aktuell -> {OUT_DIR.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
