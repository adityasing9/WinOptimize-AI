"""
WinOptimize AI - State Verifier
Confirms that applied modifications took effect immediately.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional

from optimizer.modifiers import (
    BaseModifier,
    StartupRegistryModifier,
    ScheduledTaskModifier,
    ServiceModifier,
)

logger = logging.getLogger("WinOp.Verification")


class StateVerifier:
    """
    Verifies that system configuration matches intended target states.
    Never claims an optimization succeeded unless verified.
    """

    def __init__(self):
        self.modifiers = {
            "registry_startup": StartupRegistryModifier(),
            "scheduled_task": ScheduledTaskModifier(),
            "service": ServiceModifier(),
        }

    def verify_target_state(
        self,
        target_type: str,
        target_identifier: str,
        expected_state: Dict[str, Any],
    ) -> bool:
        """Verifies state using the appropriate modifier's verify_state method."""
        modifier = self.modifiers.get(target_type)
        if not modifier:
            logger.warning("No modifier registered for target type %s", target_type)
            return False

        try:
            return modifier.verify_state(target_identifier, expected_state)
        except Exception as e:
            logger.error("State verification exception for %s: %s", target_identifier, e)
            return False
