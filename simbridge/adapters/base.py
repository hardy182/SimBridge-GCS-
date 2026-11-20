"""Base simulator adapter interface for SimBridge GCS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from simbridge.core.contracts import SimulationInfo, TelemetryFrame
from simbridge.core.video import BaseVideoSource


class BaseSimulatorAdapter(ABC):
    """Abstract base class for all simulator connections (Gazebo, PX4, Blender, Mock)."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.config = config or {}
        self._connected: bool = False
        self._connection_state: str = "IDLE"  # "IDLE", "CONNECTING", "CONNECTED", "DEGRADED", "DISCONNECTED", "ERROR"
        self._last_error: Optional[str] = None

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the simulator. Return True on success."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly terminate simulator connection and release resources."""
        pass

    def is_connected(self) -> bool:
        """Return True if connection is alive and healthy."""
        return self._connected

    @property
    def connection_state(self) -> str:
        """Return current high-level connection state."""
        return self._connection_state

    @property
    def last_error(self) -> Optional[str]:
        """Return last recorded error string, if any."""
        return self._last_error

    @abstractmethod
    def get_telemetry(self) -> TelemetryFrame:
        """Return normalized telemetry frame with latest pose, state, and diagnostics."""
        pass

    @abstractmethod
    def get_video_source(self) -> Optional[BaseVideoSource]:
        """Return the active video source associated with this simulator, if any."""
        pass

    @abstractmethod
    def get_info(self) -> SimulationInfo:
        """Return metadata about the simulation environment (world, model, active topics)."""
        pass

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return adapter-specific diagnostic metrics and telemetry details."""
        return {
            "adapter": self.name,
            "connected": self._connected,
            "state": self._connection_state,
            "error": self._last_error,
        }
