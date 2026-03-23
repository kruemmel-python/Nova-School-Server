# Distributed Playground

Der Distributed Playground ist der fortgeschrittene Bereich von Nova School für verteilte Systeme.

## Wofür er gedacht ist

Du kannst damit lernen:

- wie mehrere Services zusammenarbeiten
- wie Rollen wie Coordinator und Worker aufgebaut sind
- wie Logs und Service-Kommunikation beobachtet werden
- wie aus einem Projekt eine kleine Systemlandschaft wird

## Voraussetzung

Deine Lehrkraft oder Gruppe braucht die passende Freigabe. Besonders wichtig ist:

- `playground.manage`

Je nach Aufgabe kann zusätzlich `web.access` nötig sein.

## Zentrale Datei: `topology.json`

Der Playground liest die Topologie aus einer Datei namens `topology.json`.

Ein Service enthält mindestens:

- `name`
- `runtime`
- `entrypoint`

Optional:

- `port`
- `env`
- `kind`

## Unterstützte Service-Runtimes

- Python
- JavaScript oder Node
- Rust

## Beispielidee

```json
{
  "services": [
    {
      "name": "coordinator",
      "runtime": "python",
      "entrypoint": "services/coordinator.py",
      "port": 8100,
      "kind": "master"
    },
    {
      "name": "worker-a",
      "runtime": "rust",
      "entrypoint": "services/worker-a.rs",
      "kind": "worker"
    }
  ]
}
```

## Arbeiten mit dem Playground

Typischer Ablauf:

1. Projekt öffnen
2. `topology.json` prüfen
3. Service-Dateien bearbeiten
4. Playground starten
5. Logs und Verhalten beobachten
6. Änderungen machen und erneut testen

## Logs

Jeder Service schreibt eigene Logdaten. Das hilft dir bei:

- Fehlersuche
- Verstehen von Kommunikationsabläufen
- Testen von Startreihenfolgen
- Beobachten von Fehlern und Ausfällen

## Gute Lernfragen

- Was passiert, wenn ein Worker nicht startet?
- Wie reagiert der Coordinator auf fehlende Antworten?
- Wie ändern sich Logs und Verhalten, wenn ein Port oder Name falsch gesetzt ist?
- Wie kann man die Kommunikation robuster machen?

## Für wen dieses Modul gedacht ist

Der Playground ist kein Pflichtmodul für Einsteiger. Er ist besonders sinnvoll für:

- fortgeschrittene Schüler
- Wahlpflichtkurse
- Projektwochen
- Themen zu Netzwerken, Microservices und sicherer Kommunikation
