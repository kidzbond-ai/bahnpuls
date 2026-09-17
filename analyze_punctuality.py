"""Wertet das DB-Puenktlichkeitsarchiv aus und schreibt Bericht und Grafiken.

Erzeugt in reports/:
  puenktlichkeit.md            Bericht mit allen Tabellen
  puenktlichkeit_reihe.png     Monatsreihe der drei Kennzahlen
  puenktlichkeit_schere.png    Abstand Reisenden- zu Betriebspuenktlichkeit
"""

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).parent
REPORTS = ROOT / "reports"

# Kategoriale Slots 1-3 der validierten Palette (Hell-Modus).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dcdcd8"

# Die Schwellenwerte gehoeren in die Beschriftung: die drei Kennzahlen sind
# NICHT direkt vergleichbar. Betriebliche Puenktlichkeit misst je Verkehrshalt
# mit 5:59 min, Reisendenpuenktlichkeit misst den Fahrgast am Zielbahnhof mit
# 14:59 min und rechnet verpasste Anschluesse, Ausfaelle und Ersatzzuege ein.
NL = chr(10)

MONTHS_LONG = {
    "01": "Januar", "02": "Februar", "03": "März", "04": "April",
    "05": "Mai", "06": "Juni", "07": "Juli", "08": "August",
    "09": "September", "10": "Oktober", "11": "November", "12": "Dezember",
}

LABELS = {
    "NV_betr": "Nahverkehr, Züge" + NL + "(unter 6 Min.)",
    "FV_betr": "Fernverkehr, Züge" + NL + "(unter 6 Min.)",
    "FV_reis": "Fernverkehr, Reisende" + NL + "(unter 15 Min.)",
}
MONTHS_DE = {
    "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr", "05": "Mai", "06": "Jun",
    "07": "Jul", "08": "Aug", "09": "Sep", "10": "Okt", "11": "Nov", "12": "Dez",
}


def num(value, digits=1):
    """Deutsche Schreibweise: Dezimalkomma statt Punkt."""
    return format(value, "." + str(digits) + "f").replace(".", ",")


def load():
    df = pd.read_csv(ROOT / "data" / "db_punctuality.csv")
    wide = df.pivot(index="period", columns="metric", values="value_pct")
    wide.columns = ["FV_betr", "NV_betr", "PV_betr", "FV_reis"]
    wide["schere"] = (wide.FV_reis - wide.FV_betr).round(1)
    wide["abstand_nv_fv"] = (wide.NV_betr - wide.FV_betr).round(1)
    return wide[["PV_betr", "NV_betr", "FV_betr", "FV_reis", "schere", "abstand_nv_fv"]]


def tick_labels(periods):
    out = []
    for i, p in enumerate(periods):
        year, month = p.split("-")
        show_year = i == 0 or month == "01"
        out.append(f"{MONTHS_DE[month]}\n{year}" if show_year else MONTHS_DE[month])
    return out


def titleblock(fig, title, subtitle, size=14):
    fig.text(0.008, 0.955, title, fontsize=size, fontweight="bold",
             color=INK, va="top")
    fig.text(0.008, 0.885, subtitle, fontsize=9.5, color=MUTED, va="top")
    fig.text(0.008, 0.015, "Quelle: Deutsche Bahn AG, eigene Archivierung · bahnpuls",
             fontsize=8, color=MUTED)


def style(ax):
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def chart_series(df):
    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=200)
    x = range(len(df))

    series = (("NV_betr", AQUA), ("FV_betr", BLUE), ("FV_reis", ORANGE))
    for col, color in series:
        ax.plot(x, df[col], color=color, linewidth=2, marker="o",
                markersize=4.5, markerfacecolor=color, markeredgecolor="white",
                markeredgewidth=1.2, zorder=3, clip_on=False)

    # Direktbeschriftung traegt die Identitaet, nicht die Farbe allein. Die
    # Endwerte der beiden Fernverkehrsreihen liegen dicht beieinander, deshalb
    # werden die Beschriftungen auf einen Mindestabstand auseinandergezogen.
    MIN_GAP = 6.0
    placed = []
    for value, col, color in sorted(((df[c].iloc[-1], c, k) for c, k in series), reverse=True):
        y = value if not placed else min(value, placed[-1] - MIN_GAP)
        placed.append(y)
        ax.annotate(LABELS[col], (len(df) - 1, y),
                    xytext=(10, 0), textcoords="offset points",
                    color=color, fontsize=8.8, fontweight="bold", va="center",
                    linespacing=1.35, annotation_clip=False)

    worst = df.FV_reis.idxmin()
    wx = list(df.index).index(worst)
    ax.annotate(f"{num(df.FV_reis.min())} % — schlechtester Wert im Archiv",
                (wx, df.FV_reis.min()), xytext=(-14, -26), textcoords="offset points",
                ha="right", fontsize=8.5, color=MUTED,
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8,
                                shrinkA=0, shrinkB=4))

    style(ax)
    ax.set_xticks(list(x))
    ax.set_xticklabels(tick_labels(df.index), fontsize=8.5)
    ax.set_ylim(42, 95)
    ax.set_yticks(range(50, 95, 10))
    ax.set_yticklabels([f"{v} %" for v in range(50, 95, 10)])
    ax.set_xlim(-0.4, len(df) - 0.4)

    titleblock(fig, "Pünktlichkeit der Deutschen Bahn, Monat für Monat",
               "Anteil pünktlicher Ankünfte. Achtung: zwei verschiedene Schwellen — "
               "Züge werden mit 6 Minuten gemessen, Reisende mit 15.")

    fig.subplots_adjust(left=0.06, right=0.795, top=0.83, bottom=0.13)
    path = REPORTS / "puenktlichkeit_reihe.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def chart_gap(df):
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=200)
    x = list(range(len(df)))
    colors = [ORANGE if v < 3 else BLUE for v in df.schere]

    ax.bar(x, df.schere, color=colors, width=0.62, zorder=3)
    for xi, v in zip(x, df.schere):
        ax.annotate(num(v), (xi, v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=8, color=MUTED)

    style(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels(df.index), fontsize=8.5)
    ax.set_ylim(0, 8.6)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(["0", "2", "4", "6", "8 pp"])
    ax.set_xlim(-0.6, len(df) - 0.4)

    titleblock(fig, "Der weichere Schwellenwert hilft den Reisenden kaum noch",
               "Reisendenpünktlichkeit (15 Min.) minus betriebliche Pünktlichkeit (6 Min.)."
               + NL +
               "Orange: Vorsprung unter 3 Punkten.",
               size=13)

    fig.subplots_adjust(left=0.06, right=0.98, top=0.72, bottom=0.20)
    path = REPORTS / "puenktlichkeit_schere.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def chart_hundred(df):
    """Je 100 Zuege des letzten Monats: wie viele kommen sechs Minuten oder spaeter?"""
    period = df.index[-1]
    panels = [
        ("Fernverkehr", df.FV_betr.iloc[-1]),
        ("Nahverkehr", df.NV_betr.iloc[-1]),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=200)
    for ax, (name, punctual) in zip(axes, panels):
        late = int(round(100 - punctual))
        for i in range(100):
            row, col = divmod(i, 10)
            is_late = i >= 100 - late
            ax.scatter(col, -row, s=132, zorder=3,
                       color=ORANGE if is_late else GRID,
                       edgecolors="white", linewidths=1.4)

        ax.set_title(f"{name}" + NL + f"{late} von 100 Zügen kommen zu spät",
                     fontsize=11.5, fontweight="bold", color=INK, pad=12)
        ax.set_xlim(-0.7, 9.7)
        ax.set_ylim(-9.7, 0.7)
        ax.set_aspect("equal")
        ax.axis("off")

    y, m = period.split("-")
    titleblock(fig, f"Wie viele Züge kommen zu spät? {MONTHS_LONG[m]} {y}",
               "Ein Punkt ist ein Zug. Orange = Ankunft sechs Minuten oder später "
               "als geplant (betriebliche Pünktlichkeit).", size=13)

    fig.subplots_adjust(left=0.04, right=0.96, top=0.66, bottom=0.06, wspace=0.1)
    path = REPORTS / "puenktlichkeit_100zuege.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def report(df):
    last12 = df.loc["2025-08":"2026-07"]
    lines = [
        "# DB-Pünktlichkeit: Auswertung des Archivs",
        "",
        f"Zeitraum {df.index[0]} bis {df.index[-1]} ({len(df)} Monate). "
        "Quelle: Deutsche Bahn AG, eigene monatliche Archivierung.",
        "",
        "## Monatsreihe",
        "",
        "| Monat | Personenverkehr | Nahverkehr | Fernverkehr | Fernverkehr Reisende | Schere |",
        "|---|---|---|---|---|---|",
    ]
    for period, row in df.iterrows():
        lines.append(
            f"| {period} | {row.PV_betr:.1f} | {row.NV_betr:.1f} | "
            f"{row.FV_betr:.1f} | {row.FV_reis:.1f} | {row.schere:+.1f} |"
        )

    lines += ["", "## Kennzahlen der letzten zwölf Monate", "",
              "| Kennzahl | Mittel | Minimum | Maximum | Streuung |", "|---|---|---|---|---|"]
    for col in ("PV_betr", "NV_betr", "FV_betr", "FV_reis"):
        s = last12[col]
        lines.append(f"| {col} | {s.mean():.1f} | {s.min():.1f} ({s.idxmin()}) | "
                     f"{s.max():.1f} ({s.idxmax()}) | {s.std():.2f} |")

    lines += ["", "## Vorjahresvergleich", "",
              "| Monat | Kennzahl | Vorjahr | Aktuell | Differenz |", "|---|---|---|---|---|"]
    for month in ("06", "07"):
        for col in ("PV_betr", "NV_betr", "FV_betr", "FV_reis"):
            a, b = df.loc[f"2025-{month}", col], df.loc[f"2026-{month}", col]
            lines.append(f"| {month} | {col} | {a:.1f} | {b:.1f} | {b - a:+.1f} pp |")

    lines += ["", "## Abstand Nah- zu Fernverkehr", "",
              f"Im Mittel {df.abstand_nv_fv.mean():.1f} Prozentpunkte "
              f"(zwischen {df.abstand_nv_fv.min():.1f} und {df.abstand_nv_fv.max():.1f}).", ""]

    path = REPORTS / "puenktlichkeit.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main():
    REPORTS.mkdir(exist_ok=True)
    df = load()
    outputs = [report(df), chart_series(df), chart_hundred(df), chart_gap(df)]
    for path in outputs:
        print(f"geschrieben: {path.relative_to(ROOT)}  ({path.stat().st_size:,} Bytes)")


if __name__ == "__main__":
    main()
