<#
.SYNOPSIS
  Scarica dal database di Sterling B2B Integrator (sola lettura) il sorgente di un BP o di una mappa.

.DESCRIPTION
  BP   : versione predefinita (WFD_VERSIONS.DEFAULT_VERSION) o quella indicata con -Version. Se la versione e' stata
         salvata dal GPM (WFD_XML.GBMDATA valorizzato) scrive il .bp completo (zip con stercomm.bpml + stercomm.gpl),
         altrimenti solo il .bpml.
  Mappa: versione predefinita (MAP_VERSIONS.DEFAULT_VERSION) o quella indicata; scrive .mxl (XML) o .map (binario).
         Se e' un .map prova a convertirlo anche in .mxl accanto (stesso nome) con il Map Editor locale, tramite
         ..\..\sterling-mappe\scripts\map2mxl.py (relativo a questo script). Se lo script di conversione, Python, il
         Map Editor o pywinauto mancano, resta il .map e compare un avviso. -NoConvert per saltare la conversione.

  Connessione: -Server e -Database con autenticazione Windows integrata, oppure -ConnectionString completa.
  L'ambiente (TEST o PROD) e' quello del server indicato: lo sceglie chi lancia lo script.
  Esegue solo SELECT parametrizzate su WFD, WFD_XML, WFD_VERSIONS, MAP, MAP_VERSIONS, DATA_TABLE.
  Il nome del file prodotto e' <nome>.v<versione>[.<Label>].<estensione>; non sovrascrive senza -Force.

.EXAMPLE
  .\Export-SterlingSource.ps1 -Type Bp -Name MY_BP_NAME -Server MYSQLSERVER\INSTANCE -Database SterlingDB -Label TEST

.EXAMPLE
  .\Export-SterlingSource.ps1 -Type Map -Name MY_MAP_NAME -Version 4 -ConnectionString 'Server=myhost;Database=SterlingDB;Integrated Security=True'
#>
[CmdletBinding(DefaultParameterSetName = 'Server')]
param(
    [Parameter(Mandatory)] [ValidateSet('Bp', 'Map')] [string] $Type,
    [Parameter(Mandatory)] [string] $Name,
    [Parameter(Mandatory, ParameterSetName = 'Server')] [string] $Server,
    [Parameter(Mandatory, ParameterSetName = 'Server')] [string] $Database,
    [Parameter(Mandatory, ParameterSetName = 'ConnectionString')] [string] $ConnectionString,
    [int] $Version = 0,
    # etichetta facoltativa messa nel nome del file (es. TEST o PROD) per non confondere gli export dei due ambienti
    [string] $Label = '',
    [string] $OutDir = (Join-Path $env:USERPROFILE 'Downloads'),
    [int] $CommandTimeout = 120,
    [switch] $Force,
    [switch] $NoConvert
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Data

if ($PSCmdlet.ParameterSetName -eq 'Server') {
    $csb = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $csb['Data Source'] = $Server
    $csb['Initial Catalog'] = $Database
    $csb['Integrated Security'] = $true
    $csb['Application Name'] = 'Export-SterlingSource'
    $ConnectionString = $csb.ConnectionString
}
if (-not (Test-Path $OutDir)) { throw "Cartella di output inesistente: $OutDir" }

$conn = New-Object System.Data.SqlClient.SqlConnection $ConnectionString
$conn.Open()
Write-Host "Connesso a: $($conn.DataSource) / $($conn.Database)"

function Invoke-SterlingSelect([string] $sql, [hashtable] $params = @{}) {
    # sola lettura: si accettano solo SELECT
    if ($sql -notmatch '^\s*SELECT\s') { throw 'Sono ammesse solo query SELECT' }
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = $CommandTimeout
    foreach ($k in $params.Keys) {
        $v = $params[$k]
        if ($v -is [int]) {
            $p = $cmd.Parameters.Add($k, [System.Data.SqlDbType]::Int)
        }
        else {
            $p = $cmd.Parameters.Add($k, [System.Data.SqlDbType]::NVarChar, 255)
        }
        $p.Value = $v
    }
    $table = New-Object System.Data.DataTable
    $reader = $cmd.ExecuteReader()
    try { $table.Load($reader) } finally { $reader.Dispose(); $cmd.Dispose() }
    return , $table
}

function Get-DataBytes([string] $dataId) {
    # DATA_TABLE: le pagine (PAGE_INDEX) concatenate formano un unico gzip
    $rows = Invoke-SterlingSelect 'SELECT PAGE_INDEX, DATA_OBJECT FROM DATA_TABLE WHERE DATA_ID = @id ORDER BY PAGE_INDEX' @{ '@id' = $dataId }
    if ($rows.Rows.Count -eq 0) { throw "DATA_TABLE senza righe per $dataId" }
    $ms = New-Object System.IO.MemoryStream
    foreach ($r in $rows.Rows) { $b = [byte[]]$r['DATA_OBJECT']; $ms.Write($b, 0, $b.Length) }
    $ms.Position = 0
    $gz = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
    $out = New-Object System.IO.MemoryStream
    $gz.CopyTo($out)
    $gz.Dispose()
    return , $out.ToArray()
}

function Find-Bytes([byte[]] $hay, [byte[]] $needle, [int] $from = 0, [switch] $Last) {
    $idx = -1
    for ($i = $from; $i -le $hay.Length - $needle.Length; $i++) {
        $ok = $true
        for ($j = 0; $j -lt $needle.Length; $j++) { if ($hay[$i + $j] -ne $needle[$j]) { $ok = $false; break } }
        if ($ok) { $idx = $i; if (-not $Last) { break } }
    }
    return $idx
}

function Save-Bytes([string] $file, [byte[]] $bytes) {
    $path = Join-Path $OutDir $file
    if ((Test-Path $path) -and -not $Force) { throw "Esiste gia': $path (usa -Force per sovrascrivere)" }
    [System.IO.File]::WriteAllBytes($path, $bytes)
    Write-Output "Salvato: $path ($($bytes.Length) byte)"
}

$suffix = if ($Label) { ".$Label" } else { '' }

try {
    if ($Type -eq 'Bp') {
        if ($Version -eq 0) {
            $t = Invoke-SterlingSelect 'SELECT DEFAULT_VERSION FROM WFD_VERSIONS WHERE WFD_NAME = @name' @{ '@name' = $Name }
            if ($t.Rows.Count -eq 0) { throw "BP $Name non trovato in WFD_VERSIONS" }
            $Version = [int]$t.Rows[0]['DEFAULT_VERSION']
        }
        $row = Invoke-SterlingSelect ('SELECT x.XML, x.GBMDATA FROM WFD w JOIN WFD_XML x ON x.WFD_ID = w.WFD_ID ' +
            'AND x.WFD_VERSION = w.WFD_VERSION WHERE w.NAME = @name AND w.WFD_VERSION = @ver') @{ '@name' = $Name; '@ver' = $Version }
        if ($row.Rows.Count -eq 0) { throw "BP $Name versione $Version non trovato" }
        $base = "$Name.v$Version$suffix"
        $gbm = $row.Rows[0]['GBMDATA']
        if ($gbm -and $gbm -isnot [System.DBNull]) {
            # GBMDATA = oggetto Java serializzato che contiene lo zip del .bp: dalla firma PK\3\4 alla fine della directory centrale
            $raw = Get-DataBytes ([string]$gbm)
            $start = Find-Bytes $raw ([byte[]](0x50, 0x4B, 0x03, 0x04))
            $eocd = Find-Bytes $raw ([byte[]](0x50, 0x4B, 0x05, 0x06)) -Last
            if ($start -lt 0 -or $eocd -lt 0) { throw 'zip del .bp non trovato in GBMDATA' }
            $end = $eocd + 22 + ([int]$raw[$eocd + 20] + 256 * [int]$raw[$eocd + 21])
            Save-Bytes "$base.bp" ($raw[$start..($end - 1)])
        }
        else {
            $raw = Get-DataBytes ([string]$row.Rows[0]['XML'])
            $start = Find-Bytes $raw ([System.Text.Encoding]::ASCII.GetBytes('<process'))
            if ($start -lt 0) { throw 'BPML non trovato in WFD_XML' }
            Save-Bytes "$base.bpml" ($raw[$start..($raw.Length - 1)])
            Write-Warning 'Versione senza diagramma GPM (GBMDATA vuoto): salvato solo il BPML; il .gpl si genera con crea_bp.py / bpml2gpl.py.'
        }
    }
    else {
        if ($Version -eq 0) {
            $t = Invoke-SterlingSelect 'SELECT DEFAULT_VERSION FROM MAP_VERSIONS WHERE MAP_NAME = @name' @{ '@name' = $Name }
            if ($t.Rows.Count -eq 0) { throw "Mappa $Name non trovata in MAP_VERSIONS" }
            $Version = [int]$t.Rows[0]['DEFAULT_VERSION']
        }
        $row = Invoke-SterlingSelect 'SELECT UNCOMPILED_MAP FROM MAP WHERE MAP_NAME = @name AND MAP_VERSION = @ver' @{ '@name' = $Name; '@ver' = $Version }
        if ($row.Rows.Count -eq 0) { throw "Mappa $Name versione $Version non trovata" }
        $raw = Get-DataBytes ([string]$row.Rows[0]['UNCOMPILED_MAP'])
        $head = [System.Text.Encoding]::ASCII.GetString($raw, 0, [Math]::Min(400, $raw.Length))
        $ext = if ($head -match '<Mapper|<\?xml') { 'mxl' } else { 'map' }
        $file = "$Name.v$Version$suffix.$ext"
        Save-Bytes $file $raw
        if ($ext -eq 'map' -and -not $NoConvert) {
            # .map binario: lo salva come .mxl il Map Editor locale ("Salva con nome" pilotato da script)
            $conv = Join-Path $PSScriptRoot '..\..\sterling-mappe\scripts\map2mxl.py'
            if (-not (Test-Path $conv)) {
                Write-Warning "Convertitore non trovato ($conv): .mxl non creato. Aprire il .map nel Map Editor e salvarlo come .mxl."
            }
            elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
                Write-Warning 'Python non trovato: .mxl non creato. Aprire il .map nel Map Editor e salvarlo come .mxl.'
            }
            else {
                $pyArgs = @('-I', (Resolve-Path $conv).Path, (Join-Path $OutDir $file))
                if ($Force) { $pyArgs += '--force' }
                & python @pyArgs
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning 'Conversione in .mxl non riuscita (vedi sopra): aprire il .map nel Map Editor e salvarlo come .mxl.'
                }
            }
        }
    }
}
finally {
    $conn.Dispose()
}
