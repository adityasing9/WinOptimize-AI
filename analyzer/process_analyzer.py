"""
WinOptimize AI - Process Analysis and Correlation Engine
Analyzes system findings, maps running processes to launch origins,
evaluates rules, and generates actionable recommendations.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from scanner.models import DiagnosticReport, StartupFinding, ScheduledTaskFinding, ServiceFinding, ProcessFinding
from rules.rule_definitions import RuleRiskLevel, RuleCategory
from rules.rules_engine import RulesEngine, RuleEvaluationResult
from storage.database import DatabaseManager


@dataclass
class OptimizationRecommendation:
    recommendation_id: str
    category: str  # 'StartupEntry', 'ScheduledTask', 'Service', 'BackgroundProcess'
    component_name: str
    target_identifier: str
    risk_level: RuleRiskLevel
    confidence: float
    title: str
    description: str
    recommended_action: str
    side_effects: str
    reversibility_info: str
    requires_elevation: bool
    current_state: Dict[str, Any] = field(default_factory=dict)
    proposed_state: Dict[str, Any] = field(default_factory=dict)
    is_protected: bool = False
    is_approved: bool = False
    user_preference: Optional[str] = None
    correlated_pids: List[int] = field(default_factory=list)
    observed_ram_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


class ProcessAnalyzer:
    """
    Orchestrates deep analysis and correlation across processes, startup items,
    scheduled tasks, and services.
    """

    def __init__(self, rules_engine: Optional[RulesEngine] = None, db_manager: Optional[DatabaseManager] = None):
        self.rules_engine = rules_engine if rules_engine is not None else RulesEngine()
        self.db = db_manager if db_manager is not None else DatabaseManager()

    def analyze(self, report: DiagnosticReport) -> List[OptimizationRecommendation]:
        """
        Analyzes a complete DiagnosticReport and generates prioritized recommendations.
        """
        recommendations: List[OptimizationRecommendation] = []
        user_prefs = self.db.get_all_preferences()

        # Build lookup table of running processes by executable name & path
        proc_lookup: Dict[str, List[ProcessFinding]] = {}
        for proc in report.top_processes:
            p_name = proc.name.lower().replace(".exe", "")
            proc_lookup.setdefault(p_name, []).append(proc)
            if proc.executable_path:
                proc_lookup.setdefault(proc.executable_path.lower(), []).append(proc)

        # 1. Analyze Startup Entries
        for entry in report.startup_entries:
            # Skip if already disabled
            if not entry.is_enabled:
                continue

            target_id = f"Startup:{entry.name}"
            pref = user_prefs.get(target_id)
            if pref == "keep_enabled" or pref == "ignore":
                continue

            eval_res: RuleEvaluationResult = self.rules_engine.evaluate_startup_entry(
                name=entry.name,
                command=entry.command,
                resolved_path=entry.resolved_path,
                publisher=entry.publisher,
            )

            # Never recommend disabling protected items
            if eval_res.is_protected:
                continue

            # Only recommend if confidence >= 0.70 or known matched rule
            if not eval_res.is_matched and eval_res.confidence < 0.70:
                continue

            # Correlate running processes
            correlated = []
            ram_mb = 0.0
            entry_base = entry.name.lower()
            if entry_base in proc_lookup:
                for p in proc_lookup[entry_base]:
                    correlated.append(p.pid)
                    ram_mb += p.working_set_mb

            rec_id = f"REC-STARTUP-{uuid.uuid4().hex[:8].upper()}"
            rec = OptimizationRecommendation(
                recommendation_id=rec_id,
                category=RuleCategory.STARTUP.value,
                component_name=entry.name,
                target_identifier=target_id,
                risk_level=eval_res.risk_level,
                confidence=eval_res.confidence,
                title=f"Disable Startup Entry: {entry.name}",
                description=eval_res.explanation,
                recommended_action=eval_res.recommended_action,
                side_effects=eval_res.side_effects,
                reversibility_info=eval_res.reversibility_info,
                requires_elevation=eval_res.requires_elevation or (entry.scope.lower() == "machine"),
                current_state={
                    "is_enabled": True,
                    "location_type": entry.location_type,
                    "location_key": entry.location_key,
                    "name": entry.name,
                    "command": entry.command,
                    "scope": entry.scope,
                },
                proposed_state={
                    "is_enabled": False,
                    "location_type": entry.location_type,
                    "location_key": entry.location_key,
                    "name": entry.name,
                },
                is_protected=False,
                is_approved=False,
                user_preference=pref,
                correlated_pids=correlated,
                observed_ram_mb=round(ram_mb, 1),
            )
            recommendations.append(rec)

        # 2. Analyze Scheduled Tasks
        for task in report.scheduled_tasks:
            if task.state == "Disabled":
                continue

            target_id = f"Task:{task.task_path.rstrip('/')}/{task.task_name}"
            pref = user_prefs.get(target_id)
            if pref == "keep_enabled" or pref == "ignore":
                continue

            actions_str = "; ".join(f"{a.execute} {a.arguments}" for a in task.actions)
            eval_res = self.rules_engine.evaluate_scheduled_task(
                task_name=task.task_name,
                task_path=task.task_path,
                actions_cmd=actions_str,
            )

            if eval_res.is_protected or not eval_res.is_matched:
                continue

            rec_id = f"REC-TASK-{uuid.uuid4().hex[:8].upper()}"
            rec = OptimizationRecommendation(
                recommendation_id=rec_id,
                category=RuleCategory.SCHEDULED_TASK.value,
                component_name=task.task_name,
                target_identifier=target_id,
                risk_level=eval_res.risk_level,
                confidence=eval_res.confidence,
                title=f"Disable Scheduled Task: {task.task_name}",
                description=eval_res.explanation,
                recommended_action=eval_res.recommended_action,
                side_effects=eval_res.side_effects,
                reversibility_info=eval_res.reversibility_info,
                requires_elevation=True,
                current_state={
                    "task_name": task.task_name,
                    "task_path": task.task_path,
                    "state": task.state,
                },
                proposed_state={
                    "task_name": task.task_name,
                    "task_path": task.task_path,
                    "state": "Disabled",
                },
                is_protected=False,
                is_approved=False,
                user_preference=pref,
            )
            recommendations.append(rec)

        # 3. Analyze Running Background Processes & Memory Hogs
        grouped_procs: Dict[str, List[ProcessFinding]] = {}
        for p in report.top_processes:
            clean_name = p.name.lower().replace(".exe", "")
            grouped_procs.setdefault(clean_name, []).append(p)

        # Developer / Active Tool whitelist so we never disrupt user's workspace
        active_tools_whitelist = {"antigravity", "language_server", "winoptimizeai", "taskmgr", "windowsterminal"}

        for p_name, proc_list in grouped_procs.items():
            first_proc = proc_list[0]
            total_ram = sum(p.working_set_mb for p in proc_list)
            pids = [p.pid for p in proc_list]
            exe_path = first_proc.executable_path or ""

            # Skip core Windows, protected processes, and active IDE tools
            if p_name in active_tools_whitelist or self.rules_engine.is_protected_process(p_name, exe_path):
                continue

            target_id = f"Process:{p_name}"
            pref = user_prefs.get(target_id)
            if pref == "keep_enabled" or pref == "ignore":
                continue

            eval_res = self.rules_engine.evaluate_process(
                process_name=p_name,
                executable_path=exe_path,
                ram_mb=total_ram,
                count=len(proc_list),
            )

            # Recommend if matched rule or high RAM consumption (>= 180 MB)
            if eval_res.is_matched or total_ram >= 180.0:
                rec_id = f"REC-PROC-{uuid.uuid4().hex[:8].upper()}"
                title_str = eval_res.rule.title if eval_res.rule else f"High Memory Usage: {first_proc.name}"
                rec = OptimizationRecommendation(
                    recommendation_id=rec_id,
                    category=RuleCategory.BACKGROUND_PROCESS.value,
                    component_name=f"{first_proc.name} ({len(proc_list)}x)",
                    target_identifier=target_id,
                    risk_level=eval_res.risk_level,
                    confidence=eval_res.confidence,
                    title=title_str,
                    description=eval_res.explanation,
                    recommended_action=eval_res.recommended_action,
                    side_effects=eval_res.side_effects,
                    reversibility_info=eval_res.reversibility_info,
                    requires_elevation=eval_res.requires_elevation,
                    current_state={
                        "process_name": first_proc.name,
                        "pids": pids,
                        "count": len(proc_list),
                        "total_ram_mb": round(total_ram, 1),
                    },
                    proposed_state={
                        "process_name": first_proc.name,
                        "action": "trim_or_close",
                        "pids": pids,
                    },
                    is_protected=False,
                    is_approved=False,
                    user_preference=pref,
                    correlated_pids=pids,
                    observed_ram_mb=round(total_ram, 1),
                )
                recommendations.append(rec)

        # 4. Analyze Background Services (Gaming Services, VPNs, DBs, OEM telemetry, etc.)
        for svc in report.services_overview:
            is_manual_or_disabled = svc.start_mode.lower() in ("manual", "disabled")
            is_running = (svc.status.lower() == "running")

            # If service is already manual/disabled AND not currently running, it's already optimized
            if is_manual_or_disabled and not is_running:
                continue

            target_id = f"Service:{svc.name}"
            pref = user_prefs.get(target_id)
            if pref == "keep_enabled" or pref == "ignore":
                continue

            eval_res = self.rules_engine.evaluate_service(
                service_name=svc.name,
                display_name=svc.display_name,
                image_path=svc.binary_path,
            )

            # Never modify protected core system services
            if eval_res.is_protected:
                continue

            if eval_res.is_matched:
                if is_running and is_manual_or_disabled:
                    title_str = f"Stop Running Service: {svc.display_name or svc.name}"
                    desc_str = f"{eval_res.explanation} (Currently active in memory; startup is already {svc.start_mode})."
                    action_str = "Stop running background service"
                else:
                    title_str = eval_res.rule.title if eval_res.rule else f"Optional Service: {svc.display_name}"
                    desc_str = eval_res.explanation
                    action_str = eval_res.recommended_action
                risk_lvl = eval_res.risk_level
                conf_val = eval_res.confidence
                side_fx = eval_res.side_effects
                rev_info = eval_res.reversibility_info
            elif not svc.is_microsoft and is_running:
                # Running third-party non-core service
                if is_manual_or_disabled:
                    title_str = f"Stop Running Third-Party Service: {svc.display_name or svc.name}"
                    desc_str = f"Third-party background service '{svc.display_name or svc.name}' is actively running in memory."
                    action_str = "Stop running background service"
                else:
                    title_str = f"Optional Third-Party Service: {svc.display_name or svc.name}"
                    desc_str = f"Third-party background service '{svc.display_name or svc.name}' is running automatically at system boot."
                    action_str = "Set service startup type to Manual & Stop"
                risk_lvl = RuleRiskLevel.CONDITIONAL
                conf_val = 0.80
                side_fx = "Service will start on-demand when the host application is launched."
                rev_info = "Can be restored to Automatic via Services (services.msc) or WinOptimize."
            else:
                continue

            rec_id = f"REC-SVC-{uuid.uuid4().hex[:8].upper()}"
            rec = OptimizationRecommendation(
                recommendation_id=rec_id,
                category=RuleCategory.SERVICE.value,
                component_name=svc.display_name or svc.name,
                target_identifier=target_id,
                risk_level=risk_lvl,
                confidence=conf_val,
                title=title_str,
                description=desc_str,
                recommended_action=action_str,
                side_effects=side_fx,
                reversibility_info=rev_info,
                requires_elevation=True,
                current_state={
                    "service_name": svc.name,
                    "start_mode": svc.start_mode,
                    "status": svc.status,
                },
                proposed_state={
                    "service_name": svc.name,
                    "target_mode": "Manual" if not is_manual_or_disabled else svc.start_mode,
                    "action": "stop",
                },
                is_protected=False,
                is_approved=False,
                user_preference=pref,
            )
            recommendations.append(rec)

        # Sort recommendations: LOW risk first, then CONDITIONAL; higher confidence first
        risk_order = {RuleRiskLevel.LOW: 0, RuleRiskLevel.CONDITIONAL: 1, RuleRiskLevel.PROTECTED: 2}
        recommendations.sort(key=lambda r: (risk_order.get(r.risk_level, 99), -r.confidence, -r.observed_ram_mb))

        return recommendations
