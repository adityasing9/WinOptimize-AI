"""
WinOptimize AI - System Scanner Module
Provides read-only system inspection, data parsing, and diagnostic reporting.
"""

from .models import (
    DiagnosticReport,
    SystemInfo,
    ProcessFinding,
    StartupFinding,
    ScheduledTaskFinding,
    ServiceFinding,
    CandidateFinding,
)
from .system_scanner import SystemScanner

__all__ = [
    "DiagnosticReport",
    "SystemInfo",
    "ProcessFinding",
    "StartupFinding",
    "ScheduledTaskFinding",
    "ServiceFinding",
    "CandidateFinding",
    "SystemScanner",
]
