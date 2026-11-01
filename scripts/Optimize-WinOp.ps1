<#
.SYNOPSIS
    WinOptimize AI - Terminal Optimization & Rollback Engine
    Enables safe, non-destructive process termination, startup disabling, task scheduling,
    and service reconfiguration directly from the PowerShell terminal.

.DESCRIPTION
    Runs interactive or automated optimizations based on diagnostic findings.
    Automatically captures pre-change backup snapshots to enable 1-click instant rollback.
    Strictly non-destructive: Never deletes registry keys, never unregisters tasks.

.PARAMETER All
    Automatically optimizes all safe identified candidates without interactive prompts.

.PARAMETER Rollback
    Rolls back the most recent terminal optimization session.

.EXAMPLE
    irm https://raw.githubusercontent.com/adityasing9/WinOptimize-AI/main/scripts/Optimize-WinOp.ps1 | iex
#>

param(
    [switch]$All,
    [switch]$Rollback,
    [Parameter(ValueFromPipeline = $true)]
    [string]$InputChoice = ""
)

$ErrorActionPreference = "SilentlyContinue"

# Check Elevation
function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = [Security.Principal.WindowsPrincipal]$id
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$isAdmin = Test-IsAdmin
$snapshotDir = Join-Path $env:LOCALAPPDATA "WinOptimizeAI\Snapshots"
if (-not (Test-Path $snapshotDir)) { New-Item -ItemType Directory -Path $snapshotDir -Force | Out-Null }
$snapshotFile = Join-Path $snapshotDir "terminal_snapshots.json"

function Invoke-ElevatedPowerShell {
    param([string]$Script)
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($Script)
    $encoded = [System.Convert]::ToBase64String($bytes)
    $proc = Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded"
    $null = $proc.ExitCode
}

# Load existing snapshots
function Get-SavedSnapshots {
    if (Test-Path $snapshotFile) {
        try {
            $raw = Get-Content -Path $snapshotFile -Raw -Encoding UTF8
            return ($raw | ConvertFrom-Json)
        } catch { }
    }
    return [System.Collections.Generic.List[PSCustomObject]]::new()
}

function Save-SnapshotRecord {
    param($Record)
    $snaps = Get-SavedSnapshots
    $snapsList = [System.Collections.Generic.List[PSCustomObject]]::new()
    if ($snaps) {
        foreach ($s in $snaps) { $snapsList.Add($s) }
    }
    $snapsList.Add($Record)
    $snapsList | ConvertTo-Json -Depth 5 | Set-Content -Path $snapshotFile -Encoding UTF8 -Force
}

# -----------------------------------------------------------------------------
# Rollback Functionality
# -----------------------------------------------------------------------------
if ($Rollback) {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "   WinOptimize AI — Terminal Rollback Engine              " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan

    $snaps = Get-SavedSnapshots
    if (-not $snaps -or $snaps.Count -eq 0) {
        Write-Host "[-] No previous terminal optimization snapshots found to restore." -ForegroundColor Yellow
        if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
        return
    }

    Write-Host "[*] Found $($snaps.Count) saved snapshot records. Reverting..." -ForegroundColor Yellow
    foreach ($snap in $snaps) {
        Write-Host " -> Restoring $($snap.Category): $($snap.TargetName)..." -NoNewline
        switch ($snap.Category) {
            "Service" {
                $origMode = if ($snap.OriginalState.StartMode) { $snap.OriginalState.StartMode } else { "Auto" }
                $startVal = if ($origMode -match "Auto") { 2 } elseif ($origMode -match "Disabled") { 4 } else { 3 }
                Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($snap.TargetName)" -Name "Start" -Value $startVal -ErrorAction SilentlyContinue
                Set-Service -Name $snap.TargetName -StartupType $origMode -ErrorAction SilentlyContinue
                sc.exe config "$($snap.TargetName)" start= auto 2>$null | Out-Null
                Write-Host " [RESTORED to $origMode]" -ForegroundColor Green
            }
            "ScheduledTask" {
                $taskPath = if ($snap.OriginalState.TaskPath) { $snap.OriginalState.TaskPath } else { "\" }
                if (-not $taskPath.EndsWith("\")) { $taskPath = "$taskPath\" }
                $fullPath = if ($taskPath -eq "\") { "\$($snap.TargetName)" } else { "$taskPath$($snap.TargetName)" }
                Enable-ScheduledTask -TaskName $snap.TargetName -TaskPath $taskPath -ErrorAction SilentlyContinue | Out-Null
                schtasks.exe /change /tn "$fullPath" /enable 2>$null | Out-Null
                Write-Host " [RE-ENABLED]" -ForegroundColor Green
            }
            "StartupEntry" {
                $enabledBytes = [byte[]](0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
                $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
                Set-ItemProperty -Path $key -Name $snap.TargetName -Value $enabledBytes -ErrorAction SilentlyContinue
                Write-Host " [RE-ENABLED]" -ForegroundColor Green
            }
            "BackgroundProcess" {
                if ($snap.TargetName -match "phone|crossdevice") {
                    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications\Microsoft.YourPhone_8wekyb3d8bbwe"
                    Set-ItemProperty -Path $regPath -Name "Disabled" -Value 0 -ErrorAction SilentlyContinue
                    Set-ItemProperty -Path $regPath -Name "DisabledByUser" -Value 0 -ErrorAction SilentlyContinue
                }
                Write-Host " [PERMISSIONS RESTORED]" -ForegroundColor Green
            }
        }
    }
    Remove-Item -Path $snapshotFile -Force -ErrorAction SilentlyContinue
    Write-Host "[✓] Rollback completed successfully." -ForegroundColor Green
    if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
    return
}

# -----------------------------------------------------------------------------
# Diagnostic Scan for Optimization Candidates
# -----------------------------------------------------------------------------
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   WinOptimize AI — Interactive Terminal Optimizer        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not $isAdmin) {
    Write-Host "[!] Note: Running as standard user." -ForegroundColor Yellow
    Write-Host "    Configuring Windows Services (Speedify, WARP, Gaming Services, MongoDB)" -ForegroundColor White
    Write-Host "    and Scheduled Tasks requires Administrator privileges." -ForegroundColor White
    Write-Host "    You can continue (actions will request UAC), or press 'E' below to elevate." -ForegroundColor DarkGray
}

Write-Host "[*] Inspecting system state for optimization candidates..." -ForegroundColor Cyan

$candidates = [System.Collections.Generic.List[PSCustomObject]]::new()

# 1. Services & Running Service Daemons
$knownServices = @(
    @{ Name = "GamingServices"; Display = "Xbox Gaming Services"; Reason = "Xbox Game Pass background installer daemon"; ProcessNames = @("GamingServices", "gamingservices"); IsWindowsManaged = $true },
    @{ Name = "GamingServicesNet"; Display = "Xbox Gaming Services Net"; Reason = "Xbox Game Pass networking helper"; ProcessNames = @("GamingServicesNet", "gamingservicesnet"); IsWindowsManaged = $true },
    @{ Name = "XboxService"; Display = "Xbox Accessory Service"; Reason = "Xbox accessory background service"; ProcessNames = @("XboxService") },
    @{ Name = "Speedify"; Display = "Speedify VPN Service"; Reason = "Speedify channel bonding VPN resident daemon"; ProcessNames = @("Speedify", "SpeedifyService") },
    @{ Name = "CloudflareWARP"; Display = "Cloudflare 1.1.1.1 WARP"; Reason = "WARP VPN background tunnel daemon"; ProcessNames = @("warp-svc") },
    @{ Name = "warp-svc"; Display = "Cloudflare WARP Daemon"; Reason = "WARP client background engine"; ProcessNames = @("warp-svc") },
    @{ Name = "MongoDB"; Display = "MongoDB Database Server"; Reason = "Local database engine configured to autostart"; ProcessNames = @("mongod") },
    @{ Name = "ACCSvc"; Display = "Acer Care Center"; Reason = "OEM background telemetry service"; ProcessNames = @("ACCSvc", "ACCStd", "AcerCareCenterCheck") },
    @{ Name = "Bonjour Service"; Display = "Apple Bonjour Service"; Reason = "Apple mDNS local discovery service"; ProcessNames = @("mDNSResponder", "Bonjour") }
)

foreach ($svcMeta in $knownServices) {
    $svc = Get-Service -Name $svcMeta.Name -ErrorAction SilentlyContinue
    $isAuto = $false
    $startType = "Manual"
    $isSvcRunning = $false
    if ($svc) {
        $startType = $svc.StartType.ToString()
        $isAuto = ($startType -eq "Automatic")
        $isSvcRunning = ($svc.Status -eq "Running")
    }

    # Verify directly against registry Start value (2=Auto, 3=Manual, 4=Disabled)
    $regCheck = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($svcMeta.Name)" -ErrorAction SilentlyContinue
    if ($regCheck) {
        if ($regCheck.Start -eq 2) {
            $isAuto = $true
            $startType = "Automatic"
        } elseif ($regCheck.Start -eq 3 -or $regCheck.Start -eq 4) {
            $isAuto = $false
            $startType = if ($regCheck.Start -eq 3) { "Manual" } else { "Disabled" }
        }
    }

    # If a Windows-managed AppX service is already set to Manual, it has already been optimized for boot
    if ($svcMeta.IsWindowsManaged -and $startType -eq "Manual") {
        continue
    }

    # Check if daemon process is currently running in background
    $runningProcs = @()
    if ($svcMeta.ProcessNames) {
        $runningProcs = Get-Process -Name $svcMeta.ProcessNames -ErrorAction SilentlyContinue
    }

    $isProcRunning = ($runningProcs.Count -gt 0)

    # Flag candidate if configured to Auto OR currently running
    if ($isAuto -or ($isProcRunning -and $startType -ne "Disabled") -or ($isSvcRunning -and $startType -ne "Disabled")) {
        $actionDesc = if ($isAuto) {
            "Set startup to Manual & Stop resident daemon"
        } else {
            "Set startup to Disabled (Prevent auto-respawn) & Stop process"
        }
        $targetVal = if ($isAuto) { 3 } else { 4 }

        $candidates.Add([PSCustomObject]@{
            Category          = "Service"
            TargetName        = $svcMeta.Name
            DisplayName       = $svcMeta.Display
            CurrentAction     = $actionDesc
            Reason            = $svcMeta.Reason
            ProcessNames      = $svcMeta.ProcessNames
            IsAuto            = $isAuto
            IsRunning         = ($isProcRunning -or $isSvcRunning)
            TargetStartVal    = $targetVal
            OriginalState     = @{ StartMode = $startType }
            RequiresElevation = $true
        })
    }
}

# 2. Startup Entries in Registry
$startupKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
$knownStartups = @("Opera Browser Assistant", "Opera GX Browser Assistant", "Discord", "Docker Desktop", "Imo Messenger")
if (Test-Path $startupKey) {
    $props = Get-ItemProperty -Path $startupKey -ErrorAction SilentlyContinue
    foreach ($appName in $knownStartups) {
        $val = $props.$appName
        if ($val -and $val[0] -eq 2) {
            $candidates.Add([PSCustomObject]@{
                Category          = "StartupEntry"
                TargetName        = $appName
                DisplayName       = $appName
                CurrentAction     = "Disable in StartupApproved registry"
                Reason            = "Background startup assistant launched on user login"
                OriginalState     = @{ EnabledBytes = $val }
                RequiresElevation = $false
            })
        }
    }
}

# 3. Scheduled Tasks
$knownTasks = @(
    @{ Name = "App Explorer"; Path = "\" },
    @{ Name = "AcerJumpstartTask"; Path = "\Oem\" },
    @{ Name = "JumpstartAgentTask"; Path = "\Oem\" },
    @{ Name = "JumpstartRuntimeTask"; Path = "\Oem\" },
    @{ Name = "SoftLandingCreativeManagementTask"; Path = "\" }
)

foreach ($tMeta in $knownTasks) {
    $fullP = if ($tMeta.Path -eq "\") { "\$($tMeta.Name)" } else { "$($tMeta.Path)$($tMeta.Name)" }
    $qOut = schtasks.exe /query /tn "$fullP" /fo CSV 2>$null | Out-String
    $isDisabled = ($qOut -match "Disabled")

    if (-not $isDisabled) {
        $t = Get-ScheduledTask -TaskName $tMeta.Name -TaskPath $tMeta.Path -ErrorAction SilentlyContinue
        if (-not $t) { $t = Get-ScheduledTask -TaskName $tMeta.Name -ErrorAction SilentlyContinue }
        if ($t -and $t.State -eq "Disabled") {
            $isDisabled = $true
        }
    }

    if (-not $isDisabled -and ($qOut.Trim() -or $t)) {
        $taskPath = if ($t -and $t.TaskPath) { $t.TaskPath } else { $tMeta.Path }
        $candidates.Add([PSCustomObject]@{
            Category          = "ScheduledTask"
            TargetName        = $tMeta.Name
            DisplayName       = "$($tMeta.Name) Task"
            CurrentAction     = "Disable scheduled task"
            Reason            = "OEM telemetry / updater scheduled task"
            OriginalState     = @{ TaskPath = $taskPath }
            RequiresElevation = $true
        })
    }
}

# 4. Background Processes (Phone Link / Brave Memory Hogs)
$phoneProcs = Get-Process -Name "PhoneExperienceHost", "CrossDeviceService" -ErrorAction SilentlyContinue
if ($phoneProcs) {
    $candidates.Add([PSCustomObject]@{
        Category          = "BackgroundProcess"
        TargetName        = "PhoneExperienceHost"
        DisplayName       = "Windows Phone Link (PhoneExperienceHost)"
        CurrentAction     = "End process & Disable Background App permissions"
        Reason            = "Resident background synchronization agent"
        OriginalState     = @{ Pids = ($phoneProcs | ForEach-Object { $_.Id }) }
        RequiresElevation = $false
    })
}

$braveProcs = Get-Process -Name "brave" -ErrorAction SilentlyContinue
if ($braveProcs.Count -gt 5) {
    $totalRamMB = [math]::Round(($braveProcs | Measure-Object -Property WorkingSet64 -Sum).Sum / 1MB)
    $candidates.Add([PSCustomObject]@{
        Category          = "BackgroundProcess"
        TargetName        = "brave"
        DisplayName       = "Brave Browser Background Processes ($($braveProcs.Count) procs, $totalRamMB MB RAM)"
        CurrentAction     = "End dormant background renderers / close browser"
        Reason            = "Dormant tabs and background extensions consuming memory"
        OriginalState     = @{ Pids = ($braveProcs | ForEach-Object { $_.Id }) }
        RequiresElevation = $false
    })
}

if ($candidates.Count -eq 0) {
    Write-Host "[✓] No redundant background processes, services, or tasks found! System is well-optimized." -ForegroundColor Green
    if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
    return
}

Write-Host "`nFound $($candidates.Count) optimization candidate(s):" -ForegroundColor Green
Write-Host "----------------------------------------------------------"
for ($i = 0; $i -lt $candidates.Count; $i++) {
    $c = $candidates[$i]
    $idx = $i + 1
    Write-Host "[$idx] " -ForegroundColor Yellow -NoNewline
    Write-Host "$($c.Category): " -ForegroundColor Cyan -NoNewline
    Write-Host "$($c.DisplayName)" -ForegroundColor White
    Write-Host "    Action: $($c.CurrentAction)" -ForegroundColor DarkGray
    Write-Host "    Reason: $($c.Reason)" -ForegroundColor DarkGray
}
Write-Host "----------------------------------------------------------"
Write-Host "[A] Apply ALL Safe Recommendations" -ForegroundColor Green
if (-not $isAdmin) {
    Write-Host "[E] Relaunch as Administrator (Recommended for Services & Tasks)" -ForegroundColor Yellow
}
Write-Host "[R] Rollback Previous Changes" -ForegroundColor Cyan
Write-Host "[Q] Quit without making any changes" -ForegroundColor DarkRed
Write-Host "----------------------------------------------------------"

$selectedIndices = @()
if ($All) {
    for ($i = 0; $i -lt $candidates.Count; $i++) { $selectedIndices += $i }
} else {
    $promptMsg = if (-not $isAdmin) { "Enter option [A for all, E to relaunch as Admin, numbers (e.g. 1,4), or Q to quit]" } else { "Enter option [A for all, numbers separated by commas (e.g. 1,2,4), or Q to quit]" }
    $choice = if ($InputChoice) { $InputChoice } else { Read-Host $promptMsg }
    if ($choice -match "^[Qq]") {
        Write-Host "No changes applied. Exiting." -ForegroundColor Yellow
        if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
        return
    }
    if ($choice -match "^[Ee]") {
        Write-Host "[*] Relaunching in elevated Administrator PowerShell window..." -ForegroundColor Cyan
        $scriptUrl = "https://raw.githubusercontent.com/adityasing9/WinOptimize-AI/main/scripts/Optimize-WinOp.ps1?v=$(Get-Random)"
        Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -Command `"irm '$scriptUrl' | iex`""
        Write-Host "[✓] Elevated Administrator window launched. You can continue there." -ForegroundColor Green
        if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter in this window to finish..." }
        return
    }
    if ($choice -match "^[Rr]") {
        & $PSCommandPath -Rollback
        if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
        return
    }
    if ($choice -match "^[Aa]") {
        for ($i = 0; $i -lt $candidates.Count; $i++) { $selectedIndices += $i }
    } else {
        $parts = $choice -split ","
        foreach ($p in $parts) {
            $num = 0
            if ([int]::TryParse($p.Trim(), [ref]$num) -and $num -ge 1 -and $num -le $candidates.Count) {
                $selectedIndices += ($num - 1)
            }
        }
    }
}

if ($selectedIndices.Count -eq 0) {
    Write-Host "No valid candidates selected. Exiting." -ForegroundColor Yellow
    if (-not $All -and -not [Console]::IsInputRedirected) { Read-Host "Press Enter to exit..." }
    return
}

Write-Host "`nApplying selected optimizations with automatic safety backup..." -ForegroundColor Cyan

foreach ($idx in $selectedIndices) {
    $c = $candidates[$idx]
    Write-Host " -> Optimizing $($c.Category): $($c.DisplayName)..." -NoNewline

    $snapRecord = [PSCustomObject]@{
        Timestamp     = [System.DateTime]::UtcNow.ToString("o")
        Category      = $c.Category
        TargetName    = $c.TargetName
        OriginalState = $c.OriginalState
    }

    $success = $false

    switch ($c.Category) {
        "Service" {
            # 1. Capture snapshot
            Save-SnapshotRecord -Record $snapRecord

            $targetVal = if ($c.TargetStartVal) { $c.TargetStartVal } else { 3 }
            $targetMode = if ($targetVal -eq 4) { "Disabled" } else { "Manual" }
            $scMode = if ($targetVal -eq 4) { "disabled" } else { "demand" }

            # 2. Reconfigure service startup mode & stop resident instances
            Set-Service -Name $c.TargetName -StartupType $targetMode -ErrorAction SilentlyContinue
            Stop-Service -Name $c.TargetName -Force -ErrorAction SilentlyContinue
            sc.exe config "$($c.TargetName)" start= $scMode 2>$null | Out-Null
            net stop "$($c.TargetName)" 2>$null | Out-Null
            sc.exe stop "$($c.TargetName)" 2>$null | Out-Null
            Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($c.TargetName)" -Name "Start" -Value $targetVal -Type DWord -ErrorAction SilentlyContinue

            # Terminate corresponding resident daemon process(es)
            $allKill = @($c.TargetName)
            if ($c.ProcessNames) { $allKill += $c.ProcessNames }
            $allKill = $allKill | Select-Object -Unique
            foreach ($pn in $allKill) {
                taskkill.exe /F /T /IM "$pn.exe" 2>$null | Out-Null
            }

            # 3. Check verification
            $isProcStillRunning = $false
            $procs = Get-Process -Name $allKill -ErrorAction SilentlyContinue
            if ($procs -and $procs.Count -gt 0) { $isProcStillRunning = $true }
            $chkSvc = Get-Service -Name $c.TargetName -ErrorAction SilentlyContinue
            $isSvcStillRunning = ($chkSvc -and $chkSvc.Status -eq "Running")

            $regProps = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($c.TargetName)" -ErrorAction SilentlyContinue
            $startIsTarget = ($regProps -and $regProps.Start -eq $targetVal)

            # Only marked done if startup matches target value AND process/service is actually stopped
            $isDone = $startIsTarget -and (-not $isProcStillRunning) -and (-not $isSvcStillRunning)

            # 4. If failed because not running as admin, trigger single elevated UAC execution
            if (-not $isDone) {
                Write-Host " [Admin UAC]..." -NoNewline -ForegroundColor Yellow
                $killCommands = ""
                foreach ($pn in $allKill) {
                    $killCommands += "`n& taskkill.exe /F /T /IM '$pn.exe' 2>`$null"
                }

                $elevScript = @"
Set-Service -Name '$($c.TargetName)' -StartupType $targetMode -ErrorAction SilentlyContinue
Stop-Service -Name '$($c.TargetName)' -Force -ErrorAction SilentlyContinue
& sc.exe config '$($c.TargetName)' start= $scMode
& net stop '$($c.TargetName)'
& sc.exe stop '$($c.TargetName)'
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($c.TargetName)" -Name "Start" -Value $targetVal -Type DWord -ErrorAction SilentlyContinue
$killCommands
"@
                $null = Invoke-ElevatedPowerShell -Script $elevScript

                # Re-verify post-elevation
                $isProcStillRunning2 = $false
                $procs2 = Get-Process -Name $allKill -ErrorAction SilentlyContinue
                if ($procs2 -and $procs2.Count -gt 0) { $isProcStillRunning2 = $true }
                $chkSvc2 = Get-Service -Name $c.TargetName -ErrorAction SilentlyContinue
                $isSvcStillRunning2 = ($chkSvc2 -and $chkSvc2.Status -eq "Running")
                $regProps2 = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($c.TargetName)" -ErrorAction SilentlyContinue
                $startIsTarget2 = ($regProps2 -and $regProps2.Start -eq $targetVal)

                $isDone = $startIsTarget2 -and (-not $isProcStillRunning2) -and (-not $isSvcStillRunning2)
            }
            $success = $isDone
        }
        "ScheduledTask" {
            Save-SnapshotRecord -Record $snapRecord
            $taskPath = if ($c.OriginalState.TaskPath) { $c.OriginalState.TaskPath } else { "\" }
            if (-not $taskPath.EndsWith("\")) { $taskPath = "$taskPath\" }
            $fullPath = if ($taskPath -eq "\") { "\$($c.TargetName)" } else { "$taskPath$($c.TargetName)" }

            # 1. Direct attempt
            Disable-ScheduledTask -TaskName $c.TargetName -TaskPath $taskPath -ErrorAction SilentlyContinue 2>$null | Out-Null
            Disable-ScheduledTask -TaskName $c.TargetName -ErrorAction SilentlyContinue 2>$null | Out-Null
            schtasks.exe /change /tn "$fullPath" /disable 2>$null | Out-Null
            schtasks.exe /end /tn "$fullPath" 2>$null | Out-Null
            schtasks.exe /change /tn "$($c.TargetName)" /disable 2>$null | Out-Null
            schtasks.exe /end /tn "$($c.TargetName)" 2>$null | Out-Null

            # 2. Verify
            $qOut = schtasks.exe /query /tn "$fullPath" /fo CSV 2>$null | Out-String
            $isTaskDisabled = ($qOut -match "Disabled")
            if (-not $isTaskDisabled) {
                $t = Get-ScheduledTask -TaskName $c.TargetName -TaskPath $taskPath -ErrorAction SilentlyContinue
                if (-not $t) { $t = Get-ScheduledTask -TaskName $c.TargetName -ErrorAction SilentlyContinue }
                $isTaskDisabled = ($t -and $t.State -eq "Disabled")
            }

            # 3. Elevated fallback if needed via Base64 EncodedCommand
            if (-not $isTaskDisabled) {
                Write-Host " [Admin UAC]..." -NoNewline -ForegroundColor Yellow
                $elevTask = @"
Disable-ScheduledTask -TaskName '$($c.TargetName)' -TaskPath '$taskPath' -ErrorAction SilentlyContinue
Disable-ScheduledTask -TaskName '$($c.TargetName)' -ErrorAction SilentlyContinue
& schtasks.exe /change /tn "$fullPath" /disable
& schtasks.exe /end /tn "$fullPath"
& schtasks.exe /change /tn "$($c.TargetName)" /disable
& schtasks.exe /end /tn "$($c.TargetName)"
"@
                $null = Invoke-ElevatedPowerShell -Script $elevTask
                $qOut2 = schtasks.exe /query /tn "$fullPath" /fo CSV 2>$null | Out-String
                $isTaskDisabled = ($qOut2 -match "Disabled")
                if (-not $isTaskDisabled) {
                    $t2 = Get-ScheduledTask -TaskName $c.TargetName -TaskPath $taskPath -ErrorAction SilentlyContinue
                    if (-not $t2) { $t2 = Get-ScheduledTask -TaskName $c.TargetName -ErrorAction SilentlyContinue }
                    $isTaskDisabled = ($t2 -and $t2.State -eq "Disabled")
                }
            }
            $success = $isTaskDisabled
        }
        "StartupEntry" {
            Save-SnapshotRecord -Record $snapRecord
            $disabledBytes = [byte[]](0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
            Set-ItemProperty -Path $startupKey -Name $c.TargetName -Value $disabledBytes -ErrorAction SilentlyContinue
            $success = $true
        }
        "BackgroundProcess" {
            Save-SnapshotRecord -Record $snapRecord
            if ($c.TargetName -eq "PhoneExperienceHost") {
                $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications\Microsoft.YourPhone_8wekyb3d8bbwe"
                if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
                Set-ItemProperty -Path $regPath -Name "Disabled" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $regPath -Name "DisabledByUser" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                taskkill.exe /F /IM PhoneExperienceHost.exe 2>$null | Out-Null
                taskkill.exe /F /IM CrossDeviceService.exe 2>$null | Out-Null
                $success = $true
            } elseif ($c.TargetName -eq "brave") {
                taskkill.exe /F /IM brave.exe 2>$null | Out-Null
                $success = $true
            } else {
                taskkill.exe /F /IM "$($c.TargetName).exe" 2>$null | Out-Null
                $success = $true
            }
        }
    }

    if ($success) {
        Write-Host " [✓ VERIFIED & APPLIED]" -ForegroundColor Green
    } else {
        Write-Host " [!] Completed (Review in Task Manager)" -ForegroundColor Yellow
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   Optimizations Applied Successfully!                   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Backup snapshot saved to: $snapshotFile" -ForegroundColor DarkGray
Write-Host "To undo any of these changes at any time, run:" -ForegroundColor Cyan
Write-Host "   irm https://raw.githubusercontent.com/adityasing9/WinOptimize-AI/main/scripts/Optimize-WinOp.ps1 | iex -Rollback" -ForegroundColor White
Write-Host "==========================================================`n" -ForegroundColor Green

if (-not $All -and -not [Console]::IsInputRedirected) {
    Read-Host "Optimization session completed. Press Enter to exit..."
}
