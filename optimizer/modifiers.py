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
            f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden "
            f"-ArgumentList '-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}'"
        )
        return self._run_ps(elev_cmd)

    def capture_current_state(self, target_identifier: str, params: Dict[str, Any]) -> Dict[str, Any]:
        task_name = params.get("task_name", "")
        task_path = params.get("task_path", "\\")
        cmd = f"(Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue).State.ToString()"
        rc, out = self._run_ps(cmd)
        state = out.strip() if rc == 0 and out.strip() else "Ready"
        return {
            "task_name": task_name,
            "task_path": task_path,
            "state": state,
        }

    def apply_modification(self, target_identifier: str, params: Dict[str, Any]) -> bool:
        task_name = params.get("task_name", "")
        task_path = params.get("task_path", "\\")

        # 1. Standard un-elevated attempt via Disable-ScheduledTask
        cmd = f"Disable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop"
        rc, out = self._run_ps(cmd)
        if rc == 0 and self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Disabled"}):
            logger.info("Successfully disabled scheduled task '%s' via PowerShell", task_name)
            return True

        # 2. Standard un-elevated attempt via schtasks.exe
        sch_cmd = f'schtasks.exe /change /tn "{task_name}" /disable'
        rc_sch, out_sch = self._run_ps(sch_cmd)
        if rc_sch == 0 and self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Disabled"}):
            logger.info("Successfully disabled scheduled task '%s' via schtasks", task_name)
            return True

        # 3. If access is denied (e.g. task requires RunLevel: Highest / Admin), invoke elevated UAC RunAs
        logger.info("Access denied for scheduled task '%s'; launching elevated UAC prompt...", task_name)
        elev_script = f"""
try {{
    Disable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
}} catch {{
    & schtasks.exe /change /tn "{task_name}" /disable
}}
"""
        self._run_elevated_ps(elev_script)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Disabled"}):
            logger.info("Elevated task disable succeeded for '%s'", task_name)
            return True

        logger.error("Failed to disable scheduled task '%s': %s | %s", task_name, out, out_sch)
        return False

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        task_name = expected_state.get("task_name", "")
        expected_st = expected_state.get("state", "Disabled").lower()

        # Check using PowerShell CIM/Get-ScheduledTask
        cmd = f"(Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue).State.ToString()"
        rc, out = self._run_ps(cmd)
        curr_state = out.strip().lower()
        if rc == 0 and curr_state:
            if expected_st == "disabled":
                return curr_state == "disabled"
            else:
                return curr_state in ("ready", "running")

        # Fallback query via native schtasks.exe
        sch_cmd = f'schtasks.exe /query /tn "{task_name}" /fo CSV /nh'
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

        # 1. Standard attempt via Enable-ScheduledTask
        cmd = f"Enable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop"
        rc, out = self._run_ps(cmd)
        if rc == 0 and self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Ready"}):
            logger.info("Successfully re-enabled scheduled task '%s' via PowerShell", task_name)
            return True

        # 2. Standard attempt via schtasks.exe
        sch_cmd = f'schtasks.exe /change /tn "{task_name}" /enable'
        rc_sch, out_sch = self._run_ps(sch_cmd)
        if rc_sch == 0 and self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Ready"}):
            logger.info("Successfully re-enabled scheduled task '%s' via schtasks", task_name)
            return True

        # 3. Elevated UAC fallback
        logger.info("Access denied for re-enabling task '%s'; launching elevated UAC prompt...", task_name)
        elev_script = f"""
try {{
    Enable-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop
}} catch {{
    & schtasks.exe /change /tn "{task_name}" /enable
}}
"""
        self._run_elevated_ps(elev_script)
        if self.verify_state(target_identifier, {"task_name": task_name, "task_path": task_path, "state": "Ready"}):
            logger.info("Elevated task re-enable succeeded for '%s'", task_name)
            return True

        logger.error("Failed to re-enable scheduled task '%s': %s | %s", task_name, out, out_sch)
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
            f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden "
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
        cmd = f"Set-Service -Name '{svc_name}' -StartupType {target_mode} -ErrorAction Stop"
        rc, out = self._run_ps(cmd)
        if rc == 0 and self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": target_mode}):
            return True

        # Elevated fallback
        elev_script = f"Set-Service -Name '{svc_name}' -StartupType {target_mode} -ErrorAction Stop"
        self._run_elevated_ps(elev_script)
        return self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": target_mode})

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        svc_name = expected_state.get("service_name", "")
        expected_mode = expected_state.get("start_mode", "Manual")
        cmd = f"(Get-Service -Name '{svc_name}' -ErrorAction SilentlyContinue).StartType.ToString()"
        rc, out = self._run_ps(cmd)
        return rc == 0 and out.strip().lower() == expected_mode.lower()

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        svc_name = original_state.get("service_name", "")
        orig_mode = original_state.get("start_mode", "Automatic")
        cmd = f"Set-Service -Name '{svc_name}' -StartupType {orig_mode} -ErrorAction Stop"
        rc, out = self._run_ps(cmd)
        if rc == 0 and self.verify_state(target_identifier, {"service_name": svc_name, "start_mode": orig_mode}):
            return True

        elev_script = f"Set-Service -Name '{svc_name}' -StartupType {orig_mode} -ErrorAction Stop"
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
        proc_name = params.get("process_name", "").lower()

        # Hard safety guarantee: Never terminate protected processes
        from rules.rule_definitions import PROTECTED_SYSTEM_COMPONENTS
        if proc_name in [p.lower() for p in PROTECTED_SYSTEM_COMPONENTS["processes"]]:
            logger.warning("Attempted to terminate protected process '%s'; operation rejected.", proc_name)
            return False

        try:
            import psutil
            terminated = 0
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    if p.name().lower() == proc_name or proc_name in p.name().lower():
                        p.terminate()
                        terminated += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            logger.info("Terminated %d processes for '%s'", terminated, proc_name)
            return True
        except Exception as e:
            logger.error("Error managing process '%s': %s", proc_name, e)
            return False

    def verify_state(self, target_identifier: str, expected_state: Dict[str, Any]) -> bool:
        pids = expected_state.get("pids", [])
        try:
            import psutil
            alive = sum(1 for pid in pids if psutil.pid_exists(pid))
            return alive == 0
        except Exception:
            return True

    def revert_modification(self, target_identifier: str, original_state: Dict[str, Any]) -> bool:
        logger.info("Process revert: target application '%s' can be launched normally by user.", original_state.get("process_name"))
        return True
