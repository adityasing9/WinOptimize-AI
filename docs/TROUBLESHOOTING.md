# WinOptimize AI — Troubleshooting & Recovery Guide

## 1. How to Rollback a Change
If an application does not start as expected after an optimization:

### Option A: From Inside the WinOptimize AI UI
1. Open **WinOptimize AI**.
2. Click on the **History & Restore** tab in the sidebar.
3. Locate the snapshot associated with the component (e.g. `Discord` or `Opera Browser Assistant`).
4. Click **Restore**.
5. WinOptimize AI will immediately revert the native `StartupApproved` flag back to enabled and verify the state.

### Option B: Native Windows Task Manager Fallback
Because WinOptimize AI uses native Windows registry structures (`StartupApproved\Run`), you can also re-enable any startup entry using standard Windows tools:
1. Press `Ctrl + Shift + Esc` to open Windows **Task Manager**.
2. Click the **Startup Apps** tab.
3. Find the application in the list (it will be listed as *Disabled*).
4. Right-click and choose **Enable**.

---

## 2. Common Issues and Resolutions

### Issue: "UAC Prompt Appeared"
* **Cause**: Some startup applications or scheduled tasks reside in machine-wide scopes (`HKLM` or root Task Scheduler).
* **Resolution**: Standard user scans never require UAC. If you approve an optimization for an entry installed for *All Users*, Windows UAC will prompt you for administrative authorization. This is normal and expected.

### Issue: "PowerShell Script Execution Policy Warning"
* **Cause**: Windows client PCs may have execution policies configured to `Restricted`.
* **Resolution**: WinOptimize AI automatically passes `-ExecutionPolicy Bypass` when executing its internal read-only diagnostic script. If PowerShell is blocked entirely by corporate Group Policy, the built-in pure Python fallback engine (`psutil` + `winreg`) seamlessly handles the scan.

### Issue: "Application Keeps Reappearing After Closing"
* **Resolution**: Use the **Interactive Relaunch Observer** in the *Settings & Observer* tab:
  1. Open the Settings tab.
  2. Enter the process name in the Relaunch Diagnostic box (e.g. `browser_assistant`).
  3. Click **Start Diagnostic Session** (15s).
  4. The tool will trace the parent process ID, inspect your scheduled tasks, and pinpoint whether an auto-update task or watchdog launcher is responsible.
