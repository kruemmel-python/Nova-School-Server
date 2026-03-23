# Runner, Container, Netzwerk und Sicherheit

Nova School fuehrt Schuelercode kontrolliert aus. Dafuer existieren mehrere Schutzebenen, die je nach Einsatzszenario kombiniert werden koennen.

## Sicherheitsmodell

| Ebene | Aufgabe | Ergebnis |
| --- | --- | --- |
| Rechteprofil | steuert, welche Funktionen ein Benutzer ueberhaupt nutzen darf | keine Ausfuehrung ohne Freigabe |
| Workspace-Trennung | trennt Dateien nach Benutzer und Gruppen | kein unkontrolliertes Mischen von Projekten |
| ToolSandbox | kapselt und validiert Tool-Aufrufe | kontrollierte Prozessausfuehrung |
| SecurityPlane | unterstuetzt Identitaet, Policies und Sicherheitsbetrieb | zentraler Sicherheitskontext |
| Container-Isolation | trennt Laufzeitumgebung und Netzwerk | harte Begrenzung fuer Prozesse |

## Runner-Backends

Nova School kann zwei Grundmodelle verwenden:

- **Host-Prozess-Runner:** schnell, einfach, gut fuer kontrollierte Labors auf vertrauenswuerdigen Schulgeraeten
- **Container-Runner:** bevorzugt fuer harte Netztrennung, Ressourcenlimits und klare Betriebsgrenzen

## Netzwerkfreigaben

`web.access` ist ein Fachrecht. Es bedeutet nicht automatisch freien Zugriff fuer alles, sondern dass ein Projekt oder eine Sitzung Webkommunikation nutzen darf, wenn die gewaehlte Laufzeit es erlaubt.

Fuer harte Trennung gilt:

- ohne Freigabe Container mit `--network none`
- mit Freigabe Container im freigegebenen Netzwerkmodus
- Host-Prozess-Runner nur dort nutzen, wo Schule und Betrieb das verantworten koennen

## Sprachen und Laufzeitarten

Nova School deckt klassische Dateien, Notebook-Zellen, Webvorschau und moderne Webframeworks ab. Die eigentliche Sprachfreigabe wird ueber die `run.*`-Rechte gesteuert.

## PTY und interaktive Programme

Interaktive Vollbild-Terminalprogramme benoetigen PTY-Unterstuetzung. Nova School nutzt dafuer:

- unter Windows die passende PTY-Schicht fuer ConPTY-kompatibles Verhalten
- unter Linux die systemueblichen PTY-Mechanismen

## Betriebsempfehlungen

1. Fuer Unterricht standardmaessig Container-Backend bevorzugen.
2. Webzugriff nur fuer benoetigte Gruppen oder Projekte aktivieren.
3. LM Studio serverseitig bereitstellen, nicht auf Schuelerclients verteilen.
4. Offline-Dokumentationen lokal spiegeln, statt Internetzugang als Ersatz zu oeffnen.
5. CPU- und RAM-Limits pro Container bewusst setzen.
