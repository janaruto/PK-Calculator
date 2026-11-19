import math

import pytest

from pkcalc import tax as T

DATA = T.load_tax_data()


def single(canton_id=26, **kw):
    return T.TaxProfile(canton_id=canton_id, **kw)


def test_bundessteuer_2026_alleinstehend():
    p = single()
    # Tarif 2026: ab 82'100 -> 1'502.95 + 6.6 % ; ab 794'000 -> 11.5 % flat
    assert T.federal_income_tax(15_200, p) == 0
    assert T.federal_income_tax(100_000, p) == pytest.approx(1502.95 + 17_900 * 0.066, abs=0.01)
    assert T.federal_income_tax(1_000_000, p) == pytest.approx(115_000, abs=0.01)


def test_bundessteuer_kinderermaessigung():
    p0 = T.TaxProfile(canton_id=26, married=True)
    p2 = T.TaxProfile(canton_id=26, married=True, children=2)
    assert T.federal_income_tax(150_000, p0) - T.federal_income_tax(150_000, p2) == pytest.approx(2 * 263)


def test_zuerich_einfache_steuer_grundtarif():
    # 7000@0 + 5000@2% + 4800@3% + 8000@4% + 9700@5% + 11200@6% + 4300@7%
    assert T.simple_tax(50_000, 26, "EINKOMMENSSTEUER", ("LEDIG_ALLEINE",)) == pytest.approx(2022, abs=0.01)


def test_zuerich_stadt_einkommenssteuer():
    loc = DATA.find_location("Zürich", "ZH")
    p = T.profile_for_location(loc)
    r = T.income_tax(100_000, p)
    assert r.canton == pytest.approx(r.base * loc.income_canton / 100)
    assert r.city == pytest.approx(r.base * loc.income_city / 100)
    assert r.church == 0


@pytest.mark.parametrize("capital,expected", [(100_000, 2734), (250_000, 11253), (500_000, 28253), (1_000_000, 61552)])
def test_kapitalbezug_zug_publizierte_werte(capital, expected):
    p = T.profile_for_location(DATA.find_location("Zug", "ZG"))
    assert T.capital_withdrawal_tax(capital, p).total == pytest.approx(expected, abs=5)


def test_kapitalbezug_zuerich_stadt_500k():
    # ZKB: ca. CHF 36'000 nach Revision (1/20-Satz, mind. 2 %)
    p = T.profile_for_location(DATA.find_location("Zürich", "ZH"), confession="reformiert")
    assert 35_000 < T.capital_withdrawal_tax(500_000, p).total < 37_500


def test_vermoegens_freibetrag_aargau():
    p = single(1)
    assert T.wealth_deductions(p) == 130_000
    assert T.wealth_tax(120_000, p).total == 0


def test_formel_parser():
    assert T._eval_formula("0.49 * $wert$ / 100", 10_000) == pytest.approx(49)
    assert T._eval_formula("2 * (log $wert$ - 1)", math.e) == pytest.approx(0)
    assert T._eval_formula("-3 + 5", 0) == 2


def test_splitting_verheiratet_guenstiger():
    for cid in (1, 4, 8, 26):
        s = T.income_tax(150_000, single(cid)).total
        m = T.income_tax(150_000, single(cid, married=True)).total
        assert m < s


@pytest.mark.parametrize("cid", sorted(DATA.cantons))
def test_alle_kantone_rechnen_und_sind_monoton(cid):
    for married, children in ((False, 0), (True, 0), (False, 1)):
        p = T.TaxProfile(canton_id=cid, married=married, children=children)
        prev = -1.0
        for inc in range(0, 600_001, 20_000):
            t = T.income_tax(inc, p).total
            assert t >= prev - 1e-6
            prev = t
        prev = -1.0
        for w in range(0, 3_000_001, 250_000):
            t = T.wealth_tax(w, p).total
            assert t >= prev - 1e-6
            prev = t
        prev = -1.0
        for k in range(0, 2_000_001, 100_000):
            t = T.capital_withdrawal_tax(k, p).total
            assert t >= 0
            if cid not in T.UNVERIFIED_CAPITAL_RULES:
                assert t < k * 0.2 + 1
            assert t >= prev - 1e-6
            prev = t


def test_alle_gemeinden_haben_steuerfuesse():
    assert len(DATA.locations) > 2000
    for loc in DATA.locations:
        assert loc.income_canton >= 0 and loc.income_city >= 0


@pytest.mark.parametrize("abbr,name", sorted(T.CANTON_CAPITALS.items()))
def test_kapitalbezug_500k_im_publizierten_band(abbr, name):
    """Publizierte Vergleiche (Kantonshauptorte, ledig, ohne Kirche): CHF 25'700 bis 49'500."""
    loc = DATA.find_location(name, abbr)
    if loc.canton_id in T.UNVERIFIED_CAPITAL_RULES:
        pytest.skip("Regel nicht verifiziert")
    total = T.capital_withdrawal_tax(500_000, T.profile_for_location(loc)).total
    assert 25_000 <= total <= 50_000


def test_kapitalbezug_korrekturfaktor():
    p = T.profile_for_location(DATA.find_location("Lausanne", "VD"))
    full = T.capital_withdrawal_tax(500_000, p)
    half = T.capital_withdrawal_tax(500_000, p.with_rates(capital_tax_correction=0.5))
    assert half.bund == full.bund
    assert half.canton == pytest.approx(full.canton / 2)


def test_wallis_indexierung_senkt_satz():
    p = T.TaxProfile(canton_id=24)
    # Satz bei 100'000 entspricht unindexiertem Satz bei 100'000 / 1.73
    assert T.simple_tax(100_000, 24, "EINKOMMENSSTEUER", ("LEDIG_ALLEINE",)) < 100_000 * 0.135
