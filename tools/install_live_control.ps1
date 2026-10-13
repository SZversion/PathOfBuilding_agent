param(
	[string]$InstallRoot = (Join-Path $PSScriptRoot '..\src')
)

$ErrorActionPreference = 'Stop'
$resolvedInstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$modulesRoot = Join-Path $resolvedInstallRoot 'Modules'
$mainPath = Join-Path $modulesRoot 'Main.lua'
$sourceModulesRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\src\Modules'))

if (-not (Test-Path -LiteralPath $mainPath -PathType Leaf)) {
	throw "PoB Main.lua was not found at $mainPath"
}
if (-not (Test-Path -LiteralPath (Join-Path $modulesRoot 'BuildListHelpers.lua') -PathType Leaf)) {
	throw "The selected directory does not look like a Path of Building installation: $resolvedInstallRoot"
}

$moduleNames = @(
	'AgentControl.lua',
	'AgentErrorRegistry.lua',
	'AgentBridge.lua',
	'AgentInProcess.lua',
	'AgentSnapshot.lua',
	'AgentContext.lua',
	'AgentTool.lua',
	'AgentTrace.lua',
	'AgentMechanismTool.lua'
)
foreach ($moduleName in $moduleNames) {
	if (-not (Test-Path -LiteralPath (Join-Path $sourceModulesRoot $moduleName) -PathType Leaf)) {
		throw "Required source module is missing: $moduleName"
	}
}

$mainText = [System.IO.File]::ReadAllText($mainPath)
$newline = if ($mainText.Contains("`r`n")) { "`r`n" } else { "`n" }
$hookAlreadyInstalled = $mainText.Contains('PoB Agent control channel')
if ($hookAlreadyInstalled -and (-not $mainText.Contains('self.agentControl:OnFrame()') -or -not $mainText.Contains('self.agentControl:Shutdown()'))) {
	throw 'A partial live control hook was found. Restore its backup before reinstalling.'
}

$initAnchor = "`tself.buildSortMode = `"NAME`""
$frameAnchor = "`tif not self.saveNewModCache then"
$shutdownAnchor = "function main:Shutdown()${newline}`tself:CallMode(`"Shutdown`")"
foreach ($anchor in @($initAnchor, $frameAnchor, $shutdownAnchor)) {
	if (-not $hookAlreadyInstalled -and [System.Text.RegularExpressions.Regex]::Matches($mainText, [System.Text.RegularExpressions.Regex]::Escape($anchor)).Count -ne 1) {
		throw "PoB Main.lua does not match the expected patch point: $anchor"
	}
}

$initHook = @'
	-- The live Agent control channel is optional. Failure to initialize it must
	-- never prevent the normal PoB UI from starting.
	local controlModuleOk, controlModule = pcall(LoadModule, "Modules/AgentControl")
	if controlModuleOk and controlModule and type(controlModule.new) == "function" then
		local controlOk, control, controlErr = pcall(controlModule.new, self)
		if controlOk and control then
			self.agentControl = control
		else
			ConPrintf("PoB Agent control channel is unavailable: %s", tostring(controlOk and controlErr or control))
		end
	else
		ConPrintf("PoB Agent control module is unavailable: %s", tostring(controlModule))
	end
'@
$frameHook = @'
	if self.agentControl then
		self.onFrameFuncs["AgentControl"] = function()
			self.agentControl:OnFrame()
		end
	end
'@
$shutdownHook = @'
	if self.agentControl then
		self.agentControl:Shutdown()
		self.agentControl = nil
	end
'@

$patchedMain = $mainText
if (-not $hookAlreadyInstalled) {
	$patchedMain = $mainText.Replace($initAnchor, $initAnchor + $newline + $initHook.TrimEnd())
	$patchedMain = $patchedMain.Replace($frameAnchor, $frameHook.TrimEnd() + $newline + $frameAnchor)
	$shutdownReplacement = 'function main:Shutdown()' + $newline + $shutdownHook.TrimEnd() + $newline + "`tself:CallMode(`"Shutdown`")"
	$patchedMain = $patchedMain.Replace($shutdownAnchor, $shutdownReplacement)
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $resolvedInstallRoot ".pob-agent-live-backup-$stamp"
New-Item -ItemType Directory -Path $backupRoot | Out-Null
Copy-Item -LiteralPath $mainPath -Destination (Join-Path $backupRoot 'Main.lua')
$previousModules = @()
foreach ($moduleName in $moduleNames) {
	$destination = Join-Path $modulesRoot $moduleName
	$existed = Test-Path -LiteralPath $destination -PathType Leaf
	if ($existed) {
		Copy-Item -LiteralPath $destination -Destination (Join-Path $backupRoot $moduleName)
	}
	$previousModules += [pscustomobject]@{ name = $moduleName; existed = $existed }
}

try {
	foreach ($moduleName in $moduleNames) {
		if ($sourceModulesRoot -ne $modulesRoot) {
			Copy-Item -LiteralPath (Join-Path $sourceModulesRoot $moduleName) -Destination (Join-Path $modulesRoot $moduleName) -Force
		}
	}
	$encoding = [System.Text.UTF8Encoding]::new($false)
	[System.IO.File]::WriteAllText($mainPath, $patchedMain, $encoding)
	$manifest = [pscustomobject]@{
		installRoot = $resolvedInstallRoot
		backupRoot = $backupRoot
		mainFile = 'Modules\Main.lua'
		modules = $previousModules
		installedAt = (Get-Date).ToString('o')
	}
	$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backupRoot 'manifest.json') -Encoding UTF8
} catch {
	Copy-Item -LiteralPath (Join-Path $backupRoot 'Main.lua') -Destination $mainPath -Force
	foreach ($module in $previousModules) {
		$destination = Join-Path $modulesRoot $module.name
		$backup = Join-Path $backupRoot $module.name
		if ($module.existed -and (Test-Path -LiteralPath $backup -PathType Leaf)) {
			Copy-Item -LiteralPath $backup -Destination $destination -Force
		} elseif (Test-Path -LiteralPath $destination -PathType Leaf) {
			Remove-Item -LiteralPath $destination -Force
		}
	}
	throw
}

[pscustomobject]@{
	status = if ($hookAlreadyInstalled) { 'updated_for_next_start' } else { 'installed_for_next_start' }
	installRoot = $resolvedInstallRoot
	backupRoot = $backupRoot
	modulesCopied = $moduleNames.Count
	mainHooked = $true
} | ConvertTo-Json -Compress
