<#
.SYNOPSIS
  ARINC 615A target acceptance test driven by the ARINC-EXAMPLE data loader CLI
  (arinc_615a_operation.exe) on Windows.

.DESCRIPTION
  Runs FIND, Information, Operator Defined Download, Media Defined Download and
  an ARINC 665 Adhoc Upload against a running target, and checks each final
  status plus the downloaded payload bytes. Start the target first, e.g. on
  VxWorks:
      arinc615aPrepareTest "/sd0a/arinc_test"
      taskSpawn("tArinc", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
  Afterwards run  arinc615aVerifyTestUpload "/sd0a/arinc_test"  on the target.

  See VXWORKS_TEST_PROCEDURE.md, Phase I.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target 192.168.1.50 -CliBuild C:\ARINC-EXAMPLE\arinc_615a-main\cmake-build-cli-verify
#>
param(
  [Parameter(Mandatory = $true)] [string] $Target,
  [Parameter(Mandatory = $true)] [string] $CliBuild,
  [string] $TargetId = 'ARINC_1',
  [int] $FindPort = 1001,
  [int] $TftpPort = 59,
  [int] $TimeoutSeconds = 90,
  [string] $WorkDir = (Join-Path $env:TEMP 'arinc_cli_acceptance'),
  # vcpkg installed tree holding the CLI's DLLs. Default: <CliBuild>\vcpkg_installed
  # (in-tree builds), then C:\vi (arinc-615a-cli-tool-suite scripts).
  [string] $VcpkgInstalled = ''
)

$ErrorActionPreference = 'Stop'
$cli = Join-Path $CliBuild 'app\arinc_615a_operation\arinc_615a_operation.exe'
$compiler = Join-Path $CliBuild '_deps\arinc_665-build\app\arinc_665_media_set_compiler\arinc_665_media_set_compiler.exe'
foreach ($tool in $cli, $compiler) {
  if (-not (Test-Path $tool)) { throw "Missing $tool (build it, see VXWORKS_TEST_PROCEDURE.md Phase I)" }
}
# The CLI links Boost.Program_options, fmt and libxml++ dynamically, and vcpkg
# does not copy them beside the exe. Never mix debug DLLs into a release build.
$roots = @($VcpkgInstalled, (Join-Path $CliBuild 'vcpkg_installed'), 'C:\vi') | Where-Object { $_ -and (Test-Path $_) }
if (-not $roots) { throw 'vcpkg installed tree not found; pass -VcpkgInstalled <dir>' }
# A debug CLI imports fmtd.dll; the build folder name does not always say so.
$isDebug = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($cli)).Contains('fmtd.dll')
$flavour = if ($isDebug) { 'x64-windows\debug\bin' } else { 'x64-windows\bin' }
$dllDir = Join-Path $roots[0] $flavour
if (-not (Test-Path $dllDir)) { throw "Missing $dllDir; pass -VcpkgInstalled <dir>" }
$env:PATH = $dllDir + ';' + $env:PATH

if (Test-Path $WorkDir) { Remove-Item $WorkDir -Recurse -Force }
New-Item -ItemType Directory -Path $WorkDir | Out-Null
$script:passed = 0
$script:failed = 0

function Invoke-Cli([string] $Name, [string[]] $Arguments) {
  $out = Join-Path $WorkDir "$Name.txt"
  $process = Start-Process -FilePath $cli -ArgumentList $Arguments -NoNewWindow -PassThru `
    -RedirectStandardOutput $out -RedirectStandardError "$out.err"
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $process.Kill()
    return "TIMEOUT after $TimeoutSeconds s"
  }
  return (Get-Content $out -Raw) + (Get-Content "$out.err" -Raw)
}

function Check([string] $Id, [string] $Description, [bool] $Ok, [string] $Detail) {
  if ($Ok) { $script:passed++; Write-Host "PASS: $Id $Description" }
  else { $script:failed++; Write-Host "FAIL: $Id $Description" -ForegroundColor Red; Write-Host $Detail }
}

function Test-Payload([string] $Path) {
  if (-not (Test-Path $Path)) { return $false }
  $bytes = [IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -ne 4097) { return $false }
  for ($i = 0; $i -lt $bytes.Length; $i++) { if ($bytes[$i] -ne ($i % 251)) { return $false } }
  return $true
}

$completed = 'Final Status Code:\s+Operation completed \(0003\)'
$link = @("--target-address=$Target", "--target-id=$TargetId", "--server-port=$TftpPort", '--port-option')

# C01 FIND (the CLI needs --option=value syntax; several short options clash).
$text = Invoke-Cli 'find' @('-c', 'Find', "--target-address=$Target", "--find-port=$FindPort", '--timeout=3')
Check 'C01' "FIND answered by $Target with target ID $TargetId" ($text -match "Target ID \*\*\s+'$TargetId'") $text

# C02 Information
$text = Invoke-Cli 'information' (@('-c', 'Information') + $link)
Check 'C02' 'Information: integrity valid, part number DEMO-PN, completed' `
  (($text -match 'Information Integrity: Valid') -and ($text -match "Part Number:\s+'DEMO-PN'") -and ($text -match $completed)) $text

# C03 Operator Defined Download of payload.bin
$dir = Join-Path $WorkDir 'op_download'; New-Item -ItemType Directory $dir | Out-Null
$text = Invoke-Cli 'op_download' (@('-c', 'OpDownload') + $link + @("--download-base-directory=$dir", '--file=payload.bin'))
$file = Get-ChildItem $dir -Recurse -Filter payload.bin -ErrorAction SilentlyContinue | Select-Object -First 1
Check 'C03' 'Operator Defined Download: file list received, payload.bin byte-identical, completed' `
  (($text -match 'Received File List') -and ($text -match $completed) -and $file -and (Test-Payload $file.FullName)) $text

# C04 Media Defined Download of payload.bin
$dir = Join-Path $WorkDir 'med_download'; New-Item -ItemType Directory $dir | Out-Null
$text = Invoke-Cli 'med_download' (@('-c', 'MedDownload') + $link + @("--download-base-directory=$dir", '--file=payload.bin'))
$file = Get-ChildItem $dir -Recurse -Filter payload.bin -ErrorAction SilentlyContinue | Select-Object -First 1
Check 'C04' 'Media Defined Download: payload.bin byte-identical, completed' `
  (($text -match $completed) -and $file -and (Test-Payload $file.FullName)) $text

# C05 ARINC 665 media set with one load (DEMOLOAD.LUH -> payload.bin)
$source = Join-Path $WorkDir 'media_source'; New-Item -ItemType Directory $source | Out-Null
$payload = New-Object byte[] 4097
for ($i = 0; $i -lt $payload.Length; $i++) { $payload[$i] = [byte]($i % 251) }
[IO.File]::WriteAllBytes((Join-Path $source 'payload.bin'), $payload)
$xml = Join-Path $WorkDir 'DemoMediaSet.xml'
@'
<?xml version="1.0" encoding="utf-8" ?>
<MediaSet xmlns="http://www.thomas-vogt.de/Arinc665MediaSet" PartNumber="DEMO-MS">
  <Content>
    <File Name="payload.bin" SourcePath="payload.bin" />
    <Load Name="DEMOLOAD.LUH" PartNumber="DEMO-PN" Description="ARINC target acceptance load" >
      <TargetHardware ThwId="ARINC" />
      <DataFile FilePath="/payload.bin" PartNumber="DEMO-PN" />
    </Load>
  </Content>
</MediaSet>
'@ | Set-Content -Path $xml -Encoding UTF8
$mediaOut = Join-Path $WorkDir 'media_set'
& $compiler "--xml-file=$xml" "--source-directory=$source" "--destination-directory=$mediaOut" '--create-load-header-files=All' | Out-Null
$medium = Get-ChildItem $mediaOut -Recurse -Filter LOADS.LUM -ErrorAction SilentlyContinue | Select-Object -First 1
Check 'C05' 'ARINC 665 media set DEMO-MS compiled' ($null -ne $medium) "compiler exit code $LASTEXITCODE"

# C06 Upload of DEMOLOAD.LUH from that media set
if ($medium) {
  $text = Invoke-Cli 'upload' (@('-c', 'AdhocUpload') + $link + @("--source-directory=$($medium.DirectoryName)", '--load-header=DEMOLOAD.LUH'))
  Check 'C06' 'Adhoc Upload of DEMOLOAD.LUH (DEMO-PN): load and operation completed' `
    (($text -match "Header Filename:\s+'DEMOLOAD.LUH'") -and ($text -match $completed)) $text
}

# C07 FIND still answered after all operations
$text = Invoke-Cli 'find_after' @('-c', 'Find', "--target-address=$Target", "--find-port=$FindPort", '--timeout=3')
Check 'C07' 'Target still answers FIND after all operations' ($text -match "Target ID \*\*\s+'$TargetId'") $text

Write-Host ''
Write-Host "$script:passed passed, $script:failed failed. CLI outputs: $WorkDir"
if ($script:failed -eq 0) {
  Write-Host 'Now verify the upload on the target: arinc615aVerifyTestUpload "<test root>"'
  exit 0
}
exit 1
