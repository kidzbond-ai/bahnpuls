"""Baut die Uebersichtsseite zu offenen Bahndaten (Studienprojekt).

Nutzt die Hilfsfunktionen aus build_page.py mit, damit Zahlformat und
Bildeinbettung an beiden Stellen identisch sind.

Ausgabe: reports/uebersicht.html
"""

import datetime as dt
import pathlib
import re

from build_page import MONTHS, de, img, load, num

ROOT = pathlib.Path(__file__).parent
TEMPLATE = ROOT / "reports" / "uebersicht_template.html"
OUT = ROOT / "reports" / "uebersicht.html"


def checked_on():
    today = dt.date.today()
    return "%d. %s %d" % (today.day, MONTHS["%02d" % today.month], today.year)


def build():
    df = load()
    last = df.index[-1]
    row = df.loc[last]

    values = {
        "@CHECKED@": checked_on(),
        "@FIRST@": de(df.index[0]),
        "@LAST@": de(last),
        "@MONTHS@": str(len(df)),
        "@LATE_FV@": str(round(100 - row.FV_betr)),
        "@FV_BETR@": num(row.FV_betr),
        "@NV_BETR@": num(row.NV_betr),
        "@SCHERE_NOW@": num(row.schere),
        "@SCHERE_MAX@": num(df.schere.max()),
        "@SCHERE_MAX_MONTH@": de(df.schere.idxmax()),
        "@IMG_HUNDRED@": img("puenktlichkeit_100zuege.png"),
        "@IMG_REIHE@": img("puenktlichkeit_reihe.png"),
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
