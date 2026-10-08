param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "out")
)

$ErrorActionPreference = "Stop"
$sourceRevision = "v2.5.4"
$sourceCommit = "3b1a3468223d0ebd4042d6ce76fc6144718ef79b"
$sourceUrl = "https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic.git"
$workDirectory = Join-Path $env:TEMP ("pob-simplegraphic-hangul-" + [guid]::NewGuid().ToString("N"))
$sourceDirectory = Join-Path $workDirectory "source"
$buildDirectory = Join-Path $workDirectory "build"
$installDirectory = Join-Path $workDirectory "install-prefix"
$patchFile = Join-Path $PSScriptRoot "simplegraphic-hangul-cache.patch"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required to fetch the pinned SimpleGraphic source."
}
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw "CMake and Visual Studio 2022 C++ Build Tools are required."
}
if (-not (Test-Path -LiteralPath $patchFile)) {
    throw "The SimpleGraphic source patch is missing: $patchFile"
}

New-Item -ItemType Directory -Path $workDirectory -Force | Out-Null
git clone --depth 1 --branch $sourceRevision --recursive $sourceUrl $sourceDirectory
if ($LASTEXITCODE -ne 0) { throw "Could not fetch SimpleGraphic $sourceRevision." }
$checkedOutCommit = git -C $sourceDirectory rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $checkedOutCommit.Trim() -ne $sourceCommit) {
    throw "SimpleGraphic $sourceRevision resolved to unexpected commit $checkedOutCommit."
}

git -C $sourceDirectory apply --check $patchFile
if ($LASTEXITCODE -ne 0) { throw "The SimpleGraphic patch does not apply to $sourceRevision." }
git -C $sourceDirectory apply $patchFile
if ($LASTEXITCODE -ne 0) { throw "Could not apply the SimpleGraphic patch." }

cmake -S $sourceDirectory -B $buildDirectory -A x64 -G "Visual Studio 17 2022" `
    "-DCMAKE_TOOLCHAIN_FILE=$(Join-Path $sourceDirectory 'vcpkg/scripts/buildsystems/vcpkg.cmake')" `
    "-DCMAKE_INSTALL_PREFIX=$installDirectory" `
    -DVCPKG_TARGET_TRIPLET=x64-windows-release
if ($LASTEXITCODE -ne 0) { throw "SimpleGraphic CMake configuration failed." }

cmake --build $buildDirectory --config Release --target SimpleGraphic
if ($LASTEXITCODE -ne 0) { throw "SimpleGraphic build failed." }

$builtDll = Join-Path $buildDirectory "Release/SimpleGraphic.dll"
if (-not (Test-Path -LiteralPath $builtDll)) { throw "Built SimpleGraphic.dll was not found." }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
Copy-Item -LiteralPath $builtDll -Destination (Join-Path $OutputDirectory "SimpleGraphic.dll") -Force
Write-Output (Join-Path $OutputDirectory "SimpleGraphic.dll")
