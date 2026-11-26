<#
Desktop launcher for the keyless OpenMontage video generator.

Double-click the "OpenMontage Generator" shortcut on the Desktop to enter a
topic. The script renders an MP4 into projects/desktop/ and opens the result.

Headless use (e.g. from a terminal):
    powershell -NoProfile -ExecutionPolicy Bypass -File launch_generator.ps1 -Topic "чому небо синє" -Offline
#>
param(
    [string]$Topic,
    [string]$Out,
    [switch]$Offline,
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

if ([string]::IsNullOrWhiteSpace($Topic)) {
    $Topic = [Microsoft.VisualBasic.Interaction]::InputBox(
        'Введіть тему відео, наприклад: чому небо синє',
        'OpenMontage — генератор відео',
        'чому небо синє'
    )
}
if ([string]::IsNullOrWhiteSpace($Topic)) {
    Write-Host 'Скасовано — тему не введено.'
    exit 0
}

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    [System.Windows.Forms.MessageBox]::Show(
        "Не знайдено $python`n`nСпочатку виконайте: make setup",
        'OpenMontage — помилка', [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
    exit 1
}

$outDir = Join-Path $root 'projects\desktop'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
if ([string]::IsNullOrWhiteSpace($Out)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $Out = Join-Path $outDir "video-$stamp.mp4"
}

# Cyrillic user-profile paths require UTF-8 mode for ffmpeg concat lists.
$env:PYTHONUTF8 = '1'

$generatorArgs = @('-m', 'generator', $Topic, '--out', $Out, '--timeout', '90')
if ($Offline) { $generatorArgs += '--offline' }

Write-Host '==> OpenMontage: генерація відео'
Write-Host "    Тема: $Topic"
Write-Host "    Файл: $Out"
Write-Host ''
& $python @generatorArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0 -or -not (Test-Path $Out)) {
    [System.Windows.Forms.MessageBox]::Show(
        "Генерацію перервано (код $exitCode).`n`nДеталі — у цьому вікні консолі.`nФайл: $Out",
        'OpenMontage — помилка', [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
} else {
    Write-Host ''
    Write-Host "==> Готово: $Out"
    if (-not $NoOpen) { Start-Process -FilePath $Out }
}

Write-Host ''
Read-Host 'Натисніть Enter, щоб закрити це вікно'
