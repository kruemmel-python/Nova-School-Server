# Serverstart und Bootstrap

Dieses Dokument beschreibt den professionellen Erststart und den laufenden Startbetrieb des Nova School Servers auf Windows und Linux.

## Voraussetzungen

- Python `>= 3.12`
- Schreibzugriff auf `D:\Nova_school_server`
- Optional für interaktive PTY-Sessions auf Windows: Abhängigkeiten aus `requirements.txt`
- Optional für harte Laufzeitisolierung: Docker oder Podman
- Optional für KI-Hilfe: laufender LM-Studio-Server

## Startbefehle

### Windows

```powershell
cd D:\Nova_school_server
.\start_server.ps1
```

### Linux

```bash
cd /pfad/zu/Nova_school_server
./start_server.sh
```

## Standard-Endpunkt

- Host: `0.0.0.0`
- Port: `8877`
- Lokal: `http://127.0.0.1:8877`
- Im LAN: `http://<server-ip>:8877`

## Was beim ersten Start automatisch passiert

Beim Bootstrap werden zentrale Datenstrukturen, Inhalte und Demo-Daten angelegt:

- Datenordner unter `data/`
- Hauptdatenbank `data/school.db`
- Offline-Dokumentation unter `data/docs/`
- Profilordner für Benutzer und Gruppen
- Demo-Benutzer
- Demo-Gruppe
- Demo-Projekte

## Demo-Zugänge

| Rolle | Benutzername | Passwort |
| --- | --- | --- |
| Admin | `admin` | `NovaSchool!admin` |
| Lehrkraft | `teacher` | `NovaSchool!teacher` |
| Schüler | `student` | `NovaSchool!student` |

## Standard-Demodaten

- Gruppe: `class-1a`
- Persönliches Schülerprojekt: `Python Labor`
- Gruppenprojekt: `Web Labor`
- Lehrkraftprojekt: `Distributed Playground`

## Betriebsrelevante Einstellungen

Die Laufzeitkonfiguration kommt aus:

- `server_config.json` im Projektwurzelverzeichnis
- Umgebungsvariablen
- Standardwerten aus dem Server

Wichtige Parameter:

| Schlüssel | Standardwert | Bedeutung |
| --- | --- | --- |
| `host` | `0.0.0.0` | Bind-Adresse des HTTP-Servers für lokalen und LAN-Zugriff |
| `port` | `8877` | Port der Weboberfläche |
| `session_ttl_seconds` | `43200` | Sitzungsdauer in Sekunden |
| `run_timeout_seconds` | `20` | Timeout für einfache Dateiläufe |
| `live_run_timeout_seconds` | `300` | Timeout für Live- und PTY-Sessions |
| `tenant_id` | `nova-school` | Tenant-Kontext für Security Plane und Quoten |
| `school_name` | `Nova School Server` | Anzeigename in der Oberfläche |
| `nova_shell_path` | `H:\Nova-shell-main` | Read-only-Referenz auf NovaShell-Bausteine |

## LM Studio einbinden

Standardmäßig wird Folgendes vorbelegt:

- Base URL: `http://127.0.0.1:1234/v1`
- Modellname: leer, bis aktiv gesetzt

Empfehlung:

- LM Studio lokal auf dem Server hosten
- Base URL und Modell über das Admin-Panel speichern
- KI-Zugriff nur den Gruppen und Benutzern freigeben, die ihn didaktisch benötigen

## Runner-Backends

Nova School kennt zwei Betriebsarten:

| Backend | Beschreibung | Empfehlung |
| --- | --- | --- |
| `process` | Unsicherer Host-Prozess-Runner | Nur als ausdruecklicher Ausnahme-Fallback fuer Lehrkraft/Admin |
| `container` | Lauf in Docker oder Podman | Für Unterrichtsbetrieb und harte Isolation |

## Empfohlener Goldstandard-Betrieb

Für den schulischen Produktionseinsatz wird empfohlen:

1. `runner_backend = container`
2. `container_runtime = docker` oder `podman`
3. Container-Images je Sprache gepflegt halten
4. `web.access` nur gezielt freigeben
5. LM Studio lokal hosten und nicht offen ins Internet exponieren

## Typische Erstprüfung nach dem Start

1. Mit `admin` anmelden.
2. Im Admin-Bereich prüfen, ob Benutzer, Gruppe und Projekte vorhanden sind.
3. Im Einstellungsbereich Runner, Container-Runtime und LM-Studio-Base-URL kontrollieren.
4. Testprojekt starten.
5. Chat, Notebook, Review und Deployment-Artefakte einmal durchtesten.

## Häufige Betriebsprobleme

### Oberfläche lädt nicht

- Prüfen, ob der Serverprozess läuft.
- Prüfen, ob der Port `8877` bereits belegt ist.
- Prüfen, ob lokale Firewall-Regeln den Browserzugriff blockieren.
- Unter Windows prüfen, ob eingehende Verbindungen auf `8877` erlaubt sind.

### LM Studio antwortet nicht

- Läuft LM Studio auf dem Server?
- Stimmt die Base URL?
- Ist ein Modell geladen oder in der Konfiguration hinterlegt?
- Hat der Benutzer das Recht `ai.use`?

### Container-Läufe starten nicht

- Läuft Docker oder Podman wirklich?
- Stimmen Runtime-Name und Image-Tags?
- Sind Speicher- und CPU-Limits in einer realistischen Größenordnung gesetzt?

### PTY- oder Live-Terminal unter Windows fehlen

- `requirements.txt` installieren:

```powershell
py -3 -m pip install -r requirements.txt
```
