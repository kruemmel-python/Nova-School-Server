# Nova School Wiki für Lehrkräfte und Administration

Diese Dokumentation richtet sich an Lehrkräfte, IT-Verantwortliche und Administratoren des Nova School Servers. Sie trennt bewusst zwischen didaktischer Nutzung im Unterricht und technischem Systembetrieb.

## Ziel dieser Wiki-Sektion

- Lehrkräfte erhalten einen belastbaren Leitfaden für Unterricht, Moderation, Lernstandsdiagnose und Review-Prozesse.
- Administratoren erhalten eine präzise Referenz für Start, Konfiguration, Rechtevergabe, Sicherheitsbetrieb und Wartung.
- Beide Rollen arbeiten mit derselben Plattform, aber mit unterschiedlichen Verantwortlichkeiten.

## Dokumentenstruktur

- [01 Serverstart und Bootstrap](./01_Serverstart_und_Bootstrap.md)
- [02 Pädagogische Begleitung](./02_Paedagogische_Begleitung.md)
- [03 Rollen, Rechte und Moderation](./03_Rollen_Rechte_und_Moderation.md)
- [04 Systembetrieb, Sicherheit und Workspaces](./04_Systembetrieb_Sicherheit_und_Workspaces.md)
- [05 Playground, Reviews und Deployments](./05_Playground_Reviews_und_Deployments.md)

## Rollenverständnis

### Lehrkraft

Der Schwerpunkt liegt auf:

- Begleitung von Lernprozessen
- Sicht auf Projekte, Chats und Mentor-Verläufe
- Moderation von Kommunikationsräumen
- Nutzung von Peer-Review und Analytics

### Admin

Der Schwerpunkt liegt auf:

- Serverstart und Betriebsstabilität
- Benutzer-, Gruppen- und Rechteverwaltung
- Runner-Backends, Container-Images und Limits
- LM-Studio-Anbindung, Deployment-Artefakte und Tenant-Quoten

## Wichtiger Systemhinweis

Im aktuellen Projektstand sind die Standardrollen `teacher` und `admin` technisch beide vollständig freigeschaltet. Für den professionellen Betrieb wird trotzdem eine organisatorische Trennung empfohlen:

- Lehrkräfte arbeiten im Tagesbetrieb mit Unterricht, Projekten und Moderation.
- Die Rolle `admin` sollte für globale Konfigurationsänderungen, Quoten, Images und Infrastruktur reserviert bleiben.

## Architekturprinzipien

- Mandantenfähig: Einstellungen, Quoten und Sicherheitsobjekte sind tenantbezogen aufgebaut.
- Rollenbasiert: Rechte werden über Rollen, Gruppen-Overrides und Benutzer-Overrides aufgelöst.
- Sicherheitsorientiert: Nova School nutzt zentrale Bausteine aus NovaShell für Security Plane, ToolSandbox und KI-Runtime.
- Unterrichtstauglich: Live-Editor, Notebooks, Peer Review, Mentor und Chat sind in einer Oberfläche gebündelt.

## Stand der Implementierung

Diese Wiki-Seite dokumentiert den tatsächlichen Ist-Zustand des Projekts, nicht nur Zielbilder. Deshalb werden wichtige Grenzen ausdrücklich benannt:

- Live-Sync-Revisionsnummern sind Synchronisationsstände, kein vollständiges Version-Control-System.
- Es gibt aktuell keine eigene grafische Wiederherstellungsansicht für frühere Dateiversionen.
- Reviewer-Aliasse im Peer Review werden systemseitig erzeugt und nicht manuell gepflegt.
- Harte Netztrennung wird professionell ueber den Container-Modus erreicht; der Host-Prozess-Runner ist nur noch ein ausdruecklich freizugebender Ausnahme-Fallback.
