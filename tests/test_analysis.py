import pytest

from pkcalc import analysis as an
from pkcalc import pension as pk
from pkcalc import tax as T

LOC = T.load_tax_data().find_location("Zürich", "ZH")
PROFILE = T.profile_for_location(LOC)


def ctx(income=120_000, wealth=100_000):
    return an.TaxContext(PROFILE, income=income, wealth=wealth)


def test_irr():
    assert an.irr([100, 0, 0], 121) == pytest.approx(0.10, abs=1e-6)
    assert an.irr([0, 0, 100], 100) is None  # keine Laufzeit


def test_einkauf_steuerersparnis_und_staffelung():
    c = ctx()
    s = an.buyin_tax_saving(c, 30_000)
    assert s == pytest.approx(c.tax(120_000) - c.tax(90_000))
    stg = an.staggering_table(c, 90_000, 3)
    # Progression: verteilt sparen bringt mehr
    assert stg["Steuerersparnis total"].iloc[2] > stg["Steuerersparnis total"].iloc[0]


def test_einkauf_gewinnt_bei_gleicher_rendite():
    c = ctx()
    etf = an.EtfAssumptions(total_return=2.0, dividend_yield=1.0, ter=0.2)
    res = an.compare_buyin_vs_etf({0: 50_000}, 10, 500_000, 2.0, c, etf)
    assert res.total_savings > 0
    assert res.advantage > 0


def test_breakeven_rendite_ist_nullstelle():
    c = ctx()
    etf = an.EtfAssumptions()
    be = an.breakeven_etf_return({0: 50_000}, 20, 600_000, 2.0, c, etf)
    assert be is not None
    res = an.compare_buyin_vs_etf({0: 50_000}, 20, 600_000, 2.0, c, etf.with_return(be))
    assert abs(res.advantage) < 5


def test_einkauf_je_alter_spaeter_besser():
    c = ctx()
    plan = pk.PensionPlan(balance=200_000, employee_savings=8_000, employer_savings=10_000)
    base = pk.project(plan, 45, 65)
    df = an.buyin_by_age(50_000, 45, 65, base, 2.0, c, an.EtfAssumptions(total_return=6.0))
    assert df["Vorteil Einkauf"].iloc[-1] > df["Vorteil Einkauf"].iloc[0]
    assert df["Sperrfrist"].sum() == 3


def test_reduktion_null_ist_neutral():
    plan = pk.PensionPlan(balance=100_000, employee_savings=8_000, employer_savings=10_000)
    res = an.compare_reduced_contributions(plan, 40, 65, 0.0, ctx(), an.EtfAssumptions())
    assert res.advantage_etf == pytest.approx(0, abs=1e-6)


def test_reduktion_mehrsteuer_und_etf():
    plan = pk.PensionPlan(balance=100_000, employee_savings=8_000, employer_savings=10_000)
    res = an.compare_reduced_contributions(plan, 40, 65, 3_000.0, ctx(), an.EtfAssumptions())
    assert res.capital_reduced < res.capital_full
    assert 0 < res.total_extra_tax < res.total_reduction
    assert res.etf_value > 0


def test_zwei_gleiche_pks():
    a = pk.PensionPlan(name="A", balance=100_000, employee_savings=6_000, employer_savings=6_000)
    b = a.copy(name="B")
    cmp = an.compare_two_plans(a, b, 40, 65, ctx(), an.EtfAssumptions())
    assert cmp.summary["Differenz (B−A)"].abs().max() == pytest.approx(0, abs=1e-6)


def test_zwei_pks_hoeherer_ag_beitrag_besser():
    a = pk.PensionPlan(name="A", balance=100_000, employee_savings=6_000, employer_savings=6_000)
    b = a.copy(name="B", employer_savings=9_000)
    cmp = an.compare_two_plans(a, b, 40, 65, ctx(), an.EtfAssumptions())
    assert cmp.summary.loc["Total Nettovermögen", "Differenz (B−A)"] > 0


def test_rente_vs_kapital():
    df, info = an.annuity_vs_capital(500_000, 5.5, 65, an.TaxContext(PROFILE, income=30_000), 0.0)
    assert info["Rente brutto"] == pytest.approx(27_500)
    assert info["Rente netto"] < info["Rente brutto"]
    assert info["Break-even ohne Rendite"] is not None
    assert 75 < info["Break-even ohne Rendite"] < 100


def _split(ret, budget=20_000, potential=100_000):
    plan = pk.PensionPlan(balance=150_000, employee_savings=8_000, employer_savings=10_000, interest=2.0)
    k0 = pk.final_capital(pk.project(plan, 45, 65))
    return an.optimize_buyin_split(budget, list(range(0, 17)), 20, k0, 2.0, ctx(), an.EtfAssumptions(total_return=ret),
                                   potential)


def test_optimierung_tiefe_etf_rendite_kauft_voll_ein():
    res = _split(0.0)
    assert res.total_buyin == pytest.approx(100_000, abs=1)
    assert res.value_opt >= res.value_etf


def test_optimierung_hohe_etf_rendite_kaum_einkauf():
    res = _split(10.0)
    assert res.total_buyin <= 10_000
    assert res.best_constant == 0


def test_optimierung_ist_mindestens_so_gut_wie_extreme():
    for ret in (3.0, 5.0, 7.0):
        res = _split(ret)
        assert res.value_opt >= res.value_etf - 1
        assert res.value_opt >= res.value_max - 1
        assert all(a <= 20_000 + 1e-6 for a in res.alloc.values())
        assert res.total_buyin <= 100_000 + 1e-6
