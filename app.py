"""PK-Rechner Schweiz – Pensionskasse, Einkauf, Steuern und ETF-Vergleich.

Start:  streamlit run app.py
"""

from __future__ import annotations

import inspect
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pkcalc import analysis as an
from pkcalc import pension as pk
from pkcalc import tax as tx
from pkcalc.texts import DISCLAIMER, GLOSSAR, H, INFO

st.set_page_config(page_title="PK-Rechner Schweiz", page_icon="🏦", layout="wide")

# ---------------------------------------------------------------------------
# Darstellung
# ---------------------------------------------------------------------------

C = {  # validierte Kategorie-Reihenfolge (feste Zuordnung, nie zyklisch)
    "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
    "magenta": "#e87ba4", "green": "#008300", "violet": "#6250d6", "red": "#e34948",
    "muted": "#898781", "grid": "rgba(137,135,129,0.25)",
}
PK_COLOR, ETF_COLOR = C["blue"], C["orange"]


_NO_ARROW = {"delta_arrow": "off"} if "delta_arrow" in inspect.signature(st.metric).parameters else {}


def signed_chf(x: float) -> str:
    """Vorzeichen vorne, damit Streamlit die Richtung (rot/grün) erkennt."""
    return f"{'-' if x < 0 else '+'}CHF {abs(x):,.0f}".replace(",", "'")


def chf(x: float | None, prefix: bool = True) -> str:
    if x is None:
        return "–"
    s = f"{x:,.0f}".replace(",", "'")
    return f"CHF {s}" if prefix else s


def pct(x: float | None, d: int = 1) -> str:
    return "–" if x is None else f"{x * 100:.{d}f} %"


def style(fig: go.Figure, height: int = 380, y_title: str | None = None, x_title: str | None = None,
          y_pct: bool = False, hover: str = "x unified") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        hovermode=hover,
        separators=".'",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None),
        hoverlabel=dict(namelength=-1),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, title=x_title, zeroline=False,
                     tickformat=",.0f" if x_title and "CHF" in x_title else None)
    fig.update_yaxes(gridcolor=C["grid"], gridwidth=1, title=y_title, zeroline=False,
                     tickformat=".0%" if y_pct else ",.0f")
    return fig


def table(df: pd.DataFrame, money=(), pcts=(), pct_fmt: str = "%.1f %%", **kwargs) -> None:
    """Tabelle mit gerundeten Frankenbeträgen (Tausendertrennzeichen gemäss Browser-Sprache)."""
    df = df.copy()
    cfg = {}
    for col in money:
        df[col] = pd.to_numeric(df[col]).round(0)
        cfg[col] = st.column_config.NumberColumn(col, format="localized")
    for col in pcts:
        cfg[col] = st.column_config.NumberColumn(col, format=pct_fmt)
    st.dataframe(df, column_config=cfg, **kwargs)


def plot(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, key=key, config={"displayModeBar": False, "locale": "de-CH"})


def title_with_info(title: str, info_md: str, level: int = 3, key: str | None = None) -> None:
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment="center")
    c1.markdown(f"{'#' * level} {title}")
    with c2.popover("ℹ️ Erklärung", width="stretch", key=key):
        st.markdown(info_md)


def money_input(label: str, value: float, key: str, help: str, step: int = 1000, max_value=None,
                container=st) -> float:
    return float(container.number_input(label, min_value=0, max_value=max_value, value=int(value),
                                        step=step, key=key, help=help, format="%d"))


CAPITALS = tx.CANTON_CAPITALS


@st.cache_resource
def get_data() -> tx.TaxData:
    return tx.load_tax_data()


data = get_data()

# ---------------------------------------------------------------------------
# Sidebar – Eingaben
# ---------------------------------------------------------------------------

sb = st.sidebar
sb.title("🏦 PK-Rechner")
sb.caption("Alle Felder mit ❔ haben eine Erklärung (Maus darüber bzw. antippen).")

with sb.expander("👤 Person", expanded=True):
    age = int(st.number_input("Alter heute", 18, 69, 45, help=H["alter"]))
    horizon_mode = st.radio("Zeithorizont angeben als", ["Pensionierungsalter", "Verbleibende Arbeitsjahre"],
                            horizontal=True, help=H["horizont"], key="horizon_mode")
    if horizon_mode == "Verbleibende Arbeitsjahre":
        years_left = int(st.number_input("Verbleibende Arbeitsjahre", 1, 70 - age, max(1, 65 - age),
                                         help=H["arbeitsjahre"]))
        retirement_age = age + years_left
    else:
        retirement_age = int(st.number_input("Pensionierungsalter", max(age + 1, 58), 70, max(65, age + 1),
                                             help=H["rentenalter"]))
    st.caption(f"⏳ Noch **{retirement_age - age} Arbeitsjahre**: Pensionierung mit {retirement_age} "
               f"im Jahr {date.today().year + retirement_age - age}.")
    if retirement_age < 58:
        st.info("Vor 58 ist eine Pensionierung in der PK meist nicht möglich. Bei Erwerbsaufgabe geht das "
                "Guthaben auf ein Freizügigkeitskonto (Bezug frühestens 5 Jahre vor dem AHV-Alter). "
                "Die Rechnung nimmt vereinfacht einen Bezug am Ende der Arbeitsjahre an.")
    zivil =st.selectbox("Zivilstand", ["Alleinstehend", "Verheiratet / eingetr. Partnerschaft"],
                         help=H["zivilstand"])
    married = zivil.startswith("Verheiratet")
    children = int(st.number_input("Anzahl Kinder", 0, 10, 0, help=H["kinder"]))
    confession = st.selectbox("Konfession", list(tx.CONFESSIONS), format_func=tx.CONFESSIONS.get,
                              help=H["konfession"])

horizon = retirement_age - age

with sb.expander("🧾 Steuern & Wohnort", expanded=True):
    canton_ids = sorted(data.cantons, key=lambda cid: data.cantons[cid].name)
    zh_id = next(cid for cid in canton_ids if data.cantons[cid].abbr == "ZH")
    canton_id = st.selectbox("Kanton", canton_ids, index=canton_ids.index(zh_id),
                             format_func=lambda cid: f"{data.cantons[cid].name} ({data.cantons[cid].abbr})",
                             help=H["kanton"])
    canton = data.cantons[canton_id]
    locs = data.locations_of_canton(canton.id)
    bfs_ids = [l.bfs for l in locs]
    names = [l.name for l in locs]
    default_loc = CAPITALS.get(canton.abbr, names[0])
    bfs = st.selectbox("Gemeinde", bfs_ids, index=names.index(default_loc) if default_loc in names else 0,
                       format_func=lambda b: data.location(b).name, help=H["gemeinde"], key=f"gem_{canton.id}")
    loc = data.location(bfs)
    k = f"{loc.bfs}_{confession}"
    st.markdown("**Steuerfüsse Einkommen** (in % der einfachen Steuer, aus ESTV-Daten vorausgefüllt)")
    rate_canton = st.number_input("Kantonssteuerfuss %", 0.0, 400.0, float(loc.income_canton), 1.0,
                                  key=f"sk_{k}", help=H["sf_kanton"])
    rate_city = st.number_input("Gemeindesteuerfuss %", 0.0, 400.0, float(loc.income_city), 1.0,
                                key=f"sg_{k}", help=H["sf_gemeinde"])
    rate_church = st.number_input("Kirchensteuerfuss %", 0.0, 100.0, float(loc.income_church.get(confession, 0.0)),
                                  0.5, key=f"sc_{k}", help=H["sf_kirche"])
    income = money_input("Steuerbares Einkommen (CHF/Jahr)", 120_000, "income", H["einkommen"])
    bund_diff = st.checkbox("Steuerbares Einkommen Bund weicht ab", help=H["einkommen_bund"])
    income_bund = money_input("Steuerbares Einkommen Bund", income + 2_000, "income_bund",
                              H["einkommen_bund"]) if bund_diff else income
    wealth = money_input("Reinvermögen (CHF)", 150_000, "wealth", H["vermoegen"], step=5000)
    apply_wd = st.checkbox("Kantonale Vermögens-Freibeträge abziehen", value=True, help=H["freibetrag"])
    with st.popover("⚙️ Steuerfüsse Vermögen", width="stretch"):
        st.caption("In den meisten Gemeinden gleich wie beim Einkommen.")
        w_canton = st.number_input("Kanton % (Vermögen)", 0.0, 400.0, float(loc.wealth_canton), 1.0,
                                   key=f"wk_{k}")
        w_city = st.number_input("Gemeinde % (Vermögen)", 0.0, 400.0, float(loc.wealth_city), 1.0,
                                 key=f"wg_{k}")
        w_church = st.number_input("Kirche % (Vermögen)", 0.0, 100.0,
                                   float(loc.wealth_church.get(confession, 0.0)), 0.5, key=f"wc_{k}")
    with st.popover("⚙️ Kapitalbezugssteuer anpassen", width="stretch"):
        st.caption(H["kap_korrektur"])
        cap_corr = st.number_input("Kanton/Gemeinde in % des berechneten Werts", 10, 200, 100, 5,
                                   key=f"capcorr_{canton.id}", help=H["kap_korrektur"])
    if canton.id in tx.UNVERIFIED_CAPITAL_RULES:
        st.warning(f"Kapitalbezugssteuer {canton.abbr}: Regel nicht mit aktuellen Vergleichswerten geprüft, "
                   "Resultat eher zu hoch. Mit dem ESTV-Rechner vergleichen und oben anpassen.")
    if canton.abbr == "VS" and married:
        st.info("Wallis: Die Steuerermässigung für Verheiratete ist nicht berücksichtigt.")

profile = tx.TaxProfile(
    canton_id=canton.id, married=married, children=children,
    rate_canton=rate_canton, rate_city=rate_city, rate_church=rate_church,
    wealth_rate_canton=w_canton, wealth_rate_city=w_city, wealth_rate_church=w_church,
    capital_tax_correction=cap_corr / 100.0,
)
effective_wealth = wealth if apply_wd else wealth + tx.wealth_deductions(profile)
# Hinweis: wealth_tax() zieht Freibeträge immer ab; ohne Häkchen werden sie oben wieder addiert.

with sb.expander("🏦 Pensionskasse", expanded=True):
    balance = money_input("Aktuelles Altersguthaben (CHF)", 150_000, "balance", H["guthaben"], step=5000)
    mode = st.radio("Beiträge erfassen als", ["Fixe Beträge (CHF/Jahr)", "Altersstaffel (% vom vers. Lohn)"],
                    help=H["modus"])
    staffel = pk.default_staffel()
    insured_salary = 0.0
    an_fix = ag_fix = 0.0
    if mode.startswith("Fixe"):
        an_fix = money_input("Sparbeitrag Arbeitnehmer (CHF/Jahr)", 8_000, "an_fix", H["an_spar"], step=100)
        ag_fix = money_input("Sparbeitrag Arbeitgeber (CHF/Jahr)", 10_000, "ag_fix", H["ag_spar"], step=100)
    else:
        insured_salary = money_input("Versicherter Lohn (CHF/Jahr)", 70_000, "vers_lohn", H["vers_lohn"])
        st.caption("Sparbeiträge in % des versicherten Lohns – " + H["staffel"])
        sdf = pd.DataFrame([{"Von Alter": s.from_age, "Bis Alter": s.to_age, "AN %": s.employee_pct,
                             "AG %": s.employer_pct} for s in staffel])
        sdf = st.data_editor(sdf, hide_index=True, num_rows="dynamic", key="staffel_editor")
        staffel = [pk.StaffelStufe(int(r["Von Alter"]), int(r["Bis Alter"]), float(r["AN %"]), float(r["AG %"]))
                   for _, r in sdf.dropna().iterrows()]
    risk = money_input("Risikobeitrag Arbeitnehmer (CHF/Jahr)", 1_000, "risk", H["risiko"], step=100)
    interest = st.number_input("Verzinsung Altersguthaben % p.a.", -2.0, 10.0, 2.0, 0.25, help=H["zins"])
    uws = st.number_input("Umwandlungssatz %", 3.0, 8.0, 5.6, 0.1, help=H["uws"])
    growth = st.number_input("Lohn-/Beitragswachstum % p.a.", 0.0, 5.0, 0.0, 0.25, help=H["lohnwachstum"])
    potential = money_input("Einkaufspotenzial (CHF)", 150_000, "potential", H["potenzial"], step=5000)

plan = pk.PensionPlan(
    name="Meine PK", balance=balance, mode="fix" if mode.startswith("Fixe") else "staffel",
    employee_savings=an_fix, employer_savings=ag_fix, insured_salary=insured_salary, staffel=staffel,
    employee_risk=risk, interest=interest, conversion_rate=uws, salary_growth=growth,
    buyin_potential=potential,
)

with sb.expander("💰 Geplanter Einkauf", expanded=True):
    buy_total = money_input("Einkauf total (CHF)", min(60_000, potential), "buy_total", H["einkauf_total"],
                            step=5000)
    if buy_total > potential:
        st.warning(f"Der Einkauf übersteigt Ihr Einkaufspotenzial – es wird mit {chf(potential)} gerechnet.")
        buy_total = potential
    buy_years = int(st.number_input("Verteilt auf Jahre", 1, max(1, horizon), min(3, max(1, horizon)),
                                    help=H["einkauf_jahre"]))
    buy_start_age = int(st.number_input("Erster Einkauf mit Alter", age, retirement_age - 1,
                                        max(age, retirement_age - 3 - buy_years), help=H["einkauf_start"]))
    buyins = pk.buyin_schedule(buy_total, buy_years, buy_start_age - age, horizon)
    if buyins and max(buyins) >= horizon - 3:
        st.warning("⚠️ Einkauf innerhalb von 3 Jahren vor der Pensionierung: Diesen Teil dürfen Sie "
                   "nicht als Kapital beziehen (nur als Rente), sonst entfällt der Steuerabzug.")
    if buy_start_age - age + buy_years > horizon:
        st.info("Ein Teil des Einkaufs liegt nach der Pensionierung und wird ignoriert.")

with sb.expander("📈 Annahmen ETF / Privat anlegen", expanded=False):
    etf_ret = st.number_input("Erwartete Rendite % p.a. (vor Kosten)", -5.0, 15.0, 5.0, 0.25, help=H["etf_rendite"])
    etf_div = st.number_input("Davon Dividendenrendite % p.a.", 0.0, 10.0, 1.8, 0.1, help=H["etf_div"])
    etf_ter = st.number_input("Kosten (TER + Depot) % p.a.", 0.0, 3.0, 0.25, 0.05, help=H["etf_ter"])
    invest_savings = st.checkbox("Steuerersparnis aus Einkauf ins ETF investieren", True, help=H["steuer_invest"])

etf = an.EtfAssumptions(total_return=etf_ret, dividend_yield=etf_div, ter=etf_ter)
ctx = an.TaxContext(profile, income=income, wealth=effective_wealth, bund_offset=income_bund - income,
                    income_growth=growth)

sb.divider()
sb.caption(f"Steuerdaten {data.year}: ESTV (alle Kantone & Gemeinden). " + DISCLAIMER)

# ---------------------------------------------------------------------------
# Kernberechnungen
# ---------------------------------------------------------------------------

tax_income = tx.income_tax(income, profile, income_bund)
tax_wealth = tx.wealth_tax(effective_wealth, profile)
marg = tx.marginal_income_rate(income, profile, bund_offset=income_bund - income)

proj = pk.project(plan, age, retirement_age, buyins)
proj_base = pk.project(plan, age, retirement_age)
capital = pk.final_capital(proj)
capital_base = pk.final_capital(proj_base)
cap_tax = ctx.cap_tax(capital)
buy_cmp = an.compare_buyin_vs_etf(buyins, horizon, capital_base, interest, ctx, etf, invest_savings)

# ---------------------------------------------------------------------------
# Kopf
# ---------------------------------------------------------------------------

st.title("PK-Rechner Schweiz")
st.markdown(
    "Pensionskasse hochrechnen, Steuern berechnen, **Einkauf prüfen** und mit einer **ETF-Anlage "
    "vergleichen**. Eingaben links in der Seitenleiste – überall mit ℹ️/❔ erklärt."
)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Steuern pro Jahr", chf(tax_income.total + tax_wealth.total), border=True,
          help="Einkommens- und Vermögenssteuer: Bund + Kanton + Gemeinde + Kirche")
m2.metric("Grenzsteuersatz", pct(marg), border=True,
          help="So viel Steuern sparen Sie pro abgezogenem Franken (z.B. PK-Einkauf).")
m3.metric(f"PK-Kapital mit {retirement_age}", chf(capital), f"in {horizon} Arbeitsjahren", delta_color="off",
          **_NO_ARROW, border=True,
          help="Hochgerechnetes Altersguthaben inkl. geplanter Einkäufe")
m4.metric("Steuerersparnis Einkauf", chf(buy_cmp.total_savings), border=True,
          help="Summe der Einkommenssteuer-Ersparnis aller geplanten Einkäufe")

tabs = st.tabs(["🧾 Steuern heute", "🏦 PK-Vermögensaufbau", "💡 Einkauf – lohnt es sich?",
                "⚖️ PK vs. ETF", "🔀 Zwei PKs vergleichen", "📚 Lexikon"])

# ---------------------------------------------------------------------------
# Tab 1: Steuern
# ---------------------------------------------------------------------------

with tabs[0]:
    title_with_info(f"Ihre Steuern in {loc.name} ({canton.abbr})", INFO["steuern"], key="i_steuern")
    c1, c2 = st.columns([1.1, 1])
    with c1:
        rows = [
            ("Direkte Bundessteuer", tax_income.bund, 0.0),
            (f"Kantonssteuer ({rate_canton:g} % / {w_canton:g} %)", tax_income.canton, tax_wealth.canton),
            (f"Gemeindesteuer ({rate_city:g} % / {w_city:g} %)", tax_income.city, tax_wealth.city),
            (f"Kirchensteuer ({rate_church:g} % / {w_church:g} %)", tax_income.church, tax_wealth.church),
        ]
        tdf = pd.DataFrame(rows, columns=["Steuer", "Einkommen", "Vermögen"])
        tdf.loc[len(tdf)] = ["Total", tdf["Einkommen"].sum(), tdf["Vermögen"].sum()]
        tdf["Total"] = tdf["Einkommen"] + tdf["Vermögen"]
        table(tdf, money=("Einkommen", "Vermögen", "Total"), hide_index=True)
        st.caption(
            f"Einfache Steuer Einkommen: {chf(tax_income.base)} · Steuerbares Vermögen nach Freibeträgen: "
            f"{chf(tax_wealth.taxable)} · Einfache Vermögenssteuer: {chf(tax_wealth.base)}"
        )
    with c2:
        a, b = st.columns(2)
        a.metric("Durchschnittssteuersatz", pct(tax_income.total / income if income else 0),
                 help="Einkommenssteuer ÷ steuerbares Einkommen")
        b.metric("Grenzsteuersatz", pct(marg), help="Steuer auf die nächsten CHF 1'000 Einkommen")
        a.metric("Vermögenssteuer in ‰", f"{tax_wealth.total / wealth * 1000:.2f} ‰" if wealth else "–",
                 help="Vermögenssteuer ÷ Reinvermögen")
        mw = tx.marginal_wealth_rate(effective_wealth, profile)
        b.metric("Grenzsatz Vermögen", f"{mw * 1000:.2f} ‰",
                 help="Zusätzliche Vermögenssteuer pro CHF 1'000 Mehrvermögen – relevant fürs ETF-Depot.")

    st.markdown("#### Wie steigen die Steuern mit dem Einkommen?")
    hi = max(250_000, income * 2)
    xs = list(range(10_000, int(hi) + 1, max(2_000, int(hi / 120) // 1000 * 1000)))
    avg = [tx.income_tax_total(x, profile, income_bund - income) / x for x in xs]
    mar = [tx.marginal_income_rate(x, profile, bund_offset=income_bund - income) for x in xs]
    fig = go.Figure()
    fig.add_scatter(x=xs, y=mar, name="Grenzsteuersatz", line=dict(color=C["blue"], width=2, shape="hv"))
    fig.add_scatter(x=xs, y=avg, name="Durchschnittssteuersatz", line=dict(color=C["orange"], width=2))
    fig.add_vline(x=income, line=dict(color=C["muted"], dash="dot", width=1))
    fig.add_annotation(x=income, y=max(mar) * 1.02, text="Ihr Einkommen", showarrow=False, yanchor="bottom",
                       font=dict(color=C["muted"]))
    style(fig, y_pct=True, x_title="Steuerbares Einkommen (CHF)", y_title="Steuersatz")
    plot(fig, "tax_curve")
    st.caption("Der Grenzsteuersatz zeigt, wie viel von einem zusätzlichen (bzw. abgezogenen) Franken an "
               "die Steuer geht. Genau dieser Satz bestimmt die Ersparnis bei einem PK-Einkauf.")

    title_with_info("Kapitalbezugssteuer (PK / Säule 3a)", INFO["kapitalsteuer"], level=4, key="i_kap")
    st.caption(f"Regel Kanton {canton.abbr}: {tx.pension_rule_text(canton.id)} · Bund: {tx.pension_rule_text(0)}")
    amounts = sorted(a for a in {50_000, 100_000, 200_000, 300_000, 500_000, 750_000, 1_000_000, 1_500_000,
                                 round(capital, -3)} if a > 0)
    krows = []
    for amt in amounts:
        r = tx.capital_withdrawal_tax(amt, profile)
        krows.append({"Kapital": amt, "Bund": r.bund, "Kanton + Gemeinde + Kirche": r.canton + r.city + r.church,
                      "Total": r.total, "Satz %": r.total / amt * 100,
                      " ": "← Ihr PK-Kapital" if amt == round(capital, -3) else ""})
    table(pd.DataFrame(krows), money=("Kapital", "Bund", "Kanton + Gemeinde + Kirche", "Total"), pcts=("Satz %",),
          pct_fmt="%.2f %%", hide_index=True)

    with st.expander(f"🏘️ Vergleich: Steuern in allen Gemeinden des Kantons {canton.name}"):
        st.caption("Gleiche Einkommen/Vermögen, Steuerfüsse gemäss ESTV-Daten 2026 (Ihre manuellen Anpassungen "
                   "gelten hier nicht).")
        g_rows = []
        for l in locs:
            p2 = tx.profile_for_location(l, married, children, confession)
            ti = tax_income.base * p2.income_factor + tax_income.bund
            tw = tax_wealth.base * p2.wealth_factor
            g_rows.append({"Gemeinde": l.name, "Steuerfuss Gemeinde %": l.income_city,
                           "Einkommenssteuer": ti, "Vermögenssteuer": tw, "Total": ti + tw})
        gdf = pd.DataFrame(g_rows).sort_values("Total").reset_index(drop=True)
        gdf.index += 1
        table(gdf, money=("Einkommenssteuer", "Vermögenssteuer", "Total"))

# ---------------------------------------------------------------------------
# Tab 2: Vermögensaufbau
# ---------------------------------------------------------------------------

with tabs[1]:
    title_with_info("Hochrechnung Ihres PK-Guthabens", INFO["aufbau"], key="i_aufbau")
    pension = capital * uws / 100.0
    a, b, c, d = st.columns(4)
    a.metric(f"Altersguthaben mit {retirement_age}", chf(capital), border=True,
             help="Inkl. Zinsen, Beiträge und geplanter Einkäufe")
    b.metric("Jährliche Rente", chf(pension), f"{chf(pension / 12)} pro Monat", delta_color="off", border=True, **_NO_ARROW,
             help=H["uws"])
    c.metric("Kapitalbezugssteuer", chf(cap_tax), f"{cap_tax / capital * 100:.1f} % des Kapitals" if capital else None,
             delta_color="off", border=True, **_NO_ARROW, help=INFO["kapitalsteuer"])
    d.metric("Netto-Kapital nach Steuer", chf(capital - cap_tax), border=True)

    cum = pd.DataFrame({"Alter": proj["Alter"] + 1})
    cum["Heutiges Guthaben"] = balance
    cum["Beiträge Arbeitnehmer"] = proj["Beitrag AN"].cumsum()
    cum["Beiträge Arbeitgeber"] = proj["Beitrag AG"].cumsum()
    cum["Einkäufe"] = proj["Einkauf"].cumsum()
    cum["Zinsen"] = proj["Zins"].cumsum()
    series = [("Heutiges Guthaben", C["blue"]), ("Beiträge Arbeitnehmer", C["orange"]),
              ("Beiträge Arbeitgeber", C["aqua"]), ("Einkäufe", C["yellow"]), ("Zinsen", C["magenta"])]
    fig = go.Figure()
    for name, col in series:
        fig.add_scatter(x=cum["Alter"], y=cum[name], name=name, stackgroup="one", mode="lines",
                        line=dict(color=col, width=1), fillcolor=col,
                        hovertemplate="%{y:,.0f}")
    style(fig, height=420, x_title="Alter", y_title="CHF")
    fig.update_layout(legend_traceorder="normal")
    plot(fig, "pk_area")

    st.markdown("#### Woher kommt Ihr Kapital?")
    dec = pk.decompose(proj, balance)
    ddf = pd.DataFrame({"Quelle": list(dec), "CHF": list(dec.values())})
    ddf["Anteil"] = ddf["CHF"] / ddf["CHF"].sum() * 100 if ddf["CHF"].sum() else 0
    col_l, col_r = st.columns([1.3, 1])
    fig = go.Figure(go.Bar(x=ddf["CHF"], y=ddf["Quelle"], orientation="h",
                           marker=dict(color=[c for _, c in series], cornerradius=4),
                           text=[chf(v, False) for v in ddf["CHF"]], textposition="outside",
                           hovertemplate="%{y}: CHF %{x:,.0f}<extra></extra>"))
    style(fig, height=280, hover="closest")
    fig.update_yaxes(autorange="reversed", tickformat=None)
    fig.update_xaxes(showgrid=True, gridcolor=C["grid"], tickformat=",.0f",
                     range=[0, max(ddf["CHF"].max(), 1) * 1.18])
    with col_l:
        plot(fig, "pk_decomp")
    with col_r:
        table(ddf, money=("CHF",), pcts=("Anteil",), hide_index=True)
        st.caption("Die Beiträge des Arbeitgebers sind zusätzlicher Lohn – Sie sehen ihn nicht auf dem "
                   "Konto, er arbeitet aber für Ihre Vorsorge.")

    with st.expander("📋 Tabelle Jahr für Jahr"):
        tab = proj.copy()
        tab["Steuerersparnis Einkauf"] = [buy_cmp.savings.get(i, 0.0) for i in range(len(tab))] if horizon else 0.0
        table(tab, money=[col for col in tab.columns if col not in ("Jahr", "Alter")], hide_index=True)
        st.download_button("⬇️ Als CSV herunterladen", tab.to_csv(index=False).encode("utf-8"),
                           "pk_hochrechnung.csv", "text/csv")

    st.divider()
    title_with_info("Rente oder Kapital?", INFO["rente_kapital"], key="i_rk")
    c1, c2 = st.columns(2)
    ret_income = money_input("Übriges steuerbares Einkommen im Ruhestand (CHF/Jahr)",
                             45_000 if married else 30_000, "ret_income", H["einkommen_ruhestand"], container=c1)
    cap_return = c2.number_input("Rendite auf Kapital im Ruhestand % (nach Steuern)", -2.0, 8.0, 2.0, 0.25,
                                 help=H["rendite_kapital"])
    ctx_ret = an.TaxContext(profile, income=ret_income)
    rk_df, rk = an.annuity_vs_capital(capital, uws, retirement_age, ctx_ret, cap_return)
    a, b, c, d = st.columns(4)
    a.metric("Rente netto / Jahr", chf(rk["Rente netto"]), f"−{chf(rk['Einkommenssteuer auf Rente'])} Steuer",
             delta_color="off", border=True, **_NO_ARROW, help="Rente minus zusätzliche Einkommenssteuer im Ruhestand")
    b.metric("Kapital netto (einmalig)", chf(rk["Kapital netto"]), f"−{chf(rk['Kapitalbezugssteuer'])} Steuer",
             delta_color="off", border=True, **_NO_ARROW)
    c.metric("Break-even ohne Rendite", f"Alter {rk['Break-even ohne Rendite'] or '>100'}", border=True,
             help="Ab diesem Alter haben Sie mit der Rente netto mehr erhalten als das Netto-Kapital.")
    d.metric(f"Break-even mit {cap_return:g} % Rendite", f"Alter {rk['Break-even mit Rendite'] or '>100'}",
             border=True, help="Kapital wird angelegt und jährlich im Umfang der Netto-Rente verbraucht. "
                               "Ab diesem Alter wäre das Kapital aufgebraucht.")
    fig = go.Figure()
    fig.add_scatter(x=rk_df["Alter"], y=rk_df["Kumulierte Netto-Rente"], name="Summe Netto-Renten",
                    line=dict(color=C["blue"], width=2))
    fig.add_scatter(x=rk_df["Alter"], y=rk_df["Kapital mit Rendite (Rest)"],
                    name=f"Restkapital bei Bezug (mit {cap_return:g} % Rendite)", line=dict(color=C["orange"], width=2))
    fig.add_scatter(x=rk_df["Alter"], y=rk_df["Kapital ohne Rendite (Rest)"], name="Restkapital ohne Rendite",
                    line=dict(color=C["aqua"], width=2, dash="dot"))
    style(fig, x_title="Alter", y_title="CHF")
    plot(fig, "rk_chart")
    st.caption("Vereinfachung: Rente ohne Teuerungsausgleich, keine Ehegattenrente berücksichtigt, Vermögenssteuer "
               "auf dem Kapital ist in der Rendite 'nach Steuern' enthalten. Viele wählen eine Mischform.")

# ---------------------------------------------------------------------------
# Tab 3: Einkauf
# ---------------------------------------------------------------------------

with tabs[2]:
    title_with_info("Lohnt sich ein Einkauf in die Pensionskasse?", INFO["einkauf"], key="i_einkauf")
    if potential <= 0:
        st.info("Tragen Sie links Ihr **Einkaufspotenzial** gemäss Vorsorgeausweis ein, um einen Einkauf zu prüfen.")

    st.markdown("#### 1 · Wie viel Steuern spart der Einkauf?")
    if buyins:
        rows = []
        for i, amt in sorted(buyins.items()):
            y = ctx.income_at(i)
            rows.append({"Alter": age + i, "Einkauf": amt, "Steuerbares Einkommen vorher": y,
                         "nachher": max(0.0, y - amt), "Steuerersparnis": buy_cmp.savings[i],
                         "Ersparnis %": buy_cmp.savings[i] / amt * 100})
        edf = pd.DataFrame(rows)
        a, b, c = st.columns(3)
        a.metric("Einkauf total", chf(buy_cmp.total_buyin), border=True)
        b.metric("Steuerersparnis total", chf(buy_cmp.total_savings),
                 f"{buy_cmp.total_savings / buy_cmp.total_buyin * 100:.1f} % des Einkaufs", delta_color="off", border=True, **_NO_ARROW)
        c.metric("Effektive Kosten", chf(buy_cmp.total_buyin - buy_cmp.total_savings), border=True,
                 help="Einkauf minus Steuerersparnis = was Sie der Einkauf wirklich kostet.")
        table(edf, money=("Einkauf", "Steuerbares Einkommen vorher", "nachher", "Steuerersparnis"),
              pcts=("Ersparnis %",), hide_index=True)
    else:
        st.info("Kein Einkauf geplant – geben Sie links unter **💰 Geplanter Einkauf** einen Betrag ein.")

    curve_max = max(potential, buy_total, 50_000)
    sc = an.buyin_savings_curve(ctx, curve_max, 41)
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Ersparnis je nach Einkaufsbetrag (in einem Jahr)**")
        fig = go.Figure()
        fig.add_scatter(x=sc["Einkauf"], y=sc["Ersparnis auf letzten Franken %"] / 100, name="auf dem letzten Franken",
                        line=dict(color=C["blue"], width=2, shape="hv"))
        fig.add_scatter(x=sc["Einkauf"], y=sc["Ø Ersparnis %"] / 100, name="Ø auf dem ganzen Einkauf",
                        line=dict(color=C["orange"], width=2))
        if buyins:
            fig.add_vline(x=buy_total / buy_years, line=dict(color=C["muted"], dash="dot", width=1))
            fig.add_annotation(x=buy_total / buy_years, y=0, yref="paper", text=" Ihr Einkauf/Jahr", showarrow=False,
                               xanchor="left", yanchor="bottom", font=dict(color=C["muted"]))
        style(fig, height=340, y_pct=True, x_title="Einkauf in einem Jahr (CHF)", y_title="Steuerersparnis")
        plot(fig, "buy_curve")
        st.caption("Je grösser der Einkauf in einem Jahr, desto tiefer fällt man in der Progression – die "
                   "Ersparnis auf jedem weiteren Franken sinkt.")
    with col_r:
        st.markdown("**Staffeln: Einkauf auf mehrere Jahre verteilen**")
        stag_total = buy_total if buy_total > 0 else min(curve_max, 100_000)
        stg = an.staggering_table(ctx, stag_total, min(10, max(1, horizon)))
        fig = go.Figure(go.Bar(
            x=stg["Anzahl Jahre"], y=stg["Steuerersparnis total"],
            marker=dict(color=[C["blue"] if n == buy_years else "rgba(42,120,214,0.45)" for n in stg["Anzahl Jahre"]],
                        cornerradius=4),
            text=[chf(v, False) for v in stg["Steuerersparnis total"]], textposition="outside",
            customdata=stg["Ersparnis %"], hovertemplate="%{x} Jahre: CHF %{y:,.0f} (%{customdata:.1f} %)<extra></extra>"))
        style(fig, height=340, hover="closest", x_title="Anzahl Jahre", y_title="Steuerersparnis total (CHF)")
        fig.update_xaxes(dtick=1)
        plot(fig, "stagger")
        best = stg.loc[stg["Steuerersparnis total"].idxmax()]
        st.caption(f"Total {chf(stag_total)}: In einem Jahr gespart {chf(stg['Steuerersparnis total'].iloc[0])}, "
                   f"verteilt auf {int(best['Anzahl Jahre'])} Jahre {chf(best['Steuerersparnis total'])}. "
                   "Dunkler Balken = Ihre Wahl. (Annahme: gleiches Einkommen in allen Jahren.)")

    st.divider()
    title_with_info("2 · Einkauf in die PK oder lieber selbst in ETF anlegen?", INFO["einkauf_vs_etf"], key="i_bve")
    if not buyins:
        st.info("Für den Vergleich wird ein Beispiel-Einkauf von CHF 50'000 im nächsten Jahr verwendet.")
        cmp_buyins = {0: 50_000.0} if horizon > 0 else {}
        cmp = an.compare_buyin_vs_etf(cmp_buyins, horizon, capital_base, interest, ctx, etf, invest_savings)
    else:
        cmp_buyins, cmp = buyins, buy_cmp
    if horizon > 0 and cmp_buyins:
        irr_b, irr_e = an.buyin_irr(cmp, horizon), an.etf_net_return(cmp, horizon)
        be = an.breakeven_etf_return(cmp_buyins, horizon, capital_base, interest, ctx, etf, invest_savings)
        winner = "Einkauf in die PK" if cmp.advantage > 0 else "ETF-Anlage"
        (st.success if cmp.advantage > 0 else st.warning)(
            f"**Ergebnis: {winner} ist um {chf(abs(cmp.advantage))} besser** (Nettovermögen bei Pensionierung, "
            f"bei {etf_ret:g} % ETF-Rendite und {interest:g} % PK-Zins).")
        a, b, c, d = st.columns(4)
        a.metric("Netto mit Einkauf", chf(cmp.result_buyin), border=True,
                 help="Zusätzliches PK-Kapital nach Kapitalbezugssteuer + angelegte Steuerersparnis")
        b.metric("Netto mit ETF", chf(cmp.result_etf), border=True,
                 help="ETF-Depot bei Pensionierung nach Dividenden-, Vermögenssteuern und Kosten")
        c.metric("Rendite Einkauf p.a.", pct(irr_b), f"ETF netto: {pct(irr_e)}", delta_color="off", border=True, **_NO_ARROW,
                 help="Effektive Jahresrendite auf Ihre Nettokosten (Einkauf minus Steuerersparnis), nach "
                      "Kapitalbezugssteuer. Darunter: Nettorendite des ETF nach Kosten und Steuern.")
        d.metric("Break-even ETF-Rendite", f"{be:.2f} %" if be is not None else "–", border=True,
                 help="Ab dieser ETF-Rendite (vor Kosten) schneidet das ETF besser ab als der Einkauf.")

        with st.expander("🔎 Rechnung im Detail"):
            det = pd.DataFrame([
                ("Einkauf (eigenes Geld)", cmp.total_buyin, cmp.total_buyin),
                ("+ Wachstum bis Pensionierung", cmp.pk_capital_with - cmp.pk_capital_without - cmp.total_buyin,
                 cmp.etf_alternative - cmp.total_buyin),
                ("− zusätzliche Kapitalbezugssteuer", -cmp.extra_cap_tax, 0.0),
                ("+ Steuerersparnis" + (" inkl. ETF-Rendite" if invest_savings else ""),
                 cmp.etf_from_savings if invest_savings else cmp.total_savings, 0.0),
                ("= Nettovermögen bei Pensionierung", cmp.result_buyin, cmp.result_etf),
            ], columns=["Position", "Einkauf PK", "ETF"])
            table(det, money=("Einkauf PK", "ETF"), hide_index=True)
            st.caption(
                f"Die zusätzliche Kapitalbezugssteuer beträgt {chf(cmp.extra_cap_tax)} = "
                f"{cmp.extra_cap_tax / max(cmp.pk_capital_with - cmp.pk_capital_without, 1) * 100:.1f} % auf dem "
                "zusätzlichen Kapital – höher als der Durchschnittssatz, weil der Einkauf 'oben' auf Ihr übriges "
                "PK-Kapital kommt (Progression). Beim ETF ist die Wertentwicklung bereits nach Kosten, "
                "Dividendensteuern und Vermögenssteuer.")

        st.markdown("#### Ab wann lohnt sich ein Einkauf? – nach Einkaufsalter")
        amt_age = cmp.total_buyin / max(len(cmp.buyins), 1)
        by_age = an.buyin_by_age(amt_age, age, retirement_age, proj_base, interest, ctx, etf, invest_savings)
        pos = by_age[by_age["Vorteil Einkauf"] > 0]
        fig = go.Figure(go.Bar(
            x=by_age["Einkaufsalter"], y=by_age["Vorteil Einkauf"],
            marker=dict(color=[C["blue"] if v > 0 else C["red"] for v in by_age["Vorteil Einkauf"]], cornerradius=4),
            customdata=by_age[["Jahre bis Pensionierung", "Netto Einkauf", "Netto ETF"]].values,
            hovertemplate=("Einkauf mit %{x} (%{customdata[0]} J. vor Pension)<br>Vorteil Einkauf: CHF %{y:,.0f}"
                           "<br>Netto Einkauf: CHF %{customdata[1]:,.0f}<br>Netto ETF: CHF %{customdata[2]:,.0f}"
                           "<extra></extra>")))
        if horizon >= 1:
            fig.add_vrect(x0=retirement_age - 3.5, x1=retirement_age - 0.5, fillcolor=C["muted"], opacity=0.12,
                          line_width=0, annotation_text="3-J.-Sperrfrist Kapitalbezug",
                          annotation_position="bottom left", annotation_font_color=C["muted"])
        style(fig, height=380, hover="closest", x_title="Alter beim Einkauf (verbleibende Arbeitsjahre)",
              y_title="Vorteil Einkauf vs. ETF (CHF)")
        step = 1 if horizon <= 12 else 5 if horizon > 25 else 2
        ticks = [a for a in by_age["Einkaufsalter"] if (retirement_age - a) % step == 0 or a == age]
        fig.update_xaxes(tickvals=ticks, ticktext=[f"{a}<br>({retirement_age - a} J.)" for a in ticks])
        fig.add_hline(y=0, line=dict(color=C["muted"], width=1))
        plot(fig, "by_age")
        if len(pos) and len(pos) < len(by_age):
            st.markdown(f"➡️ Bei Ihren Annahmen lohnt sich ein Einkauf von {chf(amt_age)} **ab Alter "
                        f"{int(pos['Einkaufsalter'].min())}** (blau). Früher eingezahlt gewinnt das ETF dank höherer "
                        "Rendite über die längere Zeit (rot).")
        elif len(pos):
            st.markdown("➡️ Bei Ihren Annahmen lohnt sich der Einkauf **in jedem Alter**.")
        else:
            st.markdown("➡️ Bei Ihren Annahmen ist das ETF **in jedem Alter** besser.")
        st.caption("Ideal ist oft: Einkäufe in den letzten Jahren vor der Pensionierung, aber spätestens 3 Jahre "
                   "vor einem Kapitalbezug – und verteilt auf mehrere Jahre.")

        st.markdown("#### … nach Einkommen (Grenzsteuersatz)")
        incomes = list(range(40_000, int(max(300_000, income * 1.8)) + 1, 10_000))
        by_inc = an.buyin_by_income(cmp_buyins, horizon, capital_base, interest, ctx, etf, incomes, invest_savings)
        fig = go.Figure()
        fig.add_scatter(x=by_inc["Steuerbares Einkommen"], y=by_inc["Vorteil Einkauf"], name="Vorteil Einkauf",
                        line=dict(color=C["blue"], width=2), customdata=by_inc["Steuerersparnis %"],
                        hovertemplate="CHF %{y:,.0f} (Steuerersparnis %{customdata:.1f} %)<extra></extra>")
        fig.add_hline(y=0, line=dict(color=C["muted"], width=1))
        fig.add_vline(x=income, line=dict(color=C["muted"], dash="dot", width=1))
        fig.add_annotation(x=income, y=1, yref="paper", text="Ihr Einkommen", showarrow=False, yanchor="bottom",
                           font=dict(color=C["muted"]))
        style(fig, height=340, x_title="Steuerbares Einkommen (CHF)", y_title="Vorteil Einkauf vs. ETF (CHF)")
        plot(fig, "by_income")
        cross = by_inc[by_inc["Vorteil Einkauf"] > 0]
        if len(cross) and len(cross) < len(by_inc):
            st.markdown(f"➡️ Mit Ihrem Einkaufsplan lohnt sich der Einkauf **ab einem steuerbaren Einkommen von ca. "
                        f"{chf(cross['Steuerbares Einkommen'].min())}**.")

    st.divider()
    title_with_info("3 · Wie viel Einkauf pro Jahr lohnt sich? – Sparbudget optimal aufteilen",
                    INFO["optimierung"], key="i_opt")
    if horizon <= 1 or potential <= 0:
        st.info("Für die Optimierung braucht es ein **Einkaufspotenzial** (Seitenleiste) und mindestens 2 Jahre "
                "bis zur Pensionierung.")
    else:
        c1, c2, c3 = st.columns(3)
        budget = money_input("Sparbudget pro Jahr (CHF)", 20_000, "opt_budget", H["opt_budget"], container=c1)
        respect_lock = c3.checkbox("3-Jahres-Sperrfrist beachten", True, help=H["opt_sperrfrist"])
        last_age = retirement_age - 4 if respect_lock else retirement_age - 1
        if last_age < age:
            st.warning("Bis zur Pensionierung bleiben weniger als 4 Jahre – wegen der 3-Jahres-Sperrfrist ist kein "
                       "Einkauf mit anschliessendem Kapitalbezug mehr möglich (nur noch als Rente).")
        else:
            from_age = int(c2.number_input("Einkauf frühestens ab Alter", age, last_age, age, help=H["opt_ab"]))
            window = list(range(from_age - age, last_age - age + 1))
            res = an.optimize_buyin_split(budget, window, horizon, capital_base, interest, ctx, etf, potential)
            used = sorted(i for i, a in res.alloc.items() if a > 0)
            if used:
                st.success(
                    f"**Optimal: total {chf(res.total_buyin)} einkaufen**, verteilt auf {len(used)} Jahr(e) "
                    f"(Alter {age + used[0]}–{age + used[-1]}), im Schnitt **{chf(res.total_buyin / len(used))} pro "
                    f"Einkaufsjahr**. Der Rest des Budgets ({chf(budget * len(window) - res.total_buyin)} total) plus "
                    "die Steuerersparnis geht ins ETF.")
            else:
                st.warning("**Bei Ihren Annahmen lohnt sich kein Einkauf** – jeder Franken bringt im ETF mehr. "
                           "Das ganze Budget ins ETF (oder Annahmen prüfen: ETF-Rendite, PK-Zins, Zeitraum).")
            a, b, c, d = st.columns(4)
            a.metric("Optimaler Einkauf total", chf(res.total_buyin), border=True,
                     help="Summe aller Einkäufe im optimalen Plan (max. Einkaufspotenzial).")
            b.metric("Vermögen bei Pensionierung", chf(res.value_opt), border=True,
                     help="Was aus dem Sparbudget wird: zusätzliches PK-Kapital nach Kapitalbezugssteuer + ETF-Depot.")
            c.metric("Mehrwert ggü. nur ETF", signed_chf(res.value_opt - res.value_etf), border=True,
                     help="Optimaler Plan im Vergleich dazu, das ganze Budget ins ETF zu investieren.")
            d.metric("Mehrwert ggü. max. Einkauf", signed_chf(res.value_opt - res.value_max), border=True,
                     help="Optimaler Plan im Vergleich dazu, jedes Jahr das ganze Budget einzukaufen, "
                          "bis das Einkaufspotenzial aufgebraucht ist.")

            ages = [age + i for i in window]
            pk_part = [res.alloc.get(i, 0.0) for i in window]
            etf_part = [budget - x for x in pk_part]
            fig = go.Figure()
            fig.add_bar(x=ages, y=pk_part, name="PK-Einkauf", marker=dict(color=PK_COLOR, line=dict(width=1, color="white")),
                        hovertemplate="Alter %{x}: PK-Einkauf CHF %{y:,.0f}<extra></extra>")
            fig.add_bar(x=ages, y=etf_part, name="ins ETF", marker=dict(color=ETF_COLOR, line=dict(width=1, color="white")),
                        hovertemplate="Alter %{x}: ETF CHF %{y:,.0f}<extra></extra>")
            fig.update_layout(barmode="stack", legend_traceorder="normal")
            style(fig, height=340, hover="x unified", x_title="Alter", y_title="CHF pro Jahr")
            st.markdown("**Optimale Aufteilung Ihres Budgets pro Jahr**")
            plot(fig, "opt_split")
            st.caption("Blau = so viel lohnt sich im jeweiligen Jahr als PK-Einkauf (bis der nächste Franken im ETF "
                       "mehr bringt), Orange = Rest ins ETF. Je näher die Pensionierung, desto attraktiver der Einkauf.")

            cv = res.curve
            fig = go.Figure()
            fig.add_scatter(x=cv["Einkauf pro Jahr"], y=cv["Nettovermögen"], name="Nettovermögen bei Pensionierung",
                            line=dict(color=C["blue"], width=2),
                            hovertemplate="Einkauf CHF %{x:,.0f}/Jahr → CHF %{y:,.0f}<extra></extra>")
            best_v = float(cv["Nettovermögen"].max())
            fig.add_scatter(x=[res.best_constant], y=[best_v], mode="markers", name="Optimum",
                            marker=dict(color=C["blue"], size=10, line=dict(width=2, color="white")),
                            hovertemplate="Optimum: CHF %{x:,.0f}/Jahr<extra></extra>")
            style(fig, height=320, hover="closest", x_title="Gleicher Einkauf jedes Jahr ab Alter "
                  f"{from_age} (CHF)", y_title="Vermögen bei Pensionierung (CHF)")
            st.markdown("**Variante: jedes Jahr gleich viel einkaufen**")
            plot(fig, "opt_curve")
            if res.best_constant > 0:
                st.markdown(f"➡️ Wenn Sie **jedes Jahr gleich viel** einkaufen möchten (ab Alter {from_age}): optimal "
                            f"sind ca. **{chf(res.best_constant)} pro Jahr** – mehr lohnt sich nicht, weniger verschenkt "
                            "Steuerersparnis.")
            else:
                st.markdown(f"➡️ Ein gleichbleibender jährlicher Einkauf ab Alter {from_age} lohnt sich nicht. "
                            "Besser: zuerst ETF, Einkäufe (falls überhaupt) erst in den Jahren gemäss Balkendiagramm.")

            with st.expander("📋 Plan Jahr für Jahr"):
                rows = []
                for i in window:
                    a_i = res.alloc.get(i, 0.0)
                    s_i = res.savings.get(i, 0.0)
                    rows.append({"Alter": age + i, "Budget": budget, "PK-Einkauf": a_i, "Steuerersparnis": s_i,
                                 "Ins ETF (inkl. Ersparnis)": budget - a_i + s_i,
                                 "Grenzsteuersatz danach %": tx.marginal_income_rate(
                                     max(ctx.income_at(i) - a_i, 0), profile, bund_offset=income_bund - income) * 100})
                table(pd.DataFrame(rows), money=("Budget", "PK-Einkauf", "Steuerersparnis", "Ins ETF (inkl. Ersparnis)"),
                      pcts=("Grenzsteuersatz danach %",), hide_index=True)
            st.caption("Diese Optimierung ist unabhängig vom 'Geplanten Einkauf' in der Seitenleiste. Annahmen zu "
                       "ETF-Rendite, PK-Zins und Steuern wie links eingestellt. Gleiches steuerbares Einkommen in allen Jahren.")

    st.markdown("#### ✅ Checkliste vor dem Einkauf")
    st.markdown(
        "- Zuerst **Säule 3a** ausschöpfen (2026: max. CHF 7'258) – flexibler und ebenfalls abzugsfähig.\n"
        "- **Deckungsgrad** und Verzinsungspolitik der PK prüfen (Unterdeckung = Risiko).\n"
        "- **WEF-Vorbezug** muss zuerst zurückbezahlt werden.\n"
        "- **3-Jahres-Sperrfrist** vor einem Kapitalbezug beachten (auch beim Bezug für Wohneigentum).\n"
        "- Was passiert mit dem Einkauf im **Todesfall** vor der Pensionierung? (Reglement)\n"
        "- Liquiditätsreserve behalten – das Geld ist bis zur Pensionierung gebunden."
    )

# ---------------------------------------------------------------------------
# Tab 4: PK vs ETF
# ---------------------------------------------------------------------------

with tabs[3]:
    title_with_info("Weniger in die PK einzahlen und selbst in ETF investieren?", INFO["reduziert"], key="i_red")
    an_now, ag_now = plan.contributions(age, 0)
    if horizon <= 0:
        st.info("Keine Jahre bis zur Pensionierung.")
    elif an_now <= 0:
        st.info("Ihr Arbeitnehmer-Sparbeitrag ist 0 – erfassen Sie links Ihre PK-Beiträge.")
    else:
        c1, c2 = st.columns([1, 2])
        reduction = c1.number_input("Reduktion AN-Sparbeitrag (CHF/Jahr)", 0, int(an_now),
                                    int(min(round(an_now * 0.4, -2), an_now)), 100, help=H["reduktion"])
        c2.markdown(
            f"Heute: Sparbeitrag AN **{chf(an_now)}**, AG **{chf(ag_now)}** pro Jahr. "
            f"Mit Reduktion: AN **{chf(an_now - reduction)}**. Der AG-Beitrag bleibt gleich. "
            f"Ihr steuerbares Einkommen steigt auf **{chf(income + reduction)}**.")
        res = an.compare_reduced_contributions(plan, age, retirement_age, float(reduction), ctx, etf)
        be_r = an.breakeven_reduced(plan, age, retirement_age, float(reduction), ctx, etf)
        better = "PK reduziert + ETF" if res.advantage_etf > 0 else "Voller PK-Beitrag"
        (st.success if res.advantage_etf > 0 else st.warning)(
            f"**Ergebnis: {better} ist um {chf(abs(res.advantage_etf))} besser** (netto bei Pensionierung, "
            f"Kapitalbezug).")
        a, b, c, d = st.columns(4)
        a.metric("Netto: voller PK-Beitrag", chf(res.net_full), border=True,
                 help="PK-Kapital bei Pensionierung minus Kapitalbezugssteuer")
        b.metric("Netto: PK reduziert + ETF", chf(res.net_reduced), border=True,
                 help="Tieferes PK-Kapital nach Kapitalbezugssteuer + ETF-Depot")
        c.metric("Mehrsteuer Einkommen (total)", chf(res.total_extra_tax),
                 f"{res.total_extra_tax / res.total_reduction * 100:.1f} % der Reduktion" if res.total_reduction else None,
                 delta_color="off", border=True, **_NO_ARROW,
                 help="Weil der Lohnabzug sinkt, steigt Ihr steuerbares Einkommen.")
        d.metric("Break-even ETF-Rendite", f"{be_r:.2f} %" if be_r is not None else "–", border=True,
                 help="Ab dieser ETF-Rendite (vor Kosten) lohnt sich die Variante mit ETF.")

        dfr = res.df
        fig = go.Figure()
        fig.add_scatter(x=dfr["Alter"], y=dfr["PK (voller Beitrag)"], name="PK mit vollem Beitrag",
                        line=dict(color=PK_COLOR, width=2))
        fig.add_scatter(x=dfr["Alter"], y=dfr["PK reduziert + ETF"], name="PK reduziert + ETF (Total)",
                        line=dict(color=ETF_COLOR, width=2))
        fig.add_scatter(x=dfr["Alter"], y=dfr["ETF-Depot"], name="davon ETF-Depot",
                        line=dict(color=C["aqua"], width=2, dash="dot"))
        style(fig, height=400, x_title="Alter", y_title="CHF (vor Kapitalbezugssteuer)")
        plot(fig, "red_lines")
        st.caption("Werte vor Kapitalbezugssteuer. Das ETF-Depot ist bereits nach Kosten, Dividendensteuer und "
                   "Vermögenssteuer. Die Kapitalbezugssteuer ist im Ergebnis oben berücksichtigt.")

        st.markdown("#### Wie hängt das Ergebnis von der ETF-Rendite ab?")
        rets = [x / 2 for x in range(0, 19)]
        sens = an.reduced_sensitivity(plan, age, retirement_age, float(reduction), ctx, etf, rets)
        fig = go.Figure(go.Bar(
            x=sens["ETF-Rendite %"], y=sens["Vorteil ETF"],
            marker=dict(color=[ETF_COLOR if v > 0 else PK_COLOR for v in sens["Vorteil ETF"]], cornerradius=4),
            hovertemplate="ETF-Rendite %{x:.1f} %: Vorteil ETF CHF %{y:,.0f}<extra></extra>"))
        fig.add_hline(y=0, line=dict(color=C["muted"], width=1))
        if be_r is not None and 0 <= be_r <= 9:
            fig.add_vline(x=be_r, line=dict(color=C["muted"], dash="dot", width=1))
            fig.add_annotation(x=be_r, y=1, yref="paper", text=f"Break-even {be_r:.1f} %", showarrow=False,
                               yanchor="bottom", font=dict(color=C["muted"]))
        style(fig, height=340, hover="closest", x_title="ETF-Rendite % p.a. (vor Kosten)",
              y_title="Vorteil ETF-Variante (CHF)")
        plot(fig, "red_sens")
        st.caption("Orange = ETF-Variante besser, Blau = voller PK-Beitrag besser. Zum Vergleich: Ihre PK verzinst "
                   f"mit {interest:g} %. Beachten Sie das Schwankungsrisiko von Aktien.")
        with st.expander("📋 Jahreswerte"):
            table(dfr, money=[col for col in dfr.columns if col != "Alter"], hide_index=True)

# ---------------------------------------------------------------------------
# Tab 5: Zwei PKs vergleichen
# ---------------------------------------------------------------------------

with tabs[4]:
    title_with_info("Zwei Pensionskassen vergleichen", INFO["zwei_pks"], key="i_2pk")
    an0, ag0 = plan.contributions(age, 0)

    def plan_inputs(col, prefix: str, name: str, d: dict) -> pk.PensionPlan:
        prefix = f"{prefix}{abs(hash(tuple(d.values()))) % 10**8}"  # neue Vorgaben aus Seitenleiste -> Felder neu
        with col:
            st.markdown(f"##### {name}")
            nm = st.text_input("Bezeichnung", name, key=f"{prefix}_name")
            bal = money_input("Altersguthaben heute", d["bal"], f"{prefix}_bal", H["guthaben"] +
                              " Bei einem Stellenwechsel wird das Guthaben mitgenommen (meist gleich).", step=5000)
            a_s = money_input("Sparbeitrag AN (CHF/Jahr)", d["an"], f"{prefix}_an", H["an_spar"], step=100)
            g_s = money_input("Sparbeitrag AG (CHF/Jahr)", d["ag"], f"{prefix}_ag", H["ag_spar"], step=100)
            r_s = money_input("Risikobeitrag AN (CHF/Jahr)", d["risk"], f"{prefix}_risk", H["risiko"], step=100)
            c1, c2 = st.columns(2)
            z = c1.number_input("Verzinsung %", -2.0, 10.0, d["zins"], 0.25, key=f"{prefix}_zins", help=H["zins"])
            u = c2.number_input("Umwandlungssatz %", 3.0, 8.0, d["uws"], 0.1, key=f"{prefix}_uws", help=H["uws"])
        return pk.PensionPlan(name=nm, balance=bal, employee_savings=a_s, employer_savings=g_s, employee_risk=r_s,
                              interest=z, conversion_rate=u, salary_growth=growth)

    ca, cb = st.columns(2, border=True)
    pa = plan_inputs(ca, "pa", "PK A (heute)", dict(bal=balance, an=an0, ag=ag0, risk=risk, zins=interest, uws=uws))
    pb = plan_inputs(cb, "pb", "PK B (Alternative)",
                     dict(bal=balance, an=round(an0 * 0.8, -2), ag=round(ag0 * 1.2, -2), risk=risk,
                          zins=max(interest - 0.5, 0.0), uws=max(uws - 0.4, 3.0)))
    if pa.name == pb.name:
        pb.name = pb.name + " (B)"
    c1, c2 = st.columns(2)
    salary_diff = c1.number_input("Bruttolohn-Unterschied B gegenüber A (CHF/Jahr)", -500_000, 500_000, 0, 1000,
                                  help="Falls die Stelle mit PK B einen anderen Lohn bietet. Positiv = B zahlt mehr. "
                                       "AHV/ALV-Abzüge (6.4 %) und Steuern werden berücksichtigt.")
    invest_diff = c2.checkbox("Nettolohn-Differenz im ETF anlegen", True,
                              help="Fairer Vergleich: Wer monatlich mehr Nettolohn hat, legt die Differenz an.")
    if horizon > 0:
        pc = an.compare_two_plans(pa, pb, age, retirement_age, ctx, etf, float(salary_diff), invest_diff)
        s = pc.summary
        tot_a, tot_b = s.loc["Total Nettovermögen", pa.name], s.loc["Total Nettovermögen", pb.name]
        winner, diff = (pb.name, tot_b - tot_a) if tot_b > tot_a else (pa.name, tot_a - tot_b)
        st.success(f"**{winner}** führt bei Pensionierung zu **{chf(diff)} mehr Nettovermögen** "
                   "(PK-Kapital nach Kapitalbezugssteuer" + (" + angelegte Nettolohn-Differenz)." if invest_diff else ")."))
        a, b, c = st.columns(3)
        a.metric("Altersguthaben", chf(s.loc["Altersguthaben bei Pensionierung", pb.name]),
                 f"{signed_chf(s.loc['Altersguthaben bei Pensionierung', 'Differenz (B−A)'])} ggü. A", border=True,
                 help=f"{pb.name} bei Pensionierung")
        a.caption(f"{pa.name}: {chf(s.loc['Altersguthaben bei Pensionierung', pa.name])}")
        b.metric("Jährliche Rente", chf(s.loc["Jährliche Rente (Umwandlungssatz)", pb.name]),
                 f"{signed_chf(s.loc['Jährliche Rente (Umwandlungssatz)', 'Differenz (B−A)'])} ggü. A", border=True,
                 help=f"{pb.name}: Altersguthaben × Umwandlungssatz")
        b.caption(f"{pa.name}: {chf(s.loc['Jährliche Rente (Umwandlungssatz)', pa.name])}")
        c.metric("Total Nettovermögen", chf(tot_b), f"{signed_chf(tot_b - tot_a)} ggü. A", border=True,
                 help=f"{pb.name}: Nettokapital + ETF aus Nettolohn-Differenz")
        c.caption(f"{pa.name}: {chf(tot_a)}")

        df2 = pc.df
        fig = go.Figure()
        fig.add_scatter(x=df2["Alter"], y=df2["PK A"], name=f"{pa.name} – PK-Guthaben", line=dict(color=C["blue"], width=2))
        fig.add_scatter(x=df2["Alter"], y=df2["PK B"], name=f"{pb.name} – PK-Guthaben", line=dict(color=C["orange"], width=2))
        if invest_diff and df2["ETF A"].abs().sum() > 0:
            fig.add_scatter(x=df2["Alter"], y=df2["PK A"] + df2["ETF A"], name=f"{pa.name} – inkl. ETF",
                            line=dict(color=C["blue"], width=2, dash="dot"))
        if invest_diff and df2["ETF B"].abs().sum() > 0:
            fig.add_scatter(x=df2["Alter"], y=df2["PK B"] + df2["ETF B"], name=f"{pb.name} – inkl. ETF",
                            line=dict(color=C["orange"], width=2, dash="dot"))
        style(fig, height=400, x_title="Alter", y_title="CHF")
        plot(fig, "two_pk")

        table(s, money=list(s.columns))
        an_diff = pb.employee_total(age, 0) - pa.employee_total(age, 0)
        st.caption(
            f"Lohnabzug PK heute: {pa.name} {chf(pa.employee_total(age, 0))}, {pb.name} {chf(pb.employee_total(age, 0))} "
            f"pro Jahr ({'+' if an_diff >= 0 else '−'}{chf(abs(an_diff))}). Höhere Lohnabzüge senken den Nettolohn, "
            "aber auch die Steuern – und erhöhen das Altersguthaben.")
        with st.expander("📋 Jahreswerte"):
            table(df2, money=[col for col in df2.columns if col != "Alter"], hide_index=True)

# ---------------------------------------------------------------------------
# Tab 6: Lexikon
# ---------------------------------------------------------------------------

with tabs[5]:
    st.markdown("### 📚 Lexikon – Pensionskasse & Steuern einfach erklärt")
    q = st.text_input("Begriff suchen", placeholder="z.B. Umwandlungssatz")
    for term, text in GLOSSAR:
        if q and q.lower() not in (term + text).lower():
            continue
        with st.expander(term):
            st.markdown(text)
    st.divider()
    st.markdown("### ⚙️ Annahmen & Methodik")
    st.markdown(f"""
- **Steuern**: Tarife {data.year} von Bund und allen 26 Kantonen sowie Steuerfüsse aller {len(data.locations):,}
  Gemeinden (ESTV-Steuerdaten). Eingabe ist das *steuerbare* Einkommen; Personalsteuern werden ignoriert.
- **Kapitalbezugssteuer**: kantonsspezifische Regeln (Sondertarife, Satzbestimmung, Minimalsätze).
- **PK**: Beiträge und Einkäufe werden am Jahresende gutgeschrieben; Verzinsung auf dem Guthaben zu Jahresbeginn.
  Ein konstanter Zinssatz und Umwandlungssatz werden angenommen.
- **ETF**: Rendite vor Kosten; Dividenden werden jährlich zum Grenzsteuersatz besteuert; Vermögenssteuer auf dem
  Depotwert (zusätzlich zum übrigen Vermögen); Steuern werden aus dem Depot bezahlt; Kursgewinne steuerfrei.
- **Vergleiche** gehen von einem Kapitalbezug bei Pensionierung aus und rechnen in nominalen Franken.
- Nicht berücksichtigt: Teuerung der Tarife, Schwankungen (Sequenzrisiko), Risikoleistungen bei Tod/Invalidität,
  Erbschaft, Wohneigentumsförderung, Quellensteuer.

{DISCLAIMER}
""".replace("2,110", "2'110"))
    st.caption("Datenquelle Steuertarife: Eidg. Steuerverwaltung (ESTV), aufbereitet durch das MIT-lizenzierte "
               "Projekt devbrains-com/swisstaxcalculator.")
