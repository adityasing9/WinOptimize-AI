<#
.SYNOPSIS
    WinOptimize AI - Read-Only Diagnostic Inspection Engine
.DESCRIPTION
    Performs comprehensive, read-only system inspection of running processes,
    startup entries (registry and folders), scheduled tasks, and Windows services.
    Calculates resource observations and identifies initial optimization candidates.
    CRITICAL: This script is strictly read-only and performs zero write or modify operations.
.PARAMETER OutputPath
    Optional file path to output structured JSON diagnostic report.
.PARAMETER MaxProcesses
    Maximum number of processes to record in the report (sorted by Working Set memory). Default is 250.
.PARAMETER IncludeSystemServices
    Whether to include system-level Windows services (default is true, but flagged accordingly).
.EXAMPLE
    pwsh -File scripts\Get-WinOpDiagnostics.ps1 -OutputPath "reports\diagnostic_report.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$OutputPath = "",

    [Parameter(Mandatory = $false)]
    [int]$MaxProcesses = 250,

    [Parameter(Mandatory = $false)]
    [switch]$IncludeSystemServices = $true
)

Set-StrictMode -Off
$ErrorActionPreference = "SilentlyContinue"

$scanStartTime = [System.DateTime]::UtcNow

# Helper to check if current session is elevated (Administrator)
function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$currentIdentity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$isAdmin = Test-IsAdmin

# -----------------------------------------------------------------------------
# 1. System Overview
# -----------------------------------------------------------------------------
function Get-SystemOverview {
    $osInfo = $null
    try {
        $osCim = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $totalMemMB = [math]::Round($osCim.TotalVisibleMemorySize / 1024, 2)
        $freeMemMB = [math]::Round($osCim.FreePhysicalMemory / 1024, 2)
        $usedMemMB = [math]::Round($totalMemMB - $freeMemMB, 2)
        $memPercent = if ($totalMemMB -gt 0) { [math]::Round(($usedMemMB / $totalMemMB) * 100, 1) } else { 0 }

        $osInfo = [PSCustomObject]@{
            Caption              = $osCim.Caption
            Version              = $osCim.Version
            BuildNumber          = $osCim.BuildNumber
            OSArchitecture       = $osCim.OSArchitecture
            TotalPhysicalMemoryMB = $totalMemMB
            FreePhysicalMemoryMB  = $freeMemMB
            UsedPhysicalMemoryMB  = $usedMemMB
            MemoryUsagePercent   = $memPercent
            Source               = "CIM"
        }
    } catch {
        # Fallback to Registry and environment
        $regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        $prodName = (Get-ItemProperty $regPath -ErrorAction SilentlyContinue).ProductName
        $build = (Get-ItemProperty $regPath -ErrorAction SilentlyContinue).CurrentBuild
        $displayVer = (Get-ItemProperty $regPath -ErrorAction SilentlyContinue).DisplayVersion

        $osInfo = [PSCustomObject]@{
            Caption              = if ($prodName) { $prodName } else { [System.Environment]::OSVersion.VersionString }
            Version              = $displayVer
            BuildNumber          = $build
            OSArchitecture       = if ([System.Environment]::Is64BitOperatingSystem) { "64-bit" } else { "32-bit" }
            TotalPhysicalMemoryMB = 0
            FreePhysicalMemoryMB  = 0
            UsedPhysicalMemoryMB  = 0
            MemoryUsagePercent   = 0
            Source               = "RegistryFallback"
        }
    }

    # CPU Load
    $cpuLoad = 0
    try {
        $cpuCim = Get-CimInstance Win32_Processor -ErrorAction Stop | Measure-Object -Property LoadPercentage -Average
        if ($cpuCim.Average) { $cpuLoad = [math]::Round($cpuCim.Average, 1) }
    } catch {
        $cpuLoad = 0
    }
    $osInfo | Add-Member -NotePropertyName "CpuLoadPercent" -NotePropertyValue $cpuLoad
    $osInfo | Add-Member -NotePropertyName "MachineName" -NotePropertyValue $env:COMPUTERNAME
    $osInfo | Add-Member -NotePropertyName "CurrentUserName" -NotePropertyValue "$env:USERDOMAIN\$env:USERNAME"
    $osInfo | Add-Member -NotePropertyName "IsElevated" -NotePropertyValue $isAdmin

    return $osInfo
}

# -----------------------------------------------------------------------------
# 2. Running Processes Inspection
# -----------------------------------------------------------------------------
function Get-ProcessInspection {
    param([int]$Limit = 250)

    $processList = [System.Collections.Generic.List[PSCustomObject]]::new()
    $rawProcesses = Get-Process -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending

    # Cache CIM processes for parent PID and commandline lookup if available
    $cimProcMap = @{}
    try {
        $cimProcs = Get-CimInstance Win32_Process -ErrorAction Stop
        foreach ($cp in $cimProcs) {
            $cimProcMap[$cp.ProcessId] = [PSCustomObject]@{
                ParentProcessId = $cp.ParentProcessId
                CommandLine     = $cp.CommandLine
            }
        }
    } catch {
        # CIM might be restricted in sandboxes; continue gracefully
    }

    $count = 0
    foreach ($proc in $rawProcesses) {
        if ($count -ge $Limit) { break }
        $count++

        $procPath = ""
        $company = ""
        $fileDesc = ""
        try {
            $procPath = $proc.Path
            if (-not $procPath) { $procPath = $proc.MainModule.FileName }
        } catch { }

        if ($procPath -and (Test-Path $procPath -ErrorAction SilentlyContinue)) {
            try {
                $verInfo = (Get-Item $procPath -ErrorAction SilentlyContinue).VersionInfo
                $company = $verInfo.CompanyName
                $fileDesc = $verInfo.FileDescription
            } catch { }
        }

        $parentPid = 0
        $cmdLine = ""
        if ($cimProcMap.ContainsKey($proc.Id)) {
            $parentPid = $cimProcMap[$proc.Id].ParentProcessId
            $cmdLine = $cimProcMap[$proc.Id].CommandLine
        }

        $cpuSeconds = 0
        try {
            if ($proc.TotalProcessorTime) {
                $cpuSeconds = [math]::Round($proc.TotalProcessorTime.TotalSeconds, 2)
            }
        } catch { }

        $item = [PSCustomObject]@{
            Id               = $proc.Id
            Name             = $proc.Name
            WorkingSetMB     = [math]::Round($proc.WorkingSet64 / 1MB, 2)
            PrivateMemoryMB  = [math]::Round($proc.PrivateMemorySize64 / 1MB, 2)
            CpuTotalSeconds  = $cpuSeconds
            HasWindow        = [bool]($proc.MainWindowTitle)
            WindowTitle      = if ($proc.MainWindowTitle) { $proc.MainWindowTitle } else { "" }
            ExecutablePath   = if ($procPath) { $procPath } else { "" }
            Publisher        = if ($company) { $company } else { "" }
            Description      = if ($fileDesc) { $fileDesc } else { "" }
            ParentProcessId  = $parentPid
            CommandLine      = if ($cmdLine) { $cmdLine } else { "" }
        }
        $processList.Add($item)
    }

    return $processList
}

# -----------------------------------------------------------------------------
# 3. Startup Entries Inspection
# -----------------------------------------------------------------------------
function Get-StartupInspection {
    $startupItems = [System.Collections.Generic.List[PSCustomObject]]::new()

    # Load StartupApproved caches to inspect disabled states (0x02 = Enabled, 0x03 = Disabled)
    $approvedMap = @{}

    $approvedLocations = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"
    )

    foreach ($loc in $approvedLocations) {
        $props = Get-ItemProperty $loc -ErrorAction SilentlyContinue
        if ($props) {
            foreach ($p in $props.PSObject.Properties) {
                if ($p.Name -notmatch "^PS") {
                    $val = $p.Value
                    if ($val -is [byte[]] -and $val.Length -gt 0) {
                        $firstByte = $val[0]
                        # 0x02 is Enabled, 0x03 is Disabled
                        $isEnabled = ($firstByte -eq 2)
                        $approvedMap["$loc\$($p.Name)"] = $isEnabled
                        $approvedMap[$p.Name] = $isEnabled
                    }
                }
            }
        }
    }

    # Registry Run Keys
    $regLocations = @(
        @{ Hive = "HKCU"; Path = "Software\Microsoft\Windows\CurrentVersion\Run"; Scope = "User" },
        @{ Hive = "HKCU"; Path = "Software\Microsoft\Windows\CurrentVersion\RunOnce"; Scope = "User" },
        @{ Hive = "HKLM"; Path = "Software\Microsoft\Windows\CurrentVersion\Run"; Scope = "Machine" },
        @{ Hive = "HKLM"; Path = "Software\Microsoft\Windows\CurrentVersion\RunOnce"; Scope = "Machine" },
        @{ Hive = "HKLM"; Path = "Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"; Scope = "Machine (32-bit)" }
    )

    foreach ($reg in $regLocations) {
        $fullPath = "$($reg.Hive):\$($reg.Path)"
        $entryProps = Get-ItemProperty $fullPath -ErrorAction SilentlyContinue
        if ($entryProps) {
            foreach ($prop in $entryProps.PSObject.Properties) {
                if ($prop.Name -notmatch "^PS") {
                    $name = $prop.Name
                    $cmd = [string]$prop.Value

                    # Determine clean executable path from command string
                    $cleanPath = ""
                    if ($cmd) {
                        $trimmed = $cmd.Trim()
                        if ($trimmed.StartsWith('"')) {
                            $idx = $trimmed.IndexOf('"', 1)
                            if ($idx -gt 1) { $cleanPath = $trimmed.Substring(1, $idx - 1) }
                        } else {
                            $cleanPath = $trimmed.Split(' ')[0]
                        }
                    }

                    # Publisher info
                    $publisher = ""
                    $description = ""
                    if ($cleanPath -and (Test-Path $cleanPath -ErrorAction SilentlyContinue)) {
                        try {
                            $vi = (Get-Item $cleanPath -ErrorAction SilentlyContinue).VersionInfo
                            $publisher = $vi.CompanyName
                            $description = $vi.FileDescription
                        } catch { }
                    }

                    # Check enabled state from StartupApproved
                    $isEnabled = $true
                    if ($approvedMap.ContainsKey($name)) {
                        $isEnabled = $approvedMap[$name]
                    }

                    $startupItems.Add([PSCustomObject]@{
                        Name            = $name
                        Command         = $cmd
                        ResolvedPath    = $cleanPath
                        Publisher       = $publisher
                        Description     = $description
                        LocationType    = "Registry"
                        LocationKey     = $fullPath
                        Scope           = $reg.Scope
                        IsEnabled       = $isEnabled
                    })
                }
            }
        }
    }

    # Startup Folders
    $folders = @(
        @{ Path = [Environment]::GetFolderPath('Startup'); Scope = "User" },
        @{ Path = [Environment]::GetFolderPath('CommonStartup'); Scope = "Machine" }
    )

    $wscriptShell = $null
    try { $wscriptShell = New-Object -ComObject WScript.Shell } catch { }

    foreach ($folder in $folders) {
        if (Test-Path $folder.Path -ErrorAction SilentlyContinue) {
            $files = Get-ChildItem -Path $folder.Path -File -ErrorAction SilentlyContinue
            foreach ($f in $files) {
                $targetPath = $f.FullName
                $arguments = ""
                if ($f.Extension -eq ".lnk" -and $wscriptShell) {
                    try {
                        $shortcut = $wscriptShell.CreateShortcut($f.FullName)
                        $targetPath = $shortcut.TargetPath
                        $arguments = $shortcut.Arguments
                    } catch { }
                }

                $publisher = ""
                $description = ""
                if ($targetPath -and (Test-Path $targetPath -ErrorAction SilentlyContinue)) {
                    try {
                        $vi = (Get-Item $targetPath -ErrorAction SilentlyContinue).VersionInfo
                        $publisher = $vi.CompanyName
                        $description = $vi.FileDescription
                    } catch { }
                }

                $isEnabled = $true
                if ($approvedMap.ContainsKey($f.Name)) {
                    $isEnabled = $approvedMap[$f.Name]
                }

                $startupItems.Add([PSCustomObject]@{
                    Name            = $f.Name
                    Command         = "$targetPath $arguments".Trim()
                    ResolvedPath    = $targetPath
                    Publisher       = $publisher
                    Description     = $description
                    LocationType    = "StartupFolder"
                    LocationKey     = $folder.Path
                    Scope           = $folder.Scope
                    IsEnabled       = $isEnabled
                })
            }
        }
    }

    return $startupItems
}

# -----------------------------------------------------------------------------
# 4. Scheduled Tasks Inspection
# -----------------------------------------------------------------------------
function Get-ScheduledTaskInspection {
    $taskList = [System.Collections.Generic.List[PSCustomObject]]::new()

    try {
        $rawTasks = Get-ScheduledTask -ErrorAction Stop
        foreach ($t in $rawTasks) {
            # Filter standard core Windows internal tasks to minimize noise,
            # but keep tasks in root '\' and third-party vendor task folders.
            $isCoreWindows = ($t.TaskPath -match "^\\Microsoft\\Windows\\" -and
                             $t.TaskPath -notmatch "Customer Experience|EdgeUpdate|Windows Defender")

            if ($isCoreWindows) { continue }

            $actionsList = @()
            if ($t.Actions) {
                foreach ($act in $t.Actions) {
                    $exec = ""
                    $args = ""
                    try { $exec = $act.Execute } catch { }
                    try { $args = $act.Arguments } catch { }
                    if ($exec) {
                        $actionsList += [PSCustomObject]@{
                            Execute   = $exec
                            Arguments = $args
                        }
                    }
                }
            }

            $triggersList = @()
            if ($t.Triggers) {
                foreach ($trig in $t.Triggers) {
                    $trigType = $trig.CimClass.CimSystemProperties.ClassName
                    $trigEnabled = $true
                    try { $trigEnabled = $trig.Enabled } catch { }

                    $triggersList += [PSCustomObject]@{
                        Type    = if ($trigType) { $trigType } else { "UnknownTrigger" }
                        Enabled = $trigEnabled
                        Id      = try { $trig.Id } catch { "" }
                    }
                }
            }

            $author = ""
            $desc = ""
            try { $author = $t.Author } catch { }
            try { $desc = $t.Description } catch { }

            $taskList.Add([PSCustomObject]@{
                TaskName    = $t.TaskName
                TaskPath    = $t.TaskPath
                State       = $t.State.ToString()
                Author      = $author
                Description = $desc
                Actions     = $actionsList
                Triggers    = $triggersList
            })
        }
    } catch {
        # Handled gracefully if Scheduled Tasks RPC is restricted or unreadable
    }

    return $taskList
}

# -----------------------------------------------------------------------------
# 5. Windows Services Inspection
# -----------------------------------------------------------------------------
function Get-ServiceInspection {
    param([bool]$IncludeSystem = $true)

    $serviceList = [System.Collections.Generic.List[PSCustomObject]]::new()

    # Attempt 1: CIM Win32_Service
    $usedCim = $false
    try {
        $cimServices = Get-CimInstance Win32_Service -ErrorAction Stop
        $usedCim = $true
        foreach ($svc in $cimServices) {
            # Differentiate Windows core drivers vs optional/third-party services
            $isCoreWindows = $false
            if ($svc.PathName -match "\\\\Windows\\\\System32\\\\|\\\\Windows\\\\SysWOW64\\\\" -or $svc.PathName -match "/Windows/System32/|/Windows/SysWOW64/") {
                if ($svc.Name -notmatch "GamingServices|Xbox" -and $svc.DisplayName -notmatch "Gaming|Xbox") {
                    $isCoreWindows = $true
                }
            }
            $isMicrosoft = $isCoreWindows

            # When not including full system, skip core Windows System32 drivers, but keep user/app services
            if (-not $IncludeSystem -and $isCoreWindows) { continue }

            $serviceList.Add([PSCustomObject]@{
                Name         = $svc.Name
                DisplayName  = $svc.DisplayName
                Status       = $svc.State
                StartMode    = $svc.StartMode
                BinaryPath   = $svc.PathName
                Account      = $svc.StartName
                IsMicrosoft  = $isMicrosoft
                Source       = "CIM"
            })
        }
    } catch {
        $usedCim = $false
    }

    # Attempt 2: Fallback to HKLM Registry if CIM was inaccessible
    if (-not $usedCim) {
        $svcKey = "HKLM:\SYSTEM\CurrentControlSet\Services"
        $svcEntries = Get-ChildItem -Path $svcKey -ErrorAction SilentlyContinue
        foreach ($entry in $svcEntries) {
            $props = Get-ItemProperty -Path $entry.PSPath -ErrorAction SilentlyContinue
            if ($props.ImagePath -and $props.Start -ne $null) {
                # Start: 0=Boot, 1=System, 2=Automatic, 3=Manual, 4=Disabled
                $startModeStr = switch ($props.Start) {
                    0 { "Boot" }
                    1 { "System" }
                    2 { "Auto" }
                    3 { "Manual" }
                    4 { "Disabled" }
                    default { "Unknown ($($props.Start))" }
                }

                $img = [string]$props.ImagePath
                $disp = if ($props.DisplayName) { [string]$props.DisplayName } else { $entry.PSChildName }
                $acct = if ($props.ObjectName) { [string]$props.ObjectName } else { "" }

                $isCoreWindows = $false
                if ($img -match "system32|syswow64") {
                    if ($entry.PSChildName -notmatch "GamingServices|Xbox" -and $disp -notmatch "Gaming|Xbox") {
                        $isCoreWindows = $true
                    }
                }
                $isMicrosoft = $isCoreWindows

                if (-not $IncludeSystem -and $isCoreWindows) { continue }

                $serviceList.Add([PSCustomObject]@{
                    Name         = $entry.PSChildName
                    DisplayName  = $disp
                    Status       = "Unknown (Registry)"
                    StartMode    = $startModeStr
                    BinaryPath   = $img
                    Account      = $acct
                    IsMicrosoft  = $isMicrosoft
                    Source       = "RegistryFallback"
                })
            }
        }
    }

    return $serviceList
}

# -----------------------------------------------------------------------------
# 6. Initial Read-Only Optimization Candidate Heuristics
# -----------------------------------------------------------------------------
function Get-OptimizationCandidates {
    param(
        [System.Collections.Generic.List[PSCustomObject]]$Processes,
        [System.Collections.Generic.List[PSCustomObject]]$StartupEntries,
        [System.Collections.Generic.List[PSCustomObject]]$ScheduledTasks,
        [System.Collections.Generic.List[PSCustomObject]]$Services
    )

    $candidates = [System.Collections.Generic.List[PSCustomObject]]::new()

    # Rule-like patterns for common third-party background software
    $commonStartupPatterns = @(
        @{ Pattern = "Discord"; Name = "Discord"; Reason = "Chat client auto-starts and remains resident in system tray." },
        @{ Pattern = "Spotify"; Name = "Spotify"; Reason = "Music streaming client configured to start at boot." },
        @{ Pattern = "Steam|SteamBootstrapper"; Name = "Steam Client"; Reason = "Gaming client auto-launches in background." },
        @{ Pattern = "EpicGames|EpicOnlineServices"; Name = "Epic Games Launcher"; Reason = "Launcher stays backgrounded; only needed when playing." },
        @{ Pattern = "RiotClient|RiotClientServices"; Name = "Riot Client"; Reason = "Background launcher service loaded at sign-in." },
        @{ Pattern = "Opera.*assistant|browser_assistant"; Name = "Opera Browser Assistant"; Reason = "Background assistant service that auto-starts and stays resident." },
        @{ Pattern = "ImoDesktopApp"; Name = "Imo Messenger"; Reason = "Messaging utility configured to launch minimized." },
        @{ Pattern = "Docker Desktop"; Name = "Docker Desktop"; Reason = "High resource background hypervisor/container engine." }
    )

    # 1. Startup Candidates
    foreach ($entry in $StartupEntries) {
        if (-not $entry.IsEnabled) { continue } # Already disabled

        foreach ($p in $commonStartupPatterns) {
            if ($entry.Name -match $p.Pattern -or $entry.Command -match $p.Pattern -or $entry.ResolvedPath -match $p.Pattern) {
                $candidates.Add([PSCustomObject]@{
                    Category          = "StartupEntry"
                    TargetName        = $entry.Name
                    Identifier        = "$($entry.LocationType):$($entry.Name)"
                    RiskLevel         = "LOW"
                    Confidence        = 0.90
                    Reason            = $p.Reason
                    RecommendedAction = "Disable startup entry in StartupApproved registry"
                    OriginalCommand   = $entry.Command
                    RequiresElevation = ($entry.Scope -match "Machine")
                })
                break
            }
        }
    }

    # 2. High-Resource Background Process Candidates (WorkingSet > 150MB, no visible window)
    $protectedProcNames = @(
        "explorer", "dwm", "svchost", "csrss", "lsass", "services", "wininit", "smss",
        "RuntimeBroker", "ShellExperienceHost", "MsMpEng", "Memory Compression", "System",
        "TextInputHost", "SecurityHealthHost", "SecurityHealthSystray", "SearchHost",
        "StartMenuExperienceHost", "smartscreen", "ApplicationFrameHost"
    )
    foreach ($proc in $Processes) {
        if ($proc.WorkingSetMB -gt 150 -and (-not $proc.HasWindow) -and ($proc.Name -notin $protectedProcNames)) {
            $candidates.Add([PSCustomObject]@{
                Category          = "BackgroundProcess"
                TargetName        = $proc.Name
                Identifier        = "PID:$($proc.Id)"
                RiskLevel         = "CONDITIONAL"
                Confidence        = 0.75
                Reason            = "Consuming $([math]::Round($proc.WorkingSetMB)) MB of memory without an active user window."
                RecommendedAction = "Inspect parent launch origin (task/service/startup) rather than terminating."
                OriginalCommand   = $proc.ExecutablePath
                RequiresElevation = $false
            })
        }
    }

    # 3. Scheduled Tasks Candidates (Updaters running on daily/logon triggers)
    foreach ($task in $ScheduledTasks) {
        if ($task.State -eq "Ready" -or $task.State -eq "Running") {
            if ($task.TaskName -match "assistant|autoupdate|UpdateTask|ReportTask" -and $task.TaskPath -notmatch "^\\Microsoft\\Windows\\") {
                $candidates.Add([PSCustomObject]@{
                    Category          = "ScheduledTask"
                    TargetName        = $task.TaskName
                    Identifier        = "Task:$($task.TaskPath)$($task.TaskName)"
                    RiskLevel         = "CONDITIONAL"
                    Confidence        = 0.85
                    Reason            = "Background updater or reporting task configured to trigger automatically."
                    RecommendedAction = "Disable scheduled task (Disable-ScheduledTask)"
                    OriginalCommand   = if ($task.Actions) { ($task.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join "; " } else { "" }
                    RequiresElevation = $true
                })
            }
        }
    }

    # 4. Service Candidates (Running optional / third-party services set to Auto start)
    foreach ($svc in $Services) {
        if (($svc.Status -eq "Running" -or $svc.StartMode -eq "Auto") -and (-not $svc.IsMicrosoft)) {
            $isKnownOptional = ($svc.Name -match "GamingServices|Xbox|Speedify|MongoDB|warp|Bonjour|ACCSvc" -or 
                                $svc.DisplayName -match "Gaming Services|Xbox|Speedify|MongoDB|WARP|Bonjour|Acer Care")
            if ($isKnownOptional -or ($svc.Status -eq "Running" -and $svc.StartMode -eq "Auto")) {
                $candidates.Add([PSCustomObject]@{
                    Category          = "Service"
                    TargetName        = $svc.DisplayName
                    Identifier        = "Service:$($svc.Name)"
                    RiskLevel         = "CONDITIONAL"
                    Confidence        = 0.85
                    Reason            = "Background service '$($svc.DisplayName)' is running or configured to autostart at system boot."
                    RecommendedAction = "Set service startup type to Manual (Set-Service -StartupType Manual)"
                    OriginalCommand   = $svc.BinaryPath
                    RequiresElevation = $true
                })
            }
        }
    }

    return $candidates
}

# -----------------------------------------------------------------------------
# Execution & Report Assembly
# -----------------------------------------------------------------------------
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   WinOptimize AI - Read-Only Diagnostic Inspector        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "[1/5] Collecting System & Resource Overview..." -ForegroundColor Yellow
$sysOverview = Get-SystemOverview

Write-Host "[2/5] Inspecting Running Processes..." -ForegroundColor Yellow
$procList = Get-ProcessInspection -Limit $MaxProcesses

Write-Host "[3/5] Inspecting Startup Registry & Folders..." -ForegroundColor Yellow
$startupList = Get-StartupInspection

Write-Host "[4/5] Inspecting Scheduled Tasks..." -ForegroundColor Yellow
$taskList = Get-ScheduledTaskInspection

Write-Host "[5/5] Inspecting Windows Services..." -ForegroundColor Yellow
$svcList = Get-ServiceInspection -IncludeSystem:$IncludeSystemServices.IsPresent

Write-Host "[*] Evaluating Initial Optimization Candidates..." -ForegroundColor Yellow
$candidateList = Get-OptimizationCandidates -Processes $procList -StartupEntries $startupList -ScheduledTasks $taskList -Services $svcList

$scanEndTime = [System.DateTime]::UtcNow
$durationSec = [math]::Round(($scanEndTime - $scanStartTime).TotalSeconds, 2)

$report = [PSCustomObject]@{
    ReportMetadata = [PSCustomObject]@{
        Version         = "1.0.0-phase1-prototype"
        Engine          = "WinOp-PowerShell-Diagnostic"
        ScanTimestamp   = $scanStartTime.ToString("o")
        ScanDurationSec = $durationSec
        IsElevated      = $isAdmin
        ExecutionMode   = "READ_ONLY_STRICT"
    }
    SystemOverview = $sysOverview
    SummaryCounts  = [PSCustomObject]@{
        ProcessesCount        = $procList.Count
        StartupEntriesCount   = $startupList.Count
        ActiveStartupCount    = ($startupList | Where-Object { $_.IsEnabled }).Count
        ScheduledTasksCount   = $taskList.Count
        ServicesCount         = $svcList.Count
        IdentifiedCandidates  = $candidateList.Count
    }
    OptimizationCandidates = $candidateList
    StartupEntries         = $startupList
    ScheduledTasks         = $taskList
    TopProcesses           = ($procList | Select-Object -First 20)
    ServicesOverview       = ($svcList | Select-Object -First 30)
}

# Print Summary Table
Write-Host "`nDiagnostic Scan Completed in $durationSec seconds." -ForegroundColor Green
Write-Host "----------------------------------------------------------"
Write-Host "OS Caption:          $($sysOverview.Caption) ($($sysOverview.Version) Build $($sysOverview.BuildNumber))"
Write-Host "Physical Memory:     $($sysOverview.UsedPhysicalMemoryMB) MB used / $($sysOverview.TotalPhysicalMemoryMB) MB total ($($sysOverview.MemoryUsagePercent)%)"
Write-Host "Running Processes:   $($procList.Count) inspected"
Write-Host "Startup Entries:     $($startupList.Count) found ($(($startupList | Where-Object { $_.IsEnabled }).Count) currently enabled)"
Write-Host "Scheduled Tasks:     $($taskList.Count) non-core tasks found"
Write-Host "Services:            $($svcList.Count) inspected"
Write-Host "Potential Findings:  $($candidateList.Count) optimization candidates identified"
Write-Host "----------------------------------------------------------"

if ($candidateList.Count -gt 0) {
    Write-Host "`nTop Identified Candidates (Read-Only Preview):" -ForegroundColor Magenta
    $candidateList | Select-Object -First 10 Category, TargetName, RiskLevel, Reason | Format-Table -AutoSize
}

# Output to JSON if requested
if ($OutputPath) {
    try {
        $parentDir = Split-Path -Parent $OutputPath
        if ($parentDir -and (-not (Test-Path $parentDir))) {
            New-Item -ItemType Directory -Path $parentDir -Force -ErrorAction SilentlyContinue | Out-Null
        }
        $report | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding utf8
        Write-Host "Structured JSON diagnostic report exported to: $OutputPath" -ForegroundColor Green
    } catch {
        Write-Warning "Failed to save JSON report to '$OutputPath': $_"
    }
}

return $report
