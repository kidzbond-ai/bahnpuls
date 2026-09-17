"""Durchsucht den GENESIS-Katalog, damit die passenden Tabellen belegt statt
geraten ausgewaehlt werden koennen.

    python explore_destatis.py login
    python explore_destatis.py find eisenbahn
    python explore_destatis.py catalogue 461
    python explore_destatis.py table 46131-0001
"""

import sys

from genesis_client import GenesisError, call, check_login


def show(rows, columns, limit=60):
    if not rows:
        print("  (keine Treffer)")
        return
    for row in rows[:limit]:
        parts = [str(row.get(c, "")).strip() for c in columns]
        print(f"  {parts[0]:<16} {' | '.join(p[:78] for p in parts[1:])}")
    if len(rows) > limit:
        print(f"  ... und {len(rows) - limit} weitere")


def cmd_find(term):
    result = call("find/find", term=term, category="tables", pagelength="100")
    tables = result.get("Tables", []) if isinstance(result, dict) else []
    print(f"Tabellen zum Suchbegriff '{term}': {len(tables)}")
    show(tables, ["Code", "Content"])


def cmd_catalogue(prefix):
    result = call("catalogue/tables", selection=f"{prefix}*", pagelength="200")
    tables = result.get("List", []) if isinstance(result, dict) else []
    print(f"Tabellen unter {prefix}*: {len(tables)}")
    show(tables, ["Code", "Content"])


def cmd_table(name):
    meta = call("metadata/table", name=name)
    info = meta.get("Object", {}) if isinstance(meta, dict) else {}
    print(f"{name}: {info.get('Content', '?')}")
    print(f"Stand: {info.get('Stand', '?')}")
    print()
    csv_text = call("data/tablefile", name=name, format="ffcsv", area="all")
    lines = csv_text.splitlines()
    print(f"ffcsv: {len(lines)} Zeilen")
    for line in lines[:6]:
        print("  ", line[:200])


COMMANDS = {
    "login": lambda *_: print(f"Angemeldet als: {check_login()}"),
    "find": cmd_find,
    "catalogue": cmd_catalogue,
    "table": cmd_table,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    command, args = argv[0], argv[1:]
    if command != "login" and not args:
        print(f"'{command}' braucht ein Argument.")
        return 2
    try:
        COMMANDS[command](*args)
    except GenesisError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
