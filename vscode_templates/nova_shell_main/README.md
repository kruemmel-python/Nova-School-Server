# VS Code Vorlagen fuer `H:\Nova-shell-main`

Diese Dateien sind nur als Vorlage abgelegt, weil Aenderungen in `H:\Nova-shell-main` laut Projektvorgabe nicht direkt vorgenommen werden duerfen.

## Dateien

- `.vscode/settings.json`
- `cspell.json`

## Zweck

- richtiger Python-Interpreter fuer das Nova-Shell-Projekt
- reduzierte Pylance-Importwarnungen durch bessere Workspace-Konfiguration
- deutsches und englisches Woerterbuch fuer `cspell`
- Projektbegriffe fuer `nova_shell.py`

## Optionale Paketinstallation

Falls die Importwarnungen fuer optionale Features verschwinden sollen:

```powershell
cd H:\Nova-shell-main
python -m pip install -e ".[observability,arrow,wasm,gpu,guard]"
```

Nicht sinnvoll auf Windows:

- `bcc`
