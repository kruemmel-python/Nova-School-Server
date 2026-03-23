# Nova School Server

Nova School Server ist ein neues Projekt unter `D:\Nova_school_server` und nutzt zentrale Nova-shell-Bausteine aus `H:\Nova-shell-main` nur lesend:

- `SecurityPlane` fuer Session-Tokens und Secret-/Security-Status
- `ToolSandbox` fuer protokollierte Rechtefreigaben je Aktion
- `NovaAIProviderRuntime` fuer LM Studio als lokale Codehilfe

## Funktionen

- lokaler Schulserver mit Browser-UI
- Benutzer, Gruppen und gruppenbasierte Workspaces
- per User und Gruppe steuerbare Rechte fuer:
  - Webzugriff
  - LM Studio
  - Chat
  - Python, JavaScript, C++, Java, Rust, HTML, Node.js und npm
- persoenliche Profilordner und Gruppenordner
- Projekt-Templates fuer Python, JavaScript, C++, Java, Rust, HTML, Node.js und Frontend-Labs
- Datei-Editor plus notebook-aehnliche Code-Zellen
- Gruppen-/Projektchat mit Lehrer-Mute und Lehrerzugriff
- serverseitig abgelegte Offline-Dokumentation
- lokale Offline-Referenzbibliothek mit Suche fuer 9 Bereiche
- LM Studio als lokaler Codehelfer aus dem Editor
- sokratischer KI-Mentor mit projektspezifischem Verlauf
- kollaborative Notebooks mit WebSocket-Live-Sync, Presence und serverseitiger Konfliktauflösung
- Distributed Playground mit Worker-Enrollments, CA/Trust-Policy und startbaren Service-Topologien
- Peer-Review mit anonymisierten Reviewer-Aliassen, Snapshot-Einreichung und Audit-Analytics
- Share- und Export-Artefakte fuer Web- und Quellcode-Projekte
- interaktive Live-Runs mit Streaming fuer `stdout`/`stderr` und nachgelagerter `stdin`-Eingabe
- native PTY-/TTY-Sessions fuer Vollbild-Terminalprogramme mit Resize, Raw-Keys und ANSI-Rendering

## Start

Optional fuer Windows-PTY-Support:

```powershell
cd D:\Nova_school_server
py -3 -m pip install -r requirements.txt
```

```powershell
cd D:\Nova_school_server
.\start_server.ps1
```

Direkt per Python:

```powershell
cd D:\Nova_school_server
py -3 -m nova_school_server
```

Linux / macOS:

```bash
cd /path/to/Nova_school_server
./start_server.sh
```

Danach:

```text
lokal: http://127.0.0.1:8877
im Netzwerk: http://192.168.x.x:8877
```

Standardmäßig bindet der Server jetzt auf `0.0.0.0`, damit Clients im lokalen Netzwerk zugreifen können.

Wichtig unter Windows:

- Die Windows-Firewall muss eingehende Verbindungen auf Port `8877` zulassen.
- Falls der Zugriff aus dem LAN trotzdem scheitert, die Firewall-Regel oder das Netzwerkprofil des Adapters prüfen.

## Demo-Logins

- `admin / NovaSchool!admin`
- `teacher / NovaSchool!teacher`
- `student / NovaSchool!student`

Beim ersten Start werden Demo-Projekte angelegt:

- `student`: `Python Labor`
- `class-1a`: `Web Labor`
- `teacher`: `Distributed Playground`

## Offline-Referenzbibliothek

Neben den kurzen Schnellstart-Dokumenten gibt es jetzt eine eigene lokale Referenzbibliothek unter `/reference`.

Sie arbeitet in zwei Stufen:

- `starter`: vorhandene Schnellstart-Dokumente bleiben als lokaler Fallback sichtbar
- `mirrored`: offizielle oder primaere Referenzdateien werden lokal unter `data/reference_library/packs/<bereich>/site/` gespiegelt und danach ohne Webzugriff an die Clients ausgeliefert

Die Bibliothek ist serverseitig durchsuchbar und wird komplett lokal ausgeliefert. Schueler brauchen dafuer keinen externen Webzugriff.

### C++-Offline-Mirror aktualisieren

Die alte Markdown-Extraktion aus `cppreference` ist fuer den Unterricht nicht geeignet, weil sie Navigation, Tabellen,
Formatierung und Querverweise zerstoert. Fuer `cpp` wird deshalb ein echtes lokales HTML-Mirror von
`cppreference.com` verwendet.

Neuimport oder Aktualisierung:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_cpp --output D:\Nova_school_server\data\reference_library\packs\cpp --clean --page-limit 1200 --asset-limit 400
```

Danach:

```powershell
cd D:\Nova_school_server
.\start_server.ps1
```

Das Mirror liegt dann unter `data/reference_library/packs/cpp/site/` und wird in `/reference?area=cpp` automatisch als
`mirrored` verwendet.

### Weitere Web-Referenz-Packs aktualisieren

Fuer die weiteren Referenzbereiche gibt es einen generischen HTML-Mirror-Importer auf Basis von `wget`. Er spiegelt
offizielle oder primaere Dokumentationsseiten lokal in die jeweiligen Pack-Ordner und erzeugt eine Landing-Page pro
Bereich.

Alle konfigurierten Web-Packs neu importieren:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --all --clean
```

Einzelne Bereiche:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --pack javascript --clean
python -m nova_school_server.reference_import_web --pack java --clean
python -m nova_school_server.reference_import_web --pack rust --clean
python -m nova_school_server.reference_import_web --pack html-css --clean
python -m nova_school_server.reference_import_web --pack node-npm --clean
python -m nova_school_server.reference_import_web --pack web-frontend --clean
```

Wenn ein sehr grosser Bereich bereits heruntergeladen wurde und nur noch nachbearbeitet werden soll:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --pack rust --finalize-only
```

### Nova-School-Produktdokumentation materialisieren

Der Bereich `nova-school` in der Offline-Referenzbibliothek ist keine gespiegelte Fremdquelle, sondern eine eigene
First-Party-Produktdokumentation. Die Quellen liegen unter `docs/nova_school/` und werden automatisch in den lokalen
Referenz-Pack unter `data/reference_library/packs/nova-school/site/` materialisiert.

Manueller Neuaufbau:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.nova_product_docs
```

## Goldstandard-Module

### 1. Sokratischer KI-Mentor

- Editor-Reiter "LM Studio Codehilfe" mit Modus `Direkte Hilfe` oder `Sokratischer Mentor`
- speichert projektbezogene Mentor-Verlaeufe
- bezieht Dateiinhalt und letzte Lauf-Ausgabe in den Prompt ein
- Lehrkraefte koennen Mentor-Verlaeufe fachlich nachvollziehen

### 2. Distributed Playground

- basiert auf `topology.json`
- dispatcht Services standardmaessig an registrierte Remote-Worker
- der Hauptserver orchestriert nur noch Jobs, Artefakte und Status
- die Worker fuehren Services lokal auf ihren eigenen Hosts aus
- legt fuer jedes Playground-Projekt eigene CA- und Trust-Policy-Eintraege an
- nutzt NovaShell-Worker-Enrollments als sichtbare Sicherheits- und Orchestrierungsschicht

### 3. Kollaborative Notebooks

- Live-Sync primär ueber WebSocket, mit REST-Fallback
- serverseitige Merge-Logik pro Zelle
- gemeinsames Arbeiten an Notebook-Zellen ohne manuelle Datei-Sperren

### Live-Programme ausfuehren

- `Datei ausfuehren` bleibt der direkte Einmal-Lauf
- `Live ausfuehren` startet eine interaktive Session ueber WebSocket
- `Eingabe senden` schreibt waehrend der Laufzeit auf `stdin`
- `Session beenden` stoppt den laufenden Prozess
- Notebook-Zellen besitzen dieselben Live-Aktionen direkt an der Zelle
- ANSI-Farben, Cursorbewegungen, `\r`-Ueberschreiben und typische Prompt-Muster werden im Browser terminalartig dargestellt
- Vollbild-Terminalprogramme nutzen PTY/ConPTY unter Linux/macOS nativ und unter Windows bevorzugt `pywinpty` mit Low-Level-Fallback
- Browser-Terminals senden Raw-Keys, Paste und Resize-Ereignisse ueber WebSocket an Datei- und Notebook-Sessions
- Standard-Live-Timeout: 300 Sekunden, konfigurierbar ueber `NOVA_SCHOOL_LIVE_RUN_TIMEOUT`

### 4. Peer Review und Audit

- Projekt einreichen direkt aus der UI
- Snapshot der Einreichung wird eingefroren
- Reviewer erhalten anonymisierte Aliasse
- Audit-Analytics zeigen Runs und Fehler-vor-Erfolg

### 5. Share und Export

- `Public Share` fuer Webprojekte mit `index.html`
- `Export` als ZIP-Bundle mit Start-Hinweisen
- bei nativen Sprachen optional vorkompilierte Artefakte, wenn Toolchains lokal verfuegbar sind

## Tests

```powershell
cd D:\Nova_school_server
.\run_tests.ps1
```

Linux / macOS:

```bash
cd /path/to/Nova_school_server
./run_tests.sh
```

## Hinweise zur Isolation

Das Projekt unterstuetzt jetzt zwei Runner-Modi:

- `container`: Ausfuehrung ueber Docker oder Podman mit Image je Sprache
- `process`: unsicherer Host-Fallback, standardmaessig deaktiviert

Standard ist jetzt `container`. Der Host-Prozess-Modus darf nur noch ausdruecklich fuer Lehrkraft/Admin als
unsicherer Fallback freigegeben werden. Im Container-Modus gilt:

- ohne Recht `web.access` startet der Lauf hart mit `--network none`
- mit Recht `web.access` startet der Lauf mit `--network bridge`
- RAM-, CPU-, PID- und Sprach-Images sind serverseitig einstellbar
- read-only Root-FS plus hostseitig materialisierter Run-Workspace ohne Live-Quell-Mount
- `cap-drop ALL`, `no-new-privileges`, `seccomp`-Denylist und `ulimit` fuer Datei- und FD-Grenzen sind aktiv
- ein Run-Scheduler begrenzt gleichzeitige Ausfuehrungen global und pro Nutzerrolle
- symbolische Links und Junctions werden fuer Run-Workspaces bewusst abgewiesen

Optional kann fuer freigegebene Web-Sessions ein Proxy-Pfad gesetzt werden:

- `web_proxy_url`
- `web_proxy_no_proxy`
- `web_proxy_required`

Optional kann ausserdem eine gehaertete OCI-Runtime konfiguriert werden:

- `container_oci_runtime`, z. B. `runsc` oder `kata-runtime`

Wichtig: Das verbessert die Netzsteuerung fuer HTTP-/HTTPS-faehige Tools deutlich, ersetzt aber keine echte
Firewall- oder Egress-Proxy-Erzwingung fuer rohe Sockets. Wenn `web_proxy_required=true` gesetzt ist, verweigert
Nova School Web-Runs ohne konfigurierten Proxy serverseitig.

Das ist die vorgesehene Haertungsoption fuer Windows und Linux:

- Windows: typischerweise Docker Desktop mit Linux-Containern
- Linux: Docker oder Podman

Wichtig:

- fuer echte Containerlaeufe muss die gewaehlte Runtime installiert und gestartet sein
- Standardimages muessen lokal vorhanden sein oder einmalig geladen werden
- HTML bleibt eine lokale Vorschau und wird nicht in einem Container gerendert
- der Host-Prozess-Modus ist nur fuer ausdrueckliche Ausnahmefaelle gedacht und nicht fuer regulaeren Schuelerbetrieb

### Python-Abhaengigkeiten und GUI-Projekte

Python-Projekte koennen jetzt ein projektlokales `requirements.txt` im Projektwurzelverzeichnis mitbringen.

Verhalten:

- beim ersten Lauf installiert der Server die Pakete in einen isolierten Projekt-Run-Pfad
- danach werden sie im Server-Cache wiederverwendet
- ohne `web.access` funktioniert die Erstinstallation nur, wenn der Cache bereits vorhanden ist
- die Installation erfolgt nicht global auf dem Host, sondern nur isoliert fuer den jeweiligen Projektlauf

Wichtig fuer Python-GUI:

- `tkinter`, `turtle`, `customtkinter`, `PyQt`, `PySide` und aehnliche Desktop-GUIs sind nicht dasselbe wie Browser-UIs
- fuer Containerlaeufe bereitet Nova School bei Bedarf ein GUI-faehiges Python-Image mit virtueller Anzeige vor
- der normale Dateilauf nutzt dafuer aktuell einen GUI-Snapshot-Modus und speichert eine Vorschau unter den Run-Artefakten
- eine voll interaktive Desktop-Fensterspiegelung in den Browser ist damit noch nicht ersetzt

Wenn ihr die bereits in NovaShell genutzte Mesh-/Blob-Logik spaeter als Transport- oder Executor-Schicht nutzen wollt, kann der Container-Runner darauf aufsetzen. Im aktuellen Projekt laeuft die Container-Isolation lokal ueber Docker/Podman, ohne Veraenderungen an `H:\Nova-shell-main`.

## Remote Worker fuer den Distributed Playground

Der Distributed Playground laeuft jetzt standardmaessig im Modus `worker`. Das bedeutet:

- der Schulserver erstellt Dispatch-Jobs
- Remote-Worker claimen diese Jobs ueber HTTP
- die Services laufen auf den Worker-Rechnern, nicht im Serverprozess
- Worker-Requests sind HMAC-signiert und nonce-/timestamp-gebunden
- Job-Payloads sind signiert und koennen vom Worker vor der Ausfuehrung verifiziert werden

### Wichtige Einstellungen

- `playground_dispatch_mode`: `worker` oder explizit `local`
- `server_public_host`: optionaler externer Hostname/IP fuer Worker-Bootstrap
- `runner_backend`: `container` oder unsicherer Fallback `process`

### Worker bootstrapen

1. Admin erstellt einen Worker-Bootstrap ueber `POST /api/admin/workers/bootstrap`.
2. Der Server liefert `server_url`, `worker_id` und ein einmalig angezeigtes Token.
3. Auf dem Worker-Rechner den Agenten starten.

Windows:

```powershell
cd D:\Nova_school_server
$env:NOVA_SCHOOL_SERVER_URL = "http://192.168.178.62:8877"
$env:NOVA_SCHOOL_WORKER_ID = "lab-node-01"
$env:NOVA_SCHOOL_WORKER_TOKEN = "<bootstrap-token>"
$env:NOVA_SCHOOL_WORKER_HOST = "192.168.178.81"
.\start_worker.ps1
```

Linux:

```bash
cd /path/to/Nova_school_server
export NOVA_SCHOOL_SERVER_URL="http://192.168.178.62:8877"
export NOVA_SCHOOL_WORKER_ID="lab-node-01"
export NOVA_SCHOOL_WORKER_TOKEN="<bootstrap-token>"
export NOVA_SCHOOL_WORKER_HOST="192.168.178.81"
./start_worker.sh
```

### Anforderungen an Worker

- Python muss installiert sein
- fuer Container-Backends muss Docker oder Podman lokal auf dem Worker laufen
- die in `topology.json` definierten Ports muessen auf dem Worker nutzbar sein
- Playground-Services sollten an `NOVA_PLAYGROUND_BIND_HOST` binden und nicht hart auf `127.0.0.1`

## Struktur

- `nova_school_server/server.py`: HTTP-Server und API
- `nova_school_server/code_runner.py`: Runner fuer Sprachen und npm mit Host- und Container-Backend
- `nova_school_server/workspace.py`: Profilordner, Projekte, Dateien, Notebooks
- `nova_school_server/static/`: Weboberflaeche
- `data/docs/`: serverlokale Offline-Dokumentation
- `data/workspaces/`: User- und Gruppenordner
