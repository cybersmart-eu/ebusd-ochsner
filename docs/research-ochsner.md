# Vergleich: Erkenntnisse aus anderen Ochsner-eBUS-Projekten

Geprüft am 16.09.2026. Grundlage sind die tatsächlich gelesenen Dateien, nicht
alle Dateien, historischen Issues oder Betriebszustände der jeweiligen Anlage.
Projektberichte sind Beobachtungen der Autoren, keine Ochsner-Freigabe. Es wurde
kein Fremdcode in den neuen Recorder oder Profilgenerator übernommen.

## Ausgangspunkt: cybersmart-eu

Stand `f255ad230a025609d24cf2004986b8a5df2c5b19`.
AIR 11 C11A, UniFresh 500, Controller TEM 24849 / HW0102 / SW0605.

Das vorhandene Profil ist eine gute Grundlage: 71 aktive Lese-Definitionen,
davon 41 mit `r1`. Status Wärmepumpe, Warmwasser und Heizkreis, Startzähler,
Speicherfühler, WP-Vorlauf/-Rücklauf und Volumenstrom sind bereits enthalten.
Der nächste Fortschritt ist deshalb zuerst eine bessere Zeit- und Qualitätsbasis.

Konkrete Prüfpunkte im bestehenden Repository:

1. `_templates.csv` enthält `kwh` doppelt; Energieeinheiten sind als `kW/h` und
   `MW/h` bezeichnet. Energie sollte nach fachlicher Zuordnung `kWh`/`MWh` heißen.
   Eine Änderung kann vorhandene MQTT-/HA-Zuordnungen beeinflussen und wird deshalb
   separat migriert. Das doppelte Template sollte mit dem ebusd-Parser geprüft werden.
2. Der Templatename `unit` ist mehrfach definiert. Vor Bereinigung prüfen, welche
   Felddefinitionen auf welche Interpretation angewiesen sind.
3. Deutsche und englische Statuslisten weichen ab, z. B. Status 24 und 27 im
   Wärmepumpenstatus. Keine Zusammenführung durch bloßes Übersetzen; Rohcode und
   OTE-Anzeige unter derselben Firmware vergleichen.
4. `cycles,HCD` und `hours,HCD:2` müssen mit vollständigen Antwortbytes und Anzeige
   geprüft werden. Ein anderer Regler kann größere Felder benötigen. Ohne Beleg
   nicht auf `HCD:4` umstellen. Plausible ältere Werte sind ebenfalls Evidenz.
5. `hotwater.temp.buffer.tb.set` (05-051) und `.tb.setpoint` (01-004) getrennt
   aufzeichnen: eingestellter Normal-Sollwert versus aktueller Soll-/Anforderungswert.
   Wie genau 01-004 außerhalb einer Ladung reagiert, bleibt bei dieser Anlage zu prüfen.
6. Mindeststillstandszeit **09-023** ist im aktiven CSV nicht als Lese-Definition
   enthalten. Das ist ein gezielt zu ergänzender Messpunkt, aber kein Anlass, eine
   Registeradresse aus einer anderen Firmware zu raten. Über Dokumentation,
   Menübeobachtung/Rohantwort und Displayvergleich verifizieren.
7. Ein direkter, verifizierter Verdichter-Ein/Aus-Punkt fehlt im gelesenen aktiven
   Profil. `heatpump.status.string` ist kein universeller Ersatz. Startzähler und
   gemessene elektrische Leistung bleiben wichtige unabhängige Größen.

[Originalprofil](https://github.com/cybersmart-eu/ebusd-ochsner/blob/f255ad230a025609d24cf2004986b8a5df2c5b19/configuration/ochsner/15.24849.HW0102.SW0605.csv)
und [Templates](https://github.com/cybersmart-eu/ebusd-ochsner/blob/f255ad230a025609d24cf2004986b8a5df2c5b19/configuration/ochsner/_templates.csv).

## SmartLessing/ebusd-ochsner

Stand `38bb2e221a3920a061b25d77fe8f87a08694a8a2`.
Im README wird ebenfalls AIR 11 C11A / TEM 24849 / SW0605 / HW0102 beschrieben;
die Speicheranlage wird eingangs als getrennte PU300-/PU800-Anlage bezeichnet.
Andere README-Abschnitte sind erkennbar aus der Vorlage übernommen. Die gleiche
Reglerkennung ist nützlich; identische Hydraulik darf daraus nicht folgen.

Gelesen: README, `configuration/ochsner/tem/15.24849.HW0102.SW0605.csv`, `_templates.csv`.
Der Fork baut explizit auf cybersmart-eu auf und ergänzt Home-Assistant-Integration,
geänderte Namen mit Unterstrichen, Betriebsarten und ein weiteres Controllerprofil.
Die gelesenen Templates verwenden `kWh`/`MWh` korrekt und enthalten zusätzliche
Betriebsart-Übersetzungen. Die uneinheitlichen Statuslisten und Stunden-/Zyklentypen
sind dort aber nicht grundsätzlich gelöst.

**Nutzen:** naher Vergleichskandidat für HA-Discovery und Betriebsart-Mapping.
**Nicht ungeprüft übernehmen:** neue Namen, Skalierungen, Schreibdefinitionen und
das andere Controllerprofil. Bestehende Timberwolf-Zeitreihen sollen ihre Namen behalten.

[README](https://github.com/SmartLessing/ebusd-ochsner/blob/38bb2e221a3920a061b25d77fe8f87a08694a8a2/README.md)
und [Profil](https://github.com/SmartLessing/ebusd-ochsner/blob/38bb2e221a3920a061b25d77fe8f87a08694a8a2/configuration/ochsner/tem/15.24849.HW0102.SW0605.csv).

## deyanp/ha-ebusd-ochsner-gmww10

Stand `4a543d819bcff596d784647cb8b4bade9774cab1`.
Gelesen: README. GMWW 10 plus, TEM 22420 / SW0502 / HW0102 – **andere Firmware**.

Der Autor dokumentiert verschobene Register, vier Byte breite Zähler und den
Abgleich von Rohantworten mit der OTE-Anzeige. Außerdem unterscheidet er 05-051
(konfigurierter WW-Sollwert) und 01-004 (momentane Anforderung); auf seiner Anlage
fällt 01-004 außerhalb einer Ladung auf 10 °C.

**Nutzen:** die Verifikationsmethode: Parameterkennung, vollständige Antwort,
Bytebreite/Skalierung und Displaywert gemeinsam dokumentieren. Das ist direkt
auf die Arbeit am eigenen Projekt anwendbar.
**Nicht übertragen:** konkrete Registerverschiebung, `HCD:4`/Teiler 100 oder das
10-°C-Verhalten ohne Test an TEM 24849. Einzelne allgemeine Schlussfolgerungen im
Fremd-README sind nicht durch unsere Prüfung bestätigt.

[README mit Firmwarevergleich](https://github.com/deyanp/ha-ebusd-ochsner-gmww10/blob/4a543d819bcff596d784647cb8b4bade9774cab1/README.md).

## zeroflow/ochsner-gmdw-ebusd

Stand `c8d46dc14c31b0bb9ec6e56f20ce5aee1bb3f406`.
Gelesen: README und `findings.md`. GMDW 11 HK plus, Direktverdampfung, Circuit 22102.

Der Autor dokumentiert zuvor falsch benannte Energieregister und validierte
kWh-/MWh-Paare an seiner Anzeige. Seine Untersuchung findet Startzähler und
Betriebsstunden am verwendeten Buszugang nicht; seine daraus abgeleitete interne
Speicherarchitektur ist eine projektspezifische Schlussfolgerung, kein gesicherter
Befund für AIR 11 / 24849. Unsere vorhandene ältere Startzählerreihe darf deshalb
nicht verworfen werden.

**Nutzen:** Rohtelegramme behalten, Registeridentität und thermische/elektrische
Energie sauber trennen, zeitgleiche Zählerdifferenzen und unabhängigen Stromzähler
verwenden. Nicht jede Aussage des Dokuments zu physikalischen Effizienzgrenzen oder
interner Firmware ist durch die vorgelegten Daten hinreichend bewiesen; solche
Aussagen werden hier nicht übernommen.

[Findings](https://github.com/zeroflow/ochsner-gmdw-ebusd/blob/c8d46dc14c31b0bb9ec6e56f20ce5aee1bb3f406/findings.md).

## bensch2293/Ochsner-ebus

Stand `ed0f4087118fe752727bd30e1d380872d8f2b6e9`.
Gelesen: `15.csv`. AIR 23, OTE plus, ID27389 – andere Anlage.

Das Profil kombiniert aktive Abfragen mit passiven `u`-Definitionen für vom
Master abgefragte Temperaturen. Es beschreibt andere Zuordnungen im Energieblock.
Es enthält auch ausdrücklich unbestätigte Sensoren und Kommentare zu nur in
bestimmten Betriebszuständen aktualisierten Werten.

**Nutzen:** prüfen, welche Telegramme auf der eigenen Anlage ohnehin vorhanden
sind; unnötige Polls vermeiden. **Nicht übertragen:** Masteradresse, Energieblock
oder die Aussage über Aktualisierung im ausgeschalteten Zustand ohne eigene Messung.

[15.csv](https://github.com/bensch2293/Ochsner-ebus/blob/ed0f4087118fe752727bd30e1d380872d8f2b6e9/15.csv).

## hannescrypto/ebusd-ochsner-ote3

Stand `0fa72aae183d5679bbe2c03841dc2626f04580e0`.
Baum und `src/ochsner/ochsner_ote3.csv` geprüft. Großes TypeSpec-/CSV-Umfeld;
die gelesene kleine CSV enthält gemischte Trennzeichen und nur wenige Punkte.
Das gesamte TypeSpec-Projekt wurde nicht kompiliert oder validiert.

**Nutzen:** langfristiger Kandidat für generierte, validierte Definitionen.
Für das kurzfristige Logging der 24849-Anlage kein belegter Ersatz des vorhandenen
Profils. Kein pauschales Qualitätsurteil über die übrigen Dateien.

[Geprüfte Datei](https://github.com/hannescrypto/ebusd-ochsner-ote3/blob/0fa72aae183d5679bbe2c03841dc2626f04580e0/src/ochsner/ochsner_ote3.csv).

## Umsetzungsreihenfolge

1. Bestehende eBUS-Identität, Profile und Historie sichern; vorhandene Telegramme
   und tatsächliche Aktualisierungsintervalle messen.
2. Cache-Recorder parallel zu MQTT starten, Startzähler und drei Betriebsstatus
   gegen Display/Leistung bestätigen. Keine automatische Nullsetzung bei Ausfall.
3. Opt-in-Pollprofil offline prüfen, dann an der Anlage mit Baseline vergleichen.
4. Erst nach diesen Befunden Statuslisten, Zählertypen und Einheiten separat
   bereinigen; eine Korrektur erhält jeweils Rohbeispiel, Firmware und Testfall.
5. 09-023, WW-Hysterese und ein zuverlässiges Verdichtersignal ergänzen, soweit
   die konkrete Firmware sie liefert. Keine geratenen Schreibzugriffe.
6. Danach Ereignisauswertung: Starts nach Betriebsart, Lauf- und Pausendauern,
   Übergangsmatrix, Temperaturabfall im Speicher, Abtauanteil und Datenabdeckung.
   Erst daraus eine Regelungsoptimierung ableiten.
