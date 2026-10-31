"""
WinOptimize AI - Rules Engine Module
"""

from .rule_definitions import (
    Rule,
    RuleRiskLevel,
    RuleCategory,
    RulePrecondition,
    BUILTIN_RULES,
    PROTECTED_SYSTEM_COMPONENTS,
)
from .rules_engine import RulesEngine

__all__ = [
    "Rule",
    "RuleRiskLevel",
    "RuleCategory",
    "RulePrecondition",
    "BUILTIN_RULES",
    "PROTECTED_SYSTEM_COMPONENTS",
    "RulesEngine",
]
