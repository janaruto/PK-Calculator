"""Erzeugt die kompakte Steuerdaten-Datei ``data/tax_data_<jahr>.json``.

Quelle: aufbereitete ESTV-Steuerdaten (https://swisstaxcalculator.estv.admin.ch/#/taxdata)
aus dem MIT-lizenzierten Projekt https://github.com/devbrains-com/swisstaxcalculator
(Ordner ``data/parsed/<jahr>``).

Verwendung::

    python tools/build_tax_data.py <pfad-zu-swisstaxcalculator/data/parsed> 2026
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CANTON_NAMES = {
    1: "Aargau", 2: "Appenzell Innerrhoden", 3: "Appenzell Ausserrhoden", 4: "Bern",
    5: "Basel-Landschaft", 6: "Basel-Stadt", 7: "Freiburg", 8: "Genf", 9: "Glarus",
    10: "Graubünden", 11: "Jura", 12: "Luzern", 13: "Neuenburg", 14: "Nidwalden",
    15: "Obwalden", 16: "St. Gallen", 17: "Schaffhausen", 18: "Solothurn", 19: "Schwyz",
    20: "Thurgau", 21: "Tessin", 22: "Uri", 23: "Waadt", 24: "Wallis", 25: "Zug", 26: "Zürich",
}

TAX_TYPES = {"EINKOMMENSSTEUER", "VERMOEGENSSTEUER", "VORSORGESTEUER"}
WEALTH_DEDUCTIONS = {
    "SozVerheiratet_VM", "SozLedigMitOhneKinder_VM", "SozKind_VM",
    "SozLedigOhneKinder_VM", "SozAlleinerzieher_VM",
}
FACTOR_KEYS = [
    "IncomeRateCanton", "IncomeRateCity", "IncomeRateProtestant", "IncomeRateRoman",
    "IncomeRateChrist", "FortuneRateCanton", "FortuneRateCity", "FortuneRateProtestant",
    "FortuneRateRoman", "FortuneRateChrist",
]


def compact_tarif(t: dict) -> dict:
    return {
        "type": t["tableType"],
        "tax": t["taxType"],
        "group": t["group"],
        "splitting": t["splitting"],
        # [Betrag, Prozent, Steuer, Formel]
        "rows": [
            [r["amount"], round(r["percent"], 6), round(r["taxes"], 4), r["formula"]]
            for r in t["table"]
        ],
    }


def main(parsed_dir: str, year: str) -> None:
    base = Path(parsed_dir) / year
    out: dict = {"year": int(year), "source": "ESTV Steuerdaten via devbrains-com/swisstaxcalculator (MIT)",
                 "bund": {}, "cantons": {}, "locations": []}

    out["bund"]["tarifs"] = [
        compact_tarif(t) for t in json.loads((base / "tarifs" / "0.json").read_text())
        if t["taxType"] in TAX_TYPES
    ]

    locations = json.loads((base / "locations.json").read_text())
    abbr = {loc["CantonID"]: loc["Canton"] for loc in locations}

    for cid in range(1, 27):
        tarifs = [compact_tarif(t) for t in json.loads((base / "tarifs" / f"{cid}.json").read_text())
                  if t["taxType"] in TAX_TYPES]
        deductions = {}
        for block in json.loads((base / "deductions" / f"{cid}.json").read_text()):
            if block["type"] != "VERMOEGENSSTEUER":
                continue
            for item in block["items"]:
                if item["id"] in WEALTH_DEDUCTIONS:
                    deductions[item["id"]] = item["amount"]
        out["cantons"][str(cid)] = {
            "abbr": abbr[cid], "name": CANTON_NAMES[cid],
            "tarifs": tarifs, "wealth_deductions": deductions,
        }

        factors = {f["Location"]["BfsID"]: f for f in json.loads((base / "factors" / f"{cid}.json").read_text())}
        for loc in locations:
            if loc["CantonID"] != cid:
                continue
            f = factors.get(loc["BfsID"])
            if f is None:
                continue
            out["locations"].append({
                "bfs": loc["BfsID"], "name": loc["BfsName"], "canton": cid,
                "f": [round(f[k], 4) for k in FACTOR_KEYS],
            })

    out["factor_keys"] = FACTOR_KEYS
    target = Path(__file__).resolve().parent.parent / "data" / f"tax_data_{year}.json"
    target.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"geschrieben: {target} ({target.stat().st_size / 1024:.0f} KB, {len(out['locations'])} Gemeinden)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
