# Playground, Reviews und Deployments

Dieses Modul deckt die drei fortgeschrittenen Bereiche des Systems ab, die für projektorientierten Unterricht und professionelle Abgabeprozesse besonders relevant sind.

## Distributed Playground

Der Distributed Playground ist für Unterricht zu verteilten Systemen, Service-Orchestrierung und Vertrauensbeziehungen gedacht.

### Grundprinzip

Ein Projekt beschreibt seine Service-Topologie in `topology.json`. Der Server orchestriert diese Services, dispatcht sie aber standardmaessig an Remote-Worker. Jeder Service enthält mindestens:

- `name`
- `runtime`
- `entrypoint`

Optional möglich:

- `port`
- `env`
- `kind`

### Unterstützte Runtimes

- Python
- JavaScript oder Node
- Rust

### Was der Server automatisch ergänzt

Beim Start des Playgrounds werden systemseitig Sicherheits- und Laufzeitobjekte aufgebaut:

- Certificate Authority für das Playground-Projekt
- Trust Policy für das Playground-Projekt
- Dispatch-Jobs pro Service
- Umgebungsvariablen für Service-Namen, Ports, URLs und Tenant-Kontext
- Worker-Zuordnung anhand registrierter Node-Capabilities

### Remote-Worker-Modell

- `playground_dispatch_mode=worker` ist der Standard
- der Server fuehrt Services nicht selbst aus
- Worker-Agenten claimen Jobs ueber `/api/worker/jobs/claim`
- Artefakte werden als ZIP-Payload an die Worker ausgeliefert
- Status, Logs und Stop-Requests laufen rueckwaerts ueber die Worker-API
- Worker-Requests sind signiert und gegen Replay geschuetzt
- Job-Payloads enthalten serverseitige Signaturen fuer die Worker-Verifikation

### Log-Orte

Lokale Legacy-Logs liegen bei explizitem `local`-Modus unter:

```text
.nova-school/playground/<service>.log
```

Remote-Dispatch-Artefakte liegen unter:

```text
data/worker_dispatch/jobs/<job_id>/
```

### Didaktische Einsatzformen

- Master-Worker-Modelle
- fehlertolerante Services
- sichere Service-Kommunikation
- Einführung in verteilte Architekturen

## Peer Review

Das Review-System ist anonymisiert und auditierbar.

### Ablauf

1. Schüler reicht Projekt ein.
2. Der Server erstellt einen Snapshot.
3. Reviewer werden zugewiesen.
4. Feedback wird strukturiert erfasst.
5. Analytics ergänzen die didaktische Bewertung.

### Wichtige Fakten

- Reviewer-Aliasse werden systemseitig erzeugt.
- Es gibt keine manuelle Alias-Verwaltung im Frontend.
- Die Einreichung enthält eine Vorschau auf den Snapshot.
- Lehrkräfte sehen zusätzlich aggregierte Analytics.

## Audit-basierte Analytics

Das System nutzt protokollierte Projektläufe, um Lernpfade sichtbar zu machen.

Wesentliche Kennzahlen:

- Anzahl der Runs
- Anzahl der Fehlversuche bis zum ersten Erfolg
- Erfolg ja oder nein

Diese Werte sollten als Prozessindikatoren und nicht als alleinige Leistungsbewertung verstanden werden.

## Shares und Exporte

Nova School unterstützt zwei Artefaktarten:

| Artefakt | Zweck |
| --- | --- |
| Share | öffentlich oder schulisch erreichbare Bereitstellung einer Web-App |
| Export | ZIP-Bundle zur Abgabe, Archivierung oder Weiterverwendung |

### Shares

Voraussetzung:

- Im Projektwurzelverzeichnis muss eine `index.html` existieren.

Ergebnis:

- URL im Format `/share/<artifact_id>/index.html`

### Exporte

Ergebnis:

- Download unter `/download/<artifact_id>`
- Source-Snapshot
- Laufzeithinweise in `README_EXPORT.txt`
- je nach Sprache optionale vorkompilierte Artefakte
- bei Build-Fehlern ein `BUILD_ERROR.txt`

## Quoten

Shares und Exporte unterliegen Tenant-Quoten. Relevant sind vor allem:

- `max_active_shares`
- `max_export_artifacts`

Administrativ bedeutet das:

- Quoten nicht zu knapp setzen, wenn Portfolio-Arbeit oder viele Web-Abgaben geplant sind
- Quoten regelmäßig aufräumen, wenn Artefakte nicht mehr gebraucht werden

## Empfohlene Praxis

- Für öffentliche Präsentationen nur bewusst freigegebene Web-Projekte teilen
- Für Bewertung und Archivierung Exporte bevorzugen
- Playground gezielt in fortgeschrittenen Modulen einsetzen, nicht als Default für Einsteigergruppen
