from __future__ import annotations

from typing import Any


def _single(question_id: str, prompt: str, options: list[tuple[str, str]], correct: str, explanation: str, *, points: int = 1) -> dict[str, Any]:
    return {
        "id": question_id,
        "type": "single",
        "prompt": prompt,
        "options": [{"id": option_id, "label": label} for option_id, label in options],
        "correct": [correct],
        "points": points,
        "explanation": explanation,
    }


def _multi(question_id: str, prompt: str, options: list[tuple[str, str]], correct: list[str], explanation: str, *, points: int = 2) -> dict[str, Any]:
    return {
        "id": question_id,
        "type": "multi",
        "prompt": prompt,
        "options": [{"id": option_id, "label": label} for option_id, label in options],
        "correct": list(correct),
        "points": points,
        "explanation": explanation,
    }


def _text(question_id: str, prompt: str, accepted: list[str], explanation: str, *, points: int = 2, placeholder: str = "") -> dict[str, Any]:
    return {
        "id": question_id,
        "type": "text",
        "prompt": prompt,
        "accepted": list(accepted),
        "points": points,
        "explanation": explanation,
        "placeholder": placeholder,
    }


COURSE_CATALOG: dict[str, dict[str, Any]] = {
    "python-grundlagen": {
        "course_id": "python-grundlagen",
        "title": "Python Grundlagen",
        "subtitle": "Modullehrplan fuer einen strukturierten Einstieg in die Programmierung",
        "summary": "Vom ersten Quelltext bis zu Funktionen, Dateien, OOP und Datenvisualisierung.",
        "audience": "Schulunterricht Informatik, Einstieg bis mittleres Niveau",
        "estimated_hours": 18,
        "certificate_title": "Nova School Zertifikat Python Grundlagen",
        "pass_ratio": 0.7,
        "final_pass_ratio": 0.75,
        "modules": [
            {
                "module_id": "m01_einstieg_python",
                "title": "Einfuhrung in Python und Programmieren",
                "estimated_minutes": 35,
                "objectives": [
                    "den Unterschied zwischen Quelltext, Interpreter und Maschinencode erklaeren",
                    "erste Ausgaben mit print() verstehen",
                    "die Idee von Input und Output in Python einordnen",
                ],
                "lesson_markdown": """
## Worum geht es?

Programmieren bedeutet, einem Computer eindeutige Anweisungen zu geben. In Python schreibst du Quelltext,
der von einem Interpreter Schritt fuer Schritt ausgefuehrt wird.

## Merksaetze

- **Quelltext** ist der von Menschen geschriebene Programmcode.
- Ein **Interpreter** fuehrt den Code direkt aus.
- **Input** sind Eingaben, **Output** sind Ausgaben.
- `print()` zeigt Informationen an.

## Unterrichtsbezug

Im Nova School Server installierst du Python nicht lokal auf jedem Geraet. Stattdessen laeuft Python zentral
auf dem Schulserver und wird im Browser genutzt.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m01_q1",
                        "Welche Aussage beschreibt Python in diesem Kurs am besten?",
                        [("a", "Python ist nur ein Compiler."), ("b", "Python wird im Unterricht ueber einen Interpreter ausgefuehrt."), ("c", "Python ist eine Tabellenkalkulation."), ("d", "Python ist nur fuer Webdesign gedacht.")],
                        "b",
                        "Python-Code wird hier interpretiert und schrittweise ausgefuehrt.",
                    ),
                    _single(
                        "m01_q2",
                        "Was macht `print('Hallo Welt')`?",
                        [("a", "Es beendet Python."), ("b", "Es speichert eine Datei."), ("c", "Es gibt Text aus."), ("d", "Es importiert ein Modul.")],
                        "c",
                        "`print()` erzeugt eine Ausgabe.",
                    ),
                    _text(
                        "m01_q3",
                        "Welcher Begriff bezeichnet den von Menschen geschriebenen Programmcode?",
                        ["quelltext"],
                        "Der von Menschen geschriebene Code heisst Quelltext.",
                        placeholder="Begriff eingeben",
                    ),
                ],
            },
            {
                "module_id": "m02_shell_datentypen_variablen",
                "title": "Python-Shell, Datentypen und Variablen",
                "estimated_minutes": 45,
                "objectives": [
                    "arithmetische Operatoren und Operatorenrangfolge anwenden",
                    "Integer, Float und String unterscheiden",
                    "Variablen sinnvoll benennen und mit type() pruefen",
                ],
                "lesson_markdown": """
## Kernideen

- Zahlen koennen `int` oder `float` sein.
- Texte sind `str`.
- Variablen speichern Werte und koennen ueberschrieben werden.
- Gute Variablennamen helfen beim Lesen.

## Beispiel

```python
preis = 3.5
anzahl = 4
gesamt = preis * anzahl
print(type(gesamt))
```

`type()` zeigt den Datentyp eines Werts oder einer Variablen.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m02_q1",
                        "Welcher Datentyp beschreibt `3.14`?",
                        [("a", "int"), ("b", "float"), ("c", "str"), ("d", "bool")],
                        "b",
                        "`3.14` ist eine Gleitkommazahl und damit ein `float`.",
                    ),
                    _single(
                        "m02_q2",
                        "Was ist ein guter Variablenname nach PEP-8?",
                        [("a", "PreisProArtikel"), ("b", "preis_pro_artikel"), ("c", "preis-pro-artikel"), ("d", "2preis")],
                        "b",
                        "Kleine Buchstaben mit Unterstrichen sind die uebliche Konvention.",
                    ),
                    _text(
                        "m02_q3",
                        "Welche Funktion zeigt den Datentyp einer Variablen an?",
                        ["type", "type()"],
                        "`type()` prueft den Datentyp.",
                        placeholder="Funktionsname",
                    ),
                ],
            },
            {
                "module_id": "m03_listen_und_sequenzen",
                "title": "Listen, Indexierung, Slicing und Tuple",
                "estimated_minutes": 45,
                "objectives": [
                    "auf Listenelemente per Index zugreifen",
                    "Listen mit heterogenen Datentypen verstehen",
                    "Slicing und len() richtig einsetzen",
                ],
                "lesson_markdown": """
## Listen

Listen speichern mehrere Werte in einer Reihenfolge.

```python
werte = [4, "Apfel", 2.5]
print(werte[0])
print(len(werte))
```

## Wichtig

- Der erste Index ist `0`.
- Mit `len()` bestimmst du die Laenge.
- Mit Slicing waehlt man Teilbereiche, zum Beispiel `werte[1:3]`.
- Ein Tuple ist aehnlich wie eine Liste, aber unveraenderlich.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m03_q1",
                        "Welchen Wert liefert `liste[0]`?",
                        [("a", "Das letzte Element"), ("b", "Die Laenge der Liste"), ("c", "Das erste Element"), ("d", "Den Datentyp der Liste")],
                        "c",
                        "Index `0` bezeichnet das erste Element.",
                    ),
                    _single(
                        "m03_q2",
                        "Was liefert `len([10, 20, 30])`?",
                        [("a", "2"), ("b", "3"), ("c", "30"), ("d", "0")],
                        "b",
                        "Die Liste enthaelt drei Elemente.",
                    ),
                    _text(
                        "m03_q3",
                        "Welchen Slice-Ausdruck nutzt du, um bei `liste = [1,2,3,4]` die Werte `[2,3]` zu erhalten?",
                        ["liste[1:3]", "[1:3]"],
                        "Der Bereich startet bei Index 1 und endet vor Index 3.",
                        placeholder="z. B. liste[1:3]",
                    ),
                ],
            },
            {
                "module_id": "m04_logik_und_verzweigungen",
                "title": "Boolesche Logik und if-Verzweigungen",
                "estimated_minutes": 40,
                "objectives": [
                    "Boolesche Werte und Vergleichsoperatoren lesen",
                    "if, elif und else sinnvoll einsetzen",
                    "einfache Aussagenlogik anwenden",
                ],
                "lesson_markdown": """
## Vergleich und Entscheidung

Programme treffen Entscheidungen mit Bedingungen.

```python
alter = 14
if alter >= 14:
    print("Zugang erlaubt")
else:
    print("Noch nicht")
```

`True` und `False` sind boolesche Werte. Mit `and`, `or` und `not` kombinierst du Bedingungen.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m04_q1",
                        "Welcher Operator prueft auf Gleichheit?",
                        [("a", "="), ("b", "=="), ("c", "=>"), ("d", "!=")],
                        "b",
                        "`==` vergleicht zwei Werte.",
                    ),
                    _multi(
                        "m04_q2",
                        "Welche Werte sind boolesch?",
                        [("a", "True"), ("b", "False"), ("c", "\"Hallo\""), ("d", "7")],
                        ["a", "b"],
                        "`True` und `False` sind boolesche Werte.",
                    ),
                    _text(
                        "m04_q3",
                        "Welches Schluesselwort nutzt du in Python fuer den Alternativfall einer Bedingung?",
                        ["else"],
                        "Der Alternativfall wird mit `else` formuliert.",
                        placeholder="Schluesselwort",
                    ),
                ],
            },
            {
                "module_id": "m05_schleifen",
                "title": "for-, while- und verschachtelte Schleifen",
                "estimated_minutes": 45,
                "objectives": [
                    "for- und while-Schleifen unterscheiden",
                    "break und continue passend nutzen",
                    "einfache Verschachtelungen lesen",
                ],
                "lesson_markdown": """
## Wiederholungen

Mit Schleifen fuehrt Python Anweisungen mehrfach aus.

```python
for zahl in [1, 2, 3]:
    print(zahl)
```

```python
zaehler = 0
while zaehler < 3:
    print(zaehler)
    zaehler += 1
```

`break` beendet eine Schleife, `continue` springt zum naechsten Durchlauf.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m05_q1",
                        "Welche Schleife eignet sich besonders gut fuer alle Elemente einer Liste?",
                        [("a", "for"), ("b", "while"), ("c", "if"), ("d", "def")],
                        "a",
                        "Eine `for`-Schleife passt gut zu Listen.",
                    ),
                    _single(
                        "m05_q2",
                        "Was macht `break`?",
                        [("a", "Es startet die Schleife neu."), ("b", "Es beendet die Schleife."), ("c", "Es ueberspringt die Schleife immer."), ("d", "Es loescht die Variable.")],
                        "b",
                        "`break` beendet die aktuelle Schleife sofort.",
                    ),
                    _text(
                        "m05_q3",
                        "Welches Schluesselwort springt direkt zum naechsten Schleifendurchlauf?",
                        ["continue"],
                        "`continue` setzt mit dem naechsten Durchlauf fort.",
                        placeholder="Schluesselwort",
                    ),
                ],
            },
            {
                "module_id": "m06_funktionen_grundlagen",
                "title": "Funktionen, Parameter, return und Built-ins",
                "estimated_minutes": 50,
                "objectives": [
                    "eigene Funktionen mit Parametern definieren",
                    "return-Werte verstehen",
                    "built-in-Funktionen und String-Methoden anwenden",
                ],
                "lesson_markdown": """
## Funktionen

Funktionen fassen wiederverwendbare Anweisungen zusammen.

```python
def begruesse(name: str) -> str:
    return f"Hallo {name}"
```

## Wichtig

- Parameter nehmen Eingaben entgegen.
- `return` gibt ein Ergebnis zurueck.
- `len()`, `type()` oder `print()` sind built-in-Funktionen.
- Methoden gehoeren zu einem Datentyp, z. B. `"hallo".upper()`.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m06_q1",
                        "Wofuer steht `return` in einer Funktion?",
                        [("a", "Es wiederholt die Funktion."), ("b", "Es beendet die Funktion und gibt ein Ergebnis zurueck."), ("c", "Es importiert ein Modul."), ("d", "Es startet eine Schleife.")],
                        "b",
                        "`return` gibt das Ergebnis der Funktion zurueck.",
                    ),
                    _single(
                        "m06_q2",
                        "Was ist an `\"hallo\".upper()` richtig?",
                        [("a", "Es ist eine Schleife."), ("b", "Es ist eine Methode fuer Strings."), ("c", "Es ist ein Modul."), ("d", "Es ist ein Vergleichsoperator.")],
                        "b",
                        "`upper()` ist eine typspezifische String-Methode.",
                    ),
                    _text(
                        "m06_q3",
                        "Mit welchem Schluesselwort definierst du in Python eine Funktion?",
                        ["def"],
                        "Funktionen beginnen mit `def`.",
                        placeholder="Schluesselwort",
                    ),
                ],
            },
            {
                "module_id": "m07_erweiterte_datentypen_und_funktionen",
                "title": "Sets, Dictionaries und erweiterte Funktionen",
                "estimated_minutes": 55,
                "objectives": [
                    "Sets und Dictionaries voneinander unterscheiden",
                    "optionale, benannte und variable Parameter einordnen",
                    "Lambda und Rekursion auf Grundniveau verstehen",
                ],
                "lesson_markdown": """
## Datenstrukturen

- **Set**: ungeordnete Menge ohne doppelte Eintraege
- **Dictionary**: Zuordnung von Schluessel zu Wert

```python
punkte = {"Anna": 12, "Ben": 9}
```

## Erweiterte Funktionen

- benannte Parameter verbessern Lesbarkeit
- optionale Parameter nutzen Default-Werte
- `*args` sammelt variable Positionsparameter
- Lambdas sind kurze anonyme Funktionen
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m07_q1",
                        "Welche Struktur ordnet Schluessel einem Wert zu?",
                        [("a", "Set"), ("b", "Dictionary"), ("c", "Tuple"), ("d", "Slice")],
                        "b",
                        "Ein Dictionary arbeitet mit Schluessel-Wert-Paaren.",
                    ),
                    _single(
                        "m07_q2",
                        "Welche Aussage ueber Sets ist richtig?",
                        [("a", "Sets speichern doppelte Werte immer mehrfach."), ("b", "Sets haben automatisch Schluessel-Wert-Paare."), ("c", "Sets enthalten keine doppelten Eintraege."), ("d", "Sets koennen nur Zahlen speichern.")],
                        "c",
                        "Sets sind Mengen ohne Duplikate.",
                    ),
                    _text(
                        "m07_q3",
                        "Wie heisst die Python-Schreibweise fuer kurze anonyme Funktionen?",
                        ["lambda"],
                        "Kurze anonyme Funktionen werden mit `lambda` geschrieben.",
                        placeholder="Begriff",
                    ),
                ],
            },
            {
                "module_id": "m08_module_dateien_csv",
                "title": "Module, CSV-Dateien und prozedurale Programmierung",
                "estimated_minutes": 55,
                "objectives": [
                    "import-Anweisungen lesen und schreiben",
                    "Dateien oeffnen, lesen und schreiben",
                    "CSV als typisches Datenformat erkennen",
                ],
                "lesson_markdown": """
## Module

Mit `import` verwendest du Funktionen aus anderen Dateien oder Python-Bibliotheken.

```python
import math
print(math.sqrt(16))
```

## Dateien

```python
with open("daten.txt", "r", encoding="utf-8") as handle:
    text = handle.read()
```

CSV-Dateien speichern tabellarische Daten meist mit Trennzeichen wie `,` oder `;`.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m08_q1",
                        "Wofuer nutzt man `import`?",
                        [("a", "Zum Vergleichen von Zahlen"), ("b", "Zum Laden von Modulen"), ("c", "Zum Schliessen einer Datei"), ("d", "Zum Beenden von Python")],
                        "b",
                        "`import` bindet Module ein.",
                    ),
                    _single(
                        "m08_q2",
                        "Welche Schreibweise ist fuer Dateizugriffe besonders sicher und lesbar?",
                        [("a", "open() ohne Schliessen"), ("b", "with open(...) as handle:"), ("c", "file = []"), ("d", "import open")],
                        "b",
                        "Der `with`-Block verwaltet die Datei sauber.",
                    ),
                    _text(
                        "m08_q3",
                        "Welches Dateiformat wird haeufig fuer tabellarische Daten verwendet und im Kurs behandelt?",
                        ["csv"],
                        "CSV steht fuer tabellarische Textdaten.",
                        placeholder="Dateiformat",
                    ),
                ],
            },
            {
                "module_id": "m09_oop_und_klassen",
                "title": "Objektorientierung, Klassen und Vererbung",
                "estimated_minutes": 60,
                "objectives": [
                    "Klassen und Objekte unterscheiden",
                    "Konstruktor, Felder und Methoden anwenden",
                    "Vererbung als Erweiterungskonzept beschreiben",
                ],
                "lesson_markdown": """
## OOP-Grundidee

Objektorientierung gruppiert Daten und Verhalten in Klassen.

```python
class Hund:
    def __init__(self, name: str) -> None:
        self.name = name

    def belle(self) -> str:
        return f"{self.name} bellt."
```

Vererbung ist sinnvoll, wenn mehrere Klassen gemeinsame Eigenschaften teilen.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m09_q1",
                        "Welche Methode ist in Python der typische Konstruktor?",
                        [("a", "__main__"), ("b", "__init__"), ("c", "__len__"), ("d", "__name__")],
                        "b",
                        "`__init__` initialisiert neue Objekte.",
                    ),
                    _single(
                        "m09_q2",
                        "Was beschreibt Vererbung am besten?",
                        [("a", "Eine Klasse uebernimmt Eigenschaften einer anderen Klasse."), ("b", "Eine Datei wird geloescht."), ("c", "Eine Schleife wird beendet."), ("d", "Eine Variable wird gecastet.")],
                        "a",
                        "Vererbung erweitert gemeinsame Klassenstrukturen.",
                    ),
                    _text(
                        "m09_q3",
                        "Wie nennt man eine konkrete Instanz einer Klasse?",
                        ["objekt"],
                        "Eine Instanz einer Klasse ist ein Objekt.",
                        placeholder="Begriff",
                    ),
                ],
            },
            {
                "module_id": "m10_lesbarkeit_pakete_visualisierung",
                "title": "Dokumentation, Lesbarkeit, Pakete und Visualisierung",
                "estimated_minutes": 45,
                "objectives": [
                    "Kommentare und Docstrings sinnvoll einsetzen",
                    "Pakete und Module unterscheiden",
                    "Matplotlib als Visualisierungspaket einordnen",
                ],
                "lesson_markdown": """
## Lesbarkeit

Guter Code ist nicht nur korrekt, sondern auch lesbar.

- Kommentare erklaeren Absicht und Kontext
- Docstrings dokumentieren Funktionen und Klassen
- klare Namen und kurze Funktionen helfen beim Verstehen

## Pakete und Visualisierung

Ein Paket enthaelt mehrere Module. Fuer Visualisierung wird in Python oft `matplotlib.pyplot` genutzt.
""".strip(),
                "quiz_pass_ratio": 0.67,
                "questions": [
                    _single(
                        "m10_q1",
                        "Wofuer sind Docstrings gedacht?",
                        [("a", "Nur fuer Schleifen"), ("b", "Zur Dokumentation von Funktionen und Klassen"), ("c", "Zum Starten von Python"), ("d", "Zum Umbenennen von Dateien")],
                        "b",
                        "Docstrings dokumentieren Funktionen, Klassen und Module.",
                    ),
                    _single(
                        "m10_q2",
                        "Welches Paket wird im Kurs fuer einfache Datenvisualisierung genannt?",
                        [("a", "pygame"), ("b", "pytest"), ("c", "matplotlib"), ("d", "sqlite3")],
                        "c",
                        "`matplotlib` ist ein Standardwerkzeug fuer einfache Diagramme.",
                    ),
                    _text(
                        "m10_q3",
                        "Wie nennt man eine Sammlung mehrerer Python-Module?",
                        ["paket", "package"],
                        "Eine Sammlung mehrerer Module heisst Paket.",
                        placeholder="Begriff",
                    ),
                ],
            },
        ],
        "final_assessment": {
            "assessment_id": "python-grundlagen-abschluss",
            "title": "Abschlusspruefung Python Grundlagen",
            "instructions": "Bearbeite die Fragen ohne Hilfestellung. Die Abschlusspruefung schliesst den Kurs ab und fuehrt bei Bestehen zum Zertifikat.",
            "questions": [
                _single("f_q1", "Welcher Begriff beschreibt den von Menschen geschriebenen Programmcode?", [("a", "Bytecode"), ("b", "Quelltext"), ("c", "Index"), ("d", "Loop")], "b", "Quelltext ist der von Menschen geschriebene Programmcode."),
                _single("f_q2", "Welcher Datentyp speichert Text?", [("a", "float"), ("b", "bool"), ("c", "str"), ("d", "set")], "c", "`str` speichert Text."),
                _single("f_q3", "Welcher Ausdruck vergleicht zwei Werte auf Gleichheit?", [("a", "="), ("b", "=="), ("c", ":="), ("d", "=>")], "b", "`==` prueft auf Gleichheit."),
                _single("f_q4", "Mit welcher Schleife iterierst du typischerweise ueber eine Liste?", [("a", "for"), ("b", "while"), ("c", "if"), ("d", "def")], "a", "Listen werden typischerweise mit `for` durchlaufen."),
                _single("f_q5", "Welche Funktion liefert die Anzahl von Elementen?", [("a", "type"), ("b", "len"), ("c", "print"), ("d", "input")], "b", "`len()` gibt die Laenge zurueck."),
                _single("f_q6", "Was gibt eine Funktion mit `return` zurueck?", [("a", "Ein Modul"), ("b", "Ein Ergebnis"), ("c", "Immer True"), ("d", "Einen Kommentar")], "b", "`return` gibt das Ergebnis einer Funktion zurueck."),
                _single("f_q7", "Welche Datenstruktur besteht aus Schluessel-Wert-Paaren?", [("a", "Tuple"), ("b", "Set"), ("c", "Dictionary"), ("d", "String")], "c", "Ein Dictionary speichert Schluessel-Wert-Paare."),
                _single("f_q8", "Was nutzt du, um eine Datei sauber im Kontext zu oeffnen?", [("a", "with open(...)"), ("b", "while open(...)"), ("c", "import file"), ("d", "class open")], "a", "Der `with`-Block ist die saubere Standardform."),
                _single("f_q9", "Wie heisst der Konstruktor einer Python-Klasse?", [("a", "__name__"), ("b", "__main__"), ("c", "__init__"), ("d", "__iter__")], "c", "`__init__` initialisiert neue Objekte."),
                _single("f_q10", "Welches Paket eignet sich im Kurs fuer Diagramme?", [("a", "matplotlib"), ("b", "socket"), ("c", "tkinter"), ("d", "random")], "a", "`matplotlib` wird fuer Visualisierung eingesetzt."),
                _text("f_q11", "Welches Schluesselwort definierte Funktionen in Python?", ["def"], "Funktionen beginnen mit `def`.", placeholder="Schluesselwort"),
                _text("f_q12", "Wie heisst das Format fuer tabellarische Textdaten mit Trennzeichen, das im Kurs behandelt wird?", ["csv"], "CSV ist das behandelte Tabellenformat.", placeholder="Dateiformat"),
            ],
        },
    }
}

COURSE_CATALOG["python-grundlagen"].update(
    {
        "subject_area": "Programmierung mit Python",
        "certificate_theme": {
            "label": "Programmierung mit Python",
            "accent": "#126d67",
            "accent_dark": "#0a4d49",
            "warm": "#8f412f",
            "paper": "#fbf3e5",
        },
    }
)

COURSE_CATALOG.update(
    {
        "datenanalyse-mit-python": {
            "course_id": "datenanalyse-mit-python",
            "title": "Datenanalyse mit Python",
            "subtitle": "Aus Daten Informationen gewinnen und Ergebnisse visualisieren",
            "subject_area": "Datenanalyse und Visualisierung",
            "summary": "Tabellendaten lesen, auswerten, strukturieren und mit Diagrammen verstaendlich darstellen.",
            "audience": "Schulunterricht Informatik, Aufbaukurs nach Python Grundlagen",
            "estimated_hours": 10,
            "certificate_title": "Nova School Zertifikat Datenanalyse mit Python",
            "pass_ratio": 0.7,
            "final_pass_ratio": 0.75,
            "certificate_theme": {
                "label": "Datenanalyse und Visualisierung",
                "accent": "#245c9a",
                "accent_dark": "#193a63",
                "warm": "#3f7d63",
                "paper": "#eef5fb",
            },
            "modules": [
                {
                    "module_id": "d01_csv_und_datenquellen",
                    "title": "CSV-Dateien und Datenquellen",
                    "estimated_minutes": 40,
                    "objectives": [
                        "CSV-Dateien als tabellarische Datenquelle einordnen",
                        "Dateien mit Python lesen",
                        "Spalten und Datensaetze voneinander unterscheiden",
                    ],
                    "lesson_markdown": """
## Datensaetze lesen

Viele Schul- und Projektdaten liegen als CSV-Datei vor. Sie enthalten Zeilen fuer Datensaetze
und Spalten fuer einzelne Merkmale.

```python
import csv

with open("werte.csv", newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
```

Mit `DictReader` lassen sich Spaltennamen direkt als Schluessel verwenden.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("d01_q1", "Wofuer steht CSV?", [("a", "Computer Stored Values"), ("b", "Comma Separated Values"), ("c", "Code Syntax Version"), ("d", "Cell Sorted View")], "b", "CSV steht fuer Comma Separated Values."),
                        _single("d01_q2", "Was beschreibt in einer Tabelle typischerweise eine Zeile?", [("a", "Einen Datensatz"), ("b", "Alle Spaltennamen"), ("c", "Immer ein Diagramm"), ("d", "Nur Kommentare")], "a", "Eine Zeile repraesentiert meist einen Datensatz."),
                        _text("d01_q3", "Welches Standardmodul liest in Python CSV-Dateien?", ["csv"], "Das Modul heisst `csv`.", placeholder="Modulname"),
                    ],
                },
                {
                    "module_id": "d02_filtern_und_aggregieren",
                    "title": "Filtern, zaehlen und aggregieren",
                    "estimated_minutes": 45,
                    "objectives": [
                        "Daten nach Bedingungen filtern",
                        "Kennzahlen wie Summe und Mittelwert berechnen",
                        "einfache Auswertungsfragen formulieren",
                    ],
                    "lesson_markdown": """
## Aus Daten Fragen beantworten

Bei einer Analyse wird selten jeder Datensatz einzeln betrachtet. Stattdessen werden Daten
gefiltert, gruppiert oder zu Kennzahlen zusammengefasst.

```python
preise = [4.0, 5.5, 3.0]
mittelwert = sum(preise) / len(preise)
```
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("d02_q1", "Welche built-in-Funktion addiert Zahlen einer Liste?", [("a", "avg"), ("b", "sum"), ("c", "count"), ("d", "calc")], "b", "`sum()` addiert die Werte."),
                        _single("d02_q2", "Wozu dient ein Filter in der Datenanalyse?", [("a", "Zum Drucken von Papier"), ("b", "Zum Auswaehlen passender Datensaetze"), ("c", "Zum Kompilieren von Python"), ("d", "Zum Zeichnen von Fenstern")], "b", "Filter waehlen passende Datensaetze aus."),
                        _text("d02_q3", "Welche Funktion liefert die Anzahl von Listenelementen?", ["len", "len()"], "`len()` liefert die Anzahl der Elemente.", placeholder="Funktion"),
                    ],
                },
                {
                    "module_id": "d03_dictionaries_und_kennzahlen",
                    "title": "Dictionaries, Kategorien und Kennzahlen",
                    "estimated_minutes": 45,
                    "objectives": [
                        "Auswertungen mit Dictionaries strukturieren",
                        "Kategorien zaehlen",
                        "Kennzahlen erklaeren und interpretieren",
                    ],
                    "lesson_markdown": """
## Kategorien auswerten

Mit Dictionaries lassen sich Haeufigkeiten und Kennzahlen pro Kategorie speichern.

```python
haeufigkeit = {}
for fach in ["Python", "Python", "HTML"]:
    haeufigkeit[fach] = haeufigkeit.get(fach, 0) + 1
```
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("d03_q1", "Welche Struktur speichert Schluessel-Wert-Paare?", [("a", "set"), ("b", "dictionary"), ("c", "slice"), ("d", "tuple-loop")], "b", "Ein Dictionary speichert Schluessel und Werte."),
                        _single("d03_q2", "Wofuer kann `haeufigkeit.get(fach, 0)` genutzt werden?", [("a", "Zum sicheren Lesen eines Dictionary-Werts"), ("b", "Zum Loeschen eines Moduls"), ("c", "Zum Import von CSV"), ("d", "Zum Starten eines Containers")], "a", "`get()` liefert einen Default-Wert, wenn der Schluessel fehlt."),
                        _text("d03_q3", "Wie nennt man eine berechnete Kennzahl wie Mittelwert oder Maximum?", ["kennzahl"], "Solche berechneten Groessen nennt man Kennzahlen.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "d04_visualisierung_mit_matplotlib",
                    "title": "Diagramme mit Matplotlib",
                    "estimated_minutes": 45,
                    "objectives": [
                        "einfache Diagrammtypen unterscheiden",
                        "Achsen und Beschriftungen sinnvoll setzen",
                        "Diagramme als Kommunikationsmittel einordnen",
                    ],
                    "lesson_markdown": """
## Daten sichtbar machen

Diagramme helfen, Muster in Daten schnell zu erkennen.

```python
import matplotlib.pyplot as plt

plt.bar(["A", "B"], [4, 7])
plt.title("Beispiel")
plt.show()
```

Ein Balkendiagramm eignet sich besonders gut fuer Kategorienvergleiche.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("d04_q1", "Welches Paket wird fuer einfache Diagramme genutzt?", [("a", "pygame"), ("b", "matplotlib"), ("c", "sqlite3"), ("d", "socket")], "b", "`matplotlib` ist das Standardpaket fuer einfache Diagramme."),
                        _single("d04_q2", "Welcher Diagrammtyp passt gut zu Kategorienvergleichen?", [("a", "Balkendiagramm"), ("b", "Installationsdiagramm"), ("c", "Kommentarblock"), ("d", "Interpreterdiagramm")], "a", "Balkendiagramme zeigen Kategorien gut vergleichbar."),
                        _text("d04_q3", "Welches pyplot-Kommando setzt einen Diagrammtitel?", ["title", "plt.title", "plt.title()"], "`plt.title()` setzt den Titel.", placeholder="z. B. plt.title"),
                    ],
                },
                {
                    "module_id": "d05_interpretation_und_kommunikation",
                    "title": "Ergebnisse interpretieren und darstellen",
                    "estimated_minutes": 35,
                    "objectives": [
                        "aus Daten begruendete Aussagen formulieren",
                        "Visualisierung und Text sinnvoll kombinieren",
                        "Grenzen von Datenauswertungen benennen",
                    ],
                    "lesson_markdown": """
## Datenanalyse ist mehr als Code

Gute Datenanalyse endet nicht bei Zahlen. Wichtig ist, Ergebnisse fuer andere verstaendlich
zu formulieren und Grenzen ehrlich zu benennen.

- Welche Daten wurden ausgewertet?
- Welche Aussage ist gut begruendet?
- Welche Unsicherheiten bleiben?
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("d05_q1", "Was gehoert zu einer guten Ergebnisdarstellung?", [("a", "Nur Rohdaten ohne Erklaerung"), ("b", "Diagramm plus erklaerender Text"), ("c", "Nur Installationshinweise"), ("d", "Nur Dateinamen")], "b", "Diagramme und Text sollten zusammen erklaeren."),
                        _single("d05_q2", "Warum ist die Herkunft von Daten wichtig?", [("a", "Sie beeinflusst die Aussagekraft"), ("b", "Sie bestimmt die Farbe von Python"), ("c", "Sie startet automatisch eine Schleife"), ("d", "Sie ersetzt die Analyse")], "a", "Datenquelle und Qualitaet beeinflussen die Aussagekraft."),
                        _text("d05_q3", "Wie nennt man eine begruendete Aussage auf Basis ausgewerteter Daten?", ["interpretation"], "Die begruendete Aussage ist die Interpretation.", placeholder="Begriff"),
                    ],
                },
            ],
            "final_assessment": {
                "assessment_id": "datenanalyse-mit-python-abschluss",
                "title": "Abschlusspruefung Datenanalyse mit Python",
                "instructions": "Bearbeite die Aufgaben eigenstaendig. Die Abschlusspruefung prueft Datenverstaendnis, Auswertung und Visualisierung.",
                "questions": [
                    _single("df_q1", "Welches Modul liest CSV-Dateien?", [("a", "math"), ("b", "csv"), ("c", "json"), ("d", "time")], "b", "`csv` liest CSV-Dateien."),
                    _single("df_q2", "Was repraesentiert in einer Tabelle typischerweise eine Spalte?", [("a", "Ein Merkmal"), ("b", "Immer eine Datei"), ("c", "Einen kompletten Datensatz"), ("d", "Nur Kommentare")], "a", "Eine Spalte repraesentiert ein Merkmal."),
                    _single("df_q3", "Welche Funktion hilft beim Addieren vieler Werte?", [("a", "sum"), ("b", "plot"), ("c", "open"), ("d", "break")], "a", "`sum()` addiert Werte."),
                    _single("df_q4", "Welche Struktur eignet sich zum Zaehlen pro Kategorie?", [("a", "Dictionary"), ("b", "String"), ("c", "Bytecode"), ("d", "Interpreter")], "a", "Kategorien lassen sich gut im Dictionary verwalten."),
                    _single("df_q5", "Welches Paket wird fuer Diagramme genannt?", [("a", "pytest"), ("b", "matplotlib"), ("c", "tkinter"), ("d", "socket")], "b", "`matplotlib` erzeugt Diagramme."),
                    _single("df_q6", "Warum ist eine Interpretation wichtig?", [("a", "Damit Ergebnisse verstaendlich werden"), ("b", "Damit Python schneller startet"), ("c", "Damit CSV verschwindet"), ("d", "Damit kein Code noetig ist")], "a", "Erst die Interpretation macht Ergebnisse verstaendlich."),
                    _text("df_q7", "Wie nennt man die tabellarische Textdatei mit Trennzeichen?", ["csv"], "CSV ist das genannte Format.", placeholder="Format"),
                    _text("df_q8", "Wie heisst das Paket fuer Diagramme im Kurs?", ["matplotlib"], "`matplotlib` ist das Visualisierungspaket.", placeholder="Paketname"),
                ],
            },
        },
        "web-frontend-grundlagen": {
            "course_id": "web-frontend-grundlagen",
            "title": "Web Frontend Grundlagen",
            "subtitle": "HTML, CSS und JavaScript fuer den Browser strukturiert lernen",
            "subject_area": "Webentwicklung Frontend",
            "summary": "Von semantischem HTML ueber Layout mit CSS bis zu Interaktion mit JavaScript.",
            "audience": "Schulunterricht Informatik, Frontend-Einstieg",
            "estimated_hours": 12,
            "certificate_title": "Nova School Zertifikat Web Frontend Grundlagen",
            "pass_ratio": 0.7,
            "final_pass_ratio": 0.75,
            "certificate_theme": {
                "label": "Webentwicklung Frontend",
                "accent": "#a64b1f",
                "accent_dark": "#6e2e14",
                "warm": "#1c4f7f",
                "paper": "#fff3ea",
            },
            "modules": [
                {
                    "module_id": "w01_html_struktur",
                    "title": "HTML-Struktur und semantische Elemente",
                    "estimated_minutes": 40,
                    "objectives": [
                        "HTML als Struktur einer Webseite verstehen",
                        "Ueberschriften, Abschnitte und Listen einsetzen",
                        "semantische Elemente einordnen",
                    ],
                    "lesson_markdown": """
## HTML gibt Inhalt Struktur

HTML beschreibt, welche Inhalte eine Seite besitzt.

```html
<main>
  <h1>Mein Projekt</h1>
  <p>Willkommen auf meiner Seite.</p>
</main>
```

Semantische Elemente wie `header`, `main` oder `section` machen Inhalt nachvollziehbar.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("w01_q1", "Wofuer wird HTML vor allem genutzt?", [("a", "Fuer die Struktur von Inhalten"), ("b", "Nur fuer Farben"), ("c", "Nur fuer Serverprozesse"), ("d", "Nur fuer Datenbanken")], "a", "HTML beschreibt die Struktur der Inhalte."),
                        _single("w01_q2", "Welches Element steht typischerweise fuer die Hauptueberschrift?", [("a", "<p>"), ("b", "<h1>"), ("c", "<div>"), ("d", "<script>")], "b", "`<h1>` kennzeichnet die wichtigste Ueberschrift."),
                        _text("w01_q3", "Wie nennt man HTML-Elemente wie `main`, `section` oder `article`, die ihren Zweck bereits erkennen lassen?", ["semantisch", "semantische elemente"], "Diese Elemente nennt man semantisch.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "w02_css_layout_und_farben",
                    "title": "CSS, Layout und visuelle Gestaltung",
                    "estimated_minutes": 45,
                    "objectives": [
                        "CSS als Sprache fuer Darstellung verstehen",
                        "Selektoren, Farben und Abstaende anwenden",
                        "den Unterschied zwischen Inhalt und Gestaltung erklaeren",
                    ],
                    "lesson_markdown": """
## CSS gestaltet Inhalte

Mit CSS werden HTML-Inhalte gestaltet.

```css
body {
  background: #f7eed9;
  color: #182126;
}
```

Selektoren waehlen Elemente aus. Eigenschaften wie `color`, `margin` oder `display` bestimmen das Erscheinungsbild.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("w02_q1", "Wofuer steht CSS im Frontend?", [("a", "Client Structure Syntax"), ("b", "Cascading Style Sheets"), ("c", "Computed Script System"), ("d", "Code Styling Server")], "b", "CSS steht fuer Cascading Style Sheets."),
                        _single("w02_q2", "Welche Eigenschaft steuert die Textfarbe?", [("a", "background"), ("b", "font"), ("c", "color"), ("d", "width")], "c", "`color` steuert die Textfarbe."),
                        _text("w02_q3", "Wie nennt man den Teil vor den geschweiften Klammern, der Elemente auswaehlt?", ["selektor"], "Das ist der Selektor.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "w03_formulare_und_zugaenglichkeit",
                    "title": "Formulare, Labels und Zugänglichkeit",
                    "estimated_minutes": 40,
                    "objectives": [
                        "Formularelemente sinnvoll einsetzen",
                        "Labels mit Eingabefeldern verknuepfen",
                        "Zugaenglichkeit als Qualitaetsmerkmal verstehen",
                    ],
                    "lesson_markdown": """
## Gute Formulare

Formulare sind dann gut, wenn sie klar beschriftet und leicht bedienbar sind.

```html
<label for="name">Name</label>
<input id="name" type="text" />
```

Labels helfen allen Nutzern und verbessern die Zugaenglichkeit.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("w03_q1", "Wofuer ist ein `<label>` in Formularen wichtig?", [("a", "Zur Beschriftung eines Eingabefelds"), ("b", "Zum Starten von JavaScript"), ("c", "Zum Loeschen von CSS"), ("d", "Nur fuer Bilder")], "a", "Labels beschriften Eingabefelder."),
                        _single("w03_q2", "Warum ist Zugänglichkeit im Web wichtig?", [("a", "Damit Seiten nur auf einem Geraet laufen"), ("b", "Damit moeglichst viele Menschen Inhalte nutzen koennen"), ("c", "Damit HTML kuerzer wird"), ("d", "Damit keine Styles noetig sind")], "b", "Zugaenglichkeit erhoeht Nutzbarkeit fuer viele Menschen."),
                        _text("w03_q3", "Welches Attribut verbindet ein Label mit dem passenden Eingabefeld?", ["for"], "Das `for`-Attribut verknuepft Label und Eingabe.", placeholder="Attribut"),
                    ],
                },
                {
                    "module_id": "w04_javascript_dom_und_events",
                    "title": "JavaScript, DOM und Benutzerinteraktion",
                    "estimated_minutes": 50,
                    "objectives": [
                        "JavaScript als Sprache fuer Verhalten im Browser verstehen",
                        "DOM-Elemente auswaehlen und veraendern",
                        "Events wie Klicks verarbeiten",
                    ],
                    "lesson_markdown": """
## Interaktivitaet mit JavaScript

JavaScript reagiert auf Aktionen im Browser.

```javascript
document.querySelector("button").addEventListener("click", () => {
  console.log("geklickt");
});
```

Das DOM ist die vom Browser aufgebaute Struktur der HTML-Seite.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("w04_q1", "Wofuer wird JavaScript im Frontend vor allem genutzt?", [("a", "Fuer Verhalten und Interaktion"), ("b", "Nur fuer Farben"), ("c", "Nur fuer Datenbanken"), ("d", "Nur fuer Dateisysteme")], "a", "JavaScript steuert Verhalten und Interaktion."),
                        _single("w04_q2", "Was ist ein Event im Browser?", [("a", "Ein Programmfehler"), ("b", "Ein Ereignis wie ein Klick"), ("c", "Eine CSS-Farbe"), ("d", "Ein Dateiformat")], "b", "Ein Event ist ein Ereignis wie ein Klick oder Eingabe."),
                        _text("w04_q3", "Wie heisst die Browser-Struktur der HTML-Seite, die JavaScript bearbeiten kann?", ["dom"], "Die Struktur heisst DOM.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "w05_frontend_projekte_und_qualitaet",
                    "title": "Kleine Frontend-Projekte und Qualitaet",
                    "estimated_minutes": 40,
                    "objectives": [
                        "kleine Frontend-Projekte planen",
                        "Struktur, Stil und Verhalten zusammendenken",
                        "Lesbarkeit und Wartbarkeit im Frontend einordnen",
                    ],
                    "lesson_markdown": """
## Gute Frontend-Projekte

Ein gutes Frontend verbindet Inhalt, Gestaltung und Interaktion.

- HTML strukturiert
- CSS gestaltet
- JavaScript reagiert

Saubere Dateinamen, klare Struktur und lesbarer Code sind auch im Frontend wichtig.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("w05_q1", "Welche drei Bereiche gehoeren im Frontend-Grundkurs zusammen?", [("a", "HTML, CSS, JavaScript"), ("b", "Python, Docker, CSV"), ("c", "Rust, Java, SQL"), ("d", "TCP, UDP, DNS")], "a", "HTML, CSS und JavaScript bilden den Kern des Frontends."),
                        _single("w05_q2", "Warum ist Dateistruktur im Frontend wichtig?", [("a", "Sie verbessert Lesbarkeit und Wartung"), ("b", "Sie ersetzt die Gestaltung"), ("c", "Sie macht JavaScript ueberfluessig"), ("d", "Sie ist nur fuer Admins wichtig")], "a", "Eine klare Struktur erleichtert Arbeit und Pflege."),
                        _text("w05_q3", "Welche Sprache beschreibt im Frontend die Struktur einer Webseite?", ["html"], "HTML strukturiert die Seite.", placeholder="Sprache"),
                    ],
                },
            ],
            "final_assessment": {
                "assessment_id": "web-frontend-grundlagen-abschluss",
                "title": "Abschlusspruefung Web Frontend Grundlagen",
                "instructions": "Bearbeite die Fragen eigenstaendig. Die Abschlusspruefung prueft Struktur, Gestaltung und Interaktion im Browser.",
                "questions": [
                    _single("wf_q1", "Welche Sprache strukturiert Inhalte im Browser?", [("a", "HTML"), ("b", "CSS"), ("c", "Docker"), ("d", "CSV")], "a", "HTML strukturiert Inhalte."),
                    _single("wf_q2", "Welche Sprache gestaltet Inhalte visuell?", [("a", "HTML"), ("b", "CSS"), ("c", "JSON"), ("d", "Terminal")], "b", "CSS gestaltet Inhalte."),
                    _single("wf_q3", "Welche Sprache sorgt fuer Interaktion im Browser?", [("a", "JavaScript"), ("b", "SQL"), ("c", "Markdown"), ("d", "Bash")], "a", "JavaScript steuert Verhalten und Interaktion."),
                    _single("wf_q4", "Was ist das DOM?", [("a", "Die Browser-Struktur der HTML-Seite"), ("b", "Ein Build-Tool"), ("c", "Ein Containerformat"), ("d", "Ein Python-Modul")], "a", "Das DOM ist die Browser-Struktur der HTML-Seite."),
                    _single("wf_q5", "Wozu dient ein Label in Formularen?", [("a", "Zur Beschriftung und Zugänglichkeit"), ("b", "Zum Kompilieren"), ("c", "Zum Netzwerkzugriff"), ("d", "Zum Export als ZIP")], "a", "Labels verbessern Beschriftung und Zugänglichkeit."),
                    _single("wf_q6", "Was ist ein typisches Event?", [("a", "click"), ("b", "while"), ("c", "import"), ("d", "range")], "a", "`click` ist ein typisches Browser-Event."),
                    _text("wf_q7", "Wie heisst die Sprache fuer Darstellung und Layout im Web?", ["css"], "CSS steuert Darstellung und Layout.", placeholder="Sprache"),
                    _text("wf_q8", "Wie heisst die Struktur, die JavaScript im Browser veraendern kann?", ["dom"], "JavaScript arbeitet haeufig mit dem DOM.", placeholder="Begriff"),
                ],
            },
        },
        "cpp-grundlagen": {
            "course_id": "cpp-grundlagen",
            "title": "C++ Grundlagen",
            "subtitle": "Modullehrplan fuer strukturierten Einstieg in C++ und objektorientierte Programmierung",
            "subject_area": "Programmierung mit C++",
            "summary": "Von Hello World ueber Funktionen und Klassen bis zu Zeigern und Templates.",
            "audience": "Schulunterricht Informatik, Einstieg bis mittleres Niveau",
            "estimated_hours": 16,
            "certificate_title": "Nova School Zertifikat C++ Grundlagen",
            "pass_ratio": 0.7,
            "final_pass_ratio": 0.75,
            "certificate_theme": {
                "label": "Programmierung mit C++",
                "accent": "#224f86",
                "accent_dark": "#16355a",
                "warm": "#8f412f",
                "paper": "#eef3fb",
            },
            "modules": [
                {
                    "module_id": "c01_einfuehrung",
                    "title": "Einfuhrung, IDE und Hello World",
                    "estimated_minutes": 35,
                    "objectives": [
                        "Programme und Algorithmen als strukturierte Problemlosung beschreiben",
                        "C und C++ grundlegend unterscheiden",
                        "eine IDE fuer C++ einordnen und ein Hello-World-Programm lesen",
                    ],
                    "lesson_markdown": """
## Start in C++

C++ ist eine kompilierte Programmiersprache. Das bedeutet: Quelltext wird zuerst uebersetzt
und dann als Programm ausgefuehrt. Im Unterricht arbeitest du strukturiert mit kleinen Programmen,
die Algorithmen in nachvollziehbare Schritte zerlegen.

```cpp
#include <iostream>

int main() {
    std::cout << "Hello World" << std::endl;
    return 0;
}
```

## Merksaetze

- Ein **Algorithmus** ist eine eindeutige Handlungsvorschrift.
- C++ erweitert viele Konzepte aus C um objektorientierte und generische Programmierung.
- `main()` ist der Einstiegspunkt eines C++-Programms.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c01_q1", "Welche Aussage passt zu C++ in diesem Kurs?", [("a", "C++ ist nur eine Tabellenkalkulation."), ("b", "C++ ist eine kompilierte Programmiersprache."), ("c", "C++ wird nur fuer Webseiten genutzt."), ("d", "C++ ersetzt alle Betriebssysteme.")], "b", "C++-Quelltext wird uebersetzt und danach ausgefuehrt."),
                        _single("c01_q2", "Wofuer wird `main()` in C++ benoetigt?", [("a", "Als Kommentarblock"), ("b", "Als Einstiegspunkt des Programms"), ("c", "Nur fuer Klassen"), ("d", "Nur fuer Tests")], "b", "`main()` startet das Programm."),
                        _text("c01_q3", "Wie nennt man eine eindeutige Schrittfolge zur Loesung eines Problems?", ["algorithmus"], "Eine solche Schrittfolge heisst Algorithmus.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "c02_grundlagen",
                    "title": "Grundlagen von C++: Typen, Variablen und Operatoren",
                    "estimated_minutes": 50,
                    "objectives": [
                        "Datentypen, Variablen und Ausdruecke unterscheiden",
                        "Operatoren und Operatorrangfolgen anwenden",
                        "bitweise Arithmetik grundlegend einordnen und lesbaren Code schreiben",
                    ],
                    "lesson_markdown": """
## Werte und Typen

In C++ arbeiten Programme mit Datentypen wie `int`, `double`, `char` oder `bool`.
Variablen speichern Werte, Ausdruecke verknuepfen diese Werte mit Operatoren.

```cpp
int alter = 15;
double note = 2.3;
bool aktiv = true;
```

Bitweise Operatoren wie `&`, `|` oder `<<` arbeiten direkt auf Bits. Im Schulunterricht
werden sie vor allem zum Verstehen maschinennaher Operationen genutzt.

Guter Code nutzt sprechende Namen, nachvollziehbare Einrueckung und klare Struktur.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c02_q1", "Welcher Datentyp eignet sich fuer ganze Zahlen?", [("a", "int"), ("b", "double"), ("c", "bool"), ("d", "void")], "a", "`int` steht fuer ganze Zahlen."),
                        _single("c02_q2", "Welcher Operator gehoert zur bitweisen Arithmetik?", [("a", "&&"), ("b", "<<"), ("c", "=="), ("d", "+=")], "b", "`<<` ist ein bitweiser Shift-Operator."),
                        _text("c02_q3", "Wie nennt man einen sprechenden, klaren und gut lesbaren Stil beim Schreiben von Programmen?", ["guter code", "lesbarer code"], "Im Unterricht wird auf guten, lesbaren Code Wert gelegt.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "c03_programmierung",
                    "title": "Programmierung in C++: Funktionen, Anweisungen und Modularisierung",
                    "estimated_minutes": 55,
                    "objectives": [
                        "Funktionen mit Parametern und Rueckgabewerten lesen und schreiben",
                        "Anweisungen und Ausdruecke unterscheiden",
                        "Fehlerbehandlung, Modularisierung und Makros einordnen",
                    ],
                    "lesson_markdown": """
## Funktionen strukturieren Programme

Funktionen machen Programme uebersichtlicher und wiederverwendbar.

```cpp
int quadrat(int x) {
    return x * x;
}
```

Mit Bedingungen, Schleifen und Funktionsaufrufen entstehen groessere Programme.
Modularisierung bedeutet, Code in sinnvolle Dateien oder Bereiche zu zerlegen.
Makros aus dem Praeprozessor werden heute vorsichtig eingesetzt, weil sie weniger sicher
und weniger transparent als moderne C++-Konstrukte sind.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c03_q1", "Wozu dient `return` in einer Funktion?", [("a", "Zum Importieren eines Headers"), ("b", "Zum Zurueckgeben eines Ergebnisses"), ("c", "Zum Starten einer Klasse"), ("d", "Zum Definieren eines Namespace")], "b", "`return` liefert ein Ergebnis an den Aufrufer."),
                        _single("c03_q2", "Was beschreibt Modularisierung am besten?", [("a", "Code in sinnvolle Teile gliedern"), ("b", "Alle Befehle in eine einzige Datei schreiben"), ("c", "Nur Kommentare loeschen"), ("d", "Nur bitweise Operatoren verwenden")], "a", "Modularisierung trennt Code in sinnvolle Einheiten."),
                        _text("c03_q3", "Wie nennt man textuelle Ersetzungen des Praeprozessors wie `#define`?", ["makros"], "Solche Ersetzungen heissen Makros.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "c04_oop_einstieg",
                    "title": "Einfuhrung in objektorientierte Programmierung",
                    "estimated_minutes": 55,
                    "objectives": [
                        "Strukturen und Klassen unterscheiden",
                        "Namensraeume als Ordnungsmittel verstehen",
                        "automatisierte Tests als Qualitaetswerkzeug einordnen",
                    ],
                    "lesson_markdown": """
## Daten und Verhalten zusammenfassen

In der objektorientierten Programmierung gehoeren Daten und passende Funktionen zusammen.

```cpp
class Konto {
public:
    double stand = 0.0;

    void einzahlen(double betrag) {
        stand += betrag;
    }
};
```

`namespace` hilft dabei, Namen zu strukturieren. Automatisierte Tests pruefen, ob Funktionen
und Klassen erwartetes Verhalten zeigen.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c04_q1", "Was beschreibt eine Klasse in C++ am besten?", [("a", "Eine Sammlung aus Daten und passendem Verhalten"), ("b", "Nur eine Kommentarzeile"), ("c", "Nur eine Schleife"), ("d", "Nur eine IDE-Einstellung")], "a", "Klassen fassen Daten und Verhalten zusammen."),
                        _single("c04_q2", "Wozu dient ein Namespace?", [("a", "Zur Strukturierung von Namen"), ("b", "Zum Kompilieren ohne Quelltext"), ("c", "Zum Loeschen von Variablen"), ("d", "Zum Ersetzen von Tests")], "a", "Namespaces ordnen Bezeichner."),
                        _text("c04_q3", "Wie nennt man Programme oder Routinen, die erwartetes Verhalten automatisch pruefen?", ["tests", "automatisierte tests"], "Automatisierte Tests pruefen Verhalten systematisch.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "c05_oop_erweitert",
                    "title": "Erweiterte objektorientierte Programmierung",
                    "estimated_minutes": 60,
                    "objectives": [
                        "Vererbung als Erweiterungskonzept erklaeren",
                        "den Lebenszyklus von Objekten beschreiben",
                        "sicheren und qualitativen Code mit objektorientiertem Design verbinden",
                    ],
                    "lesson_markdown": """
## Klassen weiterdenken

Mit Vererbung koennen gemeinsame Eigenschaften wiederverwendet werden. Gleichzeitig ist es wichtig,
Verantwortlichkeiten klar zu trennen und Konstruktoren, Destruktoren und Ressourcen sauber zu behandeln.

```cpp
class Tier {
public:
    virtual void laut() = 0;
};
```

Zum Lebenszyklus gehoeren Konstruktion, Nutzung und Zerstoerung eines Objekts.
Gutes objektorientiertes Design bevorzugt klare Rollen, geringe Kopplung und sichere Ressourcenverwaltung.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c05_q1", "Wozu dient Vererbung?", [("a", "Zum Wiederverwenden und Erweitern gemeinsamer Eigenschaften"), ("b", "Zum Loeschen aller Klassen"), ("c", "Zum Ersetzen von Funktionen durch Makros"), ("d", "Zum Ausschalten des Compilers")], "a", "Vererbung erweitert gemeinsame Eigenschaften."),
                        _single("c05_q2", "Was gehoert zum Lebenszyklus eines Objekts?", [("a", "Konstruktion, Nutzung und Zerstoerung"), ("b", "Nur Ausgabe auf dem Bildschirm"), ("c", "Nur Header-Dateien"), ("d", "Nur Kommentare")], "a", "Objekte werden erzeugt, genutzt und wieder zerstoert."),
                        _text("c05_q3", "Wie nennt man das Planen von Klassenbeziehungen und Verantwortlichkeiten auf hoher Ebene?", ["design", "objektorientiertes design"], "Diese Planung gehoert zum objektorientierten Design.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "c06_fortgeschritten",
                    "title": "Fortgeschrittene Programmierung in C++",
                    "estimated_minutes": 60,
                    "objectives": [
                        "Zeiger als Speicheradressen verstehen",
                        "Templates als generische Programmierung einordnen",
                        "sichere und moderne C++-Konzepte von riskanten Mustern unterscheiden",
                    ],
                    "lesson_markdown": """
## Speicher und Generik

Zeiger speichern Adressen im Speicher. Sie sind maechtig, aber fehleranfaellig, wenn sie
unachtsam verwendet werden.

```cpp
int wert = 5;
int* zeiger = &wert;
```

Templates ermoeglichen generischen Code, der fuer mehrere Datentypen funktioniert.

```cpp
template <typename T>
T maximum(T a, T b) {
    return a > b ? a : b;
}
```

Im modernen C++ stehen Sicherheit, Lesbarkeit und bewusster Umgang mit Speicher im Vordergrund.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("c06_q1", "Was speichert ein Zeiger?", [("a", "Immer einen Text"), ("b", "Eine Speicheradresse"), ("c", "Nur einen booleschen Wert"), ("d", "Nur einen Namespace")], "b", "Zeiger speichern Speicheradressen."),
                        _single("c06_q2", "Wofuer werden Templates genutzt?", [("a", "Fuer generischen Code mit verschiedenen Typen"), ("b", "Nur fuer Kommentare"), ("c", "Nur fuer Include-Anweisungen"), ("d", "Nur fuer Fehlermeldungen")], "a", "Templates erlauben generische Funktionen und Klassen."),
                        _text("c06_q3", "Wie nennt man C++-Code, der fuer verschiedene Typen wiederverwendbar geschrieben ist?", ["generisch", "generische programmierung"], "Das ist generische Programmierung.", placeholder="Begriff"),
                    ],
                },
            ],
            "final_assessment": {
                "assessment_id": "cpp-grundlagen-abschluss",
                "title": "Abschlusspruefung C++ Grundlagen",
                "instructions": "Bearbeite die Fragen eigenstaendig. Die Abschlusspruefung prueft Sprachgrundlagen, OOP und fortgeschrittene Konzepte aus dem Kurs.",
                "questions": [
                    _single("cf_q1", "Welche Funktion ist in C++ typischerweise der Programmeinstieg?", [("a", "start"), ("b", "main"), ("c", "run"), ("d", "entry")], "b", "`main()` ist der typische Programmeinstieg."),
                    _single("cf_q2", "Welcher Datentyp steht fuer ganze Zahlen?", [("a", "float"), ("b", "string"), ("c", "int"), ("d", "void")], "c", "`int` repraesentiert ganze Zahlen."),
                    _single("cf_q3", "Wozu dient eine Funktion?", [("a", "Zum Strukturieren und Wiederverwenden von Code"), ("b", "Nur zum Einfaerben von Ausgaben"), ("c", "Nur zum Definieren von Makros"), ("d", "Nur fuer Kommentare")], "a", "Funktionen strukturieren und kapseln Code."),
                    _single("cf_q4", "Was ist ein Namespace?", [("a", "Ein Bereich zur Strukturierung von Namen"), ("b", "Eine Speicheradresse"), ("c", "Ein Compilerfehler"), ("d", "Ein Zeigertyp")], "a", "Namespaces strukturieren Namen."),
                    _single("cf_q5", "Welche Aussage passt zur Vererbung?", [("a", "Sie erweitert gemeinsame Eigenschaften von Klassen"), ("b", "Sie ersetzt alle Funktionen"), ("c", "Sie loescht Objekte automatisch"), ("d", "Sie ist nur fuer Header-Dateien relevant")], "a", "Vererbung erweitert gemeinsame Eigenschaften."),
                    _single("cf_q6", "Was speichert ein Zeiger?", [("a", "Nur Strings"), ("b", "Eine Speicheradresse"), ("c", "Nur einen Wert ohne Bezug"), ("d", "Nur Kommentare")], "b", "Zeiger speichern Speicheradressen."),
                    _text("cf_q7", "Wie heisst die C++-Technik fuer generischen Code mit verschiedenen Typen?", ["template", "templates"], "Templates machen Code generisch.", placeholder="Begriff"),
                    _text("cf_q8", "Wie nennt man automatisch ausgefuehrte Pruefungen fuer Funktionen und Klassen?", ["tests", "automatisierte tests"], "Automatisierte Tests pruefen Verhalten.", placeholder="Begriff"),
                ],
            },
        },
        "java-oop-grundlagen": {
            "course_id": "java-oop-grundlagen",
            "title": "Java OOP Grundlagen",
            "subtitle": "Objektorientierte Programmierung am Beispiel von Java",
            "subject_area": "Objektorientierte Programmierung mit Java",
            "summary": "Von Spracheinstieg und Kontrollstrukturen ueber Klassen, Vererbung und Datenstrukturen bis zur Projektumsetzung.",
            "audience": "Schulunterricht Informatik, Einstieg bis mittleres Niveau",
            "estimated_hours": 18,
            "certificate_title": "Nova School Zertifikat Java OOP Grundlagen",
            "pass_ratio": 0.7,
            "final_pass_ratio": 0.75,
            "certificate_theme": {
                "label": "Objektorientierte Programmierung mit Java",
                "accent": "#b35a1f",
                "accent_dark": "#7d3d14",
                "warm": "#1d4f78",
                "paper": "#fff1e6",
            },
            "modules": [
                {
                    "module_id": "j01_einstieg_und_grundlagen",
                    "title": "Einfuehrung in Java und Wiederholung der Programmiergrundlagen",
                    "estimated_minutes": 50,
                    "objectives": [
                        "Java als Programmiersprache einordnen",
                        "Hello World, Datentypen, Variablen und Operatoren verstehen",
                        "Kontrollstrukturen und die offizielle Dokumentation als Arbeitsmittel nutzen",
                    ],
                    "lesson_markdown": """
## Einstieg in Java

Java ist eine objektorientierte Programmiersprache. Programme werden kompiliert und auf einer
Java-Laufzeitumgebung ausgefuehrt.

```java
public class Hallo {
    public static void main(String[] args) {
        System.out.println("Hallo Welt");
    }
}
```

## Grundlagen

- Primitive Datentypen wie `int`, `double`, `boolean` und `char`
- Variablen speichern Werte
- Operatoren verknuepfen Ausdruecke
- `if`, `else`, `for` und `while` steuern den Ablauf
- Die offizielle Dokumentation hilft beim Nachschlagen von Klassen und Methoden
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("j01_q1", "Welche Methode ist in einem einfachen Java-Programm typischerweise der Einstiegspunkt?", [("a", "print()"), ("b", "main(String[] args)"), ("c", "run()"), ("d", "start()")], "b", "Die `main`-Methode startet ein einfaches Java-Programm."),
                        _single("j01_q2", "Welcher Datentyp steht in Java fuer Wahrheitswerte?", [("a", "String"), ("b", "boolean"), ("c", "char"), ("d", "float")], "b", "`boolean` repraesentiert `true` oder `false`."),
                        _text("j01_q3", "Wie nennt man die offizielle Sammlung von Klassen, Methoden und Beschreibungen zum Nachschlagen in Java?", ["dokumentation", "offizielle dokumentation", "api dokumentation"], "Die offizielle Dokumentation ist ein zentrales Arbeitsmittel in Java.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "j02_klassen_und_objekte",
                    "title": "Objektorientierte Programmierung: Klassen, Objekte, Attribute und Methoden",
                    "estimated_minutes": 60,
                    "objectives": [
                        "Klassen und Objekte unterscheiden",
                        "Attribute, Methoden, Konstruktoren und Methodenueberladung anwenden",
                        "statische Attribute und Methoden sowie Best Practices einordnen",
                    ],
                    "lesson_markdown": """
## Klassen modellieren Objekte

Eine Klasse beschreibt, welche Daten und welches Verhalten ein Objekt besitzt.

```java
public class Konto {
    private double stand;

    public Konto(double startwert) {
        this.stand = startwert;
    }

    public void einzahlen(double betrag) {
        stand += betrag;
    }
}
```

## Wichtige Begriffe

- **Attribute** speichern Zustand
- **Methoden** beschreiben Verhalten
- **Konstruktoren** erzeugen Objekte in einem gueltigen Anfangszustand
- **Methodenueberladung** erlaubt mehrere Varianten mit gleichem Namen
- **statisch** bedeutet: zur Klasse gehoerig statt zu einem einzelnen Objekt
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("j02_q1", "Was beschreibt eine Klasse am besten?", [("a", "Ein Bauplan fuer Objekte"), ("b", "Nur eine Schleife"), ("c", "Eine Fehlermeldung"), ("d", "Nur ein Klassendiagramm ohne Code")], "a", "Klassen sind Bauplaene fuer Objekte."),
                        _single("j02_q2", "Wofuer dient ein Konstruktor?", [("a", "Zum Testen von Listen"), ("b", "Zum Erzeugen und Initialisieren eines Objekts"), ("c", "Zum Ueberschreiben einer Klasse"), ("d", "Zum Importieren von Interfaces")], "b", "Ein Konstruktor initialisiert neue Objekte."),
                        _text("j02_q3", "Wie nennt man mehrere Methoden mit gleichem Namen, aber unterschiedlichen Parametern?", ["methodenueberladung", "ueberladung"], "Dieses Konzept heisst Methodenueberladung.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "j03_vererbung_und_datenstrukturen",
                    "title": "Vererbung, Interfaces und Datenstrukturen",
                    "estimated_minutes": 65,
                    "objectives": [
                        "Vererbung, abstrakte Klassen und Interfaces unterscheiden",
                        "Ueberschreiben von Methoden und Konstruktoren in Hierarchien einordnen",
                        "Listen, Sets und Maps als zentrale Datenstrukturen anwenden",
                    ],
                    "lesson_markdown": """
## Klassenbeziehungen und Sammlungen

Vererbung erlaubt es, gemeinsame Eigenschaften in Oberklassen zu beschreiben.
Interfaces definieren dagegen vertragliche Faehigkeiten.

```java
public interface Druckbar {
    void drucken();
}
```

## Datenstrukturen

- `List` speichert geordnete Elemente
- `Set` speichert eindeutige Elemente
- `Map` ordnet Schluessel Werte zu

Abstrakte Klassen und Interfaces helfen beim sauberen objektorientierten Design.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("j03_q1", "Welche Struktur eignet sich fuer geordnete Elemente mit moeglichen Duplikaten?", [("a", "List"), ("b", "Set"), ("c", "Map"), ("d", "Interface")], "a", "Eine `List` speichert geordnete Elemente."),
                        _single("j03_q2", "Was beschreibt ein Interface in Java am besten?", [("a", "Einen Vertrag fuer Faehigkeiten"), ("b", "Einen Speicherfehler"), ("c", "Eine ausgefuehrte Hauptfunktion"), ("d", "Nur eine Variable")], "a", "Interfaces beschreiben vertragliche Faehigkeiten."),
                        _text("j03_q3", "Wie heisst die Datenstruktur fuer Schluessel-Wert-Zuordnungen in Java?", ["map"], "`Map` ordnet Schluessel Werte zu.", placeholder="Datenstruktur"),
                    ],
                },
                {
                    "module_id": "j04_zusaetzliche_konzepte",
                    "title": "Generische Elemente, Fehlerbehebung, JUnit und Design-Patterns",
                    "estimated_minutes": 55,
                    "objectives": [
                        "generische Typen in Java einordnen",
                        "JUnit-Tests und Fehlersuche als Qualitaetswerkzeuge verstehen",
                        "Design-Patterns als wiederkehrende Loesungsideen beschreiben",
                    ],
                    "lesson_markdown": """
## Qualitaet und Wiederverwendung

Generische Typen wie `List<String>` machen Code sicherer und besser lesbar.
JUnit hilft dabei, Verhalten automatisiert zu pruefen.

```java
List<String> namen = new ArrayList<>();
```

Fehlerbehebung bedeutet, systematisch Ursachen zu suchen und Programme gezielt zu pruefen.
Design-Patterns sind typische Loesungsideen fuer wiederkehrende Entwurfsprobleme.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("j04_q1", "Wozu dienen generische Typen wie `List<String>`?", [("a", "Sie machen Typen explizit und sicherer"), ("b", "Sie ersetzen alle Klassen"), ("c", "Sie kompilieren Programme ohne Java"), ("d", "Sie loeschen Fehlermeldungen")], "a", "Generics verbessern Typsicherheit und Lesbarkeit."),
                        _single("j04_q2", "Wofuer wird JUnit im Kurs genutzt?", [("a", "Fuer automatisierte Tests"), ("b", "Zum Zeichnen von Klassendiagrammen"), ("c", "Zum Speichern von Maps"), ("d", "Zum Installieren der IDE")], "a", "JUnit ist ein Testframework fuer Java."),
                        _text("j04_q3", "Wie nennt man wiederkehrende bewaehrte Loesungsideen fuer typische Entwurfsprobleme?", ["design patterns", "design-patterns", "designpatterns"], "Diese Loesungsideen nennt man Design-Patterns.", placeholder="Begriff"),
                    ],
                },
                {
                    "module_id": "j05_projektplanung_und_umsetzung",
                    "title": "Planen, realisieren und erlaeutern einer Programmieraufgabe",
                    "estimated_minutes": 60,
                    "objectives": [
                        "eine Programmieraufgabe in Arbeitsschritte zerlegen",
                        "Hauptfunktionalitaet und Benutzerinterface sinnvoll aufbauen",
                        "Fertigstellung und Erlaeuterung eines Programms reflektieren",
                    ],
                    "lesson_markdown": """
## Von der Idee zum Programm

Eine gute Java-Aufgabe beginnt mit Planung:

1. Aufgabe verstehen
2. Klassen und Verantwortlichkeiten festlegen
3. Hauptfunktionalitaet umsetzen
4. Benutzerinterface planen
5. Testen, verbessern und erklaeren

Im Unterricht geht es nicht nur um Code, sondern auch um Nachvollziehbarkeit, Begruendung
von Entscheidungen und verstaendliche Darstellung der Loesung.
""".strip(),
                    "quiz_pass_ratio": 0.67,
                    "questions": [
                        _single("j05_q1", "Was gehoert zu einer guten Projektplanung?", [("a", "Arbeitsschritte und Verantwortlichkeiten festlegen"), ("b", "Direkt alles ohne Plan schreiben"), ("c", "Nur das Benutzerinterface zeichnen"), ("d", "Nur Fehlermeldungen sammeln")], "a", "Projektplanung strukturiert den Weg zur Loesung."),
                        _single("j05_q2", "Warum sollte ein Programm am Ende erklaert werden koennen?", [("a", "Damit Entscheidungen und Struktur nachvollziehbar sind"), ("b", "Damit keine Klassen noetig sind"), ("c", "Damit Tests entfallen"), ("d", "Damit Variablen automatisch entstehen")], "a", "Eine Loesung muss fachlich nachvollziehbar sein."),
                        _text("j05_q3", "Wie nennt man die sichtbare oder bedienbare Schicht eines Programms fuer den Nutzer?", ["benutzerinterface", "ui"], "Diese Schicht nennt man Benutzerinterface.", placeholder="Begriff"),
                    ],
                },
            ],
            "final_assessment": {
                "assessment_id": "java-oop-grundlagen-abschluss",
                "title": "Abschlusspruefung Java OOP Grundlagen",
                "instructions": "Bearbeite die Fragen eigenstaendig. Die Abschlusspruefung prueft Java-Grundlagen, OOP, Datenstrukturen und Projektverstaendnis.",
                "questions": [
                    _single("jf_q1", "Welche Methode startet ein einfaches Java-Programm?", [("a", "println"), ("b", "main"), ("c", "test"), ("d", "build")], "b", "Die `main`-Methode startet ein Java-Programm."),
                    _single("jf_q2", "Wofuer steht eine Klasse in Java?", [("a", "Fuer einen Bauplan von Objekten"), ("b", "Fuer eine Fehlermeldung"), ("c", "Fuer ein einzelnes Interface ohne Verhalten"), ("d", "Nur fuer Listen")], "a", "Klassen beschreiben Objekte."),
                    _single("jf_q3", "Welche Datenstruktur speichert eindeutige Elemente?", [("a", "List"), ("b", "Map"), ("c", "Set"), ("d", "Array nur mit Texten")], "c", "`Set` speichert eindeutige Elemente."),
                    _single("jf_q4", "Was beschreibt ein Interface in Java?", [("a", "Einen Vertrag fuer Methoden oder Faehigkeiten"), ("b", "Nur einen Konstruktor"), ("c", "Nur eine primitive Variable"), ("d", "Eine Fehlermeldung des Compilers")], "a", "Interfaces beschreiben vertragliche Faehigkeiten."),
                    _single("jf_q5", "Wofuer wird JUnit genutzt?", [("a", "Fuer automatisierte Tests"), ("b", "Zum Zeichnen von Fenstern"), ("c", "Zum Ersetzen aller Klassen"), ("d", "Zum Speichern von Maps")], "a", "JUnit prueft Verhalten automatisiert."),
                    _single("jf_q6", "Wozu dienen generische Typen wie `List<String>`?", [("a", "Zur Typsicherheit und Klarheit"), ("b", "Zum Loeschen von Klassen"), ("c", "Zum Vermeiden aller Methoden"), ("d", "Nur fuer Klassendiagramme")], "a", "Generics sorgen fuer mehr Typsicherheit."),
                    _text("jf_q7", "Wie nennt man das Ueberschreiben einer Methode in einer Unterklasse?", ["ueberschreiben", "override"], "Eine Unterklasse kann Methoden ueberschreiben.", placeholder="Begriff"),
                    _text("jf_q8", "Wie nennt man bewaehrte Loesungsideen fuer typische Entwurfsprobleme in der Softwareentwicklung?", ["design patterns", "design-patterns", "designpatterns"], "Diese Loesungsideen nennt man Design-Patterns.", placeholder="Begriff"),
                ],
            },
        },
    }
)


def list_courses() -> list[dict[str, Any]]:
    return [dict(course) for course in COURSE_CATALOG.values()]


def get_course(course_id: str) -> dict[str, Any] | None:
    course = COURSE_CATALOG.get(course_id)
    return dict(course) if course else None
