$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m unittest discover -s nova_school_server\tests -p "test_*.py" -v
} else {
    python -m unittest discover -s nova_school_server\tests -p "test_*.py" -v
}
