# bahnpuls

Offene Bahndaten für Deutschland und Europa, automatisiert und nachvollziehbar.

| Quelle | Was | Zeitraum | Schlüssel nötig |
|---|---|---|---|
| Deutsche Bahn | Monatliche Pünktlichkeit | ab erstem Lauf | nein |
| Eurostat | 10 Bahndatensätze, EU-weit | teils ab 1962 | nein |

## Teil 1 — DB-Pünktlichkeit

### Warum

Die DB veröffentlicht ihre Pünktlichkeitswerte monatlich, zeigt auf der Seite
aber nur ein **gleitendes Fenster von rund 14 Monaten**. Ältere Monate werden
ersatzlos entfernt, und es gibt keinen Download. Eine öffentlich zugängliche,
lange Zeitreihe der monatlichen DB-Pünktlichkeit existiert damit nicht.

Dieses Repository legt sie an: wöchentlicher Abruf, Zusammenführung in ein
wachsendes Archiv, Rohdaten-Snapshot für jeden Lauf.

### Daten

`data/db_punctuality.csv` — eine Zeile je (Monat, Kennzahl):

| Spalte | Bedeutung |
|---|---|
| `period` | Monat, `YYYY-MM` |
| `metric` | Kennzahl, z. B. `Betriebliche Pünktlichkeit Fernverkehr` |
| `value_pct` | Wert in Prozent |
| `first_seen` | Datum, an dem der Wert zuerst archiviert wurde |
| `last_seen` | Datum des letzten Abrufs, bei dem der Wert noch auf der Seite stand |
| `source_url` | Quelle |

Erfasste Kennzahlen: Betriebliche Pünktlichkeit (Personenverkehr, Fernverkehr,
Nahverkehr) und Reisendenpünktlichkeit Fernverkehr.

### Methodik und Grenzen

- **Quelle** ist ausschließlich die öffentliche Konzernseite der DB. Die Werte
  werden nicht nachgerechnet, sondern unverändert übernommen.
- **Definition der Pünktlichkeit** legt die DB fest (Ankunft mit weniger als
  sechs Minuten Verspätung). Ändert die DB ihre Methodik, ist die Zeitreihe an
  dieser Stelle gebrochen — das CSV weist das nicht aus.
- **Nachträgliche Korrekturen** durch die DB werden im CSV überschrieben. Die
  vollständige Historie bleibt über die HTML-Snapshots in `data/raw/`
  rekonstruierbar; jeder Lauf legt dort eine Kopie der Seite ab.
- **Rückwirkende Vollständigkeit** gibt es nicht: das Archiv beginnt mit dem
  ersten Lauf. Monate, die vorher aus dem Fenster gefallen sind, fehlen.

## Teil 2 — Eurostat

`fetch_eurostat.py` lädt zehn laufend gepflegte Bahndatensätze über die
Dissemination API (JSON-stat 2.0, kein API-Schlüssel nötig) und legt sie als
tidy CSV unter `data/eurostat/` ab — eine Zeile je Beobachtung, mit Codes und
Klartext-Labels nebeneinander.

| Datensatz | Inhalt | Zeitraum |
|---|---|---|
| `rail_pa_total` | Fahrgäste gesamt | 2004– |
| `rail_pa_typepas` | Fahrgäste nach Verkehrsart | 2004– |
| `rail_pa_intcmng` | Internationale Fahrgäste nach Einstiegsland | 2004– |
| `rail_go_total` | Güterverkehr gesamt | 2004– |
| `rail_if_tracks` | Gleislänge nach Elektrifizierung | 1990– |
| `rail_if_line_ga` | Streckenlänge nach Spurweite | 1962– |
| `rail_if_electri` | Elektrifizierte Strecken nach Stromsystem | 1990– |
| `rail_eq_locon` | Lokomotiven und Triebwagen nach Energiequelle | 1990– |
| `tran_sf_railac` | Eisenbahnunfälle nach Unfallart | 2006– |
| `tran_sf_railvi` | Unfallopfer nach Unfallart und Personengruppe | 2006– |

### Methodik und Grenzen

- **Kein Archivzwang.** Anders als bei der DB bleibt bei Eurostat die volle
  Zeitreihe dauerhaft abrufbar. Es wird daher nicht zusammengeführt, sondern
  komplett neu geladen.
- **Nur gepflegte Reihen.** Eingestellte Datensätze sind bewusst nicht
  enthalten: `rail_go_typeall` endet 2016, `rail_ac_catvict` endet 2015.
- **Qualitätskennzeichen** von Eurostat (vorläufig, geschätzt, Bruch in der
  Reihe) stehen unverändert in der Spalte `flag`. Wer die Werte interpretiert,
  muss sie beachten.
- **Geschrieben wird nur bei echter Änderung.** `_versions.json` merkt sich den
  von Eurostat gemeldeten Stand je Datensatz. Jeder Commit im Verlauf
  entspricht damit einer tatsächlichen Datenrevision, nicht einem Routinelauf.
- **Deutschland meldet Infrastrukturdaten nur bis 2021.** In `rail_if_tracks`,
  `rail_if_line_ga` und `rail_if_electri` endet die deutsche Reihe 2021, in
  `rail_eq_locon` bereits 2020 — während 36 andere Länder bis 2024 liefern.
  Für aktuelle Aussagen über das deutsche Netz sind diese Datensätze deshalb
  nicht brauchbar. Verkehrsleistung (`rail_pa_*`, `rail_go_total`) und
  Sicherheit (`tran_sf_*`) reichen dagegen bis 2024/2025.

- **Konstante Dimensionen entfallen.** Hat eine Dimension nur eine Ausprägung
  (etwa `freq=A`), wird sie nicht als Spalte ausgegeben.

## Nutzung

```bash
pip install -r requirements.txt
python scrape_db_punctuality.py
python fetch_eurostat.py
```

Beide Läufe sind idempotent — mehrfaches Ausführen ändert nichts.
Automatisiert laufen sie wöchentlich über `.github/workflows/archive.yml`.
