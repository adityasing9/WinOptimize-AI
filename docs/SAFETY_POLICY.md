# WinOptimize AI — Safe Optimization & Protection Policies

## Core Safety Philosophy
WinOptimize AI is engineered strictly as a non-destructive Windows maintenance and diagnostic utility. It is **not** a generic RAM cleaner or an aggressive script that terminates running processes. 

The application enforces seven mandatory safety policies across all operations.

---

### Policy 1: Protect Windows (Protected Whitelist)
Critical operating system components are permanently locked and cannot be selected or modified.

* **Protected Processes**: `explorer.exe`, `dwm.exe`, `svchost.exe`, `csrss.exe`, `lsass.exe`, `services.exe`, `wininit.exe`, `smss.exe`, `RuntimeBroker.exe`, `ShellExperienceHost.exe`, `MsMpEng.exe` (Microsoft Defender), `SecurityHealthHost.exe`, `SecurityHealthSystray.exe`, `SearchHost.exe`, `StartMenuExperienceHost.exe`, `smartscreen.exe`, `ApplicationFrameHost.exe`, `ctfmon.exe`, `taskhostw.exe`, `fontdrvhost.exe`, `sihost.exe`, `Memory Compression`, `System`.
* **Protected Services**: `WinDefend`, `SecurityHealthService`, `MpsSvc` (Windows Firewall), `Audiosrv` (Windows Audio), `AudioEndpointBuilder`, `RpcSs`, `RpcEptMapper`, `DcomLaunch`, `PlugPlay`, `Dhcp`, `Dnscache`, `EventLog`, `FontCache`, `gpsvc`, `LanmanWorkstation`, `Netman`, `nsi`, `ProfSvc`, `SamSs`, `Schedule`, `SENS`, `Themes`, `UserManager`, `wscsvc`, `W32Time`, `WlanSvc`, `KeyIso`, `BFE`, `CryptSvc`.
* **Protected Scheduled Tasks**: Root Windows maintenance tasks (`\Microsoft\Windows\Windows Defender`, `\Microsoft\Windows\DiskDiagnostic`, `\Microsoft\Windows\SystemRestore`, `\Microsoft\Windows\UpdateOrchestrator`, etc.).

---

### Policy 2: Respect User Preferences
Every discovered component supports user customization:
1. `keep_enabled`: Always preserved as enabled; excluded from future recommendation queues.
2. `optimize_when_safe`: Flagged when verified safe.
3. `ignore`: Excluded from all recommendations.
4. `ask_always`: Requires explicit individual user confirmation.

Preferences persist across scans in the local SQLite database.

---

### Policy 3: Non-Destructive Modifications (Toggle vs Delete)
* **Startup Entries**: Disabled by setting the native Windows `StartupApproved\Run` flag to `0x03` (the exact mechanism Windows Task Manager uses). Entries in `CurrentVersion\Run` are **never deleted**.
* **Scheduled Tasks**: Disabled via `Disable-ScheduledTask`. Tasks are **never unregistered or deleted**.
* **Windows Services**: Reconfigured to `Manual` or `Disabled`. Services are **never deleted**.
* **Processes**: The application **never** terminates arbitrary processes in a loop.

---

### Policy 4: Pre-Modification Snapshot & 1-Click Rollback
Before applying any change:
1. Full pre-modification state is captured into SQLite (`backup_snapshots`).
2. Exact registry binary payloads, task states, or service startup types are serialized.
3. Post-change state is verified immediately.
4. If verification fails, an automatic rollback is triggered immediately.
5. Users can restore any previous change with a single click from the History view.

---

### Policy 5: Least Privilege Enforcement
* Routine scans run un-elevated with standard user permissions.
* Elevation (UAC prompt) is requested only on-demand when an approved optimization touches machine-wide scopes (`HKLM` or Windows Services).
* The application never requires permanent Administrator rights.

---

### Policy 6: 100% Offline Privacy Guarantee
* Zero telemetry, zero analytics, zero external network requests.
* Process names, usernames, hardware specs, and configuration snapshots remain entirely on the local machine in `winop.db`.

---

### Policy 7: Honest Performance Metrics
WinOptimize AI displays real, measured physical memory and CPU usage. It never fabricates "PC Health Scores" or guarantees arbitrary speed boosts.
