# Benutzer, Gruppen und Rechte

Benutzerverwaltung in Nova School dient nicht nur der Anmeldung. Sie steuert Profilordner, Gruppenraeume, Chatrechte, KI-Freigaben, Runner-Zugriff, Netzwerkfreigaben und Administratorfunktionen.

## Objektmodell

- **Benutzer:** besitzt Benutzername, Anzeigename, Rolle, Status, Profilordner und optionale Einzelrechte.
- **Gruppe:** besitzt Gruppenordner, Mitglieder und Gruppenrechte.
- **Mitgliedschaft:** verbindet Benutzer mit Gruppen.
- **Rechteprofil:** wird aus Rollenstandard, Gruppen-Overrides und Nutzer-Overrides berechnet.

## Effektive Rechte

1. Zuerst gilt der Standard der Rolle.
2. Danach werden Gruppenrechte aufgeschaltet.
3. Danach greifen individuelle Nutzer-Overrides.
4. Explizite Verbote bleiben fuer den betroffenen Bereich bindend.

## Permission Keys

{{PERMISSION_TABLE}}

## Rollenstandard

{{ROLE_DEFAULTS_TABLE}}

## Typische Verwaltungsaufgaben

1. Einen neuen Schueler anlegen und einer Lerngruppe zuweisen.
2. Webzugriff oder KI fuer eine Gruppe freigeben oder sperren.
3. Den Status eines Nutzers aendern, zum Beispiel von aktiv auf gesperrt.
4. Einzelrechte fuer Sonderfaelle setzen, ohne die gesamte Rolle zu aendern.
5. Ein Passwort zuruecksetzen, ohne Klartextkennwoerter im Frontend anzuzeigen.

## Nachweisbarkeit und Protokollierung

Benutzerbezogene Verwaltungsaktionen muessen belegbar bleiben. Deshalb sollten folgende Aenderungen immer ueber die Verwaltungsoberflaeche erfolgen:

- Rollenwechsel
- Statuswechsel
- Aenderung des Anzeigenamens
- Passwort-Reset
- Rechte-Overrides

Diese Aenderungen werden im Audit-Kontext dokumentiert. Fuer Unterricht und Schulbetrieb ist das wichtig, weil Rechtefreigaben spaeter nachvollzogen werden muessen.

## Empfehlungen fuer Schulen

- Studentenkonten moeglichst ueber Gruppen statt ueber viele Einzelrechte steuern.
- `web.access`, `ai.use` und `admin.manage` nur bewusst und mit klarer Begruendung vergeben.
- Gesperrte oder pausierte Konten nicht loeschen, solange Nachweise und Projekte erhalten bleiben sollen.
- Lehrerrechte nicht als technische Adminrechte missverstehen. Unterrichtsbegleitung und Systembetrieb sind getrennte Aufgaben.
