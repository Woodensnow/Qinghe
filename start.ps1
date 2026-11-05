$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not $env:PYTHONIOENCODING) { $env:PYTHONIOENCODING = 'utf-8' }
$pythonCandidates = @()
if ($env:PYTHON_BIN) { $pythonCandidates += $env:PYTHON_BIN }
$pythonCandidates += (Join-Path $projectRoot '.venv\Scripts\python.exe')
$pythonCandidates += @('python', 'python3', 'py')
$pythonCandidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$selectedPython = $null
foreach ($candidate in $pythonCandidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $command) { continue }
    try {
        & $command.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $selectedPython = $command.Source
            break
        }
    } catch { continue }
}
if (-not $selectedPython) {
    throw '未找到 Python 3.10+。请安装 Python，或通过 PYTHON_BIN 指定 python.exe 路径。'
}
if ($args.Count -eq 0) { $args = @('--serve') }
& $selectedPython (Join-Path $projectRoot 'main.py') @args
exit $LASTEXITCODE
