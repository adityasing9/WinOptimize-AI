# WinOptimize AI — Intelligent Windows Background Process Optimizer

> A lightweight, intelligent Windows desktop utility that helps users identify and safely reduce unnecessary background activity, excessive startup applications, redundant scheduled tasks, and applications that repeatedly relaunch.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-green.svg)](https://www.qt.io/)
[![Safety](https://img.shields.io/badge/Safety-Protected%20Policy%20Enforced-brightgreen.svg)](docs/SAFETY_POLICY.md)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-blueviolet.svg)](docs/SAFETY_POLICY.md)

---

## The Core Workflow

$$\textbf{Scan} \longrightarrow \textbf{Analyze} \longrightarrow \textbf{Recommend} \longrightarrow \textbf{Optimize} \longrightarrow \textbf{Verify} \longrightarrow \textbf{Restore}$$

WinOptimize AI is **not** a generic RAM cleaner or an aggressive script that blindly terminates processes. It identifies the underlying causes of background activity (startup registry keys, scheduled tasks, background services, and watchdog relaunchers) and applies native, reversible configurations.

---

## Key Features

1. **Native, Non-Destructive Optimizations**:
   - Disables startup entries via the Windows native `StartupApproved\Run` registry mechanism (identical to Windows Task Manager). Registry keys are **never deleted**.
   - Disables scheduled tasks via `Disable-ScheduledTask`. Tasks are **never unregistered or deleted**.
   - Reconfigures optional services to `Manual`. Services are **never removed**.
   - Never kills running processes in a blind loop.

2. **Hardcoded Protected Whitelist**:
   - Permanent protection for Microsoft Defender (`MsMpEng`, `WinDefend`, `SecurityHealth`), Windows Firewall (`MpsSvc`), Windows Audio, Desktop Window Manager (`dwm.exe`), Local Security Authority (`lsass.exe`), RPC, and core system drivers.

3. **Atomic Pre-Modification Snapshots & 1-Click Rollback**:
   - Captures the complete serialized state (including binary registry payloads) into local SQLite storage before any change is made.
   - Verifies the state immediately after applying. If verification fails, an automatic rollback is executed immediately.
   - Restore any individual setting or previous optimization session with one click.

4. **Interactive Relaunch Diagnostic Engine**:
   - Time-bounded observation sessions that trace parent process IDs (PPIDs), cross-reference Task Scheduler actions, and identify why an application re-opens after being closed.

5. **100% Offline & Private**:
   - No cloud backends, no telemetry, no tracking. All data is stored locally in `winop.db`.

---

## Project Structure

```
WinOp/
├── app/                  # Desktop application entry point & lifecycle
│   └── main.py
├── ui/                   # PySide6 desktop interface (MVVM architecture)
│   ├── styles.py         # Dark & Light modern Fluent themes
│   ├── workers.py        # Asynchronous QThread workers (non-blocking)
│   ├── views/            # Dashboard, Findings, Recommendations, Optimize, History, Settings
│   └── main_window.py
├── scanner/              # Read-only inspection engine
│   ├── models.py         # Strongly-typed data models
│   ├── system_scanner.py # Dual-engine (PowerShell CIM + Python fallback)
│   └── diagnostic_runner.py # CLI diagnostic runner
├── rules/                # Local, versioned rule engine
│   ├── rule_definitions.py # 3-Tier risk catalog (LOW, CONDITIONAL, PROTECTED)
│   └── rules_engine.py   # Pattern matcher & confidence evaluator
├── analyzer/             # Process & launch correlation engine
│   └── process_analyzer.py
├── optimizer/            # Reversible system modifiers
│   ├── modifiers.py      # Registry, Task, and Service atomic modifiers
│   └── optimization_coordinator.py
├── backup/               # Snapshots and rollback orchestrator
│   ├── snapshot_manager.py
│   └── rollback_orchestrator.py
├── verification/         # Immediate post-change state validator
│   └── state_verifier.py
├── monitoring/           # Relaunch diagnostic engine
│   └── relaunch_detector.py
├── storage/              # SQLite database (winop.db)
│   └── database.py
├── scripts/              # Windows PowerShell diagnostic scripts
│   └── Get-WinOpDiagnostics.ps1
├── packaging/            # PyInstaller build automation & spec
│   ├── winop.spec
│   └── build_exe.py
├── tests/                # Automated test suite (17 tests)
└── docs/                 # Safety policy & troubleshooting documentation
```

---

## Quick Start

### 1. Launch the Desktop Application
```powershell
python app/main.py
```

### 2. Run the CLI Diagnostic Scanner (Read-Only)
```powershell
python -m scanner.diagnostic_runner --output-dir reports
```
This generates a structured JSON report (`reports/diagnostic_report_*.json`) and a readable Markdown summary (`reports/diagnostic_summary_*.md`).

### 3. Run the Automated Test Suite
```powershell
python -m unittest discover tests
```

---

## Standalone Executable Build

A pre-packaged Windows executable is located at:
```
dist/WinOptimizeAI/WinOptimizeAI.exe
```

To re-build the executable:
```powershell
python packaging/build_exe.py
```

---

## Safe Optimization Policies

For detailed safety specifications, read the **[Safety Policy Document](docs/SAFETY_POLICY.md)**. For rollback and troubleshooting, see the **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**.
