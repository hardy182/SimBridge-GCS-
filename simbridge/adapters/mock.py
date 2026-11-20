"""Mock simulator adapter for deterministic testing, verification, and demo mode."""

from __future__ import annotations

import math
import time
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
    TrajectoryPoint,
    VehicleState,
    Velocity,
)
from simbridge.core.video import BaseVideoSource, SyntheticVideoSource


class MockSimulatorAdapter(BaseSimulatorAdapter):
    """Deterministic simulation adapter generating synthetic telemetry and video."""

    def __init__(self, name: str = "mock", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self.video_source: Optional[BaseVideoSource] = None
        self._start_time = 0.0
        self._trajectory: List[TrajectoryPoint] = []
        self._max_traj_points = 200

        # Pattern parameters
        self.speed = float(self.config.get("speed", 1.0))
        self.base_alt = float(self.config.get("altitude", 3.5))
        self.drain_rate = float(self.config.get("battery_drain_rate", 0.05))

    def connect(self) -> bool:
        self._connection_state = "CONNECTING"
        self._start_time = time.time()
        self.video_source = SyntheticVideoSource(width=640, height=360, fps=30.0)
        self._connected = True
        self._connection_state = "CONNECTED"
        self._last_error = None
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._connection_state = "DISCONNECTED"
        if self.video_source:
            self.video_source.release()
            self.video_source = None

    def get_video_source(self) -> Optional[BaseVideoSource]:
        return self.video_source

    def get_telemetry(self) -> TelemetryFrame:
        if not self._connected:
            return TelemetryFrame(
                simulator="mock",
                connection_state=self._connection_state,
                components={"backend": "ONLINE", "simulator": "DISCONNECTED", "vehicle": "OFFLINE"},
            )

        t = time.time() - self._start_time
        w = self.speed * 0.4

        # Figure-8 / Lissajous trajectory
        x = 5.0 * math.sin(w * t)
        y = 5.0 * math.sin(2.0 * w * t) * 0.5
        z = self.base_alt + 0.5 * math.sin(w * t * 0.5)

        # Velocities
        vx = 5.0 * w * math.cos(w * t)
        vy = 5.0 * w * math.cos(2.0 * w * t)
        vz = 0.25 * w * math.cos(w * t * 0.5)

        # Dynamic attitude derived from motion
        roll = math.degrees(math.atan2(-vy, 9.81)) * 0.5
        pitch = math.degrees(math.atan2(vx, 9.81)) * 0.5
        yaw = math.degrees(math.atan2(vy, vx)) % 360.0

        # Quaternion
        cy = math.cos(math.radians(yaw * 0.5))
        sy = math.sin(math.radians(yaw * 0.5))
        cp = math.cos(math.radians(pitch * 0.5))
        sp = math.sin(math.radians(pitch * 0.5))
        cr = math.cos(math.radians(roll * 0.5))
        sr = math.sin(math.radians(roll * 0.5))

        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy

        pos = Position(x=round(x, 3), y=round(y, 3), z=round(z, 3))
        orient = Orientation(
            roll=round(roll, 2),
            pitch=round(pitch, 2),
            yaw=round(yaw, 2),
            qw=round(qw, 4),
            qx=round(qx, 4),
            qy=round(qy, 4),
            qz=round(qz, 4),
        )
        vel = Velocity(
            vx=round(vx, 2),
            vy=round(vy, 2),
            vz=round(vz, 2),
            roll_rate=round(roll * 0.1, 2),
            pitch_rate=round(pitch * 0.1, 2),
            yaw_rate=round(w * 10.0, 2),
        )
        pose = Pose(position=pos, orientation=orient, velocity=vel, timestamp=time.time())

        # Update trajectory history
        self._trajectory.append(TrajectoryPoint(x=pos.x, y=pos.y, z=pos.z, timestamp=pose.timestamp))
        if len(self._trajectory) > self._max_traj_points:
            self._trajectory.pop(0)

        # Battery calculation
        batt_pct = max(0.0, 100.0 - (t * self.drain_rate))
        voltage = 14.8 + (batt_pct / 100.0) * 2.0
        batt = BatteryStatus(
            percentage=round(batt_pct, 1),
            voltage_v=round(voltage, 2),
            current_a=12.4,
            healthy=batt_pct > 15.0,
        )

        gps = GPSStatus(
            fix_type="SIM_GROUND_TRUTH",
            satellites=14,
            lat=37.7749 + (y * 0.00001),
            lon=-122.4194 + (x * 0.00001),
            alt=round(z, 2),
            valid=True,
        )

        veh = VehicleState(
            connected=True,
            armed=True,
            flight_mode="SIMULATION",
            landed=False,
            vehicle_type="quadcopter",
            status_text="AUTONOMOUS_DEMO",
        )

        cam_telemetry = CameraTelemetry(
            state="ACTIVE",
            source="synthetic",
            width=640,
            height=360,
            fps=30.0,
            frames_captured=int(t * 30),
            frames_streamed=int(t * 30),
        )

        components = {
            "backend": "CONNECTED",
            "simulator": "CONNECTED",
            "vehicle": "PRESENT",
            "camera": "ACTIVE",
            "stream": "ACTIVE",
        }

        perf = PerformanceMetrics(
            cpu_percent=12.5,
            ram_mb=128.0,
            capture_fps=30.0,
            stream_fps=30.0,
            telemetry_hz=20.0,
            latency_ms=2.4,
        )

        return TelemetryFrame(
            timestamp=time.time(),
            simulator="mock",
            connection_state="CONNECTED",
            pose=pose,
            vehicle=veh,
            battery=batt,
            gps=gps,
            sensors=SensorHealth(),
            camera=cam_telemetry,
            performance=perf,
            trajectory=list(self._trajectory),
            components=components,
            active_topics=["/mock/pose", "/mock/imu", "/mock/camera/image"],
            diagnostic_messages=["Mock flight generator running Lissajous profile."],
        )

    def get_info(self) -> SimulationInfo:
        return SimulationInfo(
            simulator_name="Mock Simulator (Built-in)",
            version="1.0.0",
            world_name="virtual_arena",
            model_name="demo_quadcopter",
            connected=self._connected,
            state=self._connection_state,
            active_topics=["/mock/pose", "/mock/imu", "/mock/camera/image"],
            available_worlds=["virtual_arena", "synthetic_grid"],
            available_models=["demo_quadcopter", "inspection_uav"],
        )
