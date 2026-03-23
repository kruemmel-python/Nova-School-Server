# Editor, Dateien und Programmierung

In Nova School kannst du klassische Dateien und ganze Projekte direkt im Browser bearbeiten.

## Dateibereich

Links im Projekt siehst du die Projektdateien. Wenn du eine Datei anklickst, wird sie im Editor geladen.

Typische Dateitypen:

- `main.py`
- `index.html`
- `style.css`
- `main.js`
- `Cargo.toml`
- `Main.java`

## Arbeiten im Editor

Wichtige Aktionen:

| Aktion | Bedeutung |
| --- | --- |
| `Speichern` | speichert den aktuellen Dateiinhalt |
| `Datei ausführen` | startet die Datei einmalig |
| `Live ausführen` | startet eine interaktive Live-Session |
| `Vorschau` | öffnet HTML-Dateien oder Vorschaupfade im Browser |

## Speichern und Ausführen

Wichtig:

- `Speichern` speichert nur deinen Stand
- `Datei ausführen` startet den aktuellen Inhalt
- wenn du nach dem Speichern noch nicht neu gestartet hast, gilt die alte Ausgabe als veraltet

## Direkter Lauf oder Live-Lauf

### Direkter Lauf

Nutze ihn für:

- kurze Tests
- kleine Skripte
- Compiler- oder Interpreter-Feedback
- schnelle Rückmeldung ohne weitere Eingabe

### Live-Lauf

Nutze ihn für:

- Programme mit Eingaben
- längere Prozesse
- interaktive Konsolenprogramme
- Programme mit fortlaufender Ausgabe

## Programm-Eingabe

Unter dem Editor gibt es ein Feld für vorbereitete Eingaben.

Das ist sinnvoll für Programme mit:

- `input()` in Python
- `cin` in C++
- `Scanner` in Java
- `readline` oder ähnlichen Mustern

Beispiel:

```text
Ralf
```

Wenn dein Programm den Wert wirklich lesen soll, muss dein Code auch eine Eingabefunktion aufrufen.

## Unterstützte Sprachen

Welche Sprachen du wirklich nutzen darfst, hängt von deinen Rechten ab. Typischerweise unterstützt Nova School:

- Python
- JavaScript
- C++
- Java
- Rust
- HTML
- Node.js
- npm-basierte Webentwicklung

## HTML-Vorschau

Die Vorschau ist für Web-Projekte gedacht.

Typische Nutzung:

- `index.html` bearbeiten
- auf `Vorschau` klicken
- Ergebnis in neuem Fenster prüfen

## Offline-Dokumentation beim Programmieren

Im Dokumentationsbereich findest du Schnellstarts und Spickzettel, zum Beispiel für:

- Python
- JavaScript
- C++
- Java
- Rust
- HTML und CSS
- Node.js und npm
- Frontend-Entwicklung

## Python-Bibliotheken und GUI

Wenn dein Python-Projekt zusaetzliche Pakete benoetigt:

- lege eine `requirements.txt` in dein Projekt
- der Server installiert diese Pakete beim ersten erlaubten Lauf in einer isolierten Projektumgebung
- spaetere Laeufe nutzen den Server-Cache

Wichtig:

- wenn fuer dein Projekt kein Webzugriff freigegeben ist, muss die Lehrkraft die Pakete vorher einmal vorbereiten oder den ersten Lauf kurz freigeben

Bei Python-GUI-Projekten wie `tkinter` oder `turtle`:

- der Server kann solche Programme vorbereitet starten
- der normale Datei-Lauf zeigt dafuer aktuell eine GUI-Vorschau als Snapshot
- fuer echte Browseroberflaechen sind Webprojekte weiter der beste Weg

## Gute Arbeitsweise im Editor

- kleine Änderungen machen
- oft speichern
- Fehlermeldungen nicht ignorieren
- nicht mehrere Fehler gleichzeitig einbauen
- bei unklaren Fehlern zuerst den letzten funktionierenden Zustand verstehen
