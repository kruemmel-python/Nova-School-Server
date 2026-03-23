# Projekte, Workspaces und Profile

Nova School organisiert Arbeit nicht nur ueber Dateien, sondern ueber klar getrennte Besitz- und Speicherbereiche. Jeder Benutzer und jede Gruppe kann einen eigenen Arbeitsbereich besitzen.

## Workspace-Typen

- **Persoenlicher Workspace:** gehoert genau einem Benutzer.
- **Gruppen-Workspace:** gehoert einer Gruppe und wird gemeinsam genutzt.
- **Projekt-Workspace:** konkreter Projektordner innerhalb eines persoenlichen oder gruppenbezogenen Bereichs.

## Typische Struktur

```text
data/
  workspaces/
    users/
      admin/
        projects/
          testprojekt/
            main.py
            .nova-school/
              notebook.json
              runs/
    groups/
      klasse-10a/
        projects/
          datenlabor/
```

## Was im Projektordner liegt

- Quellcode und Projektdateien
- Notebook-Daten
- Laufzeitspuren unter `.nova-school/runs`
- optionale Projektmetadaten fuer Zusammenarbeit, Reviews oder Playground-Szenarien

## Materialisierung und Wiederherstellung

Projekte werden vom Server materialisiert. Das bedeutet:

- fehlende Standarddateien koennen aus Templates erzeugt werden
- Notebook-Grunddaten werden bei Bedarf initialisiert
- Verwaltungsfunktionen arbeiten mit der tatsaechlichen Ordnerstruktur, nicht nur mit Datenbankeintraegen

## Besitz und Rechte

Ein Projekt ist immer an einen Besitzerkontext gebunden:

- Benutzerprojekte folgen den Rechten des Benutzers
- Gruppenprojekte folgen Gruppenmitgliedschaft und Gruppenrechten
- Lehrkraefte sehen mehr Kontexte, um Projekte begleiten und auswerten zu koennen

## Empfehlungen fuer Unterricht

- Einzelfaelle, Uebungen und Tests in persoenlichen Workspaces starten.
- Teamarbeit und Pair Programming in Gruppenprojekten organisieren.
- Abgabeprojekte mit klarer Benennung anlegen, zum Beispiel `02_sortieraufgabe` oder `web_portfolio`.
- Projektordner nicht manuell zwischen Besitzkontexten verschieben, sondern ueber die Serverlogik neu anlegen oder verwalten.

## Verwandte Themen

- [Editor, Notebooks und Live-Terminal](/reference?area=nova-school&doc=04_Editor_Notebooks_und_Live_Terminal.md)
- [Chat, Peer Review und Audit](/reference?area=nova-school&doc=06_Chat_Peer_Review_und_Audit.md)
- [Betrieb, Backup und Troubleshooting](/reference?area=nova-school&doc=09_Betrieb_Backup_und_Troubleshooting.md)
