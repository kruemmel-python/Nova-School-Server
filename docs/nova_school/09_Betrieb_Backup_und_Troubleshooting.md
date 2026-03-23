# Betrieb, Backup und Troubleshooting

Diese Seite richtet sich vor allem an Lehrkraefte mit Technikverantwortung und an Administratoren.

## Serverstart

Unter Windows:

```powershell
cd D:\Nova_school_server
.\start_server.ps1
```

Unter Linux:

```bash
cd /srv/Nova_school_server
./start_server.sh
```

## Wichtige Betriebsbausteine

- Datenbank mit Benutzern, Gruppen, Projekten, Reviews und Einstellungen
- `data/workspaces` fuer echte Projektdateien
- `data/reference_library` fuer gespiegelte Referenzquellen
- `wiki` fuer rollenbasierte Handbuecher
- `docs/nova_school` fuer die First-Party-Produktdokumentation

## Backups

Ein brauchbares Backup umfasst mindestens:

- Datenbanken
- Workspace-Ordner
- Referenzbibliothek
- Produkt- und Wiki-Dokumentation

## Pflege der Referenzbibliothek

- Externe Spiegel fuer Sprachen in `data/reference_library/packs/<bereich>`
- Nova-School-Produktdokumentation aus `docs/nova_school`
- automatischer Neuaufbau fuer lokale Produktdokumentation beim Aufruf

Falls ein manueller Neuaufbau noetig ist:

```powershell
cd D:\Nova_school_server
python -m nova_school_server.nova_product_docs
```

## Typische Fehlerbilder

### Server nicht im Netzwerk erreichbar

- auf `0.0.0.0` statt nur auf `127.0.0.1` binden
- Firewall fuer den Port freigeben
- korrekte LAN-IP pruefen

### Dokumentation bleibt auf Starter-Stand

- Importpfad pruefen
- Dateitypen und Unterordner `site` pruefen
- Browser hart neu laden
- bei Nova-School-Doku Quellordner `docs/nova_school` pruefen

### Code reagiert nicht auf Eingaben

- pruefen, ob das Programm wirklich `stdin` liest
- Live-Session statt Einmal-Lauf verwenden, wenn Prompt-Interaktion noetig ist
- Eingaben pro Datei- oder Zellsession getrennt betrachten

### Webzugriff ist gesperrt

- `web.access` fuer Benutzer oder Gruppe pruefen
- Backend-Modus und Container-Netzwerkmodus pruefen

## Empfehlungen fuer den Regelbetrieb

1. Container-Backend als Standard verwenden.
2. Benutzer- und Gruppenrechte regelmaessig pruefen.
3. Auditdaten nicht abschalten, wenn Nachvollziehbarkeit gefordert ist.
4. Dokumentationspacks und LM Studio zentral pflegen.
5. Aenderungen immer in `D:\Nova_school_server` vornehmen, nicht in Fremdverzeichnissen.
