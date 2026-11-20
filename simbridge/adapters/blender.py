"""Blender 3D Asset & Scene Integration Adapter for SimBridge GCS."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from simbridge.adapters.base import BaseSimulatorAdapter
from simbridge.core.contracts import (
    BatteryStatus,
    CameraTelemetry,
    GPSStatus,
    Orientation,
    PerformanceMetrics,
    Pose,
    Position,
    SensorHealth,
    SimulationInfo,
    TelemetryFrame,
    VehicleState,
)
from simbridge.core.video import BaseVideoSource, SyntheticVideoSource


class BlenderAdapter(BaseSimulatorAdapter):
    """Adapter for Blender 3D environment preparation, asset inspection, and export workflows.

    Note: SimBridge GCS treats Blender as a 3D modeling, asset creation, and world design tool,
    not a physics simulation engine. Real-time telemetry is reported in asset inspection mode.
    """

    def __init__(self, name: str = "blender", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self.executable_path = str(self.config.get("executable_path", "/usr/bin/blender")).strip()
        self.asset_dir = str(self.config.get("asset_dir", "")).strip()
        self.export_format = str(self.config.get("export_format", "gltf")).strip()

        self._installed = False
        self._version: Optional[str] = None
        self._inspected_assets: List[Dict[str, Any]] = []
        self.video_source: Optional[BaseVideoSource] = None

    def connect(self) -> bool:
        self._connection_state = "CONNECTING"

        # Check executable
        bin_path = shutil.which(self.executable_path) or shutil.which("blender")
        if not bin_path or not Path(bin_path).exists():
            self._last_error = f"Blender executable not found at '{self.executable_path}' or in PATH."
            self._connection_state = "ERROR"
            self._connected = False
            return False

        self.executable_path = bin_path
        self._installed = True

        try:
            res = subprocess.run(
                [self.executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if res.returncode == 0 and res.stdout:
                self._version = res.stdout.strip().splitlines()[0]
        except Exception as e:
            self._version = f"Detected ({e})"

        # Scan asset directory if specified
        if self.asset_dir and Path(self.asset_dir).exists():
            self._scan_assets(Path(self.asset_dir))

        # Synthetic camera in asset inspection mode
        self.video_source = SyntheticVideoSource(width=640, height=360, fps=15.0)

        self._connected = True
        self._connection_state = "CONNECTED"
        self._last_error = None
        return True

    def _scan_assets(self, root: Path) -> None:
        """Scan a directory for 3D model files and export readiness."""
        supported_exts = {".blend", ".gltf", ".glb", ".dae", ".obj", ".sdf", ".urdf"}
        assets = []
        for p in root.rglob("*"):
            if p.suffix.lower() in supported_exts:
                assets.append({
                    "name": p.name,
                    "path": str(p),
                    "format": p.suffix.lower().lstrip("."),
                    "size_kb": round(p.stat().st_size / 1024, 1),
                })
        self._inspected_assets = assets

    def disconnect(self) -> None:
        if self.video_source:
            self.video_source.release()
            self.video_source = None
        self._connected = False
        self._connection_state = "DISCONNECTED"

    def get_video_source(self) -> Optional[BaseVideoSource]:
        return self.video_source

    def get_telemetry(self) -> TelemetryFrame:
        now = time.time()
        components = {
            "backend": "CONNECTED",
            "simulator": "CONNECTED" if self._connected else "DISCONNECTED",
            "vehicle": "ASSET_MODE",
            "camera": "ACTIVE" if self.video_source else "OFFLINE",
            "stream": "ACTIVE",
        }

        diag = [
            f"Blender Version: {self._version or 'Not Detected'}",
            f"Executable: {self.executable_path}",
            f"Role: 3D Asset Pipeline & Model Preparation (Non-physics)",
            f"Found Assets: {len(self._inspected_assets)}",
        ]

        return TelemetryFrame(
            timestamp=now,
            simulator="blender",
            connection_state="CONNECTED" if self._connected else "DISCONNECTED",
            pose=Pose(
                position=Position(x=0.0, y=0.0, z=0.0),
                orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
                frame_id="blender_scene",
            ),
            vehicle=VehicleState(
                connected=self._connected,
                armed=False,
                flight_mode="ASSET_INSPECTION",
                landed=True,
                status_text="3D_PIPELINE_READY",
            ),
            battery=BatteryStatus(percentage=100.0, healthy=True),
            gps=GPSStatus(fix_type="N/A", satellites=0, valid=False),
            sensors=SensorHealth(),
            camera=CameraTelemetry(state="ACTIVE", source="blender_synthetic", width=640, height=360, fps=15.0),
            performance=PerformanceMetrics(telemetry_hz=10.0),
            components=components,
            active_topics=["/blender/asset_stream", "/blender/materials"],
            diagnostic_messages=diag,
        )

    def get_info(self) -> SimulationInfo:
        return SimulationInfo(
            simulator_name="Blender 3D Asset Pipeline",
            version=self._version or "Unknown",
            world_name="asset_inspector",
            model_name="exported_mesh",
            connected=self._connected,
            state=self._connection_state,
            active_topics=["asset_pipeline", "sdf_exporter", "mesh_converter"],
            available_worlds=["studio_setup", "gazebo_environment"],
            available_models=[a["name"] for a in self._inspected_assets[:5]] if self._inspected_assets else ["default_cube"],
            error=self._last_error,
        )

    def export_asset_to_gazebo(self, blend_file: str, output_sdf_dir: str) -> Dict[str, Any]:
        """Placeholder interface for automated headless Blender SDF/GLTF export."""
        # Future live script connector
        return {
            "status": "not_implemented",
            "message": "Automated CLI conversion script interface ready; see docs/BLENDER_WORKFLOW.md for manual export guidelines.",
        }
