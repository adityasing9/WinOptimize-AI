"""
WinOptimize AI - System Scanner Orchestration
Executes read-only system inspection via native PowerShell or fallback Python APIs.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import (
    DiagnosticReport,
    SystemInfo,
    ProcessFinding,
    StartupFinding,
    ScheduledTaskFinding,
    ServiceFinding,
    CandidateFinding,
)

logger = logging.getLogger("WinOp.Scanner")


class SystemScanner:
    """
    Read-only system inspector orchestrator.
    Executes PowerShell diagnostic inspection scripts and parses structured results.
    Includes native Python fallback via psutil and winreg for high resilience.
    """

    def __init__(self, script_path: Optional[Path] = None):
        if script_path is None:
            # Default to scripts/Get-WinOpDiagnostics.ps1 relative to repo root
            base_dir = Path(__file__).resolve().parent.parent
            self.script_path = base_dir / "scripts" / "Get-WinOpDiagnostics.ps1"
        else:
            self.script_path = Path(script_path)

    def scan(self, output_json_path: Optional[str] = None, use_powershell: bool = True) -> DiagnosticReport:
        """
        Executes a complete read-only system scan and returns a DiagnosticReport.
        """
        if use_powershell and self.script_path.exists():
            try:
                return self._scan_via_powershell(output_json_path)
            except Exception as e:
                logger.warning("PowerShell diagnostic scan failed or was restricted: %s. Falling back to native Python.", e)
                return self._scan_via_python_fallback(output_json_path)
        else:
            return self._scan_via_python_fallback(output_json_path)

    def _get_powershell_executable(self) -> str:
        """Finds pwsh or powershell.exe."""
        pwsh = shutil.which("pwsh")
        if pwsh:
            return pwsh
        ps = shutil.which("powershell")
        if ps:
            return ps
        return "powershell.exe"

    def _scan_via_powershell(self, output_json_path: Optional[str]) -> DiagnosticReport:
        """Executes the PowerShell diagnostic script and parses the generated JSON."""
        ps_exe = self._get_powershell_executable()
        
        # Use provided output path or a temporary file
        temp_file = None
        if output_json_path:
            target_path = Path(output_json_path).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            report_file = str(target_path)
        else:
            temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            temp_file.close()
            report_file = temp_file.name

        cmd = [
            ps_exe,
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(self.script_path.resolve()),
            "-OutputPath", report_file,
            "-MaxProcesses", "250",
            "-IncludeSystemServices"
        ]

        logger.info("Executing diagnostic script: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if proc.returncode != 0 and not Path(report_file).exists():
            raise RuntimeError(f"PowerShell diagnostic exited with code {proc.returncode}: {proc.stderr}")

        if not Path(report_file).exists() or Path(report_file).stat().st_size == 0:
            raise RuntimeError("Diagnostic script produced empty report file.")

        with open(report_file, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)

        # Cleanup temp file if one was created
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass

        report = DiagnosticReport.from_dict(raw_data)
        return report

    def _scan_via_python_fallback(self, output_json_path: Optional[str]) -> DiagnosticReport:
        """
        Pure Python fallback inspection using psutil and winreg.
        Ensures scanner functions even if PowerShell execution is disabled or restricted.
        """
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()

        # 1. System Info via psutil
        import psutil
        mem = psutil.virtual_memory()
        cpu_load = psutil.cpu_percent(interval=0.1)

        sys_info = SystemInfo(
            caption=f"Windows {sys.getwindowsversion().major}.{sys.getwindowsversion().minor}",
            version=str(sys.getwindowsversion().major),
            build_number=str(sys.getwindowsversion().build),
            architecture=os.environ.get("PROCESSOR_ARCHITECTURE", "64-bit"),
            total_physical_memory_mb=round(mem.total / (1024 * 1024), 2),
            free_physical_memory_mb=round(mem.available / (1024 * 1024), 2),
            used_physical_memory_mb=round((mem.total - mem.available) / (1024 * 1024), 2),
            memory_usage_percent=mem.percent,
            cpu_load_percent=cpu_load,
            machine_name=os.environ.get("COMPUTERNAME", ""),
            current_user=f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}",
            is_elevated=False,
            source="PythonFallback-psutil",
        )

        # 2. Running Processes via psutil
        top_procs: List[ProcessFinding] = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'exe', 'ppid']):
            try:
                info = p.info
                mem_mb = round(info['memory_info'].rss / (1024 * 1024), 2) if info.get('memory_info') else 0.0
                top_procs.append(
                    ProcessFinding(
                        pid=info['pid'],
                        name=info.get('name', ''),
                        working_set_mb=mem_mb,
                        private_memory_mb=mem_mb,
                        executable_path=info.get('exe', '') or '',
                        parent_pid=info.get('ppid', 0) or 0,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_procs.sort(key=lambda x: x.working_set_mb, reverse=True)
        top_slice = top_procs[:250]

        # 3. Startup Registry Entries via winreg
        startup_entries: List[StartupFinding] = []
        try:
            import winreg

            locations = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "User"),
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "User"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Machine"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "Machine"),
            ]

            # Read approved map if accessible
            approved_map = {}
            for hkey, subkey in [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
            ]:
                try:
                    with winreg.OpenKey(hkey, subkey) as app_key:
                        num_vals = winreg.QueryInfoKey(app_key)[1]
                        for idx in range(num_vals):
                            name, val, _ = winreg.EnumValue(app_key, idx)
                            if isinstance(val, (bytes, bytearray)) and len(val) > 0:
                                approved_map[name] = (val[0] == 2)
                except OSError:
                    pass

            for root_hive, subkey, scope in locations:
                try:
                    with winreg.OpenKey(root_hive, subkey) as reg_key:
                        num_vals = winreg.QueryInfoKey(reg_key)[1]
                        for idx in range(num_vals):
                            name, val, _ = winreg.EnumValue(reg_key, idx)
                            cmd = str(val)
                            clean_path = cmd.strip(' "').split('"')[0] if cmd.startswith('"') else cmd.split(' ')[0]
                            is_enabled = approved_map.get(name, True)
                            startup_entries.append(
                                StartupFinding(
                                    name=name,
                                    command=cmd,
                                    resolved_path=clean_path,
                                    location_type="Registry",
                                    location_key=subkey,
                                    scope=scope,
                                    is_enabled=is_enabled,
                                )
                            )
                except OSError:
                    pass
        except ImportError:
            pass

        # 4. Initial Candidate Heuristics
        candidates: List[CandidateFinding] = []
        for s in startup_entries:
            if s.is_enabled and any(pattern in s.name.lower() or pattern in s.command.lower() for pattern in ["discord", "spotify", "steam", "opera", "assistant", "riot", "imo"]):
                candidates.append(
                    CandidateFinding(
                        category="StartupEntry",
                        target_name=s.name,
                        identifier=f"Registry:{s.name}",
                        risk_level="LOW",
                        confidence=0.90,
                        reason=f"Application '{s.name}' configured to launch automatically at sign-in.",
                        recommended_action="Disable startup entry in StartupApproved registry",
                        original_command=s.command,
                        requires_elevation=(s.scope == "Machine"),
                    )
                )

        duration = round(time.time() - start_time, 2)
        active_startups = sum(1 for s in startup_entries if s.is_enabled)

        report = DiagnosticReport(
            version="1.0.0-phase1-prototype",
            engine="WinOp-PythonFallback",
            timestamp=start_iso,
            scan_duration_sec=duration,
            is_elevated=False,
            execution_mode="READ_ONLY_STRICT",
            system=sys_info,
            processes_count=len(top_procs),
            startup_entries_count=len(startup_entries),
            active_startup_count=active_startups,
            scheduled_tasks_count=0,
            services_count=0,
            candidates=candidates,
            startup_entries=startup_entries,
            scheduled_tasks=[],
            top_processes=top_slice[:20],
            services_overview=[],
        )

        if output_json_path:
            Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                f.write(report.to_json())

        return report
