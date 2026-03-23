# Notebooks, Live-Terminal und Kollaboration

Nova School verbindet klassische Dateien mit Notebook-Zellen und interaktiven Live-Terminals.

## Notebook-Zellen

Unter dem Dateieditor kannst du Notebook-Zellen verwenden.

Typische Aktionen:

| Aktion | Bedeutung |
| --- | --- |
| `Zelle hinzufügen` | neue Notebook-Zelle anlegen |
| `Notebook speichern` | aktuellen Notebook-Zustand sichern |
| `Ausführen` | Zelle einmalig starten |
| `Live` | interaktive Live-Session für genau diese Zelle starten |
| `Eingabe senden` | Text an eine laufende Zelle schicken |
| `Stoppen` | laufende Zell-Session beenden |

## Datei-Lauf und Zell-Lauf sind getrennt

Das ist wichtig:

- `Datei ausführen` startet die Hauptdatei im Editor
- `Ausführen` in einer Zelle startet nur diese Zelle
- jede Live-Zelle hat ihre eigene Session
- Ausgaben werden nicht zwischen Datei und Zelle vermischt

## Live-Terminal

Im Live-Modus verhält sich die Ausgabe wie ein echtes Terminal.

Das bedeutet:

- fortlaufende Ausgabe wird direkt angezeigt
- Eingaben können während der Laufzeit gesendet werden
- ANSI-Farben werden dargestellt
- Wagenrücklauf und Cursor-Bewegungen werden verarbeitet
- interaktive Programme und Vollbild-Terminals werden unterstützt

## Woran du erkennst, dass dein Programm auf Eingabe wartet

Im Live-Modus zeigt Nova School den Status entsprechend an. Wenn dein Programm sichtbar auf eine Eingabe wartet:

- Text in das Eingabefeld schreiben
- auf `Eingabe senden` klicken

## Wann du Live statt Direktlauf nutzen solltest

Nutze `Live`, wenn dein Programm:

- mehrere Eingaben nacheinander braucht
- lange läuft
- ein Menü oder Prompt anzeigt
- mit Terminal-Farben arbeitet
- interaktiv ist

## Kollaboration im Notebook

Wenn deine Rechte `notebook.collaborate` enthalten, arbeitet das Notebook mit Live-Sync.

Du siehst dann:

- einen Status mit Revisionsnummer
- Presence-Chips mit Namen und Rollen
- oft auch, an welcher Zelle andere Personen gerade arbeiten

## Bedeutung der Presence-Chips

Presence-Chips zeigen, wer im Projekt aktiv ist. Sie helfen bei:

- Gruppenarbeit
- Pair Programming
- Live-Unterricht
- Abstimmung, wer gerade welche Zelle bearbeitet

## Wichtig zu Revisionen

Die Revisionsnummer zeigt den aktuellen Synchronisationsstand des Notebooks. Sie ist nützlich für Live-Zusammenarbeit, aber:

- sie ist kein Git
- sie ist keine vollständige Versionshistorie
- sie ersetzt keine saubere Dateisicherung

## Gute Zusammenarbeit im Live-Notebook

- sprecht euch ab, wer welche Zelle bearbeitet
- arbeitet in kleinen, klaren Schritten
- speichert das Notebook regelmäßig
- nutzt den Chat, wenn mehrere Personen parallel testen
- startet nicht gleichzeitig widersprüchliche Änderungen in derselben Zelle
