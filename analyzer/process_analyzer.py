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

        # Sort recommendations: LOW risk first, then CONDITIONAL; higher confidence first
        risk_order = {RuleRiskLevel.LOW: 0, RuleRiskLevel.CONDITIONAL: 1, RuleRiskLevel.PROTECTED: 2}
        recommendations.sort(key=lambda r: (risk_order.get(r.risk_level, 99), -r.confidence))

        return recommendations
