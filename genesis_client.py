"""Minimaler Client fuer die GENESIS-Online-Webservices des Statistischen Bundesamtes.

Die Zugangsdaten werden ausschliesslich aus der Umgebung gelesen
(GENESIS_USER und GENESIS_PASS) und niemals im Repository abgelegt.
GENESIS akzeptiert an Stelle des Passworts auch einen Webservice-Token;
ein Token ist vorzuziehen, weil er einzeln widerrufen werden kann.

Eigenheiten der Schnittstelle, die hier beruecksichtigt sind:
  * Alle Aufrufe sind POST. GET liefert 405.
  * Zugangsdaten gehoeren in die HTTP-Header, nicht in den Body.
  * Fehler kommen teils mit HTTP 200 und stecken dann im Feld "Type".
"""

import os
import pathlib
import sys

import requests

BASE = "https://genesis.destatis.de/genesisWS/rest/2020"
ENV_FILE = pathlib.Path(__file__).parent / ".env"


def load_env_file():
    """Uebernimmt Werte aus .env, ohne bereits gesetzte Variablen zu ueberschreiben.

    Bewusst ohne Zusatzabhaengigkeit, damit es unter PowerShell genauso
    funktioniert wie unter bash.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class GenesisError(RuntimeError):
    pass


def credentials():
    load_env_file()
    user = os.environ.get("GENESIS_USER", "").strip()
    secret = os.environ.get("GENESIS_PASS", "").strip()
    if not user or not secret:
        raise GenesisError(
            "GENESIS_USER und GENESIS_PASS sind nicht gesetzt.\n"
            "Lokal:  .env anlegen (siehe .env.example), dann 'set -a; . ./.env; set +a'\n"
            "In CI:  als GitHub Secrets hinterlegen."
        )
    return user, secret


def call(service, **params):
    """Ruft einen GENESIS-Service auf und gibt die Antwort zurueck.

    Rueckgabe ist ein dict bei JSON-Antworten, sonst der Text (etwa bei ffcsv).
    """
    user, secret = credentials()
    resp = requests.post(
        f"{BASE}/{service}",
        headers={"username": user, "password": secret},
        data={"language": "de", **params},
        timeout=120,
    )

    ctype = resp.headers.get("Content-Type", "")
    if "json" in ctype:
        payload = resp.json()
        # GENESIS meldet Fehler teilweise mit HTTP 200 im Body.
        if isinstance(payload, dict):
            status = payload.get("Status") or {}
            if payload.get("Type") == "ERROR":
                raise GenesisError(f"{payload.get('Code')}: {payload.get('Content')}")
            if isinstance(status, dict) and status.get("Type") == "ERROR":
                raise GenesisError(f"{status.get('Code')}: {status.get('Content')}")
        resp.raise_for_status()
        return payload

    resp.raise_for_status()
    text = resp.text
    if text.lstrip().startswith('{"Code"'):
        raise GenesisError(text[:200])
    return text


def check_login():
    """Prueft die Zugangsdaten gegen einen Dienst, der echte Rechte verlangt.

    helloworld/logincheck taugt dafuer nicht: der Dienst spiegelt den
    uebergebenen Nutzernamen zurueck und meldet auch bei falschen Daten Erfolg.
    catalogue/tables dagegen antwortet nur bei gueltiger Anmeldung.
    """
    call("catalogue/tables", selection="12411*", pagelength="1")
    return credentials()[0]


if __name__ == "__main__":
    try:
        print(f"Angemeldet als: {check_login()}")
    except GenesisError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)
