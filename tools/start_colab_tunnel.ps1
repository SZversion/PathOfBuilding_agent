param(
	[string]$Session = 'pob-llm',
	[string]$Distribution = 'Ubuntu-24.04',
	[int]$Port = 11435
)

$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path $env:USERPROFILE '.colab-pob'
$identity = Join-Path $stateRoot 'id_ed25519'
if (-not (Test-Path -LiteralPath $identity -PathType Leaf)) {
	throw "Colab SSH identity was not found at $identity"
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
	throw "Port $Port is already in use. Check the existing tunnel before starting another."
}
& wsl.exe -d $Distribution -u sz -- colab status -s $Session
if ($LASTEXITCODE -ne 0) {
	throw "Colab session $Session is unavailable."
}
$knownHosts = Join-Path $stateRoot 'known_hosts'
$arguments = @(
	'-N', '-T',
	'-L', "127.0.0.1:${Port}:127.0.0.1:11434",
	'-o', 'ExitOnForwardFailure=yes',
	'-o', 'ServerAliveInterval=30',
	'-o', 'ServerAliveCountMax=3',
	'-o', 'BatchMode=yes',
	'-o', 'StrictHostKeyChecking=accept-new',
	'-o', "`"UserKnownHostsFile=$knownHosts`"",
	'-o', "`"ProxyCommand=wsl.exe -d $Distribution -u sz -- colab ssh --proxy-mode -s $Session -i /home/sz/.ssh/pob_colab_ed25519`"",
	'-i', "`"$identity`"",
	'root@colab-runtime'
)
$tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $stateRoot 'tunnel.log')
for ($attempt = 0; $attempt -lt 30; $attempt++) {
	Start-Sleep -Seconds 1
	$tunnel.Refresh()
	if ($tunnel.HasExited) {
		throw "Colab tunnel exited. See $(Join-Path $stateRoot 'tunnel.log')."
	}
	if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
		Write-Output "Colab tunnel ready at http://127.0.0.1:$Port (PID $($tunnel.Id))."
		return
	}
}
Stop-Process -Id $tunnel.Id
throw 'Colab tunnel did not become ready within 30 seconds.'
