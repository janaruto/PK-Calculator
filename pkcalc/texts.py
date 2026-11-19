"""Erklärtexte (Info-Buttons, Tooltips, Lexikon) – für PK-Laien geschrieben."""

H = {
    # Person
    "alter": "Ihr heutiges Alter. Daraus ergibt sich die Anzahl Jahre bis zur Pensionierung.",
    "rentenalter": (
        "Ordentliches Rentenalter ist 65 (Frauen ab Jahrgang 1964 ebenfalls 65). "
        "Viele Pensionskassen erlauben eine Frühpensionierung ab 58 – dann ist das Kapital "
        "kleiner und der Umwandlungssatz meist tiefer."
    ),
    "zivilstand": (
        "Verheiratete (und eingetragene Partnerschaften) werden gemeinsam besteuert und erhalten "
        "einen tieferen Tarif bzw. Splitting. Konkubinatspaare gelten steuerlich als alleinstehend."
    ),
    "kinder": (
        "Anzahl Kinder, für die Sie einen Kinderabzug erhalten. Wirkt hier auf den Tarif "
        "(Alleinerziehende erhalten in vielen Kantonen den Verheiratetentarif), auf die "
        "Ermässigung der Bundessteuer (CHF 263 pro Kind) und auf die Vermögens-Freibeträge. "
        "Den Kinderabzug vom Einkommen haben Sie im steuerbaren Einkommen bereits berücksichtigt."
    ),
    "konfession": (
        "Mitglieder einer Landeskirche zahlen Kirchensteuer (ein Zuschlag in % der einfachen "
        "Steuer). Konfessionslose zahlen keine Kirchensteuer."
    ),
    # Steuern
    "kanton": "Wohnkanton per 31.12. – er bestimmt den Steuertarif (die 'einfache Steuer').",
    "gemeinde": (
        "Wohngemeinde – bestimmt den Gemeindesteuerfuss. Die Steuerfüsse werden automatisch "
        "aus den ESTV-Daten 2026 übernommen und können unten angepasst werden."
    ),
    "sf_kanton": (
        "Kantonssteuerfuss in % der einfachen Steuer. Beispiel: einfache Steuer CHF 5'000 × 95 % "
        "= CHF 4'750 Kantonssteuer. In manchen Kantonen (z.B. BS, GE) ist der Tarif bereits in "
        "Franken und der Steuerfuss beträgt 100 %."
    ),
    "sf_gemeinde": (
        "Gemeindesteuerfuss in % der einfachen Steuer. Je nach Gemeinde sehr unterschiedlich – "
        "das ist der Grund, warum die Steuern im gleichen Kanton stark variieren."
    ),
    "sf_kirche": (
        "Kirchensteuerfuss in % der einfachen Steuer (0 % ohne Konfession). "
        "Bei konfessionell gemischten Ehepaaren gilt meist die Hälfte."
    ),
    "einkommen": (
        "**Steuerbares Einkommen** gemäss Steuererklärung bzw. Steuerrechnung (Kanton/Gemeinde) – "
        "also nach allen Abzügen (Berufsauslagen, Säule 3a, PK-Beiträge, Versicherungen, "
        "Kinderabzüge …). Ihre heutigen PK-Lohnabzüge sind darin bereits abgezogen."
    ),
    "einkommen_bund": (
        "Für die direkte Bundessteuer gelten teilweise andere Abzüge, daher ist das steuerbare "
        "Einkommen beim Bund oft etwas höher. Steht auf der Veranlagung der Bundessteuer."
    ),
    "vermoegen": (
        "**Reinvermögen** = Vermögen (Konto, Wertschriften, Liegenschaften zum Steuerwert …) "
        "minus Schulden. Das PK-Guthaben und die Säule 3a gehören **nicht** dazu – sie sind "
        "vermögenssteuerfrei."
    ),
    "freibetrag": (
        "Die meisten Kantone gewähren auf dem Vermögen steuerfreie Beträge (z.B. AG CHF 130'000 "
        "für Alleinstehende). Ist das Häkchen gesetzt, zieht der Rechner diese automatisch ab. "
        "Entfernen Sie es, wenn Sie das bereits steuerbare Vermögen (nach Freibeträgen) eingeben. "
        "Im Kanton Zürich ist der Freibetrag direkt im Tarif eingebaut."
    ),
    "kap_korrektur": (
        "Die Kapitalbezugsregeln sind kantonal sehr unterschiedlich. Vergleichen Sie das Resultat mit dem "
        "offiziellen Rechner der ESTV (swisstaxcalculator.estv.admin.ch → Kapitalleistungen) und passen Sie "
        "den Kantons-/Gemeindeteil hier an (z.B. 80 %, wenn der Rechner 20 % weniger ergibt). "
        "Die Bundessteuer bleibt unverändert."
    ),
    # PK
    "guthaben": (
        "Ihr aktuelles **Altersguthaben** (Sparkapital) gemäss Vorsorgeausweis der Pensionskasse. "
        "Den Ausweis erhalten Sie jährlich (meist im Januar/Februar) oder im Online-Portal der PK."
    ),
    "modus": (
        "**Fixe Beträge**: Sie geben die heutigen jährlichen Sparbeiträge ein (einfach, steht im "
        "Vorsorgeausweis). **Altersstaffel**: Die Beiträge steigen wie in den meisten Reglementen mit "
        "dem Alter (z.B. 7 / 10 / 15 / 18 % des versicherten Lohns) – realistischer für lange Zeiträume."
    ),
    "an_spar": (
        "**Sparbeitrag Arbeitnehmer** pro Jahr – der Teil Ihres Lohnabzugs, der Ihrem "
        "Altersguthaben gutgeschrieben wird ('Altersgutschrift'). Steht im Vorsorgeausweis."
    ),
    "ag_spar": (
        "**Sparbeitrag Arbeitgeber** pro Jahr. Der Arbeitgeber muss mindestens gleich viel zahlen "
        "wie Sie (Art. 66 BVG), viele zahlen mehr. Diesen Teil sehen Sie nicht auf dem Lohnausweis, "
        "er fliesst aber in Ihr Altersguthaben."
    ),
    "risiko": (
        "**Risiko- und Verwaltungsbeitrag** des Arbeitnehmers pro Jahr. Finanziert die Invaliden- "
        "und Hinterlassenenleistungen und die Verwaltung – fliesst **nicht** ins Sparkapital, ist "
        "aber wie der Sparbeitrag steuerlich abzugsfähig. Lohnabzug PK total = Sparbeitrag + Risikobeitrag."
    ),
    "vers_lohn": (
        "**Versicherter Lohn** gemäss Vorsorgeausweis (= AHV-Lohn minus Koordinationsabzug, "
        "im BVG-Minimum 2026 max. CHF 64'260). Viele Kassen versichern auch höhere Löhne."
    ),
    "staffel": (
        "Sparbeiträge in % des versicherten Lohns je Altersstufe. Voreinstellung = BVG-Minimum "
        "(7/10/15/18 %), je hälftig AN/AG. Passen Sie die Werte an Ihr Reglement an."
    ),
    "zins": (
        "Erwartete **Verzinsung des Altersguthabens** pro Jahr. Der BVG-Mindestzins 2026 beträgt "
        "1.25 % (gilt nur fürs Obligatorium). Viele Kassen verzinsen in guten Jahren 2–5 %. "
        "Für lange Zeiträume sind 1.5–2.5 % eine vorsichtige Annahme."
    ),
    "uws": (
        "**Umwandlungssatz**: Prozentsatz, mit dem das Kapital bei Pensionierung in eine "
        "lebenslange Jahresrente umgerechnet wird. Beispiel: CHF 500'000 × 5.5 % = CHF 27'500 "
        "Rente pro Jahr. Gesetzlich 6.8 % im Obligatorium, viele Kassen wenden auf das gesamte "
        "Guthaben 4.8–6 % an ('umhüllender' Satz)."
    ),
    "lohnwachstum": (
        "Jährliches Wachstum von Lohn, Beiträgen und steuerbarem Einkommen. **0 % = Rechnung in "
        "heutiger Kaufkraft** (empfohlen, da Steuertarife laufend der Teuerung angepasst werden)."
    ),
    "potenzial": (
        "**Einkaufspotenzial** = maximaler freiwilliger Einkauf, steht im Vorsorgeausweis. "
        "Es entsteht durch Lohnerhöhungen, Beitragslücken (z.B. Auslandjahre, Teilzeit) oder "
        "Scheidung. Achtung: Ein WEF-Vorbezug muss zuerst zurückbezahlt werden."
    ),
    # Einkauf
    "einkauf_total": (
        "Geplanter freiwilliger Einkauf (Total). Der Einkauf ist vom steuerbaren Einkommen "
        "**voll abzugsfähig** – Sie sparen dadurch Steuern zum Grenzsteuersatz."
    ),
    "einkauf_jahre": (
        "Auf wie viele Jahre der Einkauf verteilt wird. Wegen der **Steuerprogression** spart "
        "man meist mehr, wenn man den Betrag auf mehrere Jahre verteilt ('staffeln')."
    ),
    "einkauf_start": "Alter beim ersten Einkauf (Einzahlung jeweils gegen Ende Jahr).",
    # ETF
    "etf_rendite": (
        "Erwartete **Gesamtrendite** (Kursgewinne + Dividenden) vor Kosten pro Jahr. Ein globaler "
        "Aktien-ETF (z.B. MSCI World/ACWI) erzielte langfristig rund 6–8 % nominal, mit starken "
        "Schwankungen (Einbrüche von −30 bis −50 % sind möglich). Vorsichtig: 4–5 %."
    ),
    "etf_div": (
        "Anteil der Rendite, der als **Dividende/Ertrag** ausgeschüttet (oder thesauriert) wird. "
        "Dieser ist jährlich als Einkommen steuerbar. Globale Aktien: ca. 1.5–2 %. "
        "Kursgewinne sind für Privatanleger steuerfrei."
    ),
    "etf_ter": (
        "Laufende Kosten: Fondskosten (TER) plus Depot-/Handelsgebühren pro Jahr in %. "
        "Günstige Indexfonds/Apps: 0.1–0.5 %."
    ),
    "steuer_invest": (
        "Wenn aktiviert, wird die Steuerersparnis aus dem Einkauf ebenfalls ins ETF investiert "
        "(faire Rechnung: in beiden Varianten fliesst gleich viel eigenes Geld)."
    ),
    "reduktion": (
        "Um wie viel CHF pro Jahr Ihr **Arbeitnehmer-Sparbeitrag** tiefer wäre – z.B. bei einem "
        "Wahlplan 'Minus' statt 'Standard', oder bei einer Kasse mit tieferen Beiträgen. Die "
        "Reduktion erhöht Ihren Nettolohn, aber auch das steuerbare Einkommen."
    ),
    # Ruhestand
    "einkommen_ruhestand": (
        "Übriges steuerbares Einkommen im Ruhestand ohne PK-Rente, z.B. AHV-Rente (max. ca. "
        "CHF 30'000–33'000/Jahr für Einzelpersonen, Ehepaare max. 150 %), Vermögenserträge."
    ),
    "rendite_kapital": (
        "Rendite nach Steuern, die Sie auf dem bezogenen Kapital während des Ruhestands erwarten "
        "(z.B. konservativ angelegt). Wird für den Kapitalverzehr verwendet."
    ),
}

INFO = {
    "steuern": """
**So funktionieren Schweizer Steuern**

Sie zahlen Steuern an **drei Ebenen**:

1. **Bund** (direkte Bundessteuer) – nur auf dem Einkommen, max. 11.5 %.
2. **Kanton** und 3. **Gemeinde** – auf Einkommen **und** Vermögen.

Kanton und Gemeinde rechnen mit einer **einfachen Steuer** (aus dem kantonalen Tarif)
und multiplizieren diese mit dem jeweiligen **Steuerfuss**:

> Steuer = einfache Steuer × (Kantonssteuerfuss + Gemeindesteuerfuss + Kirchensteuerfuss)

**Durchschnittssteuersatz** = Steuern ÷ Einkommen.
**Grenzsteuersatz** = Steuer auf den *nächsten* (bzw. *letzten*) Franken. Er ist für
Abzüge entscheidend: Ein PK-Einkauf spart Steuern zum Grenzsteuersatz.
""",
    "kapitalsteuer": """
**Kapitalbezugssteuer**

Beziehen Sie Ihr PK- oder 3a-Guthaben als Kapital, wird es **getrennt vom übrigen
Einkommen** zu einem reduzierten Satz besteuert (einmalig im Jahr des Bezugs):

* **Bund**: 1/5 des ordentlichen Tarifs.
* **Kantone**: sehr unterschiedlich (z.B. ZH: Satz für 1/20 des Kapitals, mind. 2 %).

Die Steuer ist **progressiv**: Grössere Beträge werden prozentual höher besteuert. Deshalb
lohnt es sich oft, Bezüge (PK, mehrere 3a-Konten, Ehepartner) auf mehrere Jahre zu verteilen.
Beachten Sie: Auch die **zusätzliche** Kapitalsteuer auf einem Einkauf ist höher als der
Durchschnittssatz, weil der Einkauf "oben" auf das bestehende Kapital kommt.
""",
    "aufbau": """
**Wie wächst das PK-Guthaben?**

Jedes Jahr kommen hinzu:

* **Sparbeiträge** von Ihnen (Lohnabzug) und vom Arbeitgeber (Altersgutschriften)
* **Zinsen** auf dem bestehenden Guthaben (von der PK festgelegt, mind. BVG-Mindestzins aufs Obligatorium)
* **Freiwillige Einkäufe**

Bei der Pensionierung haben Sie die Wahl (je nach Reglement):

* **Rente**: Kapital × Umwandlungssatz = lebenslange Jahresrente (100 % als Einkommen steuerbar)
* **Kapital**: einmalige Auszahlung, separat und reduziert besteuert (Kapitalbezugssteuer)
* **Mischform**: Teil Rente, Teil Kapital (mind. 25 % des Obligatoriums als Kapital ist immer möglich)
""",
    "rente_kapital": """
**Rente oder Kapital?**

* **Rente**: lebenslang garantiert (Langlebigkeitsrisiko trägt die PK), meist mit
  Ehegattenrente (60 %). Sie ist jedes Jahr voll als Einkommen steuerbar und wird nicht der
  Teuerung angepasst. Beim Tod ohne Hinterbliebene verfällt das Kapital.
* **Kapital**: flexibel, vererbbar, einmalige reduzierte Besteuerung. Dafür tragen Sie das
  Anlage- und Langlebigkeitsrisiko selbst, und das Vermögen unterliegt der Vermögenssteuer.

Der **Break-even** zeigt, ab welchem Alter die Summe der Netto-Renten das Netto-Kapital
übersteigt. Leben Sie länger, war die Rente (rein finanziell) besser.
""",
    "einkauf": """
**Was ist ein PK-Einkauf?**

Haben Sie eine **Beitragslücke** (z.B. wegen Lohnerhöhung, Auslandaufenthalt, Teilzeit,
Scheidung), können Sie freiwillig Geld in die Pensionskasse einzahlen. Vorteile:

* Der Einkauf ist **voll vom steuerbaren Einkommen abzugsfähig** → Steuerersparnis zum Grenzsteuersatz.
* Das Geld ist **vermögenssteuerfrei** und die Zinsen sind **einkommenssteuerfrei**.
* Das Altersguthaben (und damit Rente/Kapital) steigt.

Nachteile / Risiken:

* Das Geld ist **gebunden** bis zur Pensionierung (Ausnahmen: Wohneigentum, Selbständigkeit, Auswanderung).
* Die Verzinsung der PK ist oft tiefer als die Rendite von Aktien.
* Beim Kapitalbezug fällt eine (reduzierte) **Kapitalbezugssteuer** an.
* **3-Jahres-Sperrfrist** (Art. 79b Abs. 3 BVG): Leistungen aus Einkäufen dürfen innerhalb von
  3 Jahren nicht als Kapital bezogen werden – sonst wird der Steuerabzug rückwirkend gestrichen.
* Bei einer finanziell schwachen PK (Unterdeckung) kann das Geld von Sanierungsmassnahmen betroffen sein.
* Bei Tod vor der Pensionierung zahlen nicht alle Kassen Einkäufe vollständig an die Erben aus.
""",
    "einkauf_vs_etf": """
**Wie wird verglichen?**

Beide Varianten kosten Sie heute **gleich viel Geld**:

* **Variante Einkauf**: Betrag in die PK → wächst mit dem PK-Zins → bei Pensionierung
  zusätzliche Kapitalbezugssteuer. Die **Steuerersparnis** erhalten Sie zurück und legen sie
  (optional) im ETF an.
* **Variante ETF**: gleicher Betrag ins ETF-Depot → wächst mit der ETF-Rendite minus Kosten.
  Jährlich fallen **Einkommenssteuern auf Dividenden** und **Vermögenssteuer** an
  (beides wird aus dem Depot bezahlt). Kursgewinne sind steuerfrei.

Verglichen wird das Nettovermögen bei der Pensionierung (bei Kapitalbezug).
Je **kürzer** die Zeit bis zur Pensionierung und je **höher** Ihr Grenzsteuersatz, desto
eher lohnt sich der Einkauf. Bei langen Zeiträumen gewinnt oft die höhere ETF-Rendite.
""",
    "reduziert": """
**Weniger in die PK – mehr ins ETF?**

Viele Pensionskassen bieten **Wahlpläne** an (z.B. Sparplan Minus / Standard / Plus), bei
denen Sie Ihren eigenen Sparbeitrag wählen können. Der Arbeitgeberbeitrag bleibt dabei
meist gleich. Zahlen Sie weniger ein:

* steigt Ihr Nettolohn um die Reduktion,
* steigt aber auch Ihr **steuerbares Einkommen** → Sie zahlen Mehrsteuer zum Grenzsteuersatz,
* der Rest (Reduktion minus Mehrsteuer) wird hier jedes Jahr ins **ETF** investiert.

Vergleich bei Pensionierung: **PK mit vollem Beitrag** (nach Kapitalbezugssteuer)
gegen **PK mit reduziertem Beitrag + ETF-Depot**.

Bedenken Sie: Aktien schwanken stark. Die PK-Verzinsung ist zwar tiefer, aber stabil
und die Mittel sind gebunden (Schutz vor vorzeitigem Verbrauch). Prüfen Sie im Reglement,
ob ein tieferer Sparplan auch Ihre Risikoleistungen (Invalidität, Todesfall) beeinflusst.
""",
    "zwei_pks": """
**Zwei Pensionskassen vergleichen**

Nützlich bei einem **Stellenwechsel** oder bei der Wahl zwischen **zwei Sparplänen**.
Wichtige Unterschiede zwischen Kassen:

* **Arbeitgeberbeiträge** – "Geschenktes Geld": je höher, desto besser.
* **Verzinsung** – macht über Jahrzehnte einen grossen Unterschied (Zinseszins).
* **Umwandlungssatz** – bestimmt die Höhe der Rente.
* **Ihre Lohnabzüge** – höhere Abzüge senken Nettolohn **und** Steuern.

Die Simulation geht vom gleichen Bruttolohn aus (optional mit Lohnunterschied) und rechnet
fair: Wer mehr Nettolohn hat, legt die Differenz (nach Steuern) optional im ETF an.
Das eingegebene steuerbare Einkommen gilt für PK A; für PK B wird es automatisch angepasst.
""",
}

GLOSSAR = [
    ("Pensionskasse (PK) / 2. Säule",
     "Die berufliche Vorsorge. Arbeitnehmende mit einem Jahreslohn über CHF 22'680 (2026) sind "
     "obligatorisch versichert. Ziel: zusammen mit der AHV (1. Säule) ca. 60 % des letzten Lohns "
     "im Alter. Daneben gibt es die freiwillige Säule 3a."),
    ("BVG – Obligatorium und Überobligatorium",
     "Das Bundesgesetz über die berufliche Vorsorge (BVG) definiert Mindestleistungen "
     "(Obligatorium): versicherter Lohn bis CHF 90'720, Mindestzins, Umwandlungssatz 6.8 %. "
     "Was eine Kasse darüber hinaus versichert, ist das Überobligatorium – dort ist die Kasse freier."),
    ("Altersguthaben",
     "Ihr persönliches Sparkapital in der PK: Summe aller Sparbeiträge, Einkäufe und Zinsen. "
     "Daraus wird bei Pensionierung die Rente oder das Kapital berechnet."),
    ("Sparbeitrag / Altersgutschrift",
     "Der Teil der PK-Beiträge, der dem Altersguthaben gutgeschrieben wird. BVG-Minimum in % des "
     "koordinierten Lohns: 25–34 J. 7 %, 35–44 J. 10 %, 45–54 J. 15 %, 55–65 J. 18 %."),
    ("Risikobeitrag",
     "Beitrag für die Versicherung von Invalidität und Tod sowie Verwaltungskosten. Er fliesst "
     "nicht ins Altersguthaben."),
    ("Koordinationsabzug / versicherter Lohn",
     "Vom AHV-Lohn wird der Koordinationsabzug (2026: CHF 26'460) abgezogen, weil ein Teil schon "
     "über die AHV versichert ist. Das Ergebnis ist der koordinierte bzw. versicherte Lohn."),
    ("Umwandlungssatz",
     "Prozentsatz, mit dem das Altersguthaben in eine jährliche Rente umgewandelt wird. "
     "CHF 100'000 × 6 % = CHF 6'000 Rente pro Jahr, lebenslang."),
    ("BVG-Mindestzins",
     "Minimaler Zins auf dem obligatorischen Altersguthaben, vom Bundesrat festgelegt (2026: 1.25 %)."),
    ("Deckungsgrad",
     "Verhältnis Vermögen der Kasse zu ihren Verpflichtungen. Unter 100 % ist die Kasse in "
     "Unterdeckung und kann Sanierungsmassnahmen (z.B. Minderverzinsung) beschliessen."),
    ("Einkauf / Einkaufspotenzial",
     "Freiwillige Einzahlung zum Schliessen von Beitragslücken. Voll steuerabzugsfähig. Das "
     "maximal mögliche Einkaufspotenzial steht im Vorsorgeausweis."),
    ("3-Jahres-Sperrfrist",
     "Nach einem Einkauf dürfen die daraus resultierenden Leistungen während 3 Jahren nicht als "
     "Kapital bezogen werden (Art. 79b Abs. 3 BVG). Sonst wird der Steuerabzug rückgängig gemacht."),
    ("WEF-Vorbezug",
     "Vorbezug von PK-Geld für selbstbewohntes Wohneigentum. Solange er nicht zurückbezahlt ist, "
     "sind freiwillige Einkäufe nicht möglich."),
    ("Freizügigkeitsguthaben",
     "Beim Stellenwechsel wird Ihr Altersguthaben an die neue PK übertragen. Ohne neue Stelle "
     "kommt es auf ein Freizügigkeitskonto."),
    ("Wahlplan / Sparplan",
     "Manche Kassen lassen Sie zwischen mehreren Beitragsstufen wählen (z.B. Minus/Standard/Plus). "
     "Höhere eigene Beiträge = mehr Altersguthaben und mehr Steuerabzug, aber weniger Nettolohn."),
    ("Kapitalbezugssteuer",
     "Separate, reduzierte Steuer beim Bezug von Vorsorgekapital (PK, 3a). Progressiv – grosse "
     "Beträge werden prozentual höher besteuert."),
    ("Steuerbares Einkommen",
     "Einkommen nach allen Abzügen. Darauf wird der Steuertarif angewendet."),
    ("Einfache Steuer & Steuerfuss",
     "Die einfache Steuer ergibt sich aus dem kantonalen Tarif. Kanton, Gemeinde und Kirche "
     "erheben jeweils ein Vielfaches davon (Steuerfuss in %)."),
    ("Grenzsteuersatz",
     "Steuerbelastung auf dem zusätzlichen bzw. letzten Franken Einkommen. Bestimmt, wie viel "
     "ein Abzug (z.B. PK-Einkauf, Säule 3a) an Steuern spart."),
    ("Splitting",
     "Bei Verheirateten wird in manchen Kantonen der Steuersatz für das Einkommen geteilt durch "
     "einen Divisor (z.B. 1.9 oder 2) bestimmt – das senkt die Progression."),
    ("Vermögenssteuer",
     "Jährliche Steuer der Kantone und Gemeinden auf dem Reinvermögen (meist 0.1–1 %). "
     "PK- und 3a-Guthaben sind davon befreit, ein ETF-Depot nicht."),
    ("Säule 3a",
     "Gebundene private Vorsorge. 2026 max. CHF 7'258 pro Jahr abzugsfähig (mit PK). "
     "Oft die erste Wahl vor einem PK-Einkauf, da flexibler."),
    ("ETF",
     "Exchange Traded Fund – ein börsengehandelter Indexfonds, der z.B. tausende Aktien weltweit "
     "abbildet. Günstig und breit diversifiziert, aber mit Kursschwankungen."),
    ("TER",
     "Total Expense Ratio – die jährlichen Kosten eines Fonds in % des Vermögens."),
    ("Dividendenrendite",
     "Ausschüttungen eines Fonds in % pro Jahr. Für Privatpersonen als Einkommen steuerbar "
     "(auch bei thesaurierenden Fonds), Kursgewinne hingegen sind steuerfrei."),
    ("Rente vs. Kapital",
     "Rente: lebenslang, sicher, 100 % einkommenssteuerpflichtig. Kapital: flexibel, vererbbar, "
     "einmalig reduziert besteuert, aber Anlage- und Langlebigkeitsrisiko liegen bei Ihnen."),
]

DISCLAIMER = (
    "Dieser Rechner dient der Orientierung und ersetzt keine Steuer- oder Vorsorgeberatung. "
    "Steuerberechnung mit den ESTV-Tarifen 2026 (alle Kantone und Gemeinden). Vereinfacht: "
    "keine Personalsteuern, Konkubinat = alleinstehend; Kapitalbezugsregeln von VD, VS und TI nicht "
    "mit aktuellen Vergleichswerten geprüft (Korrekturfaktor in der Seitenleiste). Massgebend sind das "
    "Reglement Ihrer Pensionskasse und die Veranlagung Ihrer Steuerbehörde."
)
