"""Adapter factory for SimBridge GCS."""

from __future__ import annotations

from typing import Any, Dict, Optional
from simbridge.adapters.base import BaseSimulatorAdapter
from simbridge.adapters.blender import BlenderAdapter
from simbridge.adapters.gazebo import GazeboAdapter
from simbridge.adapters.mock import MockSimulatorAdapter
from simbridge.adapters.px4 import PX4Adapter


def create_adapter(adapter_type: str, config: Optional[Dict[str, Any]] = None) -> BaseSimulatorAdapter:
    """Factory function instantiating the requested simulator adapter."""
    t = str(adapter_type or "").lower().strip()
    cfg = config or {}

    if t in ("gazebo", "gz"):
        gz_cfg = cfg.get("gazebo", cfg)
        return GazeboAdapter(name="gazebo", config=gz_cfg)
    elif t in ("px4", "px4_sitl", "mavlink"):
        px4_cfg = cfg.get("px4", cfg)
        return PX4Adapter(name="px4", config=px4_cfg)
    elif t in ("blender", "asset"):
        blender_cfg = cfg.get("blender", cfg)
        return BlenderAdapter(name="blender", config=blender_cfg)
    elif t in ("mock", "synthetic", "demo"):
        mock_cfg = cfg.get("mock", cfg)
        return MockSimulatorAdapter(name="mock", config=mock_cfg)
    elif t in ("none", ""):
        return MockSimulatorAdapter(name="none", config={"speed": 0.0, "altitude": 0.0})
    else:
        print(f"[AdapterFactory] Unknown adapter type '{adapter_type}', falling back to Mock.")
        return MockSimulatorAdapter(name="mock", config=cfg.get("mock", cfg))
