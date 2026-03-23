# Nova School Server

Nova School Server ist eine browserbasierte Lern- und Entwicklungsplattform fuer Informatikunterricht im Schulnetz. Der Server stellt Projekte, Editor, Notebooks, Offline-Dokumentation, modulare Lehrplaene, KI-Unterstuetzung und abgesicherte Code-Ausfuehrung zentral bereit. Schueler und Lehrkraefte arbeiten ueber den Browser; die Ausfuehrung und Verwaltung liegen auf dem Server oder auf angebundenen Workern.

## Kernfunktionen

- Browserbasierte Entwicklungsumgebung fuer Python, JavaScript, C++, Java, Rust, HTML sowie Node.js/npm
- Benutzer-, Gruppen- und Rechteverwaltung fuer Unterricht, Kurse und Projekte
- Datei-Editor, Notebook-Zellen, Live-Ausfuehrung, PTY-/TTY-Terminals und Vorschau
- Offline-Referenzbibliothek mit lokalen Mirrors und eigener Produktdokumentation
- LM-Studio-Integration und sokratischer KI-Mentor
- Modullehrplaene mit Mini-Pruefungen, Abschlusspruefung und Zertifikaten
- Kollaborative Notebooks, Chat, Peer Review und Audit-Protokolle
- Distributed Playground mit Remote-Workern fuer verteilte Systeme
- Share- und Export-Funktionen fuer Unterrichts- und Abgabeformate

## Zielbild

Nova School Server trennt Client und Ausfuehrung klar:

- Clients benoetigen nur einen Browser
- Projekte, Dateien, Rechte und Dokumentation liegen zentral
- Code wird kontrolliert serverseitig oder auf Remote-Workern ausgefuehrt
- Unterricht kann vollstaendig im lokalen Netz oder mit gezielter Webfreigabe stattfinden

## Voraussetzungen

### Basis

- Python 3.12
- Browserzugriff im lokalen Netz oder ueber einen internen Host
- Schreibrechte im Projekt- und Datenverzeichnis

### Optional

- Docker oder Podman fuer Container-Isolation
- LM Studio fuer lokale KI-Unterstuetzung
- `pywinpty` fuer erweiterten PTY-Support unter Windows
- Linux-Worker oder Linux-Hauptserver fuer robuste produktive Ausfuehrung

## Schnellstart

### Abhaengigkeiten installieren

Windows:

```powershell
py -3 -m pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m pip install -r requirements.txt
```

### Server starten

Windows:

```powershell
.\start_server.ps1
```

Linux/macOS:

```bash
./start_server.sh
```

Alternativ direkt ueber Python:

```bash
python -m nova_school_server
```

Standardmaessig bindet der Server auf `0.0.0.0` und ist lokal sowie im Schulnetz erreichbar. Fuer Windows muss Port `8877` in der Firewall freigegeben sein, wenn Clients aus dem Netzwerk zugreifen sollen.

## Erster Zugriff

Nach dem Start stehen Demo-Konten zur Verfuegung:

- `admin / NovaSchool!admin`
- `teacher / NovaSchool!teacher`
- `student / NovaSchool!student`

Beim Seed werden zudem Beispielprojekte und initiale Kursdaten angelegt.

## Betriebskonzept

### Ausfuehrung

Nova School Server unterstuetzt zwei Runner-Modi:

- `container`
  - empfohlener Standard
  - Sprachlaeufe in separaten Containern
  - konfigurierbare Images, RAM-, CPU-, PID- und Laufzeitgrenzen
- `process`
  - unsicherer Host-Fallback
  - nur fuer ausdrueckliche Ausnahmefaelle

Containerlaeufe sind gehaertet durch:

- read-only Root-FS
- materialisierten Run-Workspace ohne Live-Quell-Mount
- `cap-drop ALL`
- `no-new-privileges`
- Seccomp
- `ulimit`
- Scheduler fuer globale und rollenbezogene Parallelitaet

### Netzwerkmodell

- ohne `web.access`: isolierte Ausfuehrung ohne externes Netz
- mit `web.access`: freigegebene Netzpfade gemaess Serverkonfiguration
- optionaler Proxy-Pfad mit `web_proxy_url`, `web_proxy_no_proxy` und `web_proxy_required`

### Python-Abhaengigkeiten

Python-Projekte koennen ein projektlokales `requirements.txt` enthalten.

Verhalten:

- Pakete werden pro Projektlauf isoliert vorbereitet
- erfolgreiche Paketstaende werden serverseitig gecacht
- die Erstinstallation benoetigt Netzfreigabe oder einen bereits vorhandenen Cache
- die Installation erfolgt nicht global auf dem Host

### Python-GUI

Native Python-Desktop-GUIs wie `tkinter`, `turtle`, `PyQt`, `PySide` oder `customtkinter` werden nicht als lokale Host-Fenster genutzt. Fuer solche Projekte unterstuetzt der Server einen GUI-spezifischen Ausfuehrungspfad mit virtueller Anzeige und Vorschau-Artefakten. Voll interaktive Desktop-Remoting-Oberflaechen sind davon getrennt zu betrachten.

## Zentrale Produktbereiche

### Projekte, Editor und Notebooks

- persoehnliche und gruppenbezogene Workspaces
- Datei-Editor mit Vorschau
- Notebook-Zellen mit Einzel- und Live-Ausfuehrung
- interaktive Sessions mit `stdin`, `stdout`, `stderr`, ANSI-Rendering und Resize

### Dokumentation

- `/manual` fuer rollenbezogene Bedienungsanleitungen
- `/reference` fuer die Offline-Referenzbibliothek
- lokale Mirrors fuer Sprach- und Webdokumentation
- eigene Produktdokumentation fuer Nova School

### KI

- LM-Studio-Codehilfe
- sokratischer Mentor mit projektbezogenem Verlauf
- serverseitige Freigabe pro Benutzer und Gruppe

### Modullehrplaene

- freischaltbare Kurse fuer Benutzer und Gruppen
- Mini-Module mit Sofort-Rueckmeldung
- Abschlusspruefung und Zertifikatsausgabe
- PDF-Zertifikate mit Branding und Verifikationsdaten

### Kollaboration

- Projekt- und Gruppenchat
- kollaborative Notebooks mit Live-Sync
- Peer Review mit Snapshot-Einreichung und Audit-Analyse

### Distributed Playground

- Topologien ueber `topology.json`
- Remote-Worker fuer isolierte Service-Ausfuehrung
- signierte Dispatch-Jobs und Worker-Bootstrap

## Offline-Referenzbibliothek

Die Referenzbibliothek arbeitet mit zwei Dokumenttypen:

- `starter`
  - kompakte integrierte Schnellstart-Dokumente
- `mirrored`
  - lokal gespiegelte primaere oder offizielle Dokumentationsquellen

Spiegelungen werden unter `data/reference_library/packs/<bereich>/site/` abgelegt und serverseitig indexiert.

### C++-Mirror aktualisieren

```bash
python -m nova_school_server.reference_import_cpp --output ./data/reference_library/packs/cpp --clean --page-limit 1200 --asset-limit 400
```

### Weitere Referenz-Packs aktualisieren

Alle konfigurierten Web-Packs:

```bash
python -m nova_school_server.reference_import_web --all --clean
```

Einzelne Packs:

```bash
python -m nova_school_server.reference_import_web --pack javascript --clean
python -m nova_school_server.reference_import_web --pack java --clean
python -m nova_school_server.reference_import_web --pack rust --clean
python -m nova_school_server.reference_import_web --pack html-css --clean
python -m nova_school_server.reference_import_web --pack node-npm --clean
python -m nova_school_server.reference_import_web --pack web-frontend --clean
```

Nur Nachbearbeitung eines bereits vorhandenen Packs:

```bash
python -m nova_school_server.reference_import_web --pack rust --finalize-only
```

### Produktdokumentation materialisieren

```bash
python -m nova_school_server.nova_product_docs
```

## Remote Worker

Der Distributed Playground kann Services an Remote-Worker delegieren, statt sie im Hauptserverprozess auszufuehren.

Wichtige Betriebsparameter:

- `playground_dispatch_mode`
- `server_public_host`
- `runner_backend`

Worker-Start erfolgt ueber die mitgelieferten Startskripte und Umgebungsvariablen:

- `NOVA_SCHOOL_SERVER_URL`
- `NOVA_SCHOOL_WORKER_ID`
- `NOVA_SCHOOL_WORKER_TOKEN`
- `NOVA_SCHOOL_WORKER_HOST`

Anforderungen:

- Python auf dem Worker
- Docker oder Podman fuer Container-Backends
- verfuegbare Ports gemaess `topology.json`

## Release-Arten

Es gibt vier Release-Varianten:

- `source`
  - bereinigter Projektquellcode
- `distribution`
  - sauberes Serverpaket mit leerer `data/`-Struktur
- `windows-server-package`
  - distributionsbereinigtes Windows-Paket
- `linux-server-package`
  - distributionsbereinigtes Linux-Paket

### Distribution lokal bauen

```bash
python -m nova_school_server.distribution_builder . --output-dir .
```

### Plattformpakete lokal bauen

```bash
python -m nova_school_server.distribution_builder . --output-dir . --flavor windows-server-package
python -m nova_school_server.distribution_builder . --output-dir . --flavor linux-server-package
```

## Release-Notes und Changelog

`CHANGELOG.md` und Release-Notes werden aus Git-Tags und Commit-Historie erzeugt.

### Changelog erzeugen

```bash
python -m nova_school_server.release_notes .
```

### Release-Notes fuer ein Tag erzeugen

```bash
python -m nova_school_server.release_notes . --notes-tag v0.1.0 --notes-path ./release-notes-v0.1.0.md
```

Nach Installation des Projekts stehen auch CLI-Einstiege zur Verfuegung:

- `nova-school-build-distribution`
- `nova-school-build-release-notes`

## Tests

Windows:

```powershell
.\run_tests.ps1
```

Linux/macOS:

```bash
./run_tests.sh
```

Oder direkt:

```bash
python -m unittest
```

## Projektstruktur

- `nova_school_server/server.py`
  - HTTP-Server, API, Sessions und Admin-Endpunkte
- `nova_school_server/code_runner.py`
  - Sprachrunner, Scheduling, Containerausfuehrung
- `nova_school_server/realtime.py`
  - WebSockets, Live-Runs, Kollaboration
- `nova_school_server/workspace.py`
  - Workspaces, Projekte, Dateien, Notebooks
- `nova_school_server/curriculum.py`
  - Modullehrplaene, Pruefungen, Zertifikate
- `nova_school_server/reference_library.py`
  - Offline-Referenzbibliothek und Suchindex
- `nova_school_server/static/`
  - Frontend
- `docs/`
  - Produktdokumentation
- `wiki/`
  - rollenbezogene Bedienungsanleitungen
- `data/`
  - Laufzeitdaten, Caches, Workspaces und Spiegelungen

## Lizenz

Siehe [LICENSE](LICENSE).
