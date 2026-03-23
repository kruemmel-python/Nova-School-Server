# Pädagogische Begleitung

Dieses Modul beschreibt, wie Lehrkräfte Nova School nicht nur als Code-Editor, sondern als Lernbeobachtungs- und Begleitsystem nutzen.

## Grundidee

Nova School kombiniert drei für Unterricht besonders wertvolle Perspektiven:

- sichtbare Arbeitsstände in Dateien und Notebooks
- sichtbare Kommunikationsräume im Projekt- und Gruppenkontext
- sichtbare Lernspuren durch Mentor-Verläufe, Review-Einreichungen und Run-Analytics

## Zugriff auf Schülerprojekte

Lehrkräfte können im aktuellen Systemstand alle Projekte öffnen. Das ist didaktisch relevant für:

- gezielte Hilfestellung in laufenden Projekten
- Sicht auf Gruppenarbeit
- Einsicht in Mentor-Verläufe
- Moderation in Projektchats

## Sokratischer Mentor als Diagnoseinstrument

Der Mentor ist nicht als Lösungsautomat gedacht, sondern als fragender Lernbegleiter. Intern wird der Verlauf pro Projekt und Benutzer als Thread geführt.

### Wofür Lehrkräfte den Mentor-Verlauf nutzen sollten

- um zu prüfen, ob der Schüler mit Verständnis arbeitet oder nur nach der Lösung sucht
- um zu sehen, ob die KI gute Rückfragen stellt
- um wiederkehrende fachliche Fehlvorstellungen zu erkennen
- um bei Bedarf die Aufgabenstellung nachzuschärfen

### Didaktische Auswertung

Achten Sie auf folgende Muster:

- Der Schüler beschreibt den Fehler präzise: gutes Problembewusstsein
- Der Schüler fragt nur nach fertigem Code: erhöhtes Copy-Paste-Risiko
- Der Mentor stellt kleinschrittige Fragen: guter sokratischer Verlauf
- Der Mentor springt zu schnell zur Lösung: Prompt oder Freigabepraxis nachjustieren

## Review-Analytics für Lernstandsdiagnose

Im Review-Modul werden nicht nur Einreichungen und Zuweisungen angezeigt, sondern auch Kennzahlen aus den Audit-Daten.

Wichtige Metriken:

| Metrik | Bedeutung |
| --- | --- |
| `run_count` | Anzahl protokollierter Ausführungen des Projekts |
| `failed_runs_before_success` | Anzahl fehlgeschlagener Läufe vor dem ersten erfolgreichen Lauf |
| `succeeded` | Ob mindestens ein erfolgreicher Run erfasst wurde |

### Interpretation in der Praxis

- Viele Fehlversuche bei anschließendem Erfolg sprechen oft für produktives iteratives Lernen.
- Sehr wenige Läufe bei plötzlich korrektem Ergebnis können auf externe Hilfen oder Copy-Paste hindeuten.
- Viele Fehlversuche ohne Erfolg deuten häufig auf Blockaden, unklare Grundlagen oder zu hohe Aufgabenkomplexität hin.

## Pädagogisch sinnvolle Eingriffsreihenfolge

Empfohlenes Vorgehen vor einer direkten Intervention:

1. Letzten Run und Fehlermeldung lesen.
2. Mentor-Thread prüfen.
3. Review-Status und Feedback sichten.
4. Falls Gruppenarbeit vorliegt: Presence und Kollaborationsmuster im Notebook betrachten.
5. Erst danach entscheiden, ob ein direkter Hinweis, eine Rückfrage oder eine Umgruppierung sinnvoll ist.

## Chat als Unterrichtsraum

Lehrkräfte können projektbezogene und gruppenbezogene Chats einsehen. Das ist besonders nützlich für:

- Begleitung von Gruppenarbeit
- Beobachtung von Rollenverteilung
- Erkennen von Sackgassen oder Off-Topic-Kommunikation
- Moderiertes Eingreifen bei Verstößen

## Muting professionell einsetzen

Die Mute-Funktion ist ein Moderationswerkzeug, kein Strafmechanismus. Gute Praxis:

- klaren Grund dokumentieren
- kurze, verhältnismäßige Dauer wählen
- im Anschluss Lern- oder Kommunikationsregel transparent erklären

## Grenzen des aktuellen Stands

Wichtig für eine saubere Erwartungssteuerung:

- Es gibt derzeit keine separate Vollansicht aller Audit-Log-Einträge für Lehrkräfte.
- Die Analytics werden vor allem im Review-Kontext sichtbar.
- Die Live-Sync-Revisionsnummern sind keine vollständige Versionshistorie.
- Eine grafische Wiederherstellung älterer Dateistände ist aktuell nicht Teil der Oberfläche.

## Gute Unterrichtsszenarien

### Einzelarbeit mit Mentor

- Lehrkraft gibt eine klar eingegrenzte Programmieraufgabe.
- Schüler arbeitet mit Live-Run und Mentor.
- Lehrkraft prüft bei Bedarf den Mentor-Thread und die Run-Entwicklung.

### Gruppenarbeit im Notebook

- Gruppe arbeitet im gemeinsamen Notebook.
- Lehrkraft beobachtet Presence-Chips und Projektchat.
- Bei Bedarf greift die Lehrkraft moderierend oder fachlich ein.

### Abgabe mit Peer Review

- Schüler reichen Projekte ein.
- Das System weist Reviews anonymisiert zu.
- Lehrkraft nutzt Feedback und Analytics nicht nur für Bewertung, sondern für Diagnose des Arbeitsprozesses.
