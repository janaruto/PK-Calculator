"""Pensionskasse (2. Säule): Hochrechnung des Altersguthabens.

Alle Beiträge und Einkäufe werden vereinfachend **am Jahresende** gutgeschrieben
(sie werden im Einzahlungsjahr also noch nicht verzinst). Das Guthaben zu
Jahresbeginn wird mit dem angenommenen Zinssatz verzinst.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

# BVG-Eckwerte 2026 (Beträge in CHF)
BVG = {
    "eintrittsschwelle": 22_680,
    "koordinationsabzug": 26_460,
    "obere_grenze": 90_720,
    "min_koordinierter_lohn": 3_780,
    "mindestzins": 1.25,  # % (Bundesrat, 2026)
    "umwandlungssatz": 6.8,  # % im Obligatorium
    "saeule3a_max": 7_258,
}

# BVG-Mindest-Altersgutschriften in % des koordinierten Lohns
BVG_STAFFEL = [
    (25, 34, 7.0),
    (35, 44, 10.0),
    (45, 54, 15.0),
    (55, 70, 18.0),
]


def bvg_koordinierter_lohn(ahv_lohn: float) -> float:
    """Koordinierter (versicherter) Lohn nach BVG-Minimum."""
    if ahv_lohn < BVG["eintrittsschwelle"]:
        return 0.0
    capped = min(ahv_lohn, BVG["obere_grenze"])
    return max(capped - BVG["koordinationsabzug"], BVG["min_koordinierter_lohn"])


def bvg_gutschrift_pct(age: int) -> float:
    for lo, hi, pct in BVG_STAFFEL:
        if lo <= age <= hi:
            return pct
    return 0.0


@dataclass
class StaffelStufe:
    from_age: int
    to_age: int
    employee_pct: float  # % vom versicherten Lohn
    employer_pct: float


def default_staffel(employer_share: float = 0.5) -> list[StaffelStufe]:
    return [
        StaffelStufe(lo, hi, pct * (1 - employer_share), pct * employer_share)
        for lo, hi, pct in BVG_STAFFEL
    ]


@dataclass
class PensionPlan:
    """Parameter einer Pensionskasse für eine Person."""

    name: str = "Pensionskasse"
    balance: float = 0.0  # heutiges Altersguthaben
    mode: str = "fix"  # "fix" (CHF/Jahr) oder "staffel" (% vom versicherten Lohn)
    employee_savings: float = 0.0  # Sparbeitrag Arbeitnehmer CHF/Jahr (Modus fix)
    employer_savings: float = 0.0  # Sparbeitrag Arbeitgeber CHF/Jahr (Modus fix)
    insured_salary: float = 0.0  # versicherter Lohn (Modus staffel)
    staffel: list = field(default_factory=default_staffel)
    employee_risk: float = 0.0  # Risiko-/Verwaltungsbeitrag AN CHF/Jahr (fliesst nicht ins Guthaben)
    interest: float = 2.0  # erwartete Verzinsung % p.a.
    conversion_rate: float = 5.8  # Umwandlungssatz % bei Pensionierung
    salary_growth: float = 0.0  # Lohn-/Beitragswachstum % p.a.
    buyin_potential: float = 0.0  # maximal möglicher Einkauf

    def contributions(self, age: int, year_index: int) -> tuple[float, float]:
        """Sparbeiträge (AN, AG) im Jahr ``year_index`` bei Alter ``age``."""
        growth = (1 + self.salary_growth / 100.0) ** year_index
        if self.mode == "staffel":
            salary = self.insured_salary * growth
            for st in self.staffel:
                if st.from_age <= age <= st.to_age:
                    return salary * st.employee_pct / 100.0, salary * st.employer_pct / 100.0
            return 0.0, 0.0
        return self.employee_savings * growth, self.employer_savings * growth

    def employee_total(self, age: int, year_index: int) -> float:
        """Gesamter Lohnabzug AN (Sparen + Risiko) – steuerlich abzugsfähig."""
        growth = (1 + self.salary_growth / 100.0) ** year_index
        return self.contributions(age, year_index)[0] + self.employee_risk * growth

    def copy(self, **kwargs) -> "PensionPlan":
        return replace(self, **kwargs)


def project(
    plan: PensionPlan,
    age: int,
    retirement_age: int,
    buyins: dict[int, float] | None = None,
    employee_reduction: list[float] | None = None,
) -> pd.DataFrame:
    """Jahresweise Hochrechnung bis zur Pensionierung.

    buyins: {Jahresindex: Betrag} (Einkauf am Ende des Jahres)
    employee_reduction: pro Jahr reduzierter AN-Sparbeitrag (Szenario "weniger einzahlen")
    """
    buyins = buyins or {}
    rows = []
    bal = plan.balance
    years = max(0, retirement_age - age)
    r = plan.interest / 100.0
    for i in range(years):
        a = age + i
        an, ag = plan.contributions(a, i)
        if employee_reduction is not None:
            an = max(0.0, an - employee_reduction[i])
        einkauf = buyins.get(i, 0.0)
        zins = bal * r
        end = bal + zins + an + ag + einkauf
        rows.append(
            {
                "Jahr": i + 1,
                "Alter": a,
                "Guthaben Anfang": bal,
                "Zins": zins,
                "Beitrag AN": an,
                "Beitrag AG": ag,
                "Einkauf": einkauf,
                "Guthaben Ende": end,
            }
        )
        bal = end
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(
            [{"Jahr": 0, "Alter": age, "Guthaben Anfang": bal, "Zins": 0.0, "Beitrag AN": 0.0,
              "Beitrag AG": 0.0, "Einkauf": 0.0, "Guthaben Ende": bal}]
        )
    return df


def final_capital(df: pd.DataFrame) -> float:
    return float(df["Guthaben Ende"].iloc[-1])


def decompose(df: pd.DataFrame, start_balance: float) -> dict:
    """Woher kommt das Schlusskapital?"""
    return {
        "Heutiges Guthaben": start_balance,
        "Beiträge Arbeitnehmer": float(df["Beitrag AN"].sum()),
        "Beiträge Arbeitgeber": float(df["Beitrag AG"].sum()),
        "Einkäufe": float(df["Einkauf"].sum()),
        "Zinsen": float(df["Zins"].sum()),
    }


def buyin_schedule(total: float, years: int, start_index: int, horizon: int) -> dict[int, float]:
    """Verteilt einen Einkaufsbetrag gleichmässig auf ``years`` Jahre ab ``start_index``."""
    if total <= 0 or years <= 0:
        return {}
    out = {}
    per_year = total / years
    for k in range(years):
        idx = start_index + k
        if 0 <= idx < horizon:
            out[idx] = out.get(idx, 0.0) + per_year
    return out
