"""
WinOptimize AI - Rules Engine Evaluator
Evaluates components against catalog rules and protected policies.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .rule_definitions import (
    Rule,
    RuleRiskLevel,
    RuleCategory,
    BUILTIN_RULES,
    PROTECTED_SYSTEM_COMPONENTS,
)


@dataclass
class RuleEvaluationResult:
    is_matched: bool
    risk_level: RuleRiskLevel
    confidence: float
    rule: Optional[Rule]
    explanation: str
    recommended_action: str
    side_effects: str
    reversibility_info: str
    requires_elevation: bool
    is_protected: bool = False


class RulesEngine:
    """
    Evaluator that matches inspected system components against known rules,
    enforces protected system policies, and scores confidence.
    """

    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules: List[Rule] = rules if rules is not None else list(BUILTIN_RULES)

    def is_protected_process(self, process_name: str, executable_path: str = "") -> bool:
        """Checks if process belongs to protected Windows system components."""
        p_name = process_name.lower().strip()
        p_name_exe = f"{p_name}.exe" if not p_name.endswith(".exe") else p_name

        for prot in PROTECTED_SYSTEM_COMPONENTS["processes"]:
            if p_name == prot.lower() or p_name_exe == prot.lower():
                return True

        if executable_path:
            norm_path = executable_path.lower().strip(' "\'')
            exe_file = Path(norm_path).name.lower()
            for prot in PROTECTED_SYSTEM_COMPONENTS["processes"]:
                if exe_file == prot.lower() or exe_file.replace(".exe", "") == prot.lower().replace(".exe", ""):
                    return True

            if "\\windows\\system32\\" in norm_path or "\\windows\\syswow64\\" in norm_path:
                if any(k in norm_path for k in ["svchost.exe", "lsass.exe", "csrss.exe", "services.exe", "winlogon.exe", "securityhealth"]):
                    return True

        return False

    def is_protected_service(self, service_name: str) -> bool:
        """Checks if service is essential to Windows operation."""
        s_name = service_name.lower().strip()
        for prot in PROTECTED_SYSTEM_COMPONENTS["services"]:
            if s_name == prot.lower():
                return True
        return False

    def is_protected_task(self, task_path: str, task_name: str) -> bool:
        """Checks if scheduled task is a protected Windows core task."""
        full_path = f"{task_path.rstrip('/')}/{task_name.lstrip('/')}".lower()
        for prot in PROTECTED_SYSTEM_COMPONENTS["tasks"]:
            if prot.lower() in full_path:
                return True
        return False

    def evaluate_startup_entry(
        self,
        name: str,
        command: str = "",
        resolved_path: str = "",
        publisher: str = "",
    ) -> RuleEvaluationResult:
        """Evaluates a startup entry against catalog rules and protected components."""
        target_path = resolved_path if resolved_path else command
        # 1. Check protection
        if self.is_protected_process(name, target_path):
            return RuleEvaluationResult(
                is_matched=True,
                risk_level=RuleRiskLevel.PROTECTED,
                confidence=1.0,
                rule=None,
                explanation="Essential Windows system component; strictly protected from modification.",
                recommended_action="Do not modify (Protected Component)",
                side_effects="Disabling would cause system instability or prevent Windows from starting.",
                reversibility_info="N/A",
                requires_elevation=True,
                is_protected=True,
            )

        # 2. Check rule catalog
        for rule in self.rules:
            if rule.category != RuleCategory.STARTUP:
                continue

            matched = False
            # Match by name pattern
            for pat in rule.name_patterns:
                if re.search(pat, name, re.IGNORECASE):
                    matched = True
                    break

            # Match by executable pattern
            if not matched and rule.executable_patterns and (resolved_path or command):
                target_str = resolved_path or command
                for pat in rule.executable_patterns:
                    if re.search(pat, target_str, re.IGNORECASE):
                        matched = True
                        break

            if matched:
                return RuleEvaluationResult(
                    is_matched=True,
                    risk_level=rule.risk_level,
                    confidence=rule.confidence,
                    rule=rule,
                    explanation=rule.description,
                    recommended_action=rule.recommended_action,
                    side_effects=rule.side_effects,
                    reversibility_info=rule.reversibility_info,
                    requires_elevation=rule.requires_elevation,
                    is_protected=False,
                )

        # 3. Unclassified item (Safety policy: Never automatically modify unknown components)
        return RuleEvaluationResult(
            is_matched=False,
            risk_level=RuleRiskLevel.CONDITIONAL,
            confidence=0.50,
            rule=None,
            explanation=f"Unclassified startup component '{name}'. Manual review recommended.",
            recommended_action="Review application before making changes",
            side_effects="Depends on user usage of this specific software.",
            reversibility_info="Can be restored via Windows Task Manager or WinOptimize restore.",
            requires_elevation=False,
            is_protected=False,
        )

    def evaluate_scheduled_task(
        self,
        task_name: str,
        task_path: str = "\\",
        actions_cmd: str = "",
    ) -> RuleEvaluationResult:
        """Evaluates a scheduled task against rules and protection policies."""
        if self.is_protected_task(task_path, task_name):
            return RuleEvaluationResult(
                is_matched=True,
                risk_level=RuleRiskLevel.PROTECTED,
                confidence=1.0,
                rule=None,
                explanation="Protected core Windows scheduled task.",
                recommended_action="Do not modify (Protected Component)",
                side_effects="Disabling could impair Windows maintenance or security.",
                reversibility_info="N/A",
                requires_elevation=True,
                is_protected=True,
            )

        for rule in self.rules:
            if rule.category != RuleCategory.SCHEDULED_TASK:
                continue

            matched = False
            for pat in rule.name_patterns:
                if re.search(pat, task_name, re.IGNORECASE):
                    matched = True
                    break

            if not matched and rule.executable_patterns and actions_cmd:
                for pat in rule.executable_patterns:
                    if re.search(pat, actions_cmd, re.IGNORECASE):
                        matched = True
                        break

            if matched:
                return RuleEvaluationResult(
                    is_matched=True,
                    risk_level=rule.risk_level,
                    confidence=rule.confidence,
                    rule=rule,
                    explanation=rule.description,
                    recommended_action=rule.recommended_action,
                    side_effects=rule.side_effects,
                    reversibility_info=rule.reversibility_info,
                    requires_elevation=rule.requires_elevation,
                    is_protected=False,
                )

        return RuleEvaluationResult(
            is_matched=False,
            risk_level=RuleRiskLevel.CONDITIONAL,
            confidence=0.50,
            rule=None,
            explanation=f"Unclassified scheduled task '{task_name}'.",
            recommended_action="Review task purpose before disabling",
            side_effects="Unknown without inspecting application dependencies.",
            reversibility_info="Can be re-enabled via Task Scheduler.",
            requires_elevation=True,
            is_protected=False,
        )

    def evaluate_service(self, service_name: str, display_name: str = "", image_path: str = "") -> RuleEvaluationResult:
        """Evaluates a Windows service against rules and protected policies."""
        if self.is_protected_service(service_name):
            return RuleEvaluationResult(
                is_matched=True,
                risk_level=RuleRiskLevel.PROTECTED,
                confidence=1.0,
                rule=None,
                explanation="Essential Windows operating system service.",
                recommended_action="Do not modify (Protected Service)",
                side_effects="Disabling will destabilize Windows or networking/audio subsystems.",
                reversibility_info="N/A",
                requires_elevation=True,
                is_protected=True,
            )

        for rule in self.rules:
            if rule.category != RuleCategory.SERVICE:
                continue

            matched = any(re.search(pat, service_name, re.IGNORECASE) for pat in rule.name_patterns)
            if not matched and display_name:
                matched = any(re.search(pat, display_name, re.IGNORECASE) for pat in rule.name_patterns)

            if matched:
                return RuleEvaluationResult(
                    is_matched=True,
                    risk_level=rule.risk_level,
                    confidence=rule.confidence,
                    rule=rule,
                    explanation=rule.description,
                    recommended_action=rule.recommended_action,
                    side_effects=rule.side_effects,
                    reversibility_info=rule.reversibility_info,
                    requires_elevation=rule.requires_elevation,
                    is_protected=False,
                )

        return RuleEvaluationResult(
            is_matched=False,
            risk_level=RuleRiskLevel.CONDITIONAL,
            confidence=0.50,
            rule=None,
            explanation=f"Unclassified service '{service_name}' ({display_name}).",
            recommended_action="Keep enabled unless verified as unused software",
            side_effects="May disable software dependent on this background service.",
            reversibility_info="Can be restored via Services manager.",
            requires_elevation=True,
            is_protected=False,
        )

    def evaluate_process(
        self,
        process_name: str,
        executable_path: str = "",
        ram_mb: float = 0.0,
        count: int = 1,
    ) -> RuleEvaluationResult:
        """Evaluates a running background process against rules and protected policies."""
        p_name = process_name.lower().replace(".exe", "").strip()
        exe_path = executable_path or ""

        # 1. Protected Check
        if self.is_protected_process(p_name, exe_path):
            return RuleEvaluationResult(
                is_matched=True,
                risk_level=RuleRiskLevel.PROTECTED,
                confidence=1.0,
                rule=None,
                explanation="Essential Windows system process; protected from termination.",
                recommended_action="Do not modify (Protected Process)",
                side_effects="Terminating will cause system crash or loss of desktop session.",
                reversibility_info="N/A",
                requires_elevation=True,
                is_protected=True,
            )

        # 2. Match catalog rules
        for rule in self.rules:
            if rule.category != RuleCategory.BACKGROUND_PROCESS:
                continue

            matched = any(re.search(pat, p_name, re.IGNORECASE) for pat in rule.name_patterns)
            if not matched and exe_path:
                matched = any(re.search(pat, exe_path, re.IGNORECASE) for pat in rule.executable_patterns)

            if matched:
                detail = f"Consuming {ram_mb:.1f} MB across {count} process(es)." if count > 1 else f"Consuming {ram_mb:.1f} MB."
                explanation = f"{rule.description} ({detail})"
                return RuleEvaluationResult(
                    is_matched=True,
                    risk_level=rule.risk_level,
                    confidence=rule.confidence,
                    rule=rule,
                    explanation=explanation,
                    recommended_action=rule.recommended_action,
                    side_effects=rule.side_effects,
                    reversibility_info=rule.reversibility_info,
                    requires_elevation=rule.requires_elevation,
                    is_protected=False,
                )

        # 3. Unclassified background process
        return RuleEvaluationResult(
            is_matched=False,
            risk_level=RuleRiskLevel.CONDITIONAL,
            confidence=0.60,
            rule=None,
            explanation=f"Background application '{process_name}' consuming {ram_mb:.1f} MB across {count} instance(s).",
            recommended_action="Review application memory usage or close if idle",
            side_effects="Application will close. Save any unsaved progress first.",
            reversibility_info="Can be reopened at any time.",
            requires_elevation=False,
            is_protected=False,
        )
