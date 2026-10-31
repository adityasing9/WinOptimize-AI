"""
WinOptimize AI - Relaunch Diagnostic Engine
Controlled, user-initiated diagnostic sessions that observe recurring process launches,
trace parent PIDs, and identify the root launcher mechanism (Task, Service, Watchdog).
Never continuous by default; strictly bounded diagnostic runs.
"""

from __future__ import annotations
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

import psutil

from scanner.system_scanner import SystemScanner
from scanner.models import DiagnosticReport

logger = logging.getLogger("WinOp.Monitoring")


@dataclass
class RelaunchEvent:
    timestamp: str
    target_process_name: str
    original_pid: int
    new_pid: int
    parent_pid: int
    parent_name: str
    parent_cmdline: str
    likely_cause: str  # 'ScheduledTask', 'WindowsService', 'ParentLauncher', 'Watchdog', 'Unknown'
    confidence: float
    evidence: List[str] = field(default_factory=list)
    recommended_fix: str = ""


@dataclass
class RelaunchReport:
    session_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    monitored_targets: List[str]
    events_detected: List[RelaunchEvent] = field(default_factory=list)
    summary: str = ""


class RelaunchDiagnosticSession:
    """
    Time-bounded diagnostic session to detect applications relaunching after closure.
    """

    def __init__(self, target_names: Optional[List[str]] = None, duration_seconds: int = 15):
        self.target_names = [t.lower().replace(".exe", "") for t in target_names] if target_names else []
        self.duration_seconds = max(5, min(duration_seconds, 120))  # Between 5s and 120s
        self.scanner = SystemScanner()

    def run_session(self) -> RelaunchReport:
        """
        Runs the observation loop for duration_seconds.
        """
        start_dt = datetime.now(timezone.utc)
        start_iso = start_dt.isoformat()
        session_id = f"RELAUNCH-{int(time.time())}"

        # 1. Take initial process snapshot
        initial_pids: Dict[int, str] = {}
        target_pids: Dict[int, str] = {}

        for p in psutil.process_iter(['pid', 'name']):
            try:
                pid = p.info['pid']
                name = p.info['name'].lower()
                clean_name = name.replace(".exe", "")
                initial_pids[pid] = clean_name
                if not self.target_names or clean_name in self.target_names:
                    target_pids[pid] = clean_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        logger.info("Starting relaunch diagnostic session (%ds), tracking targets: %s",
                    self.duration_seconds, self.target_names or "ALL")

        # 2. Run diagnostic inspection to cross-reference tasks & services
        system_report: Optional[DiagnosticReport] = None
        try:
            system_report = self.scanner.scan(use_powershell=True)
        except Exception as e:
            logger.warning("Could not gather system report for relaunch cross-ref: %s", e)

        events: List[RelaunchEvent] = []
        closed_pids: Set[int] = set()
        seen_relaunch_pids: Set[int] = set()

        end_time = time.time() + self.duration_seconds
        while time.time() < end_time:
            time.sleep(1.0)

            # Check if tracked processes closed
            for pid, name in list(target_pids.items()):
                if pid not in closed_pids:
                    if not psutil.pid_exists(pid):
                        closed_pids.add(pid)
                        logger.info("Observed process exit: %s (PID %d)", name, pid)

            # Check for new processes created with the same target name
            for p in psutil.process_iter(['pid', 'name', 'ppid']):
                try:
                    p_info = p.info
                    p_pid = p_info['pid']
                    p_name = p_info['name'].lower().replace(".exe", "")

                    if p_pid not in initial_pids and p_pid not in seen_relaunch_pids:
                        # Process was launched during observation window
                        if not self.target_names or p_name in self.target_names:
                            # It is a monitored target that re-emerged!
                            seen_relaunch_pids.add(p_pid)
                            parent_pid = p_info.get('ppid', 0)
                            parent_name = "Unknown"
                            parent_cmd = ""

                            if parent_pid and psutil.pid_exists(parent_pid):
                                try:
                                    parent_proc = psutil.Process(parent_pid)
                                    parent_name = parent_proc.name()
                                    parent_cmd = " ".join(parent_proc.cmdline())
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass

                            # Cross-reference root cause
                            cause, confidence, evidence, fix = self._determine_launch_cause(
                                p_name, parent_name, parent_cmd, system_report
                            )

                            orig_pid = next((op for op, on in target_pids.items() if on == p_name), 0)
                            event = RelaunchEvent(
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                target_process_name=p_name,
                                original_pid=orig_pid,
                                new_pid=p_pid,
                                parent_pid=parent_pid,
                                parent_name=parent_name,
                                parent_cmdline=parent_cmd,
                                likely_cause=cause,
                                confidence=confidence,
                                evidence=evidence,
                                recommended_fix=fix,
                            )
                            events.append(event)
                            logger.info("Detected relaunch: %s (New PID %d, Parent %s)", p_name, p_pid, parent_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        end_iso = datetime.now(timezone.utc).isoformat()
        duration = round(time.time() - (end_time - self.duration_seconds), 1)

        summary = f"Diagnostic session completed in {duration}s. {len(events)} recurring launches detected."
        return RelaunchReport(
            session_id=session_id,
            start_time=start_iso,
            end_time=end_iso,
            duration_seconds=duration,
            monitored_targets=self.target_names,
            events_detected=events,
            summary=summary,
        )

    def _determine_launch_cause(
        self,
        process_name: str,
        parent_name: str,
        parent_cmd: str,
        system_report: Optional[DiagnosticReport],
    ) -> Tuple[str, float, List[str], str]:
        """Cross-references process information against system tasks, services, and startup entries."""
        evidence = [
            f"Process '{process_name}' spawned with Parent PID originating from '{parent_name}'."
        ]

        # 1. Check if parent is svchost / Task Scheduler or Service
        p_lower = parent_name.lower()
        if "svchost" in p_lower:
            evidence.append("Parent process is Windows Service Host (svchost.exe), indicating task or service origin.")

        # 2. Check Scheduled Tasks in report
        if system_report:
            for task in system_report.scheduled_tasks:
                if re.search(process_name, task.task_name, re.IGNORECASE):
                    evidence.append(f"Matching scheduled task found: '{task.task_name}' in '{task.task_path}' (State: {task.state}).")
                    return (
                        "ScheduledTask",
                        0.90,
                        evidence,
                        f"Disable scheduled task '{task.task_name}' in Task Scheduler."
                    )
                for act in task.actions:
                    if re.search(process_name, act.execute, re.IGNORECASE):
                        evidence.append(f"Scheduled task action explicitly triggers this binary: '{act.execute}'.")
                        return (
                            "ScheduledTask",
                            0.95,
                            evidence,
                            f"Disable scheduled task '{task.task_name}'."
                        )

            # 3. Check Windows Services
            for svc in system_report.services_overview:
                if re.search(process_name, svc.name, re.IGNORECASE) or re.search(process_name, svc.binary_path, re.IGNORECASE):
                    evidence.append(f"Matching Windows Service identified: '{svc.display_name}' ({svc.name}).")
                    return (
                        "WindowsService",
                        0.85,
                        evidence,
                        f"Reconfigure service '{svc.name}' startup type to Manual."
                    )

            # 4. Check Startup Entries
            for startup in system_report.startup_entries:
                if re.search(process_name, startup.name, re.IGNORECASE) or re.search(process_name, startup.command, re.IGNORECASE):
                    evidence.append(f"Matching startup entry present in {startup.location_type} ({startup.scope}).")
                    return (
                        "StartupEntry",
                        0.80,
                        evidence,
                        f"Disable startup entry '{startup.name}'."
                    )

        # 5. Launcher watchdog fallback
        if parent_name and parent_name.lower() != "unknown" and "explorer" not in parent_name.lower():
            evidence.append(f"Application launcher or watchdog '{parent_name}' re-spawned process.")
            return (
                "ParentLauncher",
                0.75,
                evidence,
                f"Close the parent management software '{parent_name}'."
            )

        return (
            "Unknown",
            0.50,
            evidence,
            "Inspect process creation events in Windows Security Event Log (Event ID 4688)."
        )
