# Systembetrieb, Sicherheit und Workspaces

Dieses Dokument beschreibt die technische Betriebsbasis des Nova School Servers.

## Sicherheitsarchitektur

Nova School nutzt drei zentrale Bausteine aus NovaShell:

| Baustein | Zweck |
| --- | --- |
| `SecurityPlane` | Tenant-, Trust-, Zertifikats- und Sicherheitsobjekte |
| `ToolSandbox` | kontrollierte Laufumgebung für Werkzeuge und Runner |
| `NovaAIProviderRuntime` | Anbindung von LM Studio und KI-Modellen |

## Runner-Modi

### Host-Prozess-Modus

Vorteile:

- einfacher technischer Fallback fuer Wartung und Fehlersuche
- keine Abhaengigkeit von Docker oder Podman

Grenzen:

- unsicher fuer regulaeren Schuelerbetrieb
- keine harte OS-seitige Netztrennung pro Binary
- geringere Isolation im Vergleich zu Containern

Status:

- standardmaessig deaktiviert
- nur nach expliziter Freigabe
- nur fuer Lehrkraefte/Admin gedacht

### Container-Modus

Vorteile:

- harte Isolation auf Windows und Linux
- reproduzierbare Images je Sprache
- Speicher- und CPU-Limits direkt konfigurierbar
- `web.access` kann über den Netzwerkmodus des Containers wirksam kontrolliert werden

Empfehlung:

- produktiver Schulbetrieb immer bevorzugt im Container-Modus

## Verhalten von `web.access`

Im Container-Betrieb gilt:

- ohne `web.access`: Container startet mit isoliertem Netzwerk
- mit `web.access`: Container kann mit freigegebenem Netzwerkmodus laufen

Das ist der professionelle Weg, um Schülerprojekte gezielt online oder offline auszuführen.

## Container-Einstellungen

Im Admin-Panel werden folgende Werte gepflegt:

| Einstellung | Standard |
| --- | --- |
| `runner_backend` | `container` |
| `unsafe_process_backend_enabled` | `false` |
| `playground_dispatch_mode` | `worker` |
| `server_public_host` | leer, optional |
| `web_proxy_url` | leer, optional |
| `web_proxy_no_proxy` | leer, optional |
| `web_proxy_required` | `false` |
| `container_runtime` | `docker` |
| `container_oci_runtime` | leer, optional |
| `container_memory_limit` | `512m` |
| `container_cpu_limit` | `1.5` |
| `container_pids_limit` | `128` |
| `container_file_size_limit_kb` | `65536` |
| `container_nofile_limit` | `256` |
| `container_tmpfs_limit` | `64m` |
| `container_seccomp_enabled` | `true` |
| `container_seccomp_profile` | leer, optional |
| `container_image_python` | `python:3.12-slim` |
| `container_image_node` | `node:20-bookworm-slim` |
| `container_image_cpp` | `gcc:14` |
| `container_image_java` | `eclipse-temurin:21` |
| `container_image_rust` | `rust:1.81` |
| `scheduler_max_concurrent_global` | `4` |
| `scheduler_max_concurrent_student` | `1` |
| `scheduler_max_concurrent_teacher` | `2` |
| `scheduler_max_concurrent_admin` | `3` |

## Datenstruktur des Systems

Wichtige Verzeichnisse:

| Pfad | Bedeutung |
| --- | --- |
| `data/school.db` | Hauptdatenbank für Benutzer, Gruppen, Projekte, Chats, Runs, Reviews |
| `data/docs/` | Offline-Dokumentation |
| `data/workspaces/users/` | persönliche Arbeitsbereiche |
| `data/workspaces/groups/` | Gruppenarbeitsbereiche |
| `data/public_shares/` | veröffentlichte Share-Artefakte |
| `data/exports/` | ZIP-Exporte |
| `data/worker_dispatch/` | Dispatch-Jobs, Worker-Artefakte und Remote-Ausfuehrung |

## Offline-Referenzbibliothek professionell pflegen

Die Referenzbibliothek unter `/reference` sollte fuer Schueler nicht nur aus Schnellstarts bestehen, sondern aus lokal
gespiegelten Original- oder Primaerquellen. Fuer `cpp` ist der richtige Weg ein HTML-Mirror von `cppreference`, nicht
eine flache Markdown-Extraktion.

### C++-Mirror neu importieren

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_cpp --output D:\Nova_school_server\data\reference_library\packs\cpp --clean --page-limit 1200 --asset-limit 400
```

Danach den Server neu starten. Das Mirror wird unter `data/reference_library/packs/cpp/site/` abgelegt und in der
Offline-Referenzbibliothek automatisch als `mirrored` genutzt.

### Weitere Web-Referenzbereiche importieren

Fuer `javascript`, `java`, `rust`, `html-css`, `node-npm` und `web-frontend` steht ein generischer Mirror-Importer zur
Verfuegung. Er nutzt `wget`, spiegelt die Quellen lokal in die Pack-Ordner und erzeugt pro Bereich eine Landing-Page.

Alle konfigurierten Web-Packs:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --all --clean
```

Einzelner Bereich:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --pack javascript --clean
```

Wenn ein grosser Bereich bereits heruntergeladen wurde und nur noch lokal finalisiert werden soll:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.reference_import_web --pack rust --finalize-only
```

### Nova School als eigene Produktdokumentation pflegen

Der Bereich `nova-school` ist absichtlich kein externer Mirror. Er ist die offizielle Produktdokumentation des
Systems selbst.

Quellordner:

```text
docs/nova_school/
```

Materialisierter Referenz-Pack:

```text
data/reference_library/packs/nova-school/site/
```

Bei jeder Nutzung der Referenzbibliothek wird der lokale Pack automatisch neu aufgebaut, wenn sich die Quelldateien
geaendert haben. Fuer einen manuellen Neuaufbau:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.nova_product_docs
```

## Workspace-Struktur

### Persönlicher Arbeitsbereich

```text
data/workspaces/users/<username-slug>/projects/<projekt-slug>
```

### Gruppenarbeitsbereich

```text
data/workspaces/groups/<group-slug>/projects/<projekt-slug>
```

### Projektinterne Metadaten

```text
.nova-school/notebook.json
.nova-school/runs/
.nova-school/playground/
data/worker_dispatch/
```

Bedeutung:

- `notebook.json` enthält die Notebook-Zellen
- `runs/` enthält Laufartefakte und temporäre Ausführungsdaten
- `playground/` enthält servicebezogene Playground-Logs
- `data/worker_dispatch/` enthält die serverseitigen Dispatch-Artefakte fuer Remote-Worker

## Sichere Pfadauflösung

Der Workspace-Manager verhindert bewusst Pfad-Ausbrüche aus dem Projektwurzelverzeichnis. Direkte Manipulationen außerhalb des Projektpfads werden deshalb serverseitig blockiert.

## Materialisierung und Wiederherstellung von Projekten

Professionell empfohlen:

1. Projekte immer regulär über Oberfläche oder Serverlogik anlegen lassen.
2. Danach Inhalte innerhalb des Projektwurzelverzeichnisses pflegen.
3. Die `.nova-school`-Struktur nicht manuell löschen.

Wenn ein Projekt manuell wiederhergestellt werden muss:

- Projektwurzel vollständig zurückkopieren
- `.nova-school/notebook.json` erhalten oder wiederherstellen
- keine manuellen Bearbeitungen in `runs/` oder `playground/` vornehmen

## Live-Sync und Revisionen

Der Notebook-Live-Sync arbeitet mit Revisionsnummern. Diese dienen der Synchronisation zwischen Clients, nicht als vollständiges Versionsarchiv.

Praktische Konsequenz:

- Revisionen eignen sich zur Zustandsabstimmung im Live-Betrieb
- Revisionen ersetzen kein Git und keine dedizierte Dateiversionsverwaltung
- Wiederherstellung erfolgt derzeit eher über Exporte, Review-Snapshots und Dateisicherungen

## Windows- und Linux-Betrieb

### Windows

- PowerShell-Startskript vorhanden
- PTY-Unterstützung für interaktive Vollbild-Terminals vorgesehen
- `pywinpty` wird über `requirements.txt` eingebunden

### Linux

- Shell-Startskript vorhanden
- Containerbetrieb mit Docker oder Podman besonders geeignet
- PTY-Unterstützung für interaktive Sessions verfügbar

## Sicherheitsstand der Runner

Der Host-Prozess-Runner gilt als unsicherer Ausnahmebetrieb. Deshalb gilt jetzt:

- Standard-Backend: `container`
- Host-Prozess nur mit expliziter Admin-Freigabe
- Host-Prozess nur fuer Lehrkraefte/Admin gedacht
- Scheduler begrenzt gleichzeitige Ausfuehrungen global und pro Nutzer
- Container begrenzen Speicher, CPU, Datei- und FD-Nutzung und droppen Linux-Capabilities
- Container laufen mit read-only Root-FS und einer hostseitig materialisierten Run-Kopie ohne Live-Quell-Mount
- Seccomp-Denylist fuer gefaehrliche Kernel-/Tracing-/Namespace-Syscalls ist aktiv
- Symbolische Links und Junctions werden fuer Run-Workspaces und Worker-Dispatch abgewiesen
- Distributed Playground laeuft standardmaessig im Modus `worker`: Orchestrierung auf dem Server, Ausfuehrung auf Remote-Workern

## Python-Pakete und GUI-Projekte professionell betreiben

### Projektpakete mit `requirements.txt`

Wenn ein Python-Projekt zusaetzliche Bibliotheken benoetigt, liegt im Projektwurzelverzeichnis eine `requirements.txt`.

Nova School verhält sich dann so:

- Pakete werden nicht global auf dem Server installiert
- stattdessen werden sie in einen isolierten Projekt-Run-Pfad installiert
- erfolgreiche Installationen werden im Server-Cache abgelegt
- spaetere Laeufe desselben Paketstands koennen diesen Cache ohne erneute Downloads nutzen

Wichtig:

- fuer die erste Installation braucht der Lauf Webfreigabe oder einen bereits vorbereiteten Cache
- ohne Cache und ohne `web.access` wird die Installation bewusst verweigert

### Python-GUI-Projekte

Python-GUIs wie `tkinter`, `turtle`, `customtkinter`, `PyQt` oder `PySide` sind native Desktop-Oberflaechen.

Der Server unterstuetzt sie deshalb getrennt von normalen Konsolenlaeufen:

- fuer Containerlaeufe kann Nova School ein GUI-faehiges Python-Image mit `python3-tk` und virtueller Anzeige vorbereiten
- der normale Datei-Lauf erzeugt aktuell einen GUI-Snapshot als Vorschauartefakt
- fuer voll interaktive Desktop-Fenster im Browser waere zusaetzlich eine eigene GUI-Bridge noetig

Empfehlung fuer den Unterricht:

- Browseroberflaechen: HTML/CSS/JavaScript oder Frontend-Projekte
- Python-GUI-Demos: Datei-Lauf mit GUI-Snapshot
- komplexe native Desktop-Apps: nur mit bewusst vorbereiteter GUI-Infrastruktur einplanen

## Proxy- und OCI-Haertung

- `web_proxy_required=true` erzwingt, dass Webfreigaben nur zusammen mit `web_proxy_url` nutzbar sind
- `container_oci_runtime` erlaubt gehaertete Runtimes wie `runsc` oder `kata-runtime`
- das verbessert die Isolation deutlich, ersetzt aber keine vollstaendige MicroVM-Strategie von selbst

## Remote-Worker professionell betreiben

Fuer den Distributed Playground gilt jetzt:

- der Hauptserver erzeugt nur Dispatch-Jobs
- Worker-Rechner claimen Jobs ueber den Worker-Agenten
- Services laufen auf den Worker-Rechnern, nicht im HTTP-Server-Prozess

### Bootstrap-Ablauf

1. Worker ueber `POST /api/admin/workers/bootstrap` registrieren.
2. Bootstrap-Token sicher an den Zielrechner uebergeben.
3. Auf dem Worker `start_worker.ps1` oder `start_worker.sh` mit den Umgebungsvariablen starten.
4. Der Worker sendet Heartbeats und wird danach als `active` gefuehrt.

### Technische Mindestanforderungen

- Python auf jedem Worker-Rechner
- Docker oder Podman auf dem Worker, falls `runner_backend=container`
- erreichbarer `server_public_host`, falls der Server auf `0.0.0.0` bindet
- freie Ports gemaess `topology.json`

### Betriebsregel

- `playground_dispatch_mode=worker` fuer den regulaeren Betrieb verwenden
- `playground_dispatch_mode=local` nur fuer Wartung, Demo oder Fehlersuche verwenden
- Worker-Anfragen sind HMAC-signiert und gegen Nonce-Replay geschuetzt
- Fuer vollstaendige Transportabsicherung im Schulnetz bleibt TLS oder mTLS weiterhin die professionelle Zielstufe

Fuer den regulaeren Schuelerbetrieb sollte der Host-Prozess-Runner nicht aktiviert werden.

## Backup-Empfehlung

Mindestens regelmäßig sichern:

- `data/school.db`
- `data/workspaces/`
- `data/docs/`
- `data/exports/`
- `data/public_shares/`

## Betriebsrichtlinie für Schulen

- Unterrichtssysteme bevorzugt containerisiert betreiben
- Datenverzeichnis regelmäßig sichern
- Rechte und Quoten pro Halbjahr prüfen
- LM-Studio-Modelle und Container-Images versioniert pflegen
