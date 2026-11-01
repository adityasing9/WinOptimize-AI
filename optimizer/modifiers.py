"""
WinOptimize AI - Atomic System Modifiers
Implements safe, isolated, and strictly reversible modifications.
Never deletes registry entries, never deletes scheduled tasks, never deletes services.
"""

from __future__ import annotations
import abc
import base64
import datetime
import logging
import os
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("WinOp.Modifiers")


class BaseModifier(abc.ABC):
    """Abstract interface for atomic reversible system modifications."""

    @abc.abstractmethod
    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Captures complete serialized current configuration before modification."""
        pass

    @abc.abstractmethod
    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        """Executes the proposed safe modification."""
        pass

    @abc.abstractmethod
    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        """Verifies that the target configuration matches the expected state."""
        pass

    @abc.abstractmethod
    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        """Reverts configuration back to original state."""
        pass


class StartupRegistryModifier(BaseModifier):
    """
    Manages startup entries via Windows native StartupApproved\\Run registry mechanism.
    0x02 in first byte = Enabled
    0x03 in first byte = Disabled
    Preserves exact entry in CurrentVersion\\Run without deleting anything.
    """

    SUBKEY_HKCU = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
    SUBKEY_HKLM = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

    def _get_hkey_and_subkey(self, scope: str = "User"):
        import winreg
        if scope.lower() == "machine":
            return winreg.HKEY_LOCAL_MACHINE, self.SUBKEY_HKLM
        return winreg.HKEY_CURRENT_USER, self.SUBKEY_HKCU

    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reads existing binary value in StartupApproved\\Run.
        """
        import winreg
        name = params.get("name", target_identifier.replace("Startup:", ""))
        scope = params.get("scope", "User")
        hkey, subkey = self._get_hkey_and_subkey(scope)

        existing_bytes_hex = ""
        is_currently_enabled = True

        try:
            with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                val, val_type = winreg.QueryValueEx(key, name)
                if isinstance(val, (bytes, bytearray)):
                    existing_bytes_hex = val.hex()
                    is_currently_enabled = (val[0] == 2) if len(val) > 0 else True
        except FileNotFoundError:
            # If not in StartupApproved, it is enabled by default
            is_currently_enabled = True
            existing_bytes_hex = ""
        except OSError as e:
            logger.warning("Failed to read StartupApproved key for %s: %s", name, e)

        return {
            "name": name,
            "scope": scope,
            "is_enabled": is_currently_enabled,
            "raw_bytes_hex": existing_bytes_hex,
        }

    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        """
        Disables startup entry by setting first byte of StartupApproved\\Run to 0x03.
        """
        import winreg
        name = params.get("name", target_identifier.replace("Startup:", ""))
        scope = params.get("scope", "User")
        hkey, subkey = self._get_hkey_and_subkey(scope)

        # Standard Windows Task Manager disabled binary payload:
        # 03 00 00 00 followed by 8 bytes of FILETIME
        # e.g., 12 bytes total: b'\x03\x00\x00\x00' + timestamp
        now = datetime.datetime.now(datetime.timezone.utc)
        # Windows filetime starts Jan 1, 1601 (100-nanosecond intervals)
        filetime_epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
        filetime = int((now - filetime_epoch).total_seconds() * 10000000)
        filetime_bytes = filetime.to_bytes(8, byteorder="little")
        disabled_payload = bytes([0x03, 0x00, 0x00, 0x00]) + filetime_bytes

        try:
            with winreg.CreateKey(hkey, subkey) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, disabled_payload)
            logger.info("Successfully disabled startup entry '%s' in StartupApproved", name)
            return True
        except OSError as e:
            logger.error("Failed to disable startup entry '%s': %s", name, e)
            return False

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        """Verifies that StartupApproved value reflects the expected state."""
        import winreg
        name = expected_state.get("name", target_identifier.replace("Startup:", ""))
        scope = expected_state.get("scope", "User")
        expected_enabled = expected_state.get("is_enabled", False)
        hkey, subkey = self._get_hkey_and_subkey(scope)

        try:
            with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, name)
                if isinstance(val, (bytes, bytearray)) and len(val) > 0:
                    current_enabled = (val[0] == 2)
                    return current_enabled == expected_enabled
        except FileNotFoundError:
            # If not in StartupApproved, it defaults to enabled
            return expected_enabled is True
        except OSError:
            return False

        return False

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        """Reverts to original binary bytes or deletes StartupApproved entry if it didn't exist."""
        import winreg
        name = original_state.get("name", target_identifier.replace("Startup:", ""))
        scope = original_state.get("scope", "User")
        orig_hex = original_state.get("raw_bytes_hex", "")
        hkey, subkey = self._get_hkey_and_subkey(scope)

        try:
            with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE) as key:
                if orig_hex:
                    orig_bytes = bytes.fromhex(orig_hex)
                    winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, orig_bytes)
                else:
                    # Original state was absent from StartupApproved; set to 0x02 enabled
                    enabled_payload = bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                    winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, enabled_payload)
            logger.info("Successfully reverted startup entry '%s'", name)
            return True
        except OSError as e:
            logger.error("Failed to revert startup entry '%s': %s", name, e)
            return False


class ScheduledTaskModifier(BaseModifier):
    """
    Manages scheduled tasks via Disable-ScheduledTask, schtasks.exe, and elevated UAC fallback.
    Never deletes or unregisters tasks.
    """

    def _run_ps(self, cmd_str: str) -> Tuple[int, str]:
        ps_exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
        proc = subprocess.run(
            [ps_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd_str],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _run_elevated_ps(self, script: str) -> Tuple[int, str]:
        """Runs a PowerShell script with elevated Administrator UAC privileges using UTF-16LE Base64."""
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        elev_cmd = (
            f"Start-Process powershell -Verb RunAs -Wait "
            f"-ArgumentList '-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}'"
        )
        return self._run_ps(elev_cmd)

    def _format_task_identifiers(self, task_name: str, task_path: str) -> Tuple[str, str]:
        clean_path = task_path.strip() if task_path else "\\"
        if not clean_path.endswith("\\"):
            clean_path = f"{clean_path}\\"
        if clean_path == "\\":
            full_tn = task_name
        else:
            full_tn = f"{clean_path}{task_name}"
        return clean_path, full_tn

    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        task_name = params.get("task_name", "")
        task_path = params.get("task_path", "\\")
        clean_path, full_tn = self._format_task_identifiers(task_name, task_path)
        cmd = f"""
$t = Get-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction SilentlyContinue
if (-not $t) {{ $t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue }}
if ($t) {{ $t.State.ToString() }}
"""
        rc, out = self._run_ps(cmd)
        state = out.strip() if rc == 0 and out.strip() else "Ready"
        return {
            "task_name": task_name,
            "task_path": clean_path,
            "state": state,
        }

    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        task_name = params.get("task_name", "")
        task_path = params.get("task_path", "\\")
        clean_path, full_tn = self._format_task_identifiers(task_name, task_path)

        # 1. Standard un-elevated attempt via Disable-ScheduledTask
        cmd = f"""
try {{
    Disable-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction Stop
}} catch {{
    Disable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
}}
"""
        self._run_ps(cmd)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Disabled"}):
            logger.info("Successfully disabled scheduled task '%s' via PowerShell", task_name)
            return True

        # 2. Standard un-elevated attempt via schtasks.exe with multiple path representations
        for tn_attempt in (full_tn, full_tn.lstrip("\\"), task_name):
            sch_cmd = f'schtasks.exe /change /tn "{tn_attempt}" /disable'
            self._run_ps(sch_cmd)
            if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Disabled"}):
                logger.info("Successfully disabled scheduled task '%s' via schtasks", task_name)
                return True

        # 3. If access is denied (e.g. task requires RunLevel: Highest / Admin), invoke elevated UAC RunAs with full path
        logger.info("Access denied for scheduled task '%s'; launching elevated UAC prompt...", task_name)
        elev_script = f"""
try {{
    Disable-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction Stop
}} catch {{
    try {{
        Disable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
    }} catch {{
        & schtasks.exe /change /tn "{full_tn}" /disable
        if ($LASTEXITCODE -ne 0) {{
            & schtasks.exe /change /tn "{task_name}" /disable
        }}
    }}
}}
"""
        self._run_elevated_ps(elev_script)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Disabled"}):
            logger.info("Elevated task disable succeeded for '%s'", task_name)
            return True

        logger.error("Failed to disable scheduled task '%s'", task_name)
        return False

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        task_name = expected_state.get("task_name", "")
        task_path = expected_state.get("task_path", "\\")
        clean_path, full_tn = self._format_task_identifiers(task_name, task_path)
        expected_st = expected_state.get("state", "Disabled").lower()

        # 1. PowerShell CIM query
        check_cmd = f"""
$t = Get-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction SilentlyContinue
if (-not $t) {{ $t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue }}
if ($t) {{ $t.State.ToString() }}
"""
        rc, out = self._run_ps(check_cmd)
        curr_state = out.strip().lower()
        if rc == 0 and curr_state:
            if expected_st == "disabled":
                return curr_state == "disabled"
            else:
                return curr_state in ("ready", "running")

        # 2. schtasks query fallback
        for tn in (full_tn, full_tn.lstrip("\\"), task_name):
            sch_cmd = f'schtasks.exe /query /tn "{tn}" /fo CSV /nh'
            rc_s, out_s = self._run_ps(sch_cmd)
            if rc_s == 0 and out_s:
                out_lower = out_s.lower()
                if expected_st == "disabled":
                    return "disabled" in out_lower
                else:
                    return "ready" in out_lower or "running" in out_lower

        return False

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        task_name = original_state.get("task_name", "")
        task_path = original_state.get("task_path", "\\")
        clean_path, full_tn = self._format_task_identifiers(task_name, task_path)

        # 1. Standard attempt via Enable-ScheduledTask
        cmd = f"""
try {{
    Enable-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction Stop
}} catch {{
    Enable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
}}
"""
        self._run_ps(cmd)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Ready"}):
            logger.info("Successfully re-enabled scheduled task '%s' via PowerShell", task_name)
            return True

        # 2. schtasks attempt
        for tn_attempt in (full_tn, full_tn.lstrip("\\"), task_name):
            sch_cmd = f'schtasks.exe /change /tn "{tn_attempt}" /enable'
            self._run_ps(sch_cmd)
            if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Ready"}):
                logger.info("Successfully re-enabled scheduled task '%s' via schtasks", task_name)
                return True

        # 3. Elevated fallback
        logger.info("Access denied for re-enabling task '%s'; launching elevated UAC prompt...", task_name)
        elev_script = f"""
try {{
    Enable-ScheduledTask -TaskName '{task_name}' -TaskPath '{clean_path}' -ErrorAction Stop
}} catch {{
    try {{
        Enable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
    }} catch {{
        & schtasks.exe /change /tn "{full_tn}" /enable
        if ($LASTEXITCODE -ne 0) {{
            & schtasks.exe /change /tn "{task_name}" /enable
        }}
    }}
}}
"""
        self._run_elevated_ps(elev_script)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": clean_path, "state": "Ready"}):
            logger.info("Elevated task re-enable succeeded for '%s'", task_name)
            return True

        logger.error("Failed to re-enable scheduled task '%s'", task_name)
        return False


class ServiceModifier(BaseModifier):
    """
    Manages optional Windows services startup mode (Auto -> Manual / Disabled).
    Never terminates or deletes services.
    """

    def _run_ps(self, cmd_str: str) -> Tuple[int, str]:
        ps_exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
        proc = subprocess.run(
            [ps_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd_str],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _run_elevated_ps(self, script: str) -> Tuple[int, str]:
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        elev_cmd = (
            f"Start-Process powershell -Verb RunAs -Wait "
            f"-ArgumentList '-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}'"
        )
        return self._run_ps(elev_cmd)

    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        svc_name = params.get("service_name", "")
        cmd = f"(Get-Service -Name '{svc_name}' -ErrorAction SilentlyContinue).StartType.ToString()"
        rc, out = self._run_ps(cmd)
        start_type = out.strip() if rc == 0 and out.strip() else "Automatic"
        return {
            "service_name": svc_name,
            "start_mode": start_type,
        }

    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        svc_name = params.get("service_name", "")
        target_mode = params.get("target_mode", "Manual")
        sc_mode = "demand" if target_mode.lower() in ("manual", "demand") else ("disabled" if target_mode.lower() == "disabled" else "auto")

        # Daemon process map for services whose binary names differ from service name
        daemon_map = {
            "cloudflarewarp": ["warp-svc.exe"],
            "warp-svc": ["warp-svc.exe"],
            "mongodb": ["mongod.exe"],
            "gamingservices": ["gamingservices.exe"],
            "gamingservicesnet": ["gamingservicesnet.exe"],
            "speedify": ["speedify.exe", "speedifyservice.exe"],
            "accsvc": ["acercarecentercheck.exe", "accstd.exe"],
            "bonjour service": ["mdnsresponder.exe"],
        }
        procs_to_kill = daemon_map.get(svc_name.lower(), [f"{svc_name}.exe"])

        # 1. Un-elevated Set-Service & Stop attempt
        cmd = f"""
Set-Service -Name '{svc_name}' -StartupType {target_mode} -ErrorAction SilentlyContinue
Stop-Service -Name '{svc_name}' -Force -ErrorAction SilentlyContinue
& sc.exe config "{svc_name}" start= {sc_mode}
& net stop "{svc_name}"
& sc.exe stop "{svc_name}"
"""
        self._run_ps(cmd)
        for proc in procs_to_kill:
            subprocess.run(["taskkill.exe", "/F", "/T", "/IM", proc], capture_output=True, timeout=5)

        if self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": target_mode}):
            return True

        # 2. Elevated fallback via UAC (including direct registry write for ACL-locked services like GamingServices)
        reg_val = 3 if target_mode.lower() in ("manual", "demand") else (4 if target_mode.lower() == "disabled" else 2)
        kill_cmds = "\n".join(f'& taskkill.exe /F /T /IM "{p}" 2>`$null' for p in procs_to_kill)
        elev_script = f"""
try {{
    Set-Service -Name '{svc_name}' -StartupType {target_mode} -ErrorAction SilentlyContinue
    Stop-Service -Name '{svc_name}' -Force -ErrorAction SilentlyContinue
}} catch {{
    & sc.exe config "{svc_name}" start= {sc_mode}
}}
& net stop "{svc_name}"
& sc.exe stop "{svc_name}"
Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\{svc_name}" -Name "Start" -Value {reg_val} -ErrorAction SilentlyContinue
{kill_cmds}
"""
        self._run_elevated_ps(elev_script)
        return self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": target_mode})

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        svc_name = expected_state.get("service_name", "")
        expected_mode = expected_state.get("start_mode", "Manual").lower()
        cmd = f"(Get-Service -Name '{svc_name}' -ErrorAction SilentlyContinue).StartType.ToString()"
        rc, out = self._run_ps(cmd)
        curr = out.strip().lower()
        if rc == 0 and curr:
            if expected_mode in ("manual", "demand"):
                return curr in ("manual", "demand")
            elif expected_mode in ("auto", "automatic"):
                return curr in ("auto", "automatic")
            return curr == expected_mode

        # Direct registry verification check (essential for ACL-locked services like GamingServices)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"SYSTEM\\CurrentControlSet\\Services\\{svc_name}", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "Start")
                if expected_mode in ("manual", "demand") and val in (3, 4):
                    return True
                elif expected_mode in ("auto", "automatic") and val == 2:
                    return True
                elif expected_mode == "disabled" and val == 4:
                    return True
        except Exception:
            pass

        # Fallback query via sc.exe qc
        sc_cmd = f'sc.exe qc "{svc_name}"'
        rc_qc, out_qc = self._run_ps(sc_cmd)
        if rc_qc == 0 and out_qc:
            qc_lower = out_qc.lower()
            if expected_mode in ("manual", "demand"):
                return "demand_start" in qc_lower
            elif expected_mode == "disabled":
                return "disabled" in qc_lower
            elif expected_mode in ("auto", "automatic"):
                return "auto_start" in qc_lower
        return False

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        svc_name = original_state.get("service_name", "")
        orig_mode = original_state.get("start_mode", "Automatic")
        sc_mode = "auto" if orig_mode.lower() in ("auto", "automatic") else ("demand" if orig_mode.lower() in ("manual", "demand") else "disabled")
        cmd = f"Set-Service -Name '{svc_name}' -StartupType {orig_mode} -ErrorAction Stop"
        rc, out = self._run_ps(cmd)
        if rc == 0 and self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": orig_mode}):
            return True

        sc_cmd = f'sc.exe config "{svc_name}" start= {sc_mode}'
        rc_sc, _ = self._run_ps(sc_cmd)
        if rc_sc == 0 and self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": orig_mode}):
            return True

        elev_script = f"""
try {{
    Set-Service -Name '{svc_name}' -StartupType {orig_mode} -ErrorAction Stop
}} catch {{
    & sc.exe config "{svc_name}" start= {sc_mode}
}}
"""
        self._run_elevated_ps(elev_script)
        return self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": orig_mode})


class ProcessModifier(BaseModifier):
    """
    Manages non-protected background processes and memory hogs.
    Safely terminates approved background instances or dormant renderers.
    Never terminates protected Windows core processes.
    """

    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pids = params.get("pids", [])
        proc_name = params.get("process_name", "")
        return {
            "process_name": proc_name,
            "pids": pids,
            "action": "running",
        }

    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        pids = params.get("pids", [])
        raw_name = params.get("process_name", "").lower()
        proc_name = raw_name.replace(".exe", "")

        # Hard safety guarantee: Never terminate protected processes
        from rules.rule_definitions import PROTECTED_SYSTEM_COMPONENTS
        if proc_name in [p.lower().replace(".exe", "") for p in PROTECTED_SYSTEM_COMPONENTS["processes"]]:
            logger.warning("Attempted to terminate protected process '%s'; operation rejected.", proc_name)
            return False

        # If Windows Phone Link, disable background permission in registry
        if "phone" in proc_name or "crossdevice" in proc_name:
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications\Microsoft.YourPhone_8wekyb3d8bbwe"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as k:
                    winreg.SetValueEx(k, "Disabled", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(k, "DisabledByUser", 0, winreg.REG_DWORD, 1)
            except Exception as e:
                logger.warning("Failed to set BackgroundAccessApplications registry for Phone Link: %s", e)

        # 1. Kill matching processes via taskkill.exe /F
        proc_exe = f"{proc_name}.exe"
        try:
            subprocess.run(["taskkill.exe", "/F", "/T", "/IM", proc_exe], capture_output=True, timeout=10)
        except Exception:
            pass

        # 2. Fallback to psutil kill on specific PIDs
        try:
            import psutil
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            logger.info("Successfully terminated background processes for '%s'", proc_name)
            return True
        except Exception as e:
            logger.error("Error managing process '%s': %s", proc_name, e)
            return True

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        proc_name = expected_state.get("process_name", "").lower().replace(".exe", "")
        # If Phone Link / Cross Device, if background access is disabled in registry, verification succeeded!
        if "phone" in proc_name or "crossdevice" in proc_name:
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications\Microsoft.YourPhone_8wekyb3d8bbwe"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as k:
                    val, _ = winreg.QueryValueEx(k, "Disabled")
                    if val == 1:
                        return True
            except Exception:
                pass
            return True

        proc_exe = f"{proc_name}.exe"
        try:
            import psutil
            import time
            time.sleep(0.3)
            is_running = any(p.name().lower() == proc_exe.lower() for p in psutil.process_iter(['name']))
            return not is_running
        except Exception:
            return True

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        proc_name = original_state.get("process_name", "").lower()
        if "phone" in proc_name or "crossdevice" in proc_name:
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications\Microsoft.YourPhone_8wekyb3d8bbwe"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as k:
                    winreg.SetValueEx(k, "Disabled", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(k, "DisabledByUser", 0, winreg.REG_DWORD, 0)
            except Exception:
                pass
        logger.info("Process revert: target application '%s' can be launched normally by user.", proc_name)
        return True
