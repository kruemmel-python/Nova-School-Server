# Editor, Notebooks und Live-Terminal

Der Editor ist das operative Zentrum fuer Schueler und Lehrkraefte. Dateien, Notebook-Zellen, Vorschau, Chat und Laufzeitsteuerung greifen hier ineinander.

## Dateieditor

- Dateien lassen sich anlegen, oeffnen, bearbeiten und speichern.
- `Datei ausfuehren` startet den aktuellen Dateilauf.
- `Vorschau` ist fuer HTML- und Webprojekte vorgesehen.
- Alte Ausgaben werden markiert, wenn der Editorinhalt geaendert wurde, aber noch kein neuer Lauf stattgefunden hat.

## Notebook-Zellen

Notebook-Zellen eignen sich fuer kurze Experimente, Erklaerschritte und inkrementelles Arbeiten.

1. Zelle anlegen.
2. Sprache waehlen.
3. Code schreiben.
4. Direkt ausfuehren oder als Live-Session starten.
5. Ergebnis in der Zell-Ausgabe lesen.

## Programmeingabe und Live-Input

Nova School unterstuetzt zwei Formen von Eingabe:

- **Vorbereitete Eingabe:** Text wird beim Start auf `stdin` gelegt.
- **Live-Eingabe:** waehrend einer laufenden Session kann weitere Eingabe gesendet werden.

Beispiel:

```python
name = input("Name: ")
print(f"Hallo {name}!")
```

## Live-Terminal und PTY

Fuer interaktive Programme stellt Nova School ein terminalartiges Frontend bereit:

- ANSI-Farben werden gerendert.
- Prompt-Zustaende werden erkennbar.
- Cursor- und Fullscreen-Verhalten werden fuer PTY-faehige Programme unterstuetzt.
- Windows und Linux koennen dafuer jeweils ihre passende PTY-Schicht nutzen.

## Kollaborative Notebooks

Notebook-Zellen koennen gemeinsam bearbeitet werden. Dabei sind vor allem drei Dinge wichtig:

- Zellinhalte synchronisieren ueber den Kollaborationskanal.
- Ausgaben bleiben pro Zelle getrennt.
- Praesenz macht sichtbar, wer gerade am Projekt arbeitet.

## Praktische Regeln

- `Speichern` speichert nur, startet aber keinen Lauf.
- Datei-Live-Sessions und Notebook-Live-Sessions sind getrennte Prozesse.
- Eingabefelder wirken nur, wenn das Programm wirklich von `stdin` liest.
- Fuer reproduzierbare Unterrichtssituationen zuerst speichern, dann ausfuehren.
