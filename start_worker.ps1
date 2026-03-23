$ErrorActionPreference = "Stop"

$server = if ($env:NOVA_SCHOOL_SERVER_URL) { $env:NOVA_SCHOOL_SERVER_URL } else { "http://127.0.0.1:8877" }
$workerId = if ($env:NOVA_SCHOOL_WORKER_ID) { $env:NOVA_SCHOOL_WORKER_ID } else { "lab-node-01" }
$token = $env:NOVA_SCHOOL_WORKER_TOKEN
$advertiseHost = if ($env:NOVA_SCHOOL_WORKER_HOST) { $env:NOVA_SCHOOL_WORKER_HOST } else { "" }
$workRoot = if ($env:NOVA_SCHOOL_WORKER_ROOT) { $env:NOVA_SCHOOL_WORKER_ROOT } else { "$HOME\\.nova-school-worker" }

if (-not $token) {
    throw "Setze NOVA_SCHOOL_WORKER_TOKEN vor dem Start des Worker-Agenten."
}

$arguments = @(
    "-m", "nova_school_server.worker_agent",
    "--server", $server,
    "--worker-id", $workerId,
    "--token", $token,
    "--work-root", $workRoot
)

if ($advertiseHost) {
    $arguments += @("--advertise-host", $advertiseHost)
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python wurde nicht gefunden."
}

& $python.Source @arguments
