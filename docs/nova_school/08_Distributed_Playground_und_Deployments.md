# Distributed Playground und Deployments

Nova School ist nicht nur eine Einzelplatz-IDE. Mit dem Playground und den Exportfunktionen lassen sich fortgeschrittene Unterrichtsszenarien abbilden.

## Distributed Playground

Der Playground nutzt die Sicherheits- und Vertrauensbasis des Systems, um verteilte Szenarien modellierbar zu machen.

Typische Bausteine:

- `topology.json` fuer die Struktur eines Szenarios
- Worker-Enrollments
- Trust-Policies
- abgesicherte Kommunikationsbeziehungen

## Didaktische Einsatzfaelle

- einfache Client-Server-Uebungen
- Microservice-Grundlagen
- Ausfallsimulation von Workern
- gesicherte Kommunikation mit Zertifikatsprofilen

## Deployments und Shares

Nova School kann Projekte aus der Entwicklungsoberflaeche heraus weitergeben:

- ZIP-Export fuer Abgabe oder Archivierung
- Share-Funktion fuer schulinterne oder kontrollierte Bereitstellung
- Deployment-Freigaben nur fuer berechtigte Nutzer oder Gruppen

## Grenzen

- Ein Deployment ersetzt keine vollstaendige Produktionsplattform.
- Freigaben muessen an Quotas und Rechte gebunden bleiben.
- Oeffentliche Verfuegbarkeit darf nicht automatisch aus der Projektbearbeitung folgen.

## Gute Praxis

- Playground als Lernlabor verstehen, nicht als offene Produktionsumgebung.
- Deployments erst nach Review oder Lehrkraftfreigabe ermoeglichen.
- Topologien versionieren und in Projekten dokumentieren.
