"""
WinOptimize AI - Scanner Data Models
Strongly-typed data structures representing system inspection snapshots.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class SystemInfo:
    caption: str = ""
    version: str = ""
    build_number: str = ""
    architecture: str = ""
    total_physical_memory_mb: float = 0.0
    free_physical_memory_mb: float = 0.0
    used_physical_memory_mb: float = 0.0
    memory_usage_percent: float = 0.0
    cpu_load_percent: float = 0.0
    machine_name: str = ""
    current_user: str = ""
    is_elevated: bool = False
    source: str = ""


@dataclass
class ProcessFinding:
    pid: int
    name: str
    working_set_mb: float = 0.0
    private_memory_mb: float = 0.0
    cpu_total_seconds: float = 0.0
    has_window: bool = False
    window_title: str = ""
    executable_path: str = ""
    publisher: str = ""
    description: str = ""
    parent_pid: int = 0
    command_line: str = ""


@dataclass
class StartupFinding:
    name: str
    command: str = ""
    resolved_path: str = ""
    publisher: str = ""
    description: str = ""
    location_type: str = "Registry"  # 'Registry' or 'StartupFolder'
    location_key: str = ""
    scope: str = "User"  # 'User' or 'Machine'
    is_enabled: bool = True


@dataclass
class TaskAction:
    execute: str = ""
    arguments: str = ""


@dataclass
class TaskTrigger:
    type: str = ""
    enabled: bool = True
    id: str = ""


@dataclass
class ScheduledTaskFinding:
    task_name: str
    task_path: str = ""
    state: str = "Ready"  # 'Ready', 'Running', 'Disabled'
    author: str = ""
    description: str = ""
    actions: List[TaskAction] = field(default_factory=list)
    triggers: List[TaskTrigger] = field(default_factory=list)


@dataclass
class ServiceFinding:
    name: str
    display_name: str = ""
    status: str = "Stopped"  # 'Running', 'Stopped'
    start_mode: str = "Manual"  # 'Auto', 'Manual', 'Disabled'
    binary_path: str = ""
    account: str = ""
    is_microsoft: bool = False
    source: str = "CIM"


@dataclass
class CandidateFinding:
    category: str  # 'StartupEntry', 'BackgroundProcess', 'ScheduledTask', 'Service'
    target_name: str
    identifier: str
    risk_level: str  # 'LOW', 'CONDITIONAL', 'PROTECTED'
    confidence: float
    reason: str
    recommended_action: str
    original_command: str = ""
    requires_elevation: bool = False


@dataclass
class DiagnosticReport:
    version: str = "1.0.0-phase1-prototype"
    engine: str = "WinOp-PowerShell-Diagnostic"
    timestamp: str = ""
    scan_duration_sec: float = 0.0
    is_elevated: bool = False
    execution_mode: str = "READ_ONLY_STRICT"
    system: SystemInfo = field(default_factory=SystemInfo)
    processes_count: int = 0
    startup_entries_count: int = 0
    active_startup_count: int = 0
    scheduled_tasks_count: int = 0
    services_count: int = 0
    candidates: List[CandidateFinding] = field(default_factory=list)
    startup_entries: List[StartupFinding] = field(default_factory=list)
    scheduled_tasks: List[ScheduledTaskFinding] = field(default_factory=list)
    top_processes: List[ProcessFinding] = field(default_factory=list)
    services_overview: List[ServiceFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DiagnosticReport:
        meta = data.get("ReportMetadata", {})
        sys_data = data.get("SystemOverview", {})
        summary = data.get("SummaryCounts", {})

        system_info = SystemInfo(
            caption=sys_data.get("Caption", ""),
            version=str(sys_data.get("Version", "")),
            build_number=str(sys_data.get("BuildNumber", "")),
            architecture=sys_data.get("OSArchitecture", ""),
            total_physical_memory_mb=float(sys_data.get("TotalPhysicalMemoryMB", 0.0)),
            free_physical_memory_mb=float(sys_data.get("FreePhysicalMemoryMB", 0.0)),
            used_physical_memory_mb=float(sys_data.get("UsedPhysicalMemoryMB", 0.0)),
            memory_usage_percent=float(sys_data.get("MemoryUsagePercent", 0.0)),
            cpu_load_percent=float(sys_data.get("CpuLoadPercent", 0.0)),
            machine_name=sys_data.get("MachineName", ""),
            current_user=sys_data.get("CurrentUserName", ""),
            is_elevated=bool(sys_data.get("IsElevated", False)),
            source=sys_data.get("Source", ""),
        )

        candidates = []
        for c in data.get("OptimizationCandidates", []):
            candidates.append(
                CandidateFinding(
                    category=c.get("Category", ""),
                    target_name=c.get("TargetName", ""),
                    identifier=c.get("Identifier", ""),
                    risk_level=c.get("RiskLevel", "CONDITIONAL"),
                    confidence=float(c.get("Confidence", 0.0)),
                    reason=c.get("Reason", ""),
                    recommended_action=c.get("RecommendedAction", ""),
                    original_command=c.get("OriginalCommand", ""),
                    requires_elevation=bool(c.get("RequiresElevation", False)),
                )
            )

        startup_entries = []
        for s in data.get("StartupEntries", []):
            startup_entries.append(
                StartupFinding(
                    name=s.get("Name", ""),
                    command=s.get("Command", ""),
                    resolved_path=s.get("ResolvedPath", ""),
                    publisher=s.get("Publisher", ""),
                    description=s.get("Description", ""),
                    location_type=s.get("LocationType", "Registry"),
                    location_key=s.get("LocationKey", ""),
                    scope=s.get("Scope", "User"),
                    is_enabled=bool(s.get("IsEnabled", True)),
                )
            )

        tasks = []
        for t in data.get("ScheduledTasks", []):
            actions = [
                TaskAction(execute=a.get("Execute", ""), arguments=a.get("Arguments", ""))
                for a in t.get("Actions", [])
            ]
            triggers = [
                TaskTrigger(
                    type=tr.get("Type", ""),
                    enabled=bool(tr.get("Enabled", True)),
                    id=tr.get("Id", ""),
                )
                for tr in t.get("Triggers", [])
            ]
            tasks.append(
                ScheduledTaskFinding(
                    task_name=t.get("TaskName", ""),
                    task_path=t.get("TaskPath", ""),
                    state=t.get("State", "Ready"),
                    author=t.get("Author", ""),
                    description=t.get("Description", ""),
                    actions=actions,
                    triggers=triggers,
                )
            )

        top_processes = []
        for p in data.get("TopProcesses", []):
            top_processes.append(
                ProcessFinding(
                    pid=int(p.get("Id", 0)),
                    name=p.get("Name", ""),
                    working_set_mb=float(p.get("WorkingSetMB", 0.0)),
                    private_memory_mb=float(p.get("PrivateMemoryMB", 0.0)),
                    cpu_total_seconds=float(p.get("CpuTotalSeconds", 0.0)),
                    has_window=bool(p.get("HasWindow", False)),
                    window_title=p.get("WindowTitle", ""),
                    executable_path=p.get("ExecutablePath", ""),
                    publisher=p.get("Publisher", ""),
                    description=p.get("Description", ""),
                    parent_pid=int(p.get("ParentProcessId", 0)),
                    command_line=p.get("CommandLine", ""),
                )
            )

        services = []
        for svc in data.get("ServicesOverview", []):
            services.append(
                ServiceFinding(
                    name=svc.get("Name", ""),
                    display_name=svc.get("DisplayName", ""),
                    status=svc.get("Status", "Stopped"),
                    start_mode=svc.get("StartMode", "Manual"),
                    binary_path=svc.get("BinaryPath", ""),
                    account=svc.get("Account", ""),
                    is_microsoft=bool(svc.get("IsMicrosoft", False)),
                    source=svc.get("Source", "CIM"),
                )
            )

        return cls(
            version=meta.get("Version", "1.0.0-phase1-prototype"),
            engine=meta.get("Engine", "WinOp-PowerShell-Diagnostic"),
            timestamp=meta.get("ScanTimestamp", ""),
            scan_duration_sec=float(meta.get("ScanDurationSec", 0.0)),
            is_elevated=bool(meta.get("IsElevated", False)),
            execution_mode=meta.get("ExecutionMode", "READ_ONLY_STRICT"),
            system=system_info,
            processes_count=int(summary.get("ProcessesCount", len(top_processes))),
            startup_entries_count=int(summary.get("StartupEntriesCount", len(startup_entries))),
            active_startup_count=int(summary.get("ActiveStartupCount", 0)),
            scheduled_tasks_count=int(summary.get("ScheduledTasksCount", len(tasks))),
            services_count=int(summary.get("ServicesCount", len(services))),
            candidates=candidates,
            startup_entries=startup_entries,
            scheduled_tasks=tasks,
            top_processes=top_processes,
            services_overview=services,
        )

    def generate_markdown_summary(self) -> str:
        lines = [
            "# WinOptimize AI — Diagnostic Report",
            f"*Generated: {self.timestamp} | Mode: {self.execution_mode}*",
            "",
            "## 1. System Information",
            f"- **Operating System:** {self.system.caption} ({self.system.version} Build {self.system.build_number})",
            f"- **Architecture:** {self.system.architecture}",
            f"- **Physical Memory:** {self.system.used_physical_memory_mb:,.1f} MB used / {self.system.total_physical_memory_mb:,.1f} MB total ({self.system.memory_usage_percent:.1f}%)",
            f"- **CPU Utilization:** {self.system.cpu_load_percent:.1f}%",
            f"- **User Session:** `{self.system.current_user}` (Elevated: {self.system.is_elevated})",
            "",
            "## 2. Scan Summary Counts",
            f"| Metric | Inspected Count |",
            f"| :--- | :--- |",
            f"| Running Processes | {self.processes_count} |",
            f"| Startup Entries | {self.startup_entries_count} ({self.active_startup_count} active/enabled) |",
            f"| Non-Core Scheduled Tasks | {self.scheduled_tasks_count} |",
            f"| Services Evaluated | {self.services_count} |",
            f"| **Identified Optimization Candidates** | **{len(self.candidates)}** |",
            "",
            "## 3. Potential Optimization Candidates",
        ]

        if not self.candidates:
            lines.append("No immediate candidates flagged under default heuristics.")
        else:
            lines.append("| Category | Target | Risk | Confidence | Reason | Recommended Action |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for c in self.candidates:
                lines.append(
                    f"| `{c.category}` | **{c.target_name}** | `{c.risk_level}` | {int(c.confidence*100)}% | {c.reason} | {c.recommended_action} |"
                )

        lines.extend([
            "",
            "## 4. Active Startup Entries (Top Observations)",
            "| Name | Location / Scope | Publisher | Command | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for s in self.startup_entries:
            status = "Enabled" if s.is_enabled else "Disabled"
            pub = s.publisher if s.publisher else "Unknown"
            lines.append(f"| {s.name} | `{s.location_type} ({s.scope})` | {pub} | `{s.command[:60]}` | **{status}** |")

        lines.extend([
            "",
            "---",
            "*Safety Notice: This diagnostic report was generated in strict read-only mode. No registry values, tasks, services, or processes were modified.*",
        ])

        return "\n".join(lines)
