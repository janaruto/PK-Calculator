"""Analysen: PK-Einkauf, PK vs. ETF, zwei Pensionskassen, Rente vs. Kapital."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from . import pension as pk
from .tax import (
    TaxProfile,
    capital_withdrawal_tax,
    income_tax_total,
    wealth_tax,
)

# AN-Beiträge AHV/IV/EO (5.3 %) + ALV (1.1 %) – abzugsfähig, relevant bei Lohnunterschied
SOZIALABZUEGE_AN = 0.064


# ---------------------------------------------------------------------------
# Steuer-Kontext & ETF
# ---------------------------------------------------------------------------


@dataclass
class TaxContext:
    """Steuerliche Ausgangslage der Person (heute), inkl. Cache für Wiederholungen."""

    profile: TaxProfile
    income: float  # steuerbares Einkommen Kanton/Gemeinde
    wealth: float = 0.0  # Reinvermögen
    bund_offset: float = 0.0  # steuerbares Einkommen Bund minus Kanton
    income_growth: float = 0.0  # % p.a.
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    def income_at(self, i: int) -> float:
        return self.income * (1 + self.income_growth / 100.0) ** i

    def tax(self, income: float) -> float:
        key = ("i", round(income, 2))
        if key not in self._cache:
            self._cache[key] = income_tax_total(income, self.profile, self.bund_offset)
        return self._cache[key]

    def extra_income_tax(self, i: int, delta: float) -> float:
        """Mehrsteuer (bzw. Ersparnis bei negativem delta) im Jahr i."""
        y = self.income_at(i)
        return self.tax(y + delta) - self.tax(y)

    def wtax(self, w: float) -> float:
        key = ("w", round(w, 0))
        if key not in self._cache:
            self._cache[key] = wealth_tax(w, self.profile).total
        return self._cache[key]

    def extra_wealth_tax(self, extra: float) -> float:
        return self.wtax(self.wealth + max(0.0, extra)) - self.wtax(self.wealth)

    def with_income(self, income: float) -> "TaxContext":
        return replace(self, income=income, _cache={})

    def cap_tax(self, capital: float) -> float:
        key = ("k", round(capital, 0))
        if key not in self._cache:
            self._cache[key] = capital_withdrawal_tax(capital, self.profile).total
        return self._cache[key]


@dataclass
class EtfAssumptions:
    total_return: float = 5.0  # % p.a. vor Kosten, inkl. Dividenden
    dividend_yield: float = 1.8  # % p.a. – als Einkommen steuerbar
    ter: float = 0.2  # % p.a. Fondskosten (inkl. Depot)

    def with_return(self, r: float) -> "EtfAssumptions":
        return replace(self, total_return=r)


def simulate_etf(cashflows: list[float], ctx: TaxContext, etf: EtfAssumptions, tax_income: bool = True,
                 tax_wealth: bool = True) -> pd.DataFrame:
    """ETF-Depot: Einzahlungen jeweils Ende Jahr i; Steuern werden aus dem Depot bezahlt.

    * Dividenden/thesaurierte Erträge -> Einkommenssteuer (Grenzsteuersatz)
    * Depotwert per 31.12. -> Vermögenssteuer (zusätzlich zum übrigen Vermögen)
    * Kursgewinne sind für Privatanleger steuerfrei.
    """
    rows, v = [], 0.0
    for i, cf in enumerate(cashflows):
        growth = v * etf.total_return / 100.0
        costs = v * etf.ter / 100.0
        div = v * etf.dividend_yield / 100.0
        t_div = ctx.extra_income_tax(i, div) if (tax_income and div > 0) else 0.0
        v_after = v + growth - costs - t_div + cf
        t_w = ctx.extra_wealth_tax(v_after) if tax_wealth else 0.0
        end = v_after - t_w
        rows.append({"Jahr": i + 1, "Wert Anfang": v, "Rendite": growth, "Kosten": costs,
                     "Steuer Dividenden": t_div, "Vermögenssteuer": t_w, "Einzahlung": cf, "Wert Ende": end})
        v = end
    return pd.DataFrame(rows)


def etf_final(cashflows: list[float], ctx: TaxContext, etf: EtfAssumptions) -> float:
    if not cashflows:
        return 0.0
    return float(simulate_etf(cashflows, ctx, etf)["Wert Ende"].iloc[-1])


def irr(cashflows: list[float], final_value: float) -> float | None:
    """Jahresrendite, bei der Einzahlungen (Ende Jahr i) auf final_value (Ende letztes Jahr) wachsen."""
    n = len(cashflows)
    # keine Laufzeit (nur Zahlung im letzten Jahr) -> Rendite nicht definiert
    if n == 0 or sum(cashflows) <= 0 or all(cf == 0 for cf in cashflows[:-1]):
        return None

    def fv(rate: float) -> float:
        return sum(cf * (1 + rate) ** (n - 1 - i) for i, cf in enumerate(cashflows))

    lo, hi = -0.99, 1.0
    if (fv(lo) - final_value) * (fv(hi) - final_value) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if fv(mid) > final_value:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def _bisect(f, lo: float, hi: float, iters: int = 60) -> float | None:
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# PK-Einkauf
# ---------------------------------------------------------------------------


def buyin_tax_saving(ctx: TaxContext, amount: float, year_index: int = 0) -> float:
    """Steuerersparnis durch einen Einkauf von ``amount`` im Jahr ``year_index``."""
    if amount <= 0:
        return 0.0
    return -ctx.extra_income_tax(year_index, -amount)


def buyin_savings_curve(ctx: TaxContext, max_amount: float, points: int = 41) -> pd.DataFrame:
    rows = []
    step = max_amount / max(points - 1, 1)
    prev = 0.0
    for k in range(points):
        amt = step * k
        s = buyin_tax_saving(ctx, amt)
        rows.append({
            "Einkauf": amt,
            "Steuerersparnis": s,
            "Ø Ersparnis %": (s / amt * 100) if amt > 0 else None,
            "Ersparnis auf letzten Franken %": ((s - prev) / step * 100) if k > 0 else None,
        })
        prev = s
    df = pd.DataFrame(rows)
    if len(df) > 1:
        df.loc[0, "Ersparnis auf letzten Franken %"] = df.loc[1, "Ersparnis auf letzten Franken %"]
        df.loc[0, "Ø Ersparnis %"] = df.loc[1, "Ersparnis auf letzten Franken %"]
    return df


def staggering_table(ctx: TaxContext, total: float, max_years: int) -> pd.DataFrame:
    """Gesamte Steuerersparnis, wenn ``total`` auf 1..max_years Jahre verteilt wird."""
    rows = []
    for years in range(1, max(1, max_years) + 1):
        per = total / years
        s = sum(buyin_tax_saving(ctx, per, i) for i in range(years))
        rows.append({"Anzahl Jahre": years, "Einkauf pro Jahr": per, "Steuerersparnis total": s,
                     "Ersparnis %": s / total * 100 if total else 0.0})
    return pd.DataFrame(rows)


@dataclass
class BuyinComparison:
    buyins: dict
    savings: dict
    pk_capital_without: float
    pk_capital_with: float
    cap_tax_without: float
    cap_tax_with: float
    etf_from_savings: float
    etf_alternative: float
    invest_savings: bool

    @property
    def total_buyin(self) -> float:
        return sum(self.buyins.values())

    @property
    def total_savings(self) -> float:
        return sum(self.savings.values())

    @property
    def pk_gain_net(self) -> float:
        """Zusätzliches Nettokapital (nach Kapitalbezugssteuer) dank Einkauf."""
        return (self.pk_capital_with - self.cap_tax_with) - (self.pk_capital_without - self.cap_tax_without)

    @property
    def extra_cap_tax(self) -> float:
        return self.cap_tax_with - self.cap_tax_without

    @property
    def result_buyin(self) -> float:
        savings_part = self.etf_from_savings if self.invest_savings else self.total_savings
        return self.pk_gain_net + savings_part

    @property
    def result_etf(self) -> float:
        return self.etf_alternative

    @property
    def advantage(self) -> float:
        return self.result_buyin - self.result_etf


def compare_buyin_vs_etf(
    buyins: dict[int, float],
    horizon: int,
    pk_capital_without: float,
    pk_interest: float,
    ctx: TaxContext,
    etf: EtfAssumptions,
    invest_savings: bool = True,
) -> BuyinComparison:
    """Einkauf in die PK vs. gleicher Betrag in ein ETF-Depot (bis zur Pensionierung).

    Variante Einkauf: Einkauf wächst mit PK-Zins, Kapitalbezugssteuer bei Pensionierung
    (progressiv: Differenz zum Kapital ohne Einkauf), Steuerersparnis -> ETF (optional).
    Variante ETF: gleicher Betrag ins ETF-Depot (Dividenden- & Vermögenssteuer jährlich).
    """
    r = pk_interest / 100.0
    savings, extra_pk = {}, 0.0
    cf_buy, cf_save = [0.0] * horizon, [0.0] * horizon
    for i, amt in buyins.items():
        if amt <= 0 or i >= horizon:
            continue
        savings[i] = buyin_tax_saving(ctx, amt, i)
        extra_pk += amt * (1 + r) ** (horizon - 1 - i)
        cf_buy[i] += amt
        cf_save[i] += savings[i]
    k_with = pk_capital_without + extra_pk
    return BuyinComparison(
        buyins={i: a for i, a in buyins.items() if a > 0 and i < horizon},
        savings=savings,
        pk_capital_without=pk_capital_without,
        pk_capital_with=k_with,
        cap_tax_without=ctx.cap_tax(pk_capital_without),
        cap_tax_with=ctx.cap_tax(k_with),
        etf_from_savings=etf_final(cf_save, ctx, etf) if invest_savings else sum(cf_save),
        etf_alternative=etf_final(cf_buy, ctx, etf),
        invest_savings=invest_savings,
    )


def buyin_irr(cmp: BuyinComparison, horizon: int) -> float | None:
    """Effektive Jahresrendite des Einkaufs auf den Nettoaufwand (Einkauf minus Steuerersparnis)."""
    cfs = [0.0] * horizon
    for i, amt in cmp.buyins.items():
        cfs[i] += amt - cmp.savings.get(i, 0.0)
    return irr(cfs, cmp.pk_gain_net)


def etf_net_return(cmp: BuyinComparison, horizon: int) -> float | None:
    cfs = [0.0] * horizon
    for i, amt in cmp.buyins.items():
        cfs[i] += amt
    return irr(cfs, cmp.etf_alternative)


def breakeven_etf_return(
    buyins: dict[int, float], horizon: int, pk_capital_without: float, pk_interest: float,
    ctx: TaxContext, etf: EtfAssumptions, invest_savings: bool = True,
) -> float | None:
    """ETF-Rendite (% p.a. vor Kosten), ab der das ETF besser abschneidet als der Einkauf."""
    def f(rr: float) -> float:
        return compare_buyin_vs_etf(buyins, horizon, pk_capital_without, pk_interest, ctx,
                                    etf.with_return(rr), invest_savings).advantage
    return _bisect(f, -5.0, 25.0)


def buyin_by_age(
    amount: float, age: int, retirement_age: int, base_plan_df: pd.DataFrame, pk_interest: float,
    ctx: TaxContext, etf: EtfAssumptions, invest_savings: bool = True,
) -> pd.DataFrame:
    """Vorteil eines einmaligen Einkaufs je nach Einkaufsalter (Jahre bis Pensionierung)."""
    horizon = retirement_age - age
    k0 = pk.final_capital(base_plan_df)
    rows = []
    for i in range(horizon):
        c = compare_buyin_vs_etf({i: amount}, horizon, k0, pk_interest, ctx, etf, invest_savings)
        rows.append({
            "Einkaufsalter": age + i,
            "Jahre bis Pensionierung": horizon - i,
            "Vorteil Einkauf": c.advantage,
            "Netto Einkauf": c.result_buyin,
            "Netto ETF": c.result_etf,
            "Steuerersparnis": c.total_savings,
            "Rendite Einkauf %": (lambda x: x * 100 if x is not None else None)(buyin_irr(c, horizon)),
            "Sperrfrist": (horizon - i) <= 3,
        })
    return pd.DataFrame(rows)


def buyin_by_income(
    buyins: dict[int, float], horizon: int, pk_capital_without: float, pk_interest: float,
    ctx: TaxContext, etf: EtfAssumptions, incomes: list[float], invest_savings: bool = True,
) -> pd.DataFrame:
    rows = []
    for y in incomes:
        c2 = ctx.with_income(y)
        c = compare_buyin_vs_etf(buyins, horizon, pk_capital_without, pk_interest, c2, etf, invest_savings)
        total = c.total_buyin
        rows.append({
            "Steuerbares Einkommen": y,
            "Vorteil Einkauf": c.advantage,
            "Steuerersparnis %": c.total_savings / total * 100 if total else 0.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Weniger in die PK einzahlen, Differenz in ETF
# ---------------------------------------------------------------------------


@dataclass
class ReducedResult:
    df: pd.DataFrame  # jährliche Entwicklung
    capital_full: float
    capital_reduced: float
    cap_tax_full: float
    cap_tax_reduced: float
    etf_value: float
    total_reduction: float
    total_extra_tax: float

    @property
    def net_full(self) -> float:
        return self.capital_full - self.cap_tax_full

    @property
    def net_reduced(self) -> float:
        return self.capital_reduced - self.cap_tax_reduced + self.etf_value

    @property
    def advantage_etf(self) -> float:
        return self.net_reduced - self.net_full


def compare_reduced_contributions(
    plan: pk.PensionPlan, age: int, retirement_age: int, reduction: float, ctx: TaxContext,
    etf: EtfAssumptions, buyins: dict[int, float] | None = None,
) -> ReducedResult:
    """Szenario: AN-Sparbeitrag wird um ``reduction`` CHF/Jahr gesenkt (z.B. Wahlplan "Minus").

    Das steuerbare Einkommen steigt um die Reduktion -> Mehrsteuer. Der Rest wird
    jedes Jahr ins ETF investiert. Vergleich der Nettowerte bei Pensionierung.
    """
    horizon = max(0, retirement_age - age)
    growth = plan.salary_growth / 100.0
    red, extra_tax, cfs = [], [], []
    for i in range(horizon):
        an, _ = plan.contributions(age + i, i)
        d = min(reduction * (1 + growth) ** i, an)
        t = ctx.extra_income_tax(i, d)
        red.append(d)
        extra_tax.append(t)
        cfs.append(d - t)
    full = pk.project(plan, age, retirement_age, buyins)
    reduced = pk.project(plan, age, retirement_age, buyins, employee_reduction=red)
    etf_df = simulate_etf(cfs, ctx, etf) if horizon else pd.DataFrame({"Wert Ende": []})
    cap_full, cap_red = pk.final_capital(full), pk.final_capital(reduced)
    df = pd.DataFrame({
        "Alter": full["Alter"] + 1,
        "PK (voller Beitrag)": full["Guthaben Ende"],
        "PK (reduziert)": reduced["Guthaben Ende"],
        "ETF-Depot": etf_df["Wert Ende"] if horizon else 0.0,
        "Mehrsteuer Einkommen": extra_tax if horizon else 0.0,
        "Investiert ins ETF": cfs if horizon else 0.0,
    })
    df["PK reduziert + ETF"] = df["PK (reduziert)"] + df["ETF-Depot"]
    return ReducedResult(
        df=df,
        capital_full=cap_full,
        capital_reduced=cap_red,
        cap_tax_full=ctx.cap_tax(cap_full),
        cap_tax_reduced=ctx.cap_tax(cap_red),
        etf_value=float(etf_df["Wert Ende"].iloc[-1]) if horizon else 0.0,
        total_reduction=sum(red),
        total_extra_tax=sum(extra_tax),
    )


def reduced_sensitivity(
    plan: pk.PensionPlan, age: int, retirement_age: int, reduction: float, ctx: TaxContext,
    etf: EtfAssumptions, returns: list[float],
) -> pd.DataFrame:
    rows = []
    for rr in returns:
        res = compare_reduced_contributions(plan, age, retirement_age, reduction, ctx, etf.with_return(rr))
        rows.append({"ETF-Rendite %": rr, "Vorteil ETF": res.advantage_etf})
    return pd.DataFrame(rows)


def breakeven_reduced(
    plan: pk.PensionPlan, age: int, retirement_age: int, reduction: float, ctx: TaxContext,
    etf: EtfAssumptions,
) -> float | None:
    def f(rr: float) -> float:
        return compare_reduced_contributions(plan, age, retirement_age, reduction, ctx,
                                             etf.with_return(rr)).advantage_etf
    return _bisect(f, -5.0, 25.0)


# ---------------------------------------------------------------------------
# Zwei Pensionskassen vergleichen
# ---------------------------------------------------------------------------


@dataclass
class PlanComparison:
    df: pd.DataFrame
    summary: pd.DataFrame
    proj_a: pd.DataFrame
    proj_b: pd.DataFrame


def compare_two_plans(
    plan_a: pk.PensionPlan, plan_b: pk.PensionPlan, age: int, retirement_age: int,
    ctx: TaxContext, etf: EtfAssumptions, salary_diff: float = 0.0, invest_difference: bool = True,
) -> PlanComparison:
    """Vergleicht zwei Pensionskassen bei gleicher Person.

    Das eingegebene steuerbare Einkommen gilt für PK A. Für PK B wird es um die
    Differenz der abzugsfähigen AN-Beiträge (und ggf. Lohnunterschied) angepasst.
    Wer mehr Nettolohn hat, legt die Differenz (optional) in ein ETF an.
    """
    horizon = max(0, retirement_age - age)
    proj_a = pk.project(plan_a, age, retirement_age)
    proj_b = pk.project(plan_b, age, retirement_age)
    growth = plan_a.salary_growth / 100.0
    rows, cf_a, cf_b = [], [], []
    for i in range(horizon):
        a = age + i
        an_a, an_b = plan_a.employee_total(a, i), plan_b.employee_total(a, i)
        sd = salary_diff * (1 + growth) ** i
        delta_taxable = sd * (1 - SOZIALABZUEGE_AN) - (an_b - an_a)
        tax_diff = ctx.extra_income_tax(i, delta_taxable)  # Steuer B minus Steuer A
        cash_diff = sd * (1 - SOZIALABZUEGE_AN) - (an_b - an_a) - tax_diff  # Netto B minus A
        cf_a.append(max(0.0, -cash_diff))
        cf_b.append(max(0.0, cash_diff))
        rows.append({"Alter": a + 1, "Lohnabzug PK A": an_a, "Lohnabzug PK B": an_b,
                     "Steuerdifferenz (B−A)": tax_diff, "Nettolohn-Differenz (B−A)": cash_diff})
    df = pd.DataFrame(rows)
    etf_a = simulate_etf(cf_a, ctx, etf) if (horizon and invest_difference) else None
    etf_b = simulate_etf(cf_b, ctx, etf) if (horizon and invest_difference) else None
    if horizon:
        df["PK A"] = proj_a["Guthaben Ende"].values
        df["PK B"] = proj_b["Guthaben Ende"].values
        df["ETF A"] = etf_a["Wert Ende"].values if etf_a is not None else 0.0
        df["ETF B"] = etf_b["Wert Ende"].values if etf_b is not None else 0.0

    def summary_for(plan, proj, etf_df, cfs, an_key):
        cap = pk.final_capital(proj)
        cap_tax = ctx.cap_tax(cap)
        etf_val = float(etf_df["Wert Ende"].iloc[-1]) if etf_df is not None and len(etf_df) else 0.0
        an_total = float(df[an_key].sum()) if horizon else 0.0
        return {
            "Altersguthaben bei Pensionierung": cap,
            "Jährliche Rente (Umwandlungssatz)": cap * plan.conversion_rate / 100.0,
            "Kapitalbezugssteuer": cap_tax,
            "Nettokapital nach Steuer": cap - cap_tax,
            "ETF aus Nettolohn-Differenz": etf_val,
            "Total Nettovermögen": cap - cap_tax + etf_val,
            "Summe Lohnabzüge PK (AN)": an_total,
            "Summe Sparbeiträge AG": float(proj["Beitrag AG"].sum()),
            "Summe Zinsen": float(proj["Zins"].sum()),
        }

    summary = pd.DataFrame({
        plan_a.name: summary_for(plan_a, proj_a, etf_a, cf_a, "Lohnabzug PK A"),
        plan_b.name: summary_for(plan_b, proj_b, etf_b, cf_b, "Lohnabzug PK B"),
    })
    summary["Differenz (B−A)"] = summary[plan_b.name] - summary[plan_a.name]
    return PlanComparison(df=df, summary=summary, proj_a=proj_a, proj_b=proj_b)


# ---------------------------------------------------------------------------
# Rente vs. Kapital
# ---------------------------------------------------------------------------


def annuity_vs_capital(
    capital: float, conversion_rate: float, retirement_age: int, ctx_retirement: TaxContext,
    capital_return_net: float = 2.0, max_age: int = 100,
) -> tuple[pd.DataFrame, dict]:
    """Vergleicht lebenslange Rente mit Kapitalbezug (Kapitalverzehr in gleicher Höhe).

    ctx_retirement.income = übriges steuerbares Einkommen im Ruhestand (z.B. AHV).
    """
    pension = capital * conversion_rate / 100.0
    pension_tax = ctx_retirement.extra_income_tax(0, pension)
    net_pension = pension - pension_tax
    cap_tax = ctx_retirement.cap_tax(capital)
    net_capital = capital - cap_tax
    rows, cum, rest = [], 0.0, net_capital
    be_simple = be_return = None
    for a in range(retirement_age, max_age + 1):
        cum += net_pension
        rest = rest * (1 + capital_return_net / 100.0) - net_pension
        if be_simple is None and cum >= net_capital:
            be_simple = a + 1
        if be_return is None and rest <= 0:
            be_return = a + 1
        rows.append({"Alter": a + 1, "Kumulierte Netto-Rente": cum,
                     "Kapital ohne Rendite (Rest)": max(net_capital - cum, 0.0),
                     "Kapital mit Rendite (Rest)": max(rest, 0.0)})
    info = {
        "Rente brutto": pension,
        "Einkommenssteuer auf Rente": pension_tax,
        "Rente netto": net_pension,
        "Kapitalbezugssteuer": cap_tax,
        "Kapital netto": net_capital,
        "Break-even ohne Rendite": be_simple,
        "Break-even mit Rendite": be_return,
    }
    return pd.DataFrame(rows), info
