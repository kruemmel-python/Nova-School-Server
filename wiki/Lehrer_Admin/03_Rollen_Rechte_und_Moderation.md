# Rollen, Rechte und Moderation

Nova School löst Rechte mehrstufig auf. Für den professionellen Betrieb ist wichtig, nicht nur einzelne Häkchen zu setzen, sondern die Vererbungslogik zu verstehen.

## Auflösungslogik der Berechtigungen

Die effektiven Rechte eines Benutzers entstehen in dieser Reihenfolge:

1. Rollen-Default
2. Gruppen-Overrides
3. Benutzer-Overrides

Wichtige Regel:

- Wenn ein Benutzer in mehreren Gruppen ist und eine Gruppe für ein Recht explizit `false` setzt, gewinnt dieses `false` auf Gruppenebene.
- Ein expliziter Benutzer-Override wird danach als letzte Instanz angewendet.

## Standardrollen

| Rolle | Charakteristik |
| --- | --- |
| `student` | Arbeitsrechte aktiv, aber standardmäßig kein Webzugriff, keine LM-Studio-Codehilfe, keine Moderations- oder Admin-Rechte |
| `teacher` | Technisch vollständig freigeschaltet |
| `admin` | Technisch vollständig freigeschaltet |

## Rechtekatalog

Der aktuelle Rechtekatalog umfasst 24 Permission-Keys.

| Key | Kategorie | Wirkung im System |
| --- | --- | --- |
| `project.create` | Arbeitsbereich | Neue Projekte anlegen |
| `workspace.personal` | Arbeitsbereich | Eigenen Profilordner und persönliche Projekte nutzen |
| `workspace.group` | Arbeitsbereich | Gruppenordner und Gruppenprojekte nutzen |
| `files.write` | Arbeitsbereich | Dateien im Editor speichern und ändern |
| `notebook.collaborate` | Arbeitsbereich | Live-Sync und gemeinsame Notebook-Bearbeitung verwenden |
| `chat.use` | Kommunikation | Chats im Editor nutzen |
| `docs.read` | Lernen | Offline-Dokumentation im System lesen |
| `web.access` | Netzwerk | Projektläufe mit Webzugriff zulassen |
| `ai.use` | KI | LM Studio und KI-Assistenz aktivieren |
| `mentor.use` | KI | Sokratischen Mentor verwenden |
| `run.python` | Runner | Python-Dateien und Python-Zellen ausführen |
| `run.javascript` | Runner | JavaScript-Dateien ausführen |
| `run.cpp` | Runner | C++ kompilieren und ausführen |
| `run.java` | Runner | Java kompilieren und ausführen |
| `run.rust` | Runner | Rust kompilieren und ausführen |
| `run.html` | Runner | HTML-Vorschau verwenden |
| `run.node` | Runner | Node.js-Dateien ausführen |
| `run.npm` | Runner | npm-Kommandos starten |
| `playground.manage` | Runner | Distributed Playground starten und stoppen |
| `review.use` | Lernen | Peer Review einreichen und bearbeiten |
| `deploy.use` | Deployment | Shares und Exporte erzeugen |
| `teacher.chat.observe` | Moderation | Chats systemweit einsehen |
| `teacher.chat.moderate` | Moderation | Benutzer zeitweise stummschalten |
| `admin.manage` | Administration | Admin-Panel und Systemverwaltung nutzen |

## Didaktisch sinnvolle Rechteprofile

### Standard für Schüler

- Projektarbeit, Dateibearbeitung und Notebook-Kollaboration aktiv
- `web.access` standardmäßig nur bei Bedarf
- `ai.use` nur gezielt nach Unterrichtsziel
- `mentor.use` bevorzugt gemeinsam mit `ai.use` freigeben, wenn KI didaktisch vorgesehen ist

### Standard für Lehrkräfte

- alle Unterrichtsfunktionen aktiv
- Moderationsrechte aktiv
- Zugriff auf Review, Mentor und Projekte aller Teilnehmer aktiv

### Standard für Admins

- globale Einstellungen, Benutzerverwaltung, Gruppenverwaltung und Infrastrukturoperation

## Wichtiger KI-Hinweis

Im Frontend ist der Mentor-Modus nur dann praktisch nutzbar, wenn sowohl `mentor.use` als auch `ai.use` verfügbar sind. Für Schüler reicht daher `mentor.use` allein in der Praxis nicht aus.

## Moderation von Chats

Chats existieren in drei typischen Räumen:

- Schul-Lounge
- Gruppenraum
- Projektraum

Lehrkräfte können alle Räume einsehen. Mit `teacher.chat.moderate` kann ein Mute gesetzt werden mit:

- Raum
- Zielbenutzer
- Dauer in Minuten
- Begründung

## Professionelle Betriebsregeln für Rechte

- Rechte sparsam und begründet freigeben
- Webzugriff nur für Web-Projekte, Paketmanagement oder bewusst geplante Aufgaben freischalten
- `run.npm` nicht pauschal für alle Gruppen aktivieren
- `deploy.use` nur dort freigeben, wo Abgabe oder Präsentation wirklich gebraucht wird
- `admin.manage` nicht als Alltagsrolle für Klassenbetrieb verwenden

## Empfohlene Kontrollroutine pro Halbjahr

1. Gruppenrechte prüfen.
2. Benutzer-Overrides bereinigen.
3. LM-Studio-Freigaben kontrollieren.
4. Webzugriff auf notwendige Gruppen beschränken.
5. Deployment-Rechte und Quoten mit Unterrichtszielen abgleichen.
