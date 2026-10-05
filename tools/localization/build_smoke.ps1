param(
    [string]$CompilerRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.44.35207',
    [string]$SdkRoot = 'C:\Program Files (x86)\Windows Kits\10',
    [string]$SdkVersion = '10.0.26100.0',
    [string]$Artifacts = 'artifacts\english-localization'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$originalInclude = $env:INCLUDE
$originalLib = $env:LIB
Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Path $Artifacts -Force | Out-Null
    $env:INCLUDE = "$CompilerRoot\include;$SdkRoot\Include\$SdkVersion\ucrt;$SdkRoot\Include\$SdkVersion\shared;$SdkRoot\Include\$SdkVersion\um;$SdkRoot\Include\$SdkVersion\winrt"
    foreach ($architecture in @('x86', 'x64')) {
        $env:LIB = "$CompilerRoot\lib\$architecture;$SdkRoot\Lib\$SdkVersion\ucrt\$architecture;$SdkRoot\Lib\$SdkVersion\um\$architecture"
        foreach ($fixture in @('smoke_host', 'layout_smoke')) {
            $name = $fixture.Replace('_', '-')
            & "$CompilerRoot\bin\Hostx64\$architecture\cl.exe" /nologo /std:c++17 /EHsc /utf-8 /O2 /Gy "tools\localization\$fixture.cpp" "/Fe:$Artifacts\$name-$architecture.exe" "/Fo:$Artifacts\$name-$architecture.obj" /link /OPT:REF user32.lib gdi32.lib msimg32.lib
            if ($LASTEXITCODE -ne 0) { throw "$fixture build failed for $architecture" }
        }
        & "$Artifacts\layout-smoke-$architecture.exe"
        if ($LASTEXITCODE -ne 0) { throw "Layout checks failed for $architecture" }
    }
} finally {
    $env:INCLUDE = $originalInclude
    $env:LIB = $originalLib
    Pop-Location
}
