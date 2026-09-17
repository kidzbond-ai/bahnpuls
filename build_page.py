"""Baut aus dem Archiv eine fertige Seite fuer Redaktionen.

Die Grafiken werden als data-URI eingebettet, damit die Seite ohne externe
Abhaengigkeiten funktioniert. Platzhalter im Template sind mit @ markiert,
damit die geschweiften Klammern des CSS unangetastet bleiben.

Ausgabe: reports/pressemappe.html
"""

import base64
import pathlib
import re

import pandas as pd

ROOT = pathlib.Path(__file__).parent
REPORTS = ROOT / "reports"
TEMPLATE = REPORTS / "pressemappe_template.html"
OUT = REPORTS / "pressemappe.html"

MONTHS = {
    "01": "Januar", "02": "Februar", "03": "März", "04": "April",
    "05": "Mai", "06": "Juni", "07": "Juli", "08": "August",
    "09": "September", "10": "Oktober", "11": "November", "12": "Dezember",
}


def img(name):
    data = base64.b64encode((REPORTS / name).read_bytes()).decode()
    return "data:image/png;base64," + data


def num(value, digits=1):
    """Deutsche Schreibweise: Dezimalkomma statt Punkt."""
    return format(value, "." + str(digits) + "f").replace(".", ",")


def de(period):
    year, month = period.split("-")
    return MONTHS[month] + " " + year


def load():
    df = pd.read_csv(ROOT / "data" / "db_punctuality.csv")
    wide = df.pivot(index="period", columns="metric", values="value_pct")
    wide.columns = ["FV_betr", "NV_betr", "PV_betr", "FV_reis"]
    wide["schere"] = (wide.FV_reis - wide.FV_betr).round(1)
    return wide


def build():
    df = load()
    last = df.index[-1]
    row = df.loc[last]
    worst = df.FV_reis.idxmin()

    rows = []
    for period, r in df.iterrows():
        rows.append(
            "        <tr><td>" + de(period) + "</td>"
            + "<td>" + num(r.PV_betr) + "</td>"
            + "<td>" + num(r.NV_betr) + "</td>"
            + "<td>" + num(r.FV_betr) + "</td>"
            + "<td>" + num(r.FV_reis) + "</td>"
            + "<td>" + ("+" if r.schere >= 0 else "") + num(r.schere) + "</td></tr>"
        )

    values = {
        "@LAST@": de(last),
        "@FIRST@": de(df.index[0]),
        "@MONTHS@": str(len(df)),
        "@LATE_FV@": str(round(100 - row.FV_betr)),
        "@FV_BETR@": num(row.FV_betr),
        "@NV_BETR@": num(row.NV_betr),
        "@SCHERE_NOW@": num(row.schere),
        "@SCHERE_MAX@": num(df.schere.max()),
        "@SCHERE_MAX_MONTH@": de(df.schere.idxmax()),
        "@WORST@": de(worst),
        "@WORST_VAL@": num(df.FV_reis.min()),
        "@TABLE_ROWS@": "\n".join(rows),
        "@IMG_HUNDRED@": img("puenktlichkeit_100zuege.png"),
        "@IMG_REIHE@": img("puenktlichkeit_reihe.png"),
        "@IMG_SCHERE@": img("puenktlichkeit_schere.png"),
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    for token, value in values.items():
        assert token in html, "Platzhalter fehlt im Template: " + token
        html = html.replace(token, value)
    leftover = re.findall(r"@[A-Z_]{3,}@", html)
    assert not leftover, "unersetzte Platzhalter: " + ", ".join(sorted(set(leftover)))

    OUT.write_text(html, encoding="utf-8")
    print("geschrieben: %s  (%s Bytes)" % (OUT.relative_to(ROOT), format(OUT.stat().st_size, ",")))


if __name__ == "__main__":
    build()
