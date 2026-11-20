"""Gazebo Sim (Harmonic / Ionic) Transport Adapter for SimBridge GCS."""

from __future__ import annotations

import math
import os
import site
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
import psutil
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
    TrajectoryPoint,
    VehicleState,
    Velocity,
)
from simbridge.core.video import BaseVideoSource, GazeboVideoSource


def _clean_env(partition: Optional[str] = None) -> Dict[str, str]:
    """Clean system environment for Gazebo CLI or transport subprocesses."""
    env = os.environ.copy()
    if partition:
        env["GZ_PARTITION"] = partition
    for var in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
        if var in env:
            filtered = [p for p in env[var].split(":") if "snap" not in p and p.strip()]
            if filtered:
                env[var] = ":".join(filtered)
            else:
                env.pop(var, None)
    return env


class GazeboAdapter(BaseSimulatorAdapter):
    """Integrates with Gazebo Sim via native gz.transport C++ Python bindings."""

    def __init__(self, name: str = "gazebo", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self.partition = str(self.config.get("partition", "") or os.environ.get("GZ_PARTITION", "")).strip()
        self.world_name = str(self.config.get("world_name", "default")).strip()
        self.model_name = str(self.config.get("model_name", "quadcopter")).strip()
        self.dynamic_pose_topic = str(
            self.config.get("dynamic_pose_topic", f"/world/{self.world_name}/dynamic_pose/info")
        ).strip()
        self.static_pose_topic = str(
            self.config.get("static_pose_topic", f"/world/{self.world_name}/pose/info")
        ).strip()
        self.camera_topic = str(self.config.get("camera_topic", "/camera/image")).strip()
        self.sub_timeout_s = float(self.config.get("sub_timeout_s", 2.0))

        # Internal state
        self._lock = threading.Lock()
        self._last_pose_time = 0.0
        self._last_pose = Pose()
        self._vehicle_present = False
        self._trajectory: List[TrajectoryPoint] = []
        self._max_traj_points = 300
        self._discovered_topics: List[str] = []
        self._discovered_worlds: List[str] = []
        self._discovered_models: List[str] = []

        self._gz_node = None
        self.video_source: Optional[GazeboVideoSource] = None
        self._stop_event = threading.Event()
        self._discovery_thread: Optional[threading.Thread] = None

    def _discover_system(self) -> None:
        """Query available Gazebo topics, worlds, and entities."""
        clean_e = _clean_env(self.partition)
        try:
            res = subprocess.run(
                ["gz", "topic", "-l"],
                capture_output=True,
                text=True,
                timeout=2.0,
                env=clean_e,
            )
            if res.returncode == 0:
                topics = [t.strip() for t in res.stdout.splitlines() if t.strip()]
                with self._lock:
                    self._discovered_topics = topics

                # Detect active worlds and models from topic strings
                worlds = set()
                models = set()
                for t in topics:
                    parts = t.split("/")
                    if "world" in parts:
                        idx = parts.index("world")
                        if idx + 1 < len(parts):
                            worlds.add(parts[idx + 1])
                    if "model" in parts:
                        idx = parts.index("model")
                        if idx + 1 < len(parts):
                            models.add(parts[idx + 1])

                with self._lock:
                    if worlds:
                        self._discovered_worlds = sorted(list(worlds))
                        # If default world isn't in discovered, adopt first detected world
                        if self.world_name not in worlds and len(self._discovered_worlds) > 0:
                            self.world_name = self._discovered_worlds[0]
                            self.dynamic_pose_topic = f"/world/{self.world_name}/dynamic_pose/info"
                            self.static_pose_topic = f"/world/{self.world_name}/pose/info"
                    if models:
                        self._discovered_models = sorted(list(models))
        except Exception as e:
            self._last_error = f"Topic discovery error: {e}"

    def connect(self) -> bool:
        self._connection_state = "CONNECTING"
        self._stop_event.clear()

        # Step 1: Discover topics and world
        self._discover_system()

        # Step 2: Initialize Gazebo Transport Node
        site.addsitedir("/usr/lib/python3/dist-packages")
        try:
            from gz.transport import Node
            from gz.msgs.pose_v_pb2 import Pose_V

            self._gz_node = Node()
            # Subscribe to pose vector
            self._gz_node.subscribe(Pose_V, self.dynamic_pose_topic, self._on_pose_v)
            self._gz_node.subscribe(Pose_V, self.static_pose_topic, self._on_pose_v)
        except Exception as e:
            self._last_error = f"Failed to connect gz.transport Node: {e}"
            self._connection_state = "ERROR"
            self._connected = False
            return False

        # Step 3: Initialize Video Source
        try:
            self.video_source = GazeboVideoSource(
                topic=self.camera_topic,
                width=int(self.config.get("width", 640)),
                height=int(self.config.get("height", 360)),
                stale_timeout_s=self.sub_timeout_s,
            )
        except Exception as e:
            self.video_source = None
            self._last_error = f"Gazebo camera init error: {e}"

        self._connected = True
        self._connection_state = "CONNECTED"
        return True

    def _on_pose_v(self, msg: Any) -> None:
        """Callback for Gazebo Pose_V messages."""
        now = time.time()
        for p in getattr(msg, "pose", []):
            name = getattr(p, "name", "")
            # Match configured model name or general target
            if name == self.model_name or self.model_name in name:
                pos = getattr(p, "position", None)
                orient = getattr(p, "orientation", None)
                if pos and orient:
                    px = float(pos.x)
                    py = float(pos.y)
                    pz = float(pos.z)

                    qw = float(orient.w)
                    qx = float(orient.x)
                    qy = float(orient.y)
                    qz = float(orient.z)

                    r, pt, y = self._quat_to_euler(qw, qx, qy, qz)

                    with self._lock:
                        dt = max(1e-4, now - self._last_pose_time) if self._last_pose_time > 0 else 0.05
                        last_p = self._last_pose.position

                        vx = (px - last_p.x) / dt if dt > 0 else 0.0
                        vy = (py - last_p.y) / dt if dt > 0 else 0.0
                        vz = (pz - last_p.z) / dt if dt > 0 else 0.0

                        new_pose = Pose(
                            position=Position(x=round(px, 3), y=round(py, 3), z=round(pz, 3)),
                            orientation=Orientation(
                                roll=round(r, 2),
                                pitch=round(pt, 2),
                                yaw=round(y, 2),
                                qw=round(qw, 4),
                                qx=round(qx, 4),
                                qy=round(qy, 4),
                                qz=round(qz, 4),
                            ),
                            velocity=Velocity(vx=round(vx, 2), vy=round(vy, 2), vz=round(vz, 2)),
                            timestamp=now,
                        )
                        self._last_pose = new_pose
                        self._last_pose_time = now
                        self._vehicle_present = True

                        self._trajectory.append(TrajectoryPoint(x=px, y=py, z=pz, timestamp=now))
                        if len(self._trajectory) > self._max_traj_points:
                            self._trajectory.pop(0)
                break

    @staticmethod
    def _quat_to_euler(w: float, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Convert quaternion (w, x, y, z) to Euler angles (roll, pitch, yaw) in degrees."""
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1.0:
            pitch = math.copysign(math.pi / 2.0, sinp)
        else:
            pitch = math.asin(sinp)

        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return (
            math.degrees(roll),
            math.degrees(pitch),
            (math.degrees(yaw) + 360.0) % 360.0,
        )

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._gz_node:
            try:
                self._gz_node.unsubscribe(self.dynamic_pose_topic)
                self._gz_node.unsubscribe(self.static_pose_topic)
            except Exception:
                pass
            self._gz_node = None

        if self.video_source:
            self.video_source.release()
            self.video_source = None

        self._connected = False
        self._connection_state = "DISCONNECTED"

    def get_video_source(self) -> Optional[BaseVideoSource]:
        return self.video_source

    def is_vehicle_present(self) -> bool:
        with self._lock:
            return self._vehicle_present and ((time.time() - self._last_pose_time) < self.sub_timeout_s)

    def get_telemetry(self) -> TelemetryFrame:
        now = time.time()
        present = self.is_vehicle_present()

        with self._lock:
            pose = self._last_pose
            traj = list(self._trajectory)
            topics = list(self._discovered_topics)

        # Camera state
        cam_state = "IDLE"
        cam_fps = 0.0
        cam_captured = 0
        cam_err = None
        if self.video_source and isinstance(self.video_source, GazeboVideoSource):
            cam_captured = self.video_source._frames_received
            if cam_captured > 0:
                cam_state = "ACTIVE"
                cam_fps = 15.0
            else:
                cam_state = "CONNECTING"
            cam_err = self.video_source._last_error

        cam_telemetry = CameraTelemetry(
            state=cam_state,
            source="gazebo",
            width=640,
            height=360,
            fps=cam_fps,
            frames_captured=cam_captured,
            error=cam_err,
        )

        veh_state = VehicleState(
            connected=self._connected,
            armed=present,
            flight_mode="SIMULATION" if present else "STANDBY",
            landed=(pose.position.z <= 0.1),
            vehicle_type="quadcopter",
            status_text="PRESENT" if present else "WAITING_FOR_MODEL",
        )

        components = {
            "backend": "CONNECTED",
            "simulator": "CONNECTED" if self._connected else "DISCONNECTED",
            "vehicle": "PRESENT" if present else "NOT SPAWNED",
            "camera": cam_state,
            "stream": "ACTIVE",
        }

        # Check sensors from topic names
        imu_health = "NOMINAL" if any("imu" in t for t in topics) else "N/A"
        cam_health = "NOMINAL" if any("image" in t or "camera" in t for t in topics) else "DEGRADED"

        return TelemetryFrame(
            timestamp=now,
            simulator="gazebo",
            connection_state="CONNECTED" if self._connected else "DISCONNECTED",
            pose=pose,
            vehicle=veh_state,
            battery=BatteryStatus(percentage=100.0, voltage_v=16.8, healthy=True),
            gps=GPSStatus(fix_type="SIM_GROUND_TRUTH", satellites=16, valid=True),
            sensors=SensorHealth(imu=imu_health, camera=cam_health),
            camera=cam_telemetry,
            performance=PerformanceMetrics(telemetry_hz=20.0),
            trajectory=traj,
            components=components,
            active_topics=topics,
            diagnostic_messages=[
                f"World: {self.world_name}",
                f"Model: {self.model_name}",
                f"Dynamic Pose Topic: {self.dynamic_pose_topic}",
                f"Vehicle present: {present}",
            ],
        )

    def get_info(self) -> SimulationInfo:
        return SimulationInfo(
            simulator_name="Gazebo Sim",
            version="Harmonic / Ionic",
            world_name=self.world_name,
            model_name=self.model_name,
            connected=self._connected,
            state=self._connection_state,
            active_topics=list(self._discovered_topics),
            available_worlds=list(self._discovered_worlds),
            available_models=list(self._discovered_models),
            error=self._last_error,
        )
