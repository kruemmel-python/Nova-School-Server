$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m nova_school_server
} else {
    python -m nova_school_server
}
