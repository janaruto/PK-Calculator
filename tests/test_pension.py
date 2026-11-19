import pytest

from pkcalc import pension as pk


def test_projektion_fixe_beitraege():
    plan = pk.PensionPlan(balance=100_000, employee_savings=5_000, employer_savings=5_000, interest=2.0)
    df = pk.project(plan, 63, 65)
    assert len(df) == 2
    assert df["Guthaben Ende"].iloc[0] == pytest.approx(112_000)
    assert pk.final_capital(df) == pytest.approx(112_000 * 1.02 + 10_000)


def test_projektion_mit_einkauf_und_zerlegung():
    plan = pk.PensionPlan(balance=50_000, employee_savings=1_000, employer_savings=2_000, interest=1.0)
    df = pk.project(plan, 60, 65, buyins={1: 10_000})
    dec = pk.decompose(df, 50_000)
    assert dec["Einkäufe"] == 10_000
    assert sum(dec.values()) == pytest.approx(pk.final_capital(df))


def test_altersstaffel():
    plan = pk.PensionPlan(mode="staffel", insured_salary=60_000, staffel=pk.default_staffel(0.5))
    assert plan.contributions(30, 0) == pytest.approx((2_100, 2_100))
    assert plan.contributions(56, 0) == pytest.approx((5_400, 5_400))


def test_bvg_koordinierter_lohn():
    assert pk.bvg_koordinierter_lohn(20_000) == 0
    assert pk.bvg_koordinierter_lohn(25_000) == 3_780
    assert pk.bvg_koordinierter_lohn(80_000) == 80_000 - 26_460
    assert pk.bvg_koordinierter_lohn(200_000) == 90_720 - 26_460


def test_buyin_schedule():
    assert pk.buyin_schedule(60_000, 3, 2, 10) == {2: 20_000, 3: 20_000, 4: 20_000}
    assert pk.buyin_schedule(60_000, 3, 9, 10) == {9: 20_000}  # Rest nach Pensionierung entfällt
    assert pk.buyin_schedule(0, 3, 0, 10) == {}
