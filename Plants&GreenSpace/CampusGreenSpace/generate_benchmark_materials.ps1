$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression.FileSystem

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = (Get-Location).Path }
$OutDir = Join-Path $Root "benchmark_outputs"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function HtmlEscape([object]$Value) {
    if ($null -eq $Value) { return "" }
    return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

function Percent([double]$Part, [double]$Whole, [int]$Digits = 1) {
    if ($Whole -eq 0) { return 0 }
    return [math]::Round(($Part * 100.0 / $Whole), $Digits)
}

function Normalize-Species([string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Name)) { return "" }
    $Clean = ($Name -replace '[xX]', ' ' -replace '[^A-Za-z ]', ' ' -replace '\s+', ' ').Trim()
    $Parts = $Clean.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($Parts.Count -ge 2) {
        return (($Parts[0..1] -join ' ').ToLowerInvariant())
    }
    return $Clean.ToLowerInvariant()
}

function ReadEntryText($Zip, [string]$Name) {
    $Entry = $Zip.GetEntry($Name)
    if (-not $Entry) { return $null }
    $Reader = New-Object IO.StreamReader($Entry.Open())
    try { return $Reader.ReadToEnd() } finally { $Reader.Close() }
}

function ColumnIndex([string]$CellRef) {
    $Letters = ($CellRef -replace '\d', '')
    $N = 0
    foreach ($Ch in $Letters.ToCharArray()) {
        $N = $N * 26 + ([int][char]$Ch - [int][char]'A' + 1)
    }
    return $N - 1
}

function Get-SharedStrings($Zip) {
    $Text = ReadEntryText $Zip "xl/sharedStrings.xml"
    $Shared = New-Object System.Collections.Generic.List[string]
    if (-not $Text) { return $Shared }
    [xml]$Xml = $Text
    $Ns = New-Object Xml.XmlNamespaceManager($Xml.NameTable)
    $Ns.AddNamespace("x", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    foreach ($Si in $Xml.SelectNodes("//x:si", $Ns)) {
        $Texts = $Si.SelectNodes(".//x:t", $Ns) | ForEach-Object { $_.'#text' }
        $Shared.Add(($Texts -join ""))
    }
    return $Shared
}

function Get-WorkbookSheets($Zip) {
    [xml]$Workbook = ReadEntryText $Zip "xl/workbook.xml"
    $Ns = New-Object Xml.XmlNamespaceManager($Workbook.NameTable)
    $Ns.AddNamespace("x", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    return @($Workbook.SelectNodes("//x:sheet", $Ns))
}

function Resolve-CellValue($Cell, $Ns, $Shared) {
    $V = $Cell.SelectSingleNode("x:v", $Ns)
    $Value = if ($V) { $V.InnerText } else { "" }
    if ($Cell.GetAttribute("t") -eq "s" -and $Value -match "^\d+$" -and [int]$Value -lt $Shared.Count) {
        return $Shared[[int]$Value]
    }
    return $Value
}

function Get-XlsxSheetInfo([string]$Path) {
    $Zip = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Path))
    try {
        $Shared = Get-SharedStrings $Zip
        $Sheets = Get-WorkbookSheets $Zip
        $Info = New-Object System.Collections.Generic.List[object]
        for ($I = 0; $I -lt $Sheets.Count; $I++) {
            $EntryName = "xl/worksheets/sheet{0}.xml" -f ($I + 1)
            $Text = ReadEntryText $Zip $EntryName
            if (-not $Text) { continue }
            [xml]$SheetXml = $Text
            $Ns = New-Object Xml.XmlNamespaceManager($SheetXml.NameTable)
            $Ns.AddNamespace("x", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
            $Rows = @($SheetXml.SelectNodes("//x:sheetData/x:row", $Ns))
            $HeaderRows = @()
            foreach ($Row in ($Rows | Select-Object -First 2)) {
                $Vals = @()
                foreach ($Cell in $Row.SelectNodes("x:c", $Ns)) {
                    $Vals += (Resolve-CellValue $Cell $Ns $Shared)
                }
                $HeaderRows += ($Vals -join " | ")
            }
            $Info.Add([pscustomobject]@{
                File = Split-Path $Path -Leaf
                Sheet = $Sheets[$I].name
                Rows = $Rows.Count
                HeaderPreview = ($HeaderRows -join " / ")
            })
        }
        return $Info
    }
    finally {
        $Zip.Dispose()
    }
}

function Read-ShanghaiCityWorkbook([string]$Path) {
    $Zip = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Path))
    try {
        $Shared = Get-SharedStrings $Zip
        $Sheets = Get-WorkbookSheets $Zip
        $Records = New-Object System.Collections.Generic.List[object]
        for ($I = 0; $I -lt $Sheets.Count; $I++) {
            $Text = ReadEntryText $Zip ("xl/worksheets/sheet{0}.xml" -f ($I + 1))
            if (-not $Text) { continue }
            [xml]$SheetXml = $Text
            $Ns = New-Object Xml.XmlNamespaceManager($SheetXml.NameTable)
            $Ns.AddNamespace("x", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
            foreach ($Row in $SheetXml.SelectNodes("//x:sheetData/x:row", $Ns)) {
                if ([int]$Row.r -le 2) { continue }
                $Scientific = ""
                $Native = ""
                $Invasive = ""
                foreach ($Cell in $Row.SelectNodes("x:c", $Ns)) {
                    $Idx = ColumnIndex $Cell.r
                    if ($Idx -ne 8 -and $Idx -ne 13 -and $Idx -ne 14) { continue }
                    $Val = Resolve-CellValue $Cell $Ns $Shared
                    if ($Idx -eq 8) { $Scientific = $Val }
                    if ($Idx -eq 13) { $Native = $Val }
                    if ($Idx -eq 14) { $Invasive = $Val }
                }
                if (-not [string]::IsNullOrWhiteSpace($Scientific)) {
                    $Records.Add([pscustomobject]@{
                        District = $Sheets[$I].name
                        ScientificName = $Scientific
                        NormalizedName = Normalize-Species $Scientific
                        NativeStatus = $Native
                        InvasiveStatus = $Invasive
                    })
                }
            }
        }
        return $Records
    }
    finally {
        $Zip.Dispose()
    }
}

function Profile-Csv([string]$Path, [string[]]$LabelColumns) {
    $Rows = @(Import-Csv -LiteralPath $Path)
    $Columns = if ($Rows.Count -gt 0) { @($Rows[0].PSObject.Properties.Name) } else { @() }
    $Missing = @{}
    foreach ($Col in $Columns) { $Missing[$Col] = 0 }
    $Labels = @{}
    foreach ($Col in $LabelColumns) { $Labels[$Col] = @{} }
    $Unique = @{
        ScientificName = @{}
        LocationID = @{}
        Locality = @{}
        SourceID = @{}
    }
    $FullRows = @{}
    $LocationSpecies = @{}
    foreach ($Row in $Rows) {
        foreach ($Col in $Columns) {
            if ([string]::IsNullOrWhiteSpace($Row.$Col)) { $Missing[$Col]++ }
        }
        foreach ($Col in $LabelColumns) {
            if ($Columns -contains $Col) {
                $Val = if ([string]::IsNullOrWhiteSpace($Row.$Col)) { "(missing)" } else { $Row.$Col }
                if (-not $Labels[$Col].ContainsKey($Val)) { $Labels[$Col][$Val] = 0 }
                $Labels[$Col][$Val]++
            }
        }
        foreach ($Key in @("ScientificName", "LocationID", "Locality", "SourceID")) {
            if (($Columns -contains $Key) -and -not [string]::IsNullOrWhiteSpace($Row.$Key)) {
                $Unique[$Key][$Row.$Key] = $true
            }
        }
        $FullKey = (($Columns | ForEach-Object { $Row.$_ }) -join "`t")
        if (-not $FullRows.ContainsKey($FullKey)) { $FullRows[$FullKey] = 0 }
        $FullRows[$FullKey]++
        if (($Columns -contains "LocationID") -and ($Columns -contains "ScientificName")) {
            $Pair = "$($Row.LocationID)`t$($Row.ScientificName)"
            if (-not $LocationSpecies.ContainsKey($Pair)) { $LocationSpecies[$Pair] = 0 }
            $LocationSpecies[$Pair]++
        }
    }
    $DuplicateFullRows = 0
    foreach ($K in $FullRows.Keys) {
        if ($FullRows[$K] -gt 1) { $DuplicateFullRows += $FullRows[$K] }
    }
    $DuplicateLocationSpecies = 0
    foreach ($K in $LocationSpecies.Keys) {
        if ($LocationSpecies[$K] -gt 1) { $DuplicateLocationSpecies += $LocationSpecies[$K] }
    }
    $MissingList = @()
    foreach ($Col in $Columns) {
        $MissingList += [pscustomobject]@{
            Column = $Col
            Missing = $Missing[$Col]
            Percent = Percent $Missing[$Col] $Rows.Count 2
        }
    }
    $LabelList = @{}
    foreach ($Col in $Labels.Keys) {
        $LabelList[$Col] = @($Labels[$Col].GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
            [pscustomobject]@{ Label = $_.Key; Count = $_.Value; Percent = Percent $_.Value $Rows.Count 1 }
        })
    }
    return [pscustomobject]@{
        File = Split-Path $Path -Leaf
        Rows = $Rows.Count
        Columns = $Columns
        Missing = $MissingList
        Labels = $LabelList
        UniqueScientificName = $Unique.ScientificName.Count
        UniqueLocationID = $Unique.LocationID.Count
        UniqueLocality = $Unique.Locality.Count
        UniqueSourceID = $Unique.SourceID.Count
        DuplicateFullRows = $DuplicateFullRows
        DuplicateLocationSpeciesRows = $DuplicateLocationSpecies
        RowsData = $Rows
    }
}

function Top-Groups($Rows, [string]$Column, [int]$Top = 10) {
    return @($Rows | Group-Object $Column | Sort-Object Count -Descending | Select-Object -First $Top | ForEach-Object {
        [pscustomobject]@{ Label = $_.Name; Count = $_.Count }
    })
}

function Unique-By($Rows, [string]$Column) {
    $Map = @{}
    foreach ($R in $Rows) {
        $V = $R.$Column
        if (-not [string]::IsNullOrWhiteSpace($V) -and -not $Map.ContainsKey($V)) { $Map[$V] = $R }
    }
    return @($Map.Values)
}

function BarTable($Items, [string]$LabelField = "Label", [string]$CountField = "Count") {
    $Max = 1
    foreach ($Item in $Items) { if ([double]$Item.$CountField -gt $Max) { $Max = [double]$Item.$CountField } }
    $Rows = foreach ($Item in $Items) {
        $W = [math]::Max(2, [math]::Round(([double]$Item.$CountField * 100.0 / $Max), 1))
        "<tr><td>$(HtmlEscape $Item.$LabelField)</td><td class='num'>$(HtmlEscape $Item.$CountField)</td><td><div class='bar'><span style='width:$W%'></span></div></td></tr>"
    }
    return ($Rows -join "`n")
}

function SimpleRows($Items, [string[]]$Fields) {
    return (($Items | ForEach-Object {
        $Cells = foreach ($F in $Fields) { "<td>$(HtmlEscape $_.$F)</td>" }
        "<tr>$($Cells -join '')</tr>"
    }) -join "`n")
}

$AllFiles = @(Get-ChildItem -Path $Root -File | Sort-Object Name | Select-Object Name, Extension, Length, LastWriteTime)
$ArchiveFiles = @($AllFiles | Where-Object { $_.Extension -in ".zip", ".7z", ".rar", ".tar", ".gz" })
$XmlFiles = @($AllFiles | Where-Object { $_.Extension -eq ".xml" })

$CampusPlant = Profile-Csv (Join-Path $Root "ERDP-2021-02.4.1-Plant_List.csv") @("GrowthForm", "Plant_NativenessStatus", "TaxonRank")
$Locality = Profile-Csv (Join-Path $Root "ERDP-2021-02.3.1-Locality_Infor.csv") @("Region", "Province", "City", "Locality_Type")
$Source = Profile-Csv (Join-Path $Root "ERDP-2021-02.5.1-Source_List.csv") @("SourceType")
$ShanghaiCampus = Profile-Csv (Join-Path $Root "Plants_Shanghai.csv") @("GrowthForm", "Plant_NativenessStatus", "TaxonRank")
$ShanghaiCampusEnriched = Profile-Csv (Join-Path $Root "Plants_Shanghai_enriched.csv") @("District", "GrowthForm", "Plant_NativenessStatus")

$XlsxInfo = @()
foreach ($Xlsx in Get-ChildItem -Path $Root -Filter "*.xlsx" -File | Sort-Object Name) {
    $XlsxInfo += Get-XlsxSheetInfo $Xlsx.FullName
}

$CityWorkbookPath = @(Get-ChildItem -Path $Root -Filter "*.xlsx" -File | Sort-Object Length -Descending | Select-Object -First 1)[0].FullName
$CityRecords = @(Read-ShanghaiCityWorkbook $CityWorkbookPath)
$CityUnique = Unique-By $CityRecords "ScientificName"
$CityUniqueNorm = @{}
foreach ($R in $CityRecords) { if ($R.NormalizedName) { $CityUniqueNorm[$R.NormalizedName] = $true } }

$ShanghaiUniqueSpeciesRows = Unique-By $ShanghaiCampus.RowsData "ScientificName"
$ShanghaiUniqueNorm = @{}
foreach ($R in $ShanghaiCampus.RowsData) {
    $N = Normalize-Species $R.ScientificName
    if ($N) { $ShanghaiUniqueNorm[$N] = $true }
}
$OverlapNorm = 0
foreach ($K in $ShanghaiUniqueNorm.Keys) {
    if ($CityUniqueNorm.ContainsKey($K)) { $OverlapNorm++ }
}

$CampusNativeUnique = @($ShanghaiUniqueSpeciesRows | Group-Object Plant_NativenessStatus | Sort-Object Count -Descending | ForEach-Object {
    [pscustomobject]@{ Label = $_.Name; Count = $_.Count; Percent = Percent $_.Count $ShanghaiUniqueSpeciesRows.Count 1 }
})
$CityNativeUnique = @($CityUnique | Group-Object NativeStatus | Sort-Object Count -Descending | ForEach-Object {
    [pscustomobject]@{ Label = $_.Name; Count = $_.Count; Percent = Percent $_.Count $CityUnique.Count 1 }
})
$CityInvasiveUnique = @($CityUnique | Group-Object InvasiveStatus | Sort-Object Count -Descending | ForEach-Object {
    [pscustomobject]@{ Label = $_.Name; Count = $_.Count; Percent = Percent $_.Count $CityUnique.Count 1 }
})
$CampusNonnative = @($CampusNativeUnique | Where-Object { $_.Label -eq "Nonnative" } | Select-Object -First 1)
$CityNonnative = @($CityNativeUnique | Sort-Object Count | Select-Object -First 1)
$CampusNonnativeSpecies = if ($CampusNonnative.Count -gt 0) { $CampusNonnative[0].Count } else { 0 }
$CampusNonnativePercent = if ($CampusNonnative.Count -gt 0) { $CampusNonnative[0].Percent } else { 0 }
$CityNonnativeSpecies = if ($CityNonnative.Count -gt 0) { $CityNonnative[0].Count } else { 0 }
$CityNonnativePercent = if ($CityNonnative.Count -gt 0) { $CityNonnative[0].Percent } else { 0 }

$TopLocalities = Top-Groups $ShanghaiCampus.RowsData "Locality" 10
$TopDistricts = Top-Groups $ShanghaiCampusEnriched.RowsData "District" 10
$CityDistricts = Top-Groups $CityRecords "District" 20

$SourceTypes = @()
if ($Source.Labels.ContainsKey("SourceType")) { $SourceTypes = $Source.Labels["SourceType"] }

$Profile = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    local_only = $true
    files = $AllFiles
    missing_xml_files_named_in_prompt = ($XmlFiles.Count -eq 0)
    archive_files = $ArchiveFiles
    xlsx_sheets = $XlsxInfo
    tables = [pscustomobject]@{
        campus_plant = $CampusPlant | Select-Object * -ExcludeProperty RowsData
        locality = $Locality | Select-Object * -ExcludeProperty RowsData
        source = $Source | Select-Object * -ExcludeProperty RowsData
        shanghai_campus = $ShanghaiCampus | Select-Object * -ExcludeProperty RowsData
        shanghai_campus_enriched = $ShanghaiCampusEnriched | Select-Object * -ExcludeProperty RowsData
        shanghai_city_workbook = [pscustomobject]@{
            district_record_rows = $CityRecords.Count
            unique_scientific_names = $CityUnique.Count
            normalized_unique_names = $CityUniqueNorm.Count
            native_status_unique_species = $CityNativeUnique
            invasive_status_unique_species = $CityInvasiveUnique
        }
    }
    comparison = [pscustomobject]@{
        shanghai_campus_unique_species = $ShanghaiCampus.UniqueScientificName
        shanghai_campus_normalized_unique_species = $ShanghaiUniqueNorm.Count
        city_unique_species = $CityUnique.Count
        city_normalized_unique_species = $CityUniqueNorm.Count
        normalized_overlap = $OverlapNorm
        city_species_coverage_by_campus_percent = Percent $OverlapNorm $CityUniqueNorm.Count 1
        campus_species_matched_to_city_percent = Percent $OverlapNorm $ShanghaiUniqueNorm.Count 1
    }
}

$JsonPath = Join-Path $OutDir "benchmark_profile.json"
$Profile | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $JsonPath -Encoding UTF8

$MissingRows = @()
foreach ($P in @($CampusPlant, $ShanghaiCampus, $ShanghaiCampusEnriched, $Locality, $Source)) {
    foreach ($M in $P.Missing) {
        if ($M.Missing -gt 0) {
            $MissingRows += [pscustomobject]@{
                File = $P.File
                Column = $M.Column
                Missing = $M.Missing
                Percent = $M.Percent
            }
        }
    }
}
if ($MissingRows.Count -eq 0) {
    $MissingRows += [pscustomobject]@{ File = "CSV core tables"; Column = "all inspected columns"; Missing = 0; Percent = 0 }
}

$ScaleItems = @(
    [pscustomobject]@{ Label = "Campus plant records"; Count = $CampusPlant.Rows },
    [pscustomobject]@{ Label = "Shanghai campus plant records"; Count = $ShanghaiCampus.Rows },
    [pscustomobject]@{ Label = "Shanghai city district-record rows"; Count = $CityRecords.Count },
    [pscustomobject]@{ Label = "Campus localities"; Count = $Locality.Rows },
    [pscustomobject]@{ Label = "Sources"; Count = $Source.Rows }
)

$ComparisonRows = @(
    [pscustomobject]@{ Aspect = "Scale"; Campus = "$($ShanghaiCampus.Rows) records from $($ShanghaiCampus.UniqueLocality) Shanghai campus localities"; City = "$($CityRecords.Count) district-record rows across $((@($CityRecords | Select-Object -ExpandProperty District -Unique)).Count) district sheets"; Risk = "Different record units: campus occurrence rows vs district checklist rows." },
    [pscustomobject]@{ Aspect = "Species coverage"; Campus = "$($ShanghaiCampus.UniqueScientificName) unique scientific names; $($ShanghaiUniqueNorm.Count) normalized binomials"; City = "$($CityUnique.Count) unique scientific names; $($CityUniqueNorm.Count) normalized binomials"; Risk = "Only $OverlapNorm normalized names overlap; campus covers $(Percent $OverlapNorm $CityUniqueNorm.Count 1)% of city normalized species." },
    [pscustomobject]@{ Aspect = "Alien / nonnative"; Campus = (($CampusNativeUnique | ForEach-Object { "$($_.Label): $($_.Count) ($($_.Percent)%)" }) -join "; "); City = (($CityNativeUnique | ForEach-Object { "$($_.Label): $($_.Count) ($($_.Percent)%)" }) -join "; "); Risk = "Definitions differ: campus uses Native/Nonnative, city uses Shanghai native/non-native." },
    [pscustomobject]@{ Aspect = "Invasive label"; Campus = "Not available in campus plant CSV"; City = (($CityInvasiveUnique | ForEach-Object { "$($_.Label): $($_.Count) ($($_.Percent)%)" }) -join "; "); Risk = "Cannot train or evaluate invasive-label tasks fairly without adding labels to campus data." },
    [pscustomobject]@{ Aspect = "Spatial coverage"; Campus = (($TopDistricts | ForEach-Object { "$($_.Label): $($_.Count)" }) -join "; "); City = "17 district/unknown sheets"; Risk = "Shanghai campus subset is concentrated in Yangpu, Baoshan, Minhang, and Fengxian." }
)

$HtmlPath = Join-Path $OutDir "CampusGreenSpace_Benchmark_CourseMaterial.html"
$MdPath = Join-Path $OutDir "benchmark_findings_summary.md"

$Css = @"
:root {
  --paper: #fbfaf5;
  --ink: #243126;
  --muted: #657066;
  --line: #d8d2c3;
  --accent: #2f6f5e;
  --accent2: #c97b43;
  --warn: #9f3f2f;
  --card: #ffffff;
  --soft: #eef1e6;
}
* { box-sizing: border-box; }
body { margin: 0; background: radial-gradient(circle at top left, #e6eee2, transparent 34rem), linear-gradient(135deg, #fbfaf5, #efe8d8); color: var(--ink); font-family: Georgia, "Times New Roman", serif; }
main { max-width: 1180px; margin: 0 auto; padding: 34px 22px 56px; }
header { border: 1px solid var(--line); background: rgba(255,255,255,.72); padding: 28px; border-radius: 28px; box-shadow: 0 20px 60px rgba(49,57,41,.08); }
h1 { margin: 0 0 10px; font-size: clamp(34px, 5vw, 62px); line-height: .98; letter-spacing: -.04em; }
h2 { margin: 34px 0 12px; font-size: 28px; letter-spacing: -.02em; }
h3 { margin: 22px 0 8px; font-size: 20px; }
p { line-height: 1.62; }
.deck { max-width: 850px; color: var(--muted); font-size: 18px; }
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 18px; box-shadow: 0 10px 30px rgba(49,57,41,.05); }
.metric { font-size: 34px; font-weight: 700; color: var(--accent); line-height: 1; }
.label { margin-top: 8px; color: var(--muted); font-size: 14px; }
.callout { border-left: 6px solid var(--accent2); background: #fff7eb; padding: 16px 18px; border-radius: 14px; }
.risk { border-left-color: var(--warn); background: #fff0ec; }
table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 18px; overflow: hidden; border: 1px solid var(--line); }
th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
th { background: var(--soft); font-size: 13px; text-transform: uppercase; letter-spacing: .06em; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { height: 12px; background: #e7e0d1; border-radius: 999px; overflow: hidden; min-width: 120px; }
.bar span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), #7fa56f); border-radius: inherit; }
.matrix td:nth-child(4) { color: var(--warn); }
.pill { display: inline-block; padding: 6px 10px; border-radius: 999px; background: var(--soft); margin: 3px 4px 3px 0; font-size: 13px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
ol, ul { padding-left: 22px; }
li { margin: 8px 0; line-height: 1.48; }
code { background: #ede6d8; padding: 2px 5px; border-radius: 5px; }
footer { color: var(--muted); margin-top: 34px; font-size: 13px; }
@media (max-width: 900px) { .grid, .two { grid-template-columns: 1fr; } main { padding: 18px 12px 36px; } header { padding: 20px; } }
"@

$Html = @"
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Green Space Benchmark Course Material</title>
<style>
$Css
</style>
</head>
<body>
<main>
<header>
  <p class="pill">Local-only benchmark analysis</p>
  <p class="pill">Generated: $(HtmlEscape (Get-Date))</p>
  <h1>Can Shanghai campus flora stand for Shanghai plant diversity?</h1>
  <p class="deck">This direct-open course material turns the local plant files into benchmark knowledge for design master students. It focuses on evidence, missingness, coverage, research questions, curator tasks, and fair benchmark design.</p>
</header>

<section>
  <h2>Key Findings</h2>
  <div class="grid">
    <div class="card"><div class="metric">$($ShanghaiCampus.UniqueScientificName)</div><div class="label">unique Shanghai campus scientific names</div></div>
    <div class="card"><div class="metric">$($CityUnique.Count)</div><div class="label">unique city checklist scientific names</div></div>
    <div class="card"><div class="metric">$(Percent $OverlapNorm $CityUniqueNorm.Count 1)%</div><div class="label">city normalized species covered by campus subset</div></div>
    <div class="card"><div class="metric">$($ArchiveFiles.Count)</div><div class="label">external archive files found</div></div>
  </div>
  <p class="callout risk"><strong>Benchmark readiness:</strong> useful for a teaching benchmark, but not ready as a high-stakes ecological benchmark without curation. The strongest risks are schema mismatch between campus and city files, weak exact name matching, uneven district coverage, no explicit license file, and no XML files present even though the prompt names XML materials.</p>
</section>

<section>
  <h2>Evidence Cards</h2>
  <div class="two">
    <div class="card">
      <h3>Research focus 1</h3>
      <p><strong>Can campus diversity represent Shanghai?</strong> Not fully. After simple binomial normalization, the Shanghai campus subset matches $OverlapNorm of $($CityUniqueNorm.Count) city normalized species, or $(Percent $OverlapNorm $CityUniqueNorm.Count 1)% city coverage. This means the campus subset is informative but not representative enough by itself.</p>
    </div>
    <div class="card">
      <h3>Research focus 2</h3>
      <p><strong>Is alien plant proportion higher on campus?</strong> The campus subset has $CampusNonnativeSpecies nonnative unique species out of $($ShanghaiUniqueSpeciesRows.Count), or $CampusNonnativePercent%. The city workbook has $CityNonnativeSpecies non-native unique species out of $($CityUnique.Count), or $CityNonnativePercent%. Under these local labels, the campus nonnative share is higher, but the definitions should be harmonized before a formal claim.</p>
    </div>
  </div>
</section>

<section>
  <h2>Scale And Coverage</h2>
  <table>
    <thead><tr><th>Item</th><th class="num">Count</th><th>Visual scale</th></tr></thead>
    <tbody>$(BarTable $ScaleItems)</tbody>
  </table>
  <h3>Shanghai Campus Localities</h3>
  <table>
    <thead><tr><th>Locality</th><th class="num">Rows</th><th>Visual scale</th></tr></thead>
    <tbody>$(BarTable $TopLocalities)</tbody>
  </table>
  <h3>Shanghai Campus Districts</h3>
  <table>
    <thead><tr><th>District</th><th class="num">Rows</th><th>Visual scale</th></tr></thead>
    <tbody>$(BarTable $TopDistricts)</tbody>
  </table>
</section>

<section>
  <h2>Nativeness Comparison</h2>
  <div class="two">
    <div>
      <h3>Campus unique species</h3>
      <table><thead><tr><th>Status</th><th class="num">Species</th><th class="num">Percent</th></tr></thead><tbody>$(SimpleRows $CampusNativeUnique @("Label","Count","Percent"))</tbody></table>
    </div>
    <div>
      <h3>City unique species</h3>
      <table><thead><tr><th>Status</th><th class="num">Species</th><th class="num">Percent</th></tr></thead><tbody>$(SimpleRows $CityNativeUnique @("Label","Count","Percent"))</tbody></table>
    </div>
  </div>
</section>

<section>
  <h2>Missingness Report</h2>
  <p>The inspected core CSV tables have no missing cells in their declared columns. This is good for classroom exercises, but it does not solve schema gaps such as missing campus invasive labels or missing city campus identifiers.</p>
  <table><thead><tr><th>File</th><th>Column</th><th class="num">Missing</th><th class="num">Percent</th></tr></thead><tbody>$(SimpleRows $MissingRows @("File","Column","Missing","Percent"))</tbody></table>
</section>

<section>
  <h2>Comparison Matrix</h2>
  <table class="matrix"><thead><tr><th>Aspect</th><th>Campus evidence</th><th>City evidence</th><th>Benchmark risk</th></tr></thead><tbody>$(SimpleRows $ComparisonRows @("Aspect","Campus","City","Risk"))</tbody></table>
</section>

<section>
  <h2>Files And Schemas</h2>
  <table><thead><tr><th>File</th><th>Purpose</th><th>Evidence</th></tr></thead><tbody>
    <tr><td>ERDP-2021-02.4.1-Plant_List.csv</td><td>Campus plant occurrence table.</td><td>$($CampusPlant.Rows) rows, $($CampusPlant.UniqueScientificName) species names, columns: $(HtmlEscape ($CampusPlant.Columns -join ", ")).</td></tr>
    <tr><td>ERDP-2021-02.3.1-Locality_Infor.csv</td><td>Campus/locality metadata table.</td><td>$($Locality.Rows) rows, location, region, city, climate, area, and establishment fields.</td></tr>
    <tr><td>ERDP-2021-02.5.1-Source_List.csv</td><td>Bibliographic provenance table.</td><td>$($Source.Rows) sources; useful for provenance, but licensing is not explicit in the local folder.</td></tr>
    <tr><td>Plants_Shanghai.csv</td><td>Filtered Shanghai campus plant subset.</td><td>$($ShanghaiCampus.Rows) rows from $($ShanghaiCampus.UniqueLocality) localities. Filter note explains inclusion rules.</td></tr>
    <tr><td>Plants_Shanghai_enriched.csv</td><td>Shanghai campus subset with district and coordinate fields.</td><td>$($ShanghaiCampusEnriched.Rows) rows split across $($TopDistricts.Count) districts.</td></tr>
    <tr><td>$(HtmlEscape (Split-Path $CityWorkbookPath -Leaf))</td><td>City-wide wild and escaped vascular plant checklist split by district.</td><td>$($CityRecords.Count) district-record rows, $($CityUnique.Count) unique scientific names, $($CityNativeUnique.Count) native-status categories.</td></tr>
    <tr><td>Plants_Shanghai_*Translated.xlsx</td><td>Derived translated/exported campus workbooks.</td><td>Useful for presentation, but XLSX headers include blank styled rows in some sheets, so CSV is safer for reproducible analysis.</td></tr>
  </tbody></table>
</section>

<section>
  <h2>Risks, Anomalies, And Curator Tasks</h2>
  <ul>
    <li><strong>Missing prompt files:</strong> no local <code>.xml</code> file was found, although the prompt names XML materials. Curator task: place the XML files in the folder or update the benchmark manifest.</li>
    <li><strong>Name mismatch:</strong> exact scientific-name overlap between campus and city files fails because the campus file includes author strings while the city scientific-name field usually does not. Curator task: create a canonical taxon key.</li>
    <li><strong>Schema mismatch:</strong> campus has growth form and nativeness, city has Shanghai native/non-native plus invasive labels. Curator task: create a crosswalk table with shared label definitions.</li>
    <li><strong>Coverage imbalance:</strong> Shanghai campus rows concentrate in Yangpu, Baoshan, Minhang, and Fengxian. Curator task: document whether missing districts are true absence or sampling absence.</li>
    <li><strong>Packaging risk:</strong> no external archive is present, but XLSX is itself a zipped format with styled or blank header rows. Curator task: publish canonical CSV exports for each sheet.</li>
    <li><strong>Provenance risk:</strong> source metadata exists, but no explicit license file was found. Curator task: add a license and citation instructions before public benchmark release.</li>
  </ul>
</section>

<section>
  <h2>Research Questions For Students</h2>
  <ol>
    <li>Which Shanghai campus plant species are shared with the city-wide checklist after taxon-name normalization?</li>
    <li>Which plant families are overrepresented on campuses compared with the city checklist?</li>
    <li>Do campuses show a higher nonnative share than Shanghai overall after labels are harmonized?</li>
    <li>Which districts are under-covered by the campus subset, and how does that affect visual interpretation?</li>
    <li>Are campus tree, shrub, and herb proportions shaped more by design choices or by regional ecology?</li>
    <li>How would the conclusion change if representation is measured by species, families, or growth forms?</li>
  </ol>
</section>

<section>
  <h2>Suggested Benchmark Tasks</h2>
  <table><thead><tr><th>Task</th><th>Input</th><th>Expected output</th><th>Why it matters</th></tr></thead><tbody>
    <tr><td>Schema matching</td><td>Campus and city plant tables</td><td>Column crosswalk and risk notes</td><td>Tests whether a tool understands messy ecological tables.</td></tr>
    <tr><td>Taxon normalization</td><td>Scientific names with and without authors</td><td>Canonical binomial or accepted-name key</td><td>Required before fair overlap measurement.</td></tr>
    <tr><td>Nativeness comparison</td><td>Harmonized native labels</td><td>Campus vs city nonnative proportions</td><td>Directly addresses the research focus.</td></tr>
    <tr><td>Coverage audit</td><td>District and locality fields</td><td>Coverage map/table and bias statement</td><td>Prevents overclaiming representativeness.</td></tr>
    <tr><td>Student dashboard</td><td>Curated CSV slices</td><td>Readable cards, matrix, and charts</td><td>Tests communication, not only computation.</td></tr>
  </tbody></table>
</section>

<section>
  <h2>Metrics And Fair Evaluation Protocol</h2>
  <ul>
    <li><strong>Schema task metrics:</strong> precision/recall of matched columns against a curator-approved crosswalk.</li>
    <li><strong>Taxon task metrics:</strong> exact match rate on canonical names, plus manual review rate for uncertain names.</li>
    <li><strong>Comparison task metrics:</strong> correct numerator, denominator, percentage, and caveat for label-definition differences.</li>
    <li><strong>Visualization metrics:</strong> all charts must cite source files, show units, and avoid implying unobserved districts are zero-diversity districts.</li>
    <li><strong>Fair tool comparison:</strong> give every model or tool the same file slice, same prompt, same allowed operations, and same scoring rubric. Do not let one tool use internet taxonomy lookup if others are local-only.</li>
  </ul>
</section>

<section>
  <h2>Student-Friendly Workflow Guide</h2>
  <ol>
    <li>Make a file manifest: list every CSV, XLSX, note, script, and output file.</li>
    <li>Read schemas before drawing charts: identify keys, labels, and missing columns.</li>
    <li>Profile counts: rows, unique species, localities, districts, labels, and sources.</li>
    <li>Separate description from benchmark judgment: a pretty chart is not enough if coverage is biased.</li>
    <li>Create a name-normalization rule and record its limits.</li>
    <li>Compare campus and city data only after units and labels are made comparable.</li>
    <li>Write curator tasks for every unresolved risk.</li>
    <li>Package outputs so another student can open the HTML and rerun <code>generate_benchmark_materials.ps1</code>.</li>
  </ol>
</section>

<section>
  <h2>Benchmark Proposal Template</h2>
  <table><thead><tr><th>Section</th><th>Student fill-in</th></tr></thead><tbody>
    <tr><td>Benchmark name</td><td>Short title and ecological scale.</td></tr>
    <tr><td>Dataset slice</td><td>Files, rows, filters, and date of generation.</td></tr>
    <tr><td>Research question</td><td>One measurable question plus why it matters.</td></tr>
    <tr><td>Gold standard</td><td>Curated schema crosswalk, taxon key, and label definitions.</td></tr>
    <tr><td>Tasks</td><td>What a model/tool must produce.</td></tr>
    <tr><td>Metrics</td><td>How outputs are scored fairly.</td></tr>
    <tr><td>Known risks</td><td>Missing files, biased coverage, ambiguous labels, licensing gaps.</td></tr>
    <tr><td>Visual communication</td><td>Cards, matrix, chart types, and evidence links.</td></tr>
  </tbody></table>
</section>

<footer>
  Evidence is generated from local files only. Machine-readable profile: <code>benchmark_profile.json</code>. Summary markdown: <code>benchmark_findings_summary.md</code>.
</footer>
</main>
</body>
</html>
"@

Set-Content -LiteralPath $HtmlPath -Value $Html -Encoding UTF8

$Md = @"
# Campus Green Space Benchmark Findings

Generated from local files only: $(Get-Date)

## Findings summary

- Shanghai campus plant subset: $($ShanghaiCampus.Rows) rows, $($ShanghaiCampus.UniqueScientificName) unique scientific names, $($ShanghaiCampus.UniqueLocality) campus/locality names.
- Shanghai city workbook: $($CityRecords.Count) district-record rows, $($CityUnique.Count) unique scientific names.
- After simple binomial normalization, $OverlapNorm campus names overlap with the city checklist. This covers $(Percent $OverlapNorm $CityUniqueNorm.Count 1)% of city normalized species and matches $(Percent $OverlapNorm $ShanghaiUniqueNorm.Count 1)% of campus normalized species.
- Campus unique-species nonnative share: $CampusNonnativePercent%. City unique-species non-native share: $CityNonnativePercent%.
- The campus nonnative share is higher under the local labels, but a formal claim needs a curated label crosswalk.

## Missingness report

The inspected core CSV files show no missing cells in declared columns. The more important gaps are schema gaps: no campus invasive label, no shared canonical taxon key, no local XML files despite the prompt naming XML, and no explicit license file.

## Curator task list

- Add or remove the XML references in the benchmark manifest.
- Create a canonical taxon-name table for campus and city records.
- Harmonize Native/Nonnative with the city workbook's Shanghai native/non-native labels.
- Export city XLSX sheets to canonical CSV files.
- Add license and citation instructions.
- Document whether district gaps are ecological absences or sampling absences.

## Suggested benchmark tasks

- Schema matching between campus and city plant data.
- Taxon normalization from scientific names with and without authors.
- Campus vs city nativeness comparison with clear denominators.
- District coverage audit and bias statement.
- Student dashboard generation with evidence-linked charts.

## Suggested metrics and evaluation protocol

- Score schema matches with precision and recall against a curated crosswalk.
- Score taxon normalization by canonical-name accuracy and unresolved-review rate.
- Score quantitative answers by correct numerator, denominator, percentage, and caveat.
- Score visual outputs by evidence links, unit clarity, and correct treatment of missing coverage.
- Compare tools fairly using the same data slice, same prompt, same local-only rule, and same rubric.

## Output files

- CampusGreenSpace_Benchmark_CourseMaterial.html
- benchmark_profile.json
- benchmark_findings_summary.md
"@

Set-Content -LiteralPath $MdPath -Value $Md -Encoding UTF8

Write-Host "Generated:"
Write-Host $HtmlPath
Write-Host $JsonPath
Write-Host $MdPath
