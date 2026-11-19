"""Schweizer Steuer-Engine: Einkommens-, Vermögens- und Kapitalbezugssteuer.

Berechnet die Steuern von Bund, Kanton, Gemeinde und Kirche auf Basis der
ESTV-Tarifdaten (alle 26 Kantone, alle Gemeinden inkl. Steuerfüsse).

Logik portiert aus dem MIT-lizenzierten Projekt
https://github.com/devbrains-com/swisstaxcalculator (Tarif-Typen ZUERICH, BUND,
FLATTAX, FREIBURG, FORMEL; Splitting; Kapitalbezug-Definitionen je Kanton).

Vereinfachungen (bewusst):
* Eingabe ist das **steuerbare Einkommen** (alle Abzüge bereits berücksichtigt).
* Personalsteuern/Kopfsteuern (wenige Franken) werden ignoriert.
* Konkubinat wird wie "alleinstehend" behandelt.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_YEAR = 2026

# Ermässigung der direkten Bundessteuer pro Kind (Elterntarif, Art. 36 Abs. 2bis DBG)
BUND_ABZUG_PRO_KIND = 263.0

# Kantonshauptorte (Voreinstellung der Gemeinde)
CANTON_CAPITALS = {
    "ZH": "Zürich", "BE": "Bern", "LU": "Luzern", "UR": "Altdorf (UR)", "SZ": "Schwyz",
    "OW": "Sarnen", "NW": "Stans", "GL": "Glarus", "ZG": "Zug", "FR": "Fribourg",
    "SO": "Solothurn", "BS": "Basel", "BL": "Liestal", "SH": "Schaffhausen", "AR": "Herisau",
    "AI": "Appenzell", "SG": "St. Gallen", "GR": "Chur", "AG": "Aarau", "TG": "Frauenfeld",
    "TI": "Bellinzona", "VD": "Lausanne", "VS": "Sion", "NE": "Neuchâtel", "GE": "Genève",
    "JU": "Delémont",
}

CONFESSIONS = {
    "keine": "Keine / konfessionslos",
    "reformiert": "Evangelisch-reformiert",
    "katholisch": "Römisch-katholisch",
    "christkatholisch": "Christkatholisch",
}

# ---------------------------------------------------------------------------
# Daten
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tarif:
    type: str
    tax: str
    group: str
    splitting: float
    rows: tuple  # (betrag, prozent, steuer, formel)


@dataclass(frozen=True)
class Location:
    bfs: int
    name: str
    canton_id: int
    canton_abbr: str
    income_canton: float
    income_city: float
    income_church: dict
    wealth_canton: float
    wealth_city: float
    wealth_church: dict

    @property
    def label(self) -> str:
        return f"{self.name} ({self.canton_abbr})"


@dataclass(frozen=True)
class Canton:
    id: int
    abbr: str
    name: str
    tarifs: tuple
    wealth_deductions: dict


class TaxData:
    """Lädt die kompakten ESTV-Daten eines Steuerjahres."""

    def __init__(self, year: int = DEFAULT_YEAR):
        raw = json.loads((DATA_DIR / f"tax_data_{year}.json").read_text(encoding="utf-8"))
        self.year = raw["year"]
        self.bund_tarifs = tuple(self._tarif(t) for t in raw["bund"]["tarifs"])
        self.cantons: dict[int, Canton] = {}
        for cid, c in raw["cantons"].items():
            self.cantons[int(cid)] = Canton(
                id=int(cid),
                abbr=c["abbr"],
                name=c["name"],
                tarifs=tuple(self._tarif(t) for t in c["tarifs"]),
                wealth_deductions=dict(c["wealth_deductions"]),
            )
        keys = raw["factor_keys"]
        self.locations: list[Location] = []
        for loc in raw["locations"]:
            f = dict(zip(keys, loc["f"]))
            cid = loc["canton"]
            self.locations.append(
                Location(
                    bfs=loc["bfs"],
                    name=loc["name"],
                    canton_id=cid,
                    canton_abbr=self.cantons[cid].abbr,
                    income_canton=f["IncomeRateCanton"],
                    income_city=f["IncomeRateCity"],
                    income_church={
                        "keine": 0.0,
                        "reformiert": f["IncomeRateProtestant"],
                        "katholisch": f["IncomeRateRoman"],
                        "christkatholisch": f["IncomeRateChrist"],
                    },
                    wealth_canton=f["FortuneRateCanton"],
                    wealth_city=f["FortuneRateCity"],
                    wealth_church={
                        "keine": 0.0,
                        "reformiert": f["FortuneRateProtestant"],
                        "katholisch": f["FortuneRateRoman"],
                        "christkatholisch": f["FortuneRateChrist"],
                    },
                )
            )
        self.locations.sort(key=lambda l: (l.canton_abbr, l.name))
        self._by_bfs = {l.bfs: l for l in self.locations}

    @staticmethod
    def _tarif(t: dict) -> Tarif:
        return Tarif(
            type=t["type"],
            tax=t["tax"],
            group=t["group"],
            splitting=float(t["splitting"] or 0),
            rows=tuple((float(a), float(p), float(s), f) for a, p, s, f in t["rows"]),
        )

    def location(self, bfs: int) -> Location:
        return self._by_bfs[bfs]

    def find_location(self, name: str, canton_abbr: str | None = None) -> Location:
        for loc in self.locations:
            if loc.name == name and (canton_abbr is None or loc.canton_abbr == canton_abbr):
                return loc
        raise KeyError(name)

    def locations_of_canton(self, canton_id: int) -> list[Location]:
        return [l for l in self.locations if l.canton_id == canton_id]

    def tarifs(self, canton_id: int) -> tuple:
        return self.bund_tarifs if canton_id == 0 else self.cantons[canton_id].tarifs


@lru_cache(maxsize=4)
def load_tax_data(year: int = DEFAULT_YEAR) -> TaxData:
    return TaxData(year)


# ---------------------------------------------------------------------------
# Steuerprofil
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxProfile:
    """Alles, was es neben den Beträgen für eine Steuerberechnung braucht.

    Steuerfüsse in Prozent der einfachen Steuer (z.B. 95 für 95 %).
    """

    canton_id: int
    married: bool = False
    children: int = 0
    rate_canton: float = 100.0
    rate_city: float = 100.0
    rate_church: float = 0.0
    wealth_rate_canton: float = 100.0
    wealth_rate_city: float = 100.0
    wealth_rate_church: float = 0.0
    year: int = DEFAULT_YEAR
    capital_tax_correction: float = 1.0  # Korrekturfaktor Kapitalbezugssteuer Kanton/Gemeinde/Kirche

    @property
    def groups(self) -> tuple:
        if self.married:
            return ("VERHEIRATET",)
        if self.children > 0:
            return ("LEDIG_MIT_KINDER", "LEDIG_ALLEINE")
        return ("LEDIG_ALLEINE",)

    @property
    def income_factor(self) -> float:
        return (self.rate_canton + self.rate_city + self.rate_church) / 100.0

    @property
    def wealth_factor(self) -> float:
        return (self.wealth_rate_canton + self.wealth_rate_city + self.wealth_rate_church) / 100.0

    def with_rates(self, **kwargs) -> "TaxProfile":
        return replace(self, **kwargs)


def profile_for_location(
    loc: Location,
    married: bool = False,
    children: int = 0,
    confession: str = "keine",
    year: int = DEFAULT_YEAR,
) -> TaxProfile:
    return TaxProfile(
        canton_id=loc.canton_id,
        married=married,
        children=children,
        rate_canton=loc.income_canton,
        rate_city=loc.income_city,
        rate_church=loc.income_church.get(confession, 0.0),
        wealth_rate_canton=loc.wealth_canton,
        wealth_rate_city=loc.wealth_city,
        wealth_rate_church=loc.wealth_church.get(confession, 0.0),
        year=year,
    )


# ---------------------------------------------------------------------------
# Tarif-Mechanik
# ---------------------------------------------------------------------------

SPLITTING_GROUPS = {"VERHEIRATET", "LEDIG_MIT_KINDER"}

# Kantone, deren Einkommenstarif in den ESTV-Daten unindexiert vorliegt: Einkommen wird zur
# Satzbestimmung durch den Indexierungssatz geteilt (Wallis 2026: Kantonsindexierung 173 %).
INCOME_INDEX = {24: 1.73}


def _find_tarif(tarifs: tuple, tax_type: str, groups: tuple) -> tuple[Tarif, str]:
    candidates = [t for t in tarifs if t.tax == tax_type]
    if not candidates:
        raise LookupError(f"Kein Tarif für {tax_type}")
    for g in groups:
        for t in candidates:
            if t.group == "ALLE" or g in t.group.split(","):
                return t, g
    raise LookupError(f"Kein Tarif für {tax_type} / {groups}")


def _floor100(x: float) -> float:
    return math.floor(max(x, 0.0) / 100.0) * 100.0


def _tax_zuerich(amount: float, rows: tuple) -> float:
    # Zeilen sind Stufenbreiten (Zürcher Darstellung)
    tax, remaining = 0.0, amount
    for width, pct, _, _ in rows:
        used = min(remaining, width)
        tax += used * pct / 100.0
        remaining -= used
        if remaining <= 0:
            break
    return tax


def _tax_bund(amount: float, rows: tuple) -> float:
    last = None
    for row in rows:
        if row[0] <= amount:
            last = row
        else:
            break
    if last is None:
        return 0.0
    base, pct, taxes, _ = last
    return taxes + (amount - base) * pct / 100.0


def _tax_freiburg(amount: float, rows: tuple) -> float:
    # Linear interpolierter Durchschnittssatz auf das ganze Einkommen
    last = None
    for row in rows:
        if row[0] >= amount:
            if last is None or last[0] == 0:
                return 0.0
            span = row[0] - last[0]
            pct = last[1] + (row[1] - last[1]) * (amount - last[0]) / span if span else row[1]
            return amount * pct / 100.0
        last = row
    # oberhalb der Tabelle: letzter Satz
    return amount * rows[-1][1] / 100.0


_TOKEN = re.compile(r"\s*(\$wert\$|log|[()+\-*/]|\d+(?:\.\d+)?|\.\d+)")


def _eval_formula(formula: str, wert: float) -> float:
    """Sicherer Mini-Parser für ESTV-Formeln (+ - * / log, Klammern, $wert$)."""
    if not formula or not formula.strip():
        return 0.0
    tokens, pos, s = [], 0, formula
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            if s[pos:].strip() == "":
                break
            raise ValueError(f"Unerwartetes Zeichen in Formel: {formula!r}")
        tokens.append(m.group(1))
        pos = m.end()

    i = 0

    def expr():
        nonlocal i
        v = term()
        while i < len(tokens) and tokens[i] in "+-":
            op = tokens[i]
            i += 1
            r = term()
            v = v + r if op == "+" else v - r
        return v

    def term():
        nonlocal i
        v = unary()
        while i < len(tokens) and tokens[i] in ("*", "/"):
            op = tokens[i]
            i += 1
            r = unary()
            v = v * r if op == "*" else v / r
        return v

    def unary():
        nonlocal i
        if tokens[i] == "-":
            i += 1
            return -primary()
        return primary()

    def primary():
        nonlocal i
        tok = tokens[i]
        if tok == "log":
            i += 1
            return math.log(primary())
        if tok == "(":
            i += 1
            v = expr()
            i += 1  # ')'
            return v
        i += 1
        return wert if tok == "$wert$" else float(tok)

    result = expr()
    return result if math.isfinite(result) else 0.0


def _tax_formel(amount: float, rows: tuple) -> float:
    last = None
    for row in rows:
        if row[0] <= amount:
            last = row
        else:
            break
    if last is None or not last[3]:
        return 0.0
    return max(0.0, _eval_formula(last[3], amount))


def _tarif_amount(amount: float, tarif: Tarif) -> float:
    ttype = tarif.type
    if ttype == "ZUERICH" and any(r[2] > 0 for r in tarif.rows):
        ttype = "BUND"
    if ttype == "FLATTAX":
        return amount * tarif.rows[0][1] / 100.0
    if ttype == "ZUERICH":
        return _tax_zuerich(amount, tarif.rows)
    if ttype == "BUND":
        return _tax_bund(amount, tarif.rows)
    if ttype == "FREIBURG":
        return _tax_freiburg(amount, tarif.rows)
    if ttype == "FORMEL":
        return _tax_formel(amount, tarif.rows)
    raise ValueError(f"Unbekannter Tariftyp {tarif.type}")


def simple_tax(amount: float, canton_id: int, tax_type: str, groups: tuple, year: int = DEFAULT_YEAR) -> float:
    """Einfache Steuer (Kanton) bzw. Steuerbetrag (Bund, canton_id=0) gemäss Tarif."""
    if amount <= 0:
        return 0.0
    tarif, group = _find_tarif(load_tax_data(year).tarifs(canton_id), tax_type, groups)
    split = tarif.splitting if tarif.splitting > 0 and group in SPLITTING_GROUPS else 0.0
    if tax_type == "EINKOMMENSSTEUER" and canton_id in INCOME_INDEX:
        split = (split or 1.0) * INCOME_INDEX[canton_id]
    base = amount / split if split else amount
    base = base if tarif.type == "FORMEL" else _floor100(base)
    tax = _tarif_amount(base, tarif)
    return tax * split if split else tax


def has_tarif(canton_id: int, tax_type: str, year: int = DEFAULT_YEAR) -> bool:
    return any(t.tax == tax_type for t in load_tax_data(year).tarifs(canton_id))


# ---------------------------------------------------------------------------
# Resultate
# ---------------------------------------------------------------------------


@dataclass
class TaxResult:
    bund: float = 0.0
    canton: float = 0.0
    city: float = 0.0
    church: float = 0.0
    base: float = 0.0  # einfache Steuer
    taxable: float = 0.0
    details: dict = field(default_factory=dict)

    @property
    def total(self) -> float:
        return self.bund + self.canton + self.city + self.church

    def __add__(self, other: "TaxResult") -> "TaxResult":
        return TaxResult(
            self.bund + other.bund,
            self.canton + other.canton,
            self.city + other.city,
            self.church + other.church,
        )


# ---------------------------------------------------------------------------
# Einkommenssteuer
# ---------------------------------------------------------------------------


def federal_income_tax(taxable_income: float, profile: TaxProfile) -> float:
    tax = simple_tax(taxable_income, 0, "EINKOMMENSSTEUER", profile.groups, profile.year)
    tax -= BUND_ABZUG_PRO_KIND * profile.children
    return max(0.0, tax)


def income_tax(
    taxable_income: float,
    profile: TaxProfile,
    taxable_income_bund: float | None = None,
) -> TaxResult:
    """Einkommenssteuer Bund + Kanton + Gemeinde + Kirche."""
    taxable_income = max(0.0, taxable_income)
    bund_income = taxable_income if taxable_income_bund is None else max(0.0, taxable_income_bund)
    base = simple_tax(taxable_income, profile.canton_id, "EINKOMMENSSTEUER", profile.groups, profile.year)
    return TaxResult(
        bund=federal_income_tax(bund_income, profile),
        canton=base * profile.rate_canton / 100.0,
        city=base * profile.rate_city / 100.0,
        church=base * profile.rate_church / 100.0,
        base=base,
        taxable=taxable_income,
    )


def income_tax_total(taxable_income: float, profile: TaxProfile, bund_offset: float = 0.0) -> float:
    """Kurzform für Gesamtsteuer; ``bund_offset`` = Bund-Einkommen minus Kantons-Einkommen."""
    return income_tax(taxable_income, profile, taxable_income + bund_offset).total


def marginal_income_rate(
    taxable_income: float, profile: TaxProfile, step: float = 1000.0, bund_offset: float = 0.0
) -> float:
    """Grenzsteuersatz (Steuer auf die nächsten ``step`` Franken)."""
    t0 = income_tax_total(taxable_income, profile, bund_offset)
    t1 = income_tax_total(taxable_income + step, profile, bund_offset)
    return (t1 - t0) / step


# ---------------------------------------------------------------------------
# Vermögenssteuer
# ---------------------------------------------------------------------------


def wealth_deductions(profile: TaxProfile) -> float:
    """Kantonale Sozialabzüge/Freibeträge auf dem Vermögen (falls nicht im Tarif)."""
    d = load_tax_data(profile.year).cantons[profile.canton_id].wealth_deductions
    total = 0.0
    if profile.married:
        total += d.get("SozVerheiratet_VM", 0.0)
    else:
        total += d.get("SozLedigMitOhneKinder_VM", 0.0)
        if profile.children > 0:
            total += d.get("SozAlleinerzieher_VM", 0.0)
        else:
            total += d.get("SozLedigOhneKinder_VM", 0.0)
    total += d.get("SozKind_VM", 0.0) * profile.children
    return total


def wealth_tax(net_wealth: float, profile: TaxProfile, apply_deductions: bool = True) -> TaxResult:
    """Vermögenssteuer Kanton + Gemeinde + Kirche (der Bund erhebt keine)."""
    taxable = max(0.0, net_wealth - (wealth_deductions(profile) if apply_deductions else 0.0))
    if not has_tarif(profile.canton_id, "VERMOEGENSSTEUER", profile.year):
        return TaxResult(taxable=taxable)
    base = simple_tax(taxable, profile.canton_id, "VERMOEGENSSTEUER", profile.groups, profile.year)
    return TaxResult(
        canton=base * profile.wealth_rate_canton / 100.0,
        city=base * profile.wealth_rate_city / 100.0,
        church=base * profile.wealth_rate_church / 100.0,
        base=base,
        taxable=taxable,
    )


def marginal_wealth_rate(net_wealth: float, profile: TaxProfile, step: float = 10000.0) -> float:
    return (wealth_tax(net_wealth + step, profile).total - wealth_tax(net_wealth, profile).total) / step


# ---------------------------------------------------------------------------
# Kapitalbezugssteuer (Vorsorgekapital, Säule 2 und 3a)
# ---------------------------------------------------------------------------

# Definitionen je Kanton (Quelle: devbrains swisstaxcalculator, Stand 2022, Zug ergänzt)
# type: IncomeTaxFactor   -> ordentlicher Tarif x Faktor
#       RentIncomeFactor  -> Satz von (Kapital x Faktor), angewendet auf ganzes Kapital
#       RentIncomeFactorOwn -> wie oben, aber mit eigenem Vorsorgetarif
#       Tarif / Flattax   -> eigener Vorsorgetarif
PENSION_CAPITAL_RULES: dict[int, dict] = {
    0: {"type": "IncomeTaxFactor", "factor": 0.2, "text": "1/5 des ordentlichen Tarifs (Art. 38 DBG)"},
    26: {"type": "RentIncomeFactor", "factor": 0.05, "min": 0.02,
         "text": "Satz für 1/20 des Kapitals, einfache Steuer mind. 2 % (§ 37 StG ZH)"},
    4: {"type": "Tarif", "text": "eigener Vorsorgetarif"},
    12: {"type": "IncomeTaxFactor", "factor": 1 / 3, "min": 0.005, "text": "1/3 des ordentlichen Tarifs"},
    22: {"type": "Flattax", "church_factor": 0.005, "text": "proportionaler Satz"},
    19: {"type": "RentIncomeFactor", "factor": 0.04, "max": 0.025, "text": "Satz für 1/25 des Kapitals, max. 2.5 %"},
    15: {"type": "IncomeTaxFactor", "factor": 0.4, "text": "40 % des ordentlichen Tarifs"},
    # Nidwalden: 1/4 (abgeglichen mit publizierten Vergleichswerten 2025)
    14: {"type": "IncomeTaxFactor", "factor": 0.25, "text": "1/4 des ordentlichen Tarifs"},
    9: {"type": "Flattax", "text": "proportionaler Satz"},
    # Zug: 30 % des ordentlichen Tarifs bis CHF 230'400, 40 % darüber, mind. 1 %
    25: {"type": "IncomeTaxFactorStaged", "factor": 0.3, "factor_high": 0.4, "threshold": 230400,
         "min": 0.01, "text": "30 % (bis 230'400) bzw. 40 % des ordentlichen Tarifs, mind. 1 %"},
    7: {"type": "Tarif", "text": "eigener Vorsorgetarif"},
    18: {"type": "IncomeTaxFactor", "factor": 0.25, "text": "1/4 des ordentlichen Tarifs"},
    6: {"type": "Tarif", "text": "eigener Vorsorgetarif"},
    5: {"type": "Tarif", "max": 0.045, "text": "eigener Vorsorgetarif, max. 4.5 %"},
    17: {"type": "IncomeTaxFactor", "factor": 0.2, "text": "1/5 des ordentlichen Tarifs"},
    3: {"type": "Tarif", "text": "eigener Vorsorgetarif"},
    2: {"type": "IncomeTaxFactor", "factor": 0.25, "min": 0.005, "text": "1/4 des ordentlichen Tarifs"},
    16: {"type": "Flattax", "text": "proportionaler Satz"},
    10: {"type": "RentIncomeFactorOwn", "factor": 1 / 15, "min": 0.015, "max": 0.02,
         "text": "Satz für 1/15 des Kapitals (Vorsorgetarif), 1.5–2 %"},
    1: {"type": "IncomeTaxFactor", "factor": 0.3, "min": 0.01, "text": "30 % des ordentlichen Tarifs"},
    20: {"type": "Flattax", "text": "proportionaler Satz"},
    21: {"type": "RentIncomeFactor", "factor": 0.068, "min": 0.02, "text": "Rentensatz, mind. 2 %"},
    23: {"type": "IncomeTaxFactor", "factor": 0.33, "text": "1/3 des ordentlichen Tarifs"},
    24: {"type": "RentIncomeFactor", "factor": 0.068, "min": 0.02, "text": "Rentensatz, mind. 2 %"},
    13: {"type": "IncomeTaxFactor", "factor": 0.25, "min": 0.025, "text": "1/4 des ordentlichen Tarifs"},
    8: {"type": "IncomeTaxFactor", "factor": 0.2, "text": "1/5 des ordentlichen Tarifs"},
    11: {"type": "Tarif", "text": "eigener Vorsorgetarif"},
}


# Regeln, die nicht mit aktuellen Vergleichswerten abgeglichen werden konnten (eher zu hoch)
UNVERIFIED_CAPITAL_RULES = {21, 23, 24}


def _pension_base(capital: float, canton_id: int, groups: tuple, year: int) -> float:
    rule = PENSION_CAPITAL_RULES[canton_id]
    kind = rule["type"]
    if kind == "IncomeTaxFactor":
        tax = simple_tax(capital, canton_id, "EINKOMMENSSTEUER", groups, year) * rule["factor"]
    elif kind == "IncomeTaxFactorStaged":
        # Stufenweise: Steueranteil bis zur Schwelle mit tiefem, darüber mit hohem Faktor
        ordinary = simple_tax(capital, canton_id, "EINKOMMENSSTEUER", groups, year)
        if capital <= rule["threshold"]:
            tax = ordinary * rule["factor"]
        else:
            low = simple_tax(rule["threshold"], canton_id, "EINKOMMENSSTEUER", groups, year)
            tax = low * rule["factor"] + (ordinary - low) * rule["factor_high"]
    elif kind in ("RentIncomeFactor", "RentIncomeFactorOwn"):
        tax_type = "EINKOMMENSSTEUER" if kind == "RentIncomeFactor" else "VORSORGESTEUER"
        reduced = _floor100(capital * rule["factor"])
        if reduced <= 0:
            tax = 0.0
        else:
            rate = simple_tax(reduced, canton_id, tax_type, groups, year) / reduced
            tax = capital * rate
    else:  # Tarif / Flattax
        tax = simple_tax(capital, canton_id, "VORSORGESTEUER", groups, year)
    if "min" in rule:
        tax = max(tax, capital * rule["min"])
    if "max" in rule:
        tax = min(tax, capital * rule["max"])
    return tax


def capital_withdrawal_tax(capital: float, profile: TaxProfile) -> TaxResult:
    """Steuer auf Kapitalbezug aus Pensionskasse / Säule 3a (separat vom Einkommen)."""
    capital = max(0.0, capital)
    if capital <= 0:
        return TaxResult()
    bund = _pension_base(capital, 0, profile.groups, profile.year)
    base = _pension_base(capital, profile.canton_id, profile.groups, profile.year) * profile.capital_tax_correction
    rule = PENSION_CAPITAL_RULES[profile.canton_id]
    church_base = (capital * rule["church_factor"] * profile.capital_tax_correction
                   if "church_factor" in rule else base)
    return TaxResult(
        bund=bund,
        canton=base * profile.rate_canton / 100.0,
        city=base * profile.rate_city / 100.0,
        church=church_base * profile.rate_church / 100.0,
        base=base,
        taxable=capital,
    )


def pension_rule_text(canton_id: int) -> str:
    return PENSION_CAPITAL_RULES[canton_id]["text"]
