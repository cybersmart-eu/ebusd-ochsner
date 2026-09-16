# Ochsner eBUS: belastbare Aufzeichnung von Starts und Betriebsarten

Entwurf für AIR 11 C11A, TEM 24849, HW 0102, SW 0605. Vor der Nutzung die
tatsächliche Identität mit `ebusctl info` vergleichen. Keine Fremd-Firmware wird
durch diesen Entwurf als kompatibel freigegeben. Die bestehende Konfiguration
bleibt erhalten; dieses Paket verändert weder eine laufende Anlage noch Sollwerte.

## Ergebnis, das die Messung liefern soll

Für jede beobachtete Lauf-Folge sollen Startzähler, elektrische Leistung,
Wärmepumpenstatus, Warmwasserstatus und Temperaturen dieselbe Zeitachse besitzen.
So kann man Heizen → Warmwasser, Abtauen und erneute Heizanforderungen trennen.
Ein Leistungsabfall allein identifiziert die Betriebsart nicht. Ein steigender
Startzähler belegt Starts, aber sein Abfragezeitpunkt ist nicht zwingend deren
exakter Zeitpunkt. Ein Status „Heizbetrieb“ der Wärmepumpe allein unterscheidet
Raumheizung und Warmwasser nicht zuverlässig; der Warmwasserstatus gehört dazu.

Die Aufzeichnung ist zunächst eine Referenzmessung. Steuerungsautomatik und
Optimierung von Temperaturen/Stillstandszeiten sind eine getrennte nächste Stufe.

## Architektur

1. **ebusd** dekodiert und aktualisiert seinen Cache durch eBUS-Telegramme und
   gezielte Leseabfragen. Adressen und Datentypen bleiben controllerspezifisch.
2. **HTTP-Cache-Recorder** in `tools/ebus_capture.py` speichert Original-JSON,
   numerische Zustände, verfügbare rohe Master-/Slave-Arrays, `lastup`, Empfangszeit
   in UTC, eine monotone lokale Zeit und Busstatus in einer SQLite-Datei.
3. **Bestehendes MQTT → Timberwolf/InfluxDB → Grafana** kann parallel weiterlaufen.
   Numerische Statuscodes und Text können aus demselben Datensatz abgeleitet werden;
   keine zweite konkurrierende eBUS-Definition für dieselbe Adresse nötig.
4. Rohtelegramm-Logging von ebusd ergänzt den Cache-Recorder bei Bedarf. Der
   HTTP-Cache enthält nur den zuletzt sichtbaren Zustand. Mehrere Änderungen
   zwischen zwei HTTP-Abfragen können verloren gehen. Er ist daher **kein
   vollständiger Bus-Mitschnitt**. Für sekundengenaue Untersuchungen Rohtelegramme
   oder jede MQTT-Publikation zusätzlich mit Zeitstempel archivieren.

Der Recorder nutzt ausschließlich `/data/<circuit>?exact=true&full=true&raw=true&numeric=true&verbose=true`.
Er benutzt **kein** `required`, `maxage`, `poll`, `define` oder `write`. Ein
5-Sekunden-HTTP-Intervall erzeugt keine 5-Sekunden-eBUS-Messung. Es archiviert den
Cache. Ob ebusd die benötigten Werte rechtzeitig erhält, muss separat gemessen werden.
`raw=true` erhält verfügbare Rohantworten, stellt aber nicht jedes Telegramm bereit.

## Messpunkte und Prioritäten

| Stufe | Namen im bestehenden Profil | Zweck / vorläufiges Ziel für tatsächliche Updates |
|---|---|---|
| r1 | `heatpump.status.string`, `hotwater.status.string`, `heating.status.string`, `heatmanager.status`, `heatpump.cycles` | Übergänge und Starts; im Diagnosefenster möglichst 5–15 s |
| r2 | `hotwater.temp.buffer.tb`, `hotwater.temp.buffer.tb.setpoint`, `heatmanager.temp.buffer.tpo`, `.tpm`, `heatpump.temp.twv`, `.twr`, `heatpump.flow` | Speicher und Hydraulik; möglichst 15–30 s |
| r9 | Außen-/Quellentemperaturen, Heizkreis-Vorlauf/Soll, Zusatzheizstatus, Betriebsstunden und Energie-Teile | Kontext; zunächst 1–5 min, Zusatzheizstatus bei Bedarf höher priorisieren |
| r, ohne Dauerpoll | Konfigurationswerte, z. B. `hotwater.temp.buffer.tb.set` | Zu Messbeginn und nach Änderungen gezielt erfassen |

Die Bereiche sind Messziele, keine garantierten Takte. `r2` bedeutet jede zweite
Pollrunde, nicht alle zwei Sekunden. Im ursprünglichen Profil stehen **41 r1**-
Zeilen. Bei einem 5-s-Slot ergibt das grob 205 s pro Vollrunde, sofern keine anderen
Telegramme zusätzliche Updates liefern. Auch das neue Profil garantiert keine
5–15 s: die tatsächlichen `lastup`-Abstände und Fehler müssen zeigen, ob weniger
Pollpunkte, eine vorsichtige Verkürzung des globalen Intervalls oder passive
Updates nötig sind. Nicht blind alle Werte auf schnelle Abfrage stellen.

Die Namen bleiben erhalten, damit bestehende MQTT-Verbraucher nicht durch eine
Umbenennung von Punkten in Unterstriche brechen. Eine solche Umbenennung kann
später in einem dokumentierten MQTT-/HA-Adapter stattfinden.

## Aufnahme starten (Python 3.10 oder neuer)

Voraussetzung: ebusd läuft bereits, seine HTTP-Schnittstelle ist vom Recorder aus
erreichbar, und das passende Controller-Profil ist geladen. Der Recorder startet
keinen ebusd und richtet den Bus nicht neu ein. Für einen Rechner neben ebusd:

```bash
python3 tools/ebus_capture.py collect \
  --url http://localhost:8080 --circuit 24849 \
  --db recordings/baseline.sqlite --interval 5 --stale-after 90 \
  --controller 'TEM;24849;0605;0102' \
  --config-revision 'einzutragender-Git-Commit' \
  --config-file configuration/ochsner/15.24849.HW0102.SW0605.csv \
  --config-file configuration/ochsner/_templates.csv
```

`--controller` ist eine dokumentierte Angabe des Betreibers, keine automatische
Identitätsprüfung. Bei Verwendung eines generierten Profils dessen tatsächliche
Datei als `--config-file` angeben. Zugang nur über das bestehende vertrauenswürdige
Netz/VPN; keine Zugangsdaten in die URL oder ins öffentliche Repository schreiben.

Mit `--once` einmalig eine Momentaufnahme erstellen. `Ctrl+C` beendet sauber.
Jeder Start legt einen neuen Datensatz in `runs` mit Versionsangaben und
Konfigurations-Hashes an. Wiederholte Starts können dieselbe SQLite-Datei nutzen.
Der Prozess muss zum Dauerbetrieb durch die vorhandene Dienst-/Containerverwaltung
überwacht werden; diese erste Version enthält keinen installierenden Service.

```bash
python3 tools/ebus_capture.py report --db recordings/baseline.sqlite
python3 tools/ebus_capture.py export --db recordings/baseline.sqlite > recordings/baseline.csv
python3 -m unittest discover -s tests -v
```

Der Export enthält Zeit, Punkt, Quellenzeit, Alter, Qualitätsflag und das
unveränderte Message-JSON einschließlich aller Felder. Die SQLite-Tabellen
`snapshots` (HTTP-/Busfehler) und `runs` (Metadaten) sind zusätzlich aufzubewahren;
der CSV-Export allein ersetzt das Archiv nicht.

## Opt-in: priorisiertes Diagnoseprofil erzeugen

```bash
mkdir -p recordings
python3 tools/build_logging_profile.py > recordings/15.24849.HW0102.SW0605.csv
```

Erstellt eine separate CSV nur mit Lese-Definitionen, abgestuften Pollprioritäten
und vorhandenen Einstellungen zum gelegentlichen Auslesen. Relay-Test-Definitionen
sind nicht enthalten. **Nicht zusätzlich zum Originalprofil laden**: es ist ein
Alternativprofil für denselben Controller. `_templates.csv` und `broadcast.csv`
werden weiterhin benötigt. Vor Installation in einem separaten Konfigurationsbaum
mit der eigenen ebusd-Version `--checkconfig` prüfen. Danach erst kontrolliert
übernehmen. Der Python-Test prüft die Transformation, ersetzt den ebusd-Parser und
den Vergleich mit der realen Anlage aber nicht. Der Generator ist auf das bekannte
Quellprofil zugeschnitten und bricht bei fehlenden Pflichtpunkten ab.

Die bekannten widersprüchlichen Statusübersetzungen und fraglichen Datentypen des
Originals werden ausdrücklich **nicht automatisch korrigiert**. Numerische Codes,
Originalantwort und OTE-Display liefern die Grundlage für die spätere Korrektur.

## Qualität: Empfang ist nicht Messung

- `received_utc`: Zeitpunkt, zu dem der Recorder die HTTP-Antwort erhalten hat.
- `source_epoch`: das `lastup` der einzelnen Nachricht, laut ebusd UTC-Sekunden.
- `age_s`: Differenz, nur bei synchronisierten Uhren aussagekräftig.
- `fresh`: innerhalb des gewählten Alterslimits; **kein Beweis für korrekte
  Registerzuordnung oder physikalischen Messwert**.
- `stale`: zu alter Cache. Für langsame r9-Werte kann das 90-s-Standardlimit zu
  streng sein; nach der Referenzmessung je Messpunkt differenzieren.
- `never_received`, `invalid_timestamp`, `clock_skew`, `no_bus_signal` und HTTP-
  Fehler bleiben sichtbar. Fehlende Werte werden niemals als null ersetzt.

Unveränderte Temperaturen oder Zähler sind nicht automatisch eingefroren. Prüfen,
ob Telegramme weiter eintreffen und `lastup` fortschreitet. Ein gültig wiederholt
übertragenes, aber im Regler eingefrorenes Register ist allein am Alter nicht
erkennbar: dafür braucht es Vergleich mit Leistung, Status und OTE-Anzeige.

Der Bericht zählt bewusst **Cache-Beobachtungen und unterschiedliche Quellenzeiten
getrennt**. Das sind keine exakten Telegrammzahlen: `lastup` hat Sekundenauflösung
und mehrere Updates können zwischen zwei Cache-Abfragen auftreten. Alle
Cache-Beobachtungen bleiben für die Nachprüfung gespeichert. Unplausible
Zählerabfälle/-sprünge werden bewahrt; die Auswertung muss sie markieren statt
Reset-Erholungen als Starts zu zählen. Noch keine automatische Reset-/Wrap-Korrektur.

## Energie und spätere Auswertung

- Physischer Wärmepumpen-Stromzähler bleibt die Referenz für elektrische Energie.
- Reglerenergie zunächst als **controllerspezifischer Registerwert** behandeln.
  OTE-Parameterkennung, Einheit, Skalierung und Messumfang gegen Anzeige verifizieren.
- kWh-/MWh-Teile separat archivieren. Erst nach Prüfung `1000*MWh + kWh` bilden;
  zeitversetztes Auslesen am Überlauf kann einen falschen Sprung erzeugen. Paare um
  einen Überlauf erneut lesen und bis zur Bestätigung als unsicher kennzeichnen.
- COP/JAZ nur mit verifizierter Wärmemenge und gleicher Zeit-/Systemgrenze. Ein
  Verhältnis unbekannter Reglerzähler ist keine bestätigte Effizienz.
- Für Starts Zeitintervalle statt Scheingenauigkeit ausgeben: letzter sicherer
  Aus-Zustand bis erster sicherer Ein-Zustand. Bei Datenlücken kein Ereignis erfinden.
- Ein Zählerzuwachs von 2 zwischen zwei Abfragen belegt zwei gezählte Starts, nicht
  deren genaue Zeitpunkte oder Betriebsarten.

## Aufbewahrung und Validierung an der Anlage

Zunächst 48–72 Stunden inklusive mindestens einer normalen Heiz-/Warmwasserfolge
erfassen; Abtauung gegebenenfalls in einer gesonderten kalten Messphase. Im selben
Fenster die vorhandene Leistungsmessung exportieren. Einen Übergang am OTE
beobachten und Zeit/Status/Startzähler notieren. Das bestätigt die Zuordnung.

Das Archiv wächst absichtlich ohne automatische Löschung; Größe nach dem ersten
Tag prüfen. Für den Dauerbetrieb Tagesdateien, kontrollierte Aufbewahrung und
Backups ergänzen. Während der Aufnahme SQLite-Backup-API verwenden oder den
Recorder zum Kopieren stoppen: die `.sqlite` allein kann bei aktivem WAL-Modus
noch nicht alle Daten enthalten. Kein Backup durch bloßes Kopieren der Hauptdatei
bei laufendem Prozess. Konfigurationsdateien und `ebusctl info` zur Aufnahme sichern.

Die Software wurde offline und gegen einen simulierten HTTP-Endpunkt geprüft.
Keine Aussage über die tatsächliche Erreichbarkeit, Telegrammqualität oder
Temperatur-/Statuszuordnung an einer realen Ochsner-Anlage ist damit verbunden.

## Quellen

- [ebusd HTTP API](https://github.com/john30/ebusd/wiki/3.2.-HTTP-client)
- [ebusd Nachrichtentypen/Pollprioritäten](https://github.com/john30/ebusd/wiki/4.1.-Message-definition)
- [ebusd Startoptionen](https://github.com/john30/ebusd/wiki/2.-Run)
- [Vergleich der Ochsner-Projekte und offene Prüfpunkte](research-ochsner.md)
