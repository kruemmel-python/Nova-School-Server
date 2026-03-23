# Ueberblick und Rollenmodell

Nova School ist eine mandantenfaehige Entwicklungsumgebung fuer Unterricht, Uebung, Abgabe und technische Betreuung. Das System kombiniert Editor, Notebook, Live-Terminal, Referenzbibliothek, KI-Unterstuetzung, Auditierbarkeit und sichere Runner in einer gemeinsamen Schuloberflaeche.

## Kernprinzipien

- **Sichere Ausfuehrung:** Code laeuft kontrolliert ueber Runner, Sandbox und optional Container-Isolation.
- **Rollenbasierter Zugriff:** Jeder Benutzer arbeitet mit einem klaren Rechteprofil.
- **Nachvollziehbarkeit:** Aenderungen, Reviews und viele Verwaltungsaktionen werden protokolliert.
- **Offline-Lernen:** Referenzbibliotheken und Produktdokumentation sind lokal verfuegbar.
- **Didaktische Begleitung:** Lehrkraefte koennen Rechte, KI-Zugang, Chats und Reviews steuern.

## Rollen im System

| Rolle | Hauptaufgabe | Typischer Fokus |
| --- | --- | --- |
| Student | Lernen, Programmieren, Abgeben, kollaborieren | Projekte, Notebooks, Chat, Referenzen, Mentor |
| Teacher | Begleiten, moderieren, freigeben, auswerten | Gruppen, Rechte, Chataufsicht, Lernanalyse |
| Admin | Technischer Betrieb und globale Verwaltung | Servereinstellungen, Benutzerverwaltung, Sicherheit, Runtime |

## Arbeitslogik

1. Benutzer melden sich mit ihrem Profil an.
2. Projekte liegen in persoenlichen oder gruppenbezogenen Workspaces.
3. Rechte werden aus Rolle, Gruppenrechten und Nutzer-Overrides zusammengesetzt.
4. Code laeuft ueber Host-Runner oder Container-Runner.
5. Dokumentation, KI, Chat, Reviews und Deployments folgen denselben Rechtepruefungen.

## Diese Referenz und die Bedienungsanleitung

Die **Produktdokumentation** in diesem Bereich beschreibt das System als Ganzes: Architektur, Rechte, Module, Betrieb und Best Practices.

Die **Bedienungsanleitung** unter [Bedienungsanleitung](/manual) bleibt rollenbasiert und fuehrt Schritt fuer Schritt durch konkrete Oberflaechenablaeufe.

## Wann diese Dokumentation sinnvoll ist

- Wenn Lehrkraefte verstehen wollen, wie Rechte technisch und didaktisch zusammenwirken.
- Wenn Administratoren Container, Netzwerkgrenzen oder LM Studio aufsetzen.
- Wenn Schueler nachschlagen wollen, wie Projekte, Notebook-Zellen oder Live-Terminals zusammenhaengen.
- Wenn eine Schule ein belastbares Referenzwerk fuer Einfuehrung, Betrieb und Nachweisbarkeit braucht.

## Verwandte Funktionen

- [Benutzer, Gruppen und Rechte](/reference?area=nova-school&doc=02_Benutzer_Gruppen_und_Rechte.md)
- [Editor, Notebooks und Live-Terminal](/reference?area=nova-school&doc=04_Editor_Notebooks_und_Live_Terminal.md)
- [Runner, Container, Netzwerk und Sicherheit](/reference?area=nova-school&doc=07_Runner_Container_Netzwerk_und_Sicherheit.md)
