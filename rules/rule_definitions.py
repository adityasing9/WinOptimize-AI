"""
WinOptimize AI - Rule Definitions and Protected Whitelist
Defines rule schema, risk tiers, and local rule catalog.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class RuleRiskLevel(str, Enum):
    LOW = "LOW"
    CONDITIONAL = "CONDITIONAL"
    PROTECTED = "PROTECTED"


class RuleCategory(str, Enum):
    STARTUP = "StartupEntry"
    SCHEDULED_TASK = "ScheduledTask"
    SERVICE = "Service"
    BACKGROUND_PROCESS = "BackgroundProcess"


@dataclass
class RulePrecondition:
    check_type: str  # e.g., 'exists', 'is_enabled', 'not_dependency_of'
    target: str


@dataclass
class Rule:
    rule_id: str
    component_name: str
    category: RuleCategory
    risk_level: RuleRiskLevel
    confidence: float
    title: str
    description: str
    recommended_action: str
    side_effects: str
    reversibility_info: str
    name_patterns: List[str] = field(default_factory=list)
    publisher_patterns: List[str] = field(default_factory=list)
    executable_patterns: List[str] = field(default_factory=list)
    path_patterns: List[str] = field(default_factory=list)
    requires_elevation: bool = False
    preconditions: List[RulePrecondition] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Protected System Components (HARD-LOCKED: NEVER MODIFY OR DISABLE)
# -----------------------------------------------------------------------------
PROTECTED_SYSTEM_COMPONENTS = {
    "processes": {
        "explorer.exe", "dwm.exe", "svchost.exe", "csrss.exe", "lsass.exe",
        "services.exe", "wininit.exe", "smss.exe", "RuntimeBroker.exe",
        "ShellExperienceHost.exe", "MsMpEng.exe", "SecurityHealthHost.exe",
        "SecurityHealthSystray.exe", "SearchHost.exe", "StartMenuExperienceHost.exe",
        "smartscreen.exe", "ApplicationFrameHost.exe", "ctfmon.exe", "taskhostw.exe",
        "fontdrvhost.exe", "sihost.exe", "Memory Compression", "System"
    },
    "services": {
        "WinDefend", "SecurityHealthService", "MpsSvc", "Audiosrv", "AudioEndpointBuilder",
        "RpcSs", "RpcEptMapper", "DcomLaunch", "PlugPlay", "Dhcp", "Dnscache",
        "EventLog", "FontCache", "gpsvc", "LanmanWorkstation", "Netman",
        "nsi", "ProfSvc", "SamSs", "Schedule", "SENS", "Themes", "UserManager",
        "wscsvc", "W32Time", "WlanSvc", "KeyIso", "BFE", "CryptSvc"
    },
    "tasks": {
        r"\Microsoft\Windows\Windows Defender",
        r"\Microsoft\Windows\Chkdsk",
        r"\Microsoft\Windows\DiskDiagnostic",
        r"\Microsoft\Windows\Registry",
        r"\Microsoft\Windows\SystemRestore",
        r"\Microsoft\Windows\Time Synchronization",
        r"\Microsoft\Windows\UpdateOrchestrator",
        r"\Microsoft\Windows\WaaSMedic"
    }
}


# -----------------------------------------------------------------------------
# Built-in Rule Catalog
# -----------------------------------------------------------------------------
BUILTIN_RULES: List[Rule] = [
    # 1. Opera Browser Assistants
    Rule(
        rule_id="RULE-STARTUP-OPERA-ASSISTANT-001",
        component_name="Opera Browser Assistant",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Opera Browser Background Assistant",
        description="Background assistant utility that auto-starts with Windows to check promotions and updates.",
        recommended_action="Disable startup entry in StartupApproved registry",
        side_effects="Opera will not launch background assistant at startup. Browser functions normally when opened.",
        reversibility_info="Restore native StartupApproved flag to enabled (0x02).",
        name_patterns=[r"Opera.*Assistant", r"browser_assistant"],
        executable_patterns=[r"browser_assistant\.exe"],
        requires_elevation=False,
    ),
    Rule(
        rule_id="RULE-TASK-OPERA-UPDATE-002",
        component_name="Opera Scheduled Autoupdate",
        category=RuleCategory.SCHEDULED_TASK,
        risk_level=RuleRiskLevel.CONDITIONAL,
        confidence=0.90,
        title="Opera Autoupdate Scheduled Task",
        description="Recurring scheduled task triggering updater at user logon and daily intervals.",
        recommended_action="Disable scheduled task",
        side_effects="Automatic background updates will pause until the browser is manually opened.",
        reversibility_info="Re-enable task using Disable-ScheduledTask / Enable-ScheduledTask.",
        name_patterns=[r"Opera.*scheduled.*Autoupdate", r"Opera.*assistant.*Autoupdate"],
        requires_elevation=False,
    ),

    # 2. Discord
    Rule(
        rule_id="RULE-STARTUP-DISCORD-003",
        component_name="Discord",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Discord Auto-Launch at Sign-In",
        description="Discord starts minimized in the system tray upon user logon, consuming 150-300MB RAM.",
        recommended_action="Disable startup entry",
        side_effects="Discord will not launch automatically; launch manually when you wish to chat.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"^Discord$"],
        executable_patterns=[r"Discord\.exe", r"Update\.exe"],
        requires_elevation=False,
    ),

    # 3. Spotify
    Rule(
        rule_id="RULE-STARTUP-SPOTIFY-004",
        component_name="Spotify",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Spotify Music Startup",
        description="Spotify configured to launch minimized upon sign-in.",
        recommended_action="Disable startup entry",
        side_effects="Spotify will not open until launched manually.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"^Spotify$"],
        executable_patterns=[r"Spotify\.exe"],
        requires_elevation=False,
    ),

    # 4. Steam Gaming Launcher
    Rule(
        rule_id="RULE-STARTUP-STEAM-005",
        component_name="Steam",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Steam Client Bootstrapper",
        description="Steam client automatically launches in background at startup.",
        recommended_action="Disable startup entry",
        side_effects="Steam will not run in tray until you manually open it to play games.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"^Steam$", r"SteamClient"],
        executable_patterns=[r"steam\.exe"],
        requires_elevation=False,
    ),

    # 5. Epic Games Launcher
    Rule(
        rule_id="RULE-STARTUP-EPIC-006",
        component_name="Epic Games Launcher",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Epic Games Launcher Startup",
        description="Epic Games background launcher starts automatically at boot.",
        recommended_action="Disable startup entry",
        side_effects="Launcher opens on-demand when playing Epic games.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"EpicGamesLauncher", r"Epic Games"],
        executable_patterns=[r"EpicGamesLauncher\.exe"],
        requires_elevation=False,
    ),

    # 6. Riot Client
    Rule(
        rule_id="RULE-STARTUP-RIOT-007",
        component_name="Riot Client",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Riot Client Services",
        description="Riot Games client services loaded in background mode at sign-in.",
        recommended_action="Disable startup entry",
        side_effects="Riot games will start the client on-demand when launched.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"RiotClient", r"Riot Client Services"],
        executable_patterns=[r"RiotClientServices\.exe"],
        requires_elevation=False,
    ),

    # 7. Imo Messenger
    Rule(
        rule_id="RULE-STARTUP-IMO-008",
        component_name="Imo Messenger",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.95,
        title="Imo Messenger Auto-Launch",
        description="Messaging client configured to run minimized at startup.",
        recommended_action="Disable startup entry",
        side_effects="Incoming calls or messages will not ring until application is opened.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"Imo Messenger", r"ImoDesktopApp"],
        executable_patterns=[r"ImoDesktopApp\.exe"],
        requires_elevation=False,
    ),

    # 8. Docker Desktop
    Rule(
        rule_id="RULE-STARTUP-DOCKER-009",
        component_name="Docker Desktop",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.CONDITIONAL,
        confidence=0.90,
        title="Docker Desktop Background Virtualization",
        description="Docker Desktop starts WSL2/Hyper-V VM at startup, using 1-4GB+ RAM continuously.",
        recommended_action="Disable startup entry",
        side_effects="Docker containers will not run in the background until Docker Desktop is manually started.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"Docker Desktop"],
        executable_patterns=[r"Docker Desktop\.exe"],
        requires_elevation=False,
    ),

    # 9. Zoom Updaters
    Rule(
        rule_id="RULE-TASK-ZOOM-010",
        component_name="Zoom Auto Update Task",
        category=RuleCategory.SCHEDULED_TASK,
        risk_level=RuleRiskLevel.CONDITIONAL,
        confidence=0.90,
        title="Zoom Scheduled Update Task",
        description="Periodic scheduled task checking for Zoom meeting client updates in background.",
        recommended_action="Disable scheduled task",
        side_effects="Zoom will check for updates when opened or in-meeting.",
        reversibility_info="Re-enable scheduled task.",
        name_patterns=[r"ZoomUpdateTask"],
        requires_elevation=False,
    ),

    # 10. Microsoft Edge AutoLaunch
    Rule(
        rule_id="RULE-STARTUP-EDGE-011",
        component_name="Microsoft Edge AutoLaunch",
        category=RuleCategory.STARTUP,
        risk_level=RuleRiskLevel.LOW,
        confidence=0.90,
        title="Edge Background Startup Preloader",
        description="Edge browser preloader configured to run with --no-startup-window at logon.",
        recommended_action="Disable startup entry",
        side_effects="Edge browser will start normally when clicked by user.",
        reversibility_info="Restore StartupApproved flag.",
        name_patterns=[r"MicrosoftEdgeAutoLaunch"],
        executable_patterns=[r"msedge\.exe"],
        requires_elevation=False,
    ),
]
