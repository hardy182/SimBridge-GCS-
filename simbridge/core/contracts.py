"""Normalized telemetry, vehicle state, and simulation data contracts."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Orientation(BaseModel):
    roll: float = 0.0   # deg
    pitch: float = 0.0  # deg
    yaw: float = 0.0    # deg
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0


class Velocity(BaseModel):
    vx: float = 0.0     # m/s
    vy: float = 0.0     # m/s
    vz: float = 0.0     # m/s
    roll_rate: float = 0.0  # deg/s
    pitch_rate: float = 0.0 # deg/s
    yaw_rate: float = 0.0   # deg/s


class Pose(BaseModel):
    position: Position = Field(default_factory=Position)
    orientation: Orientation = Field(default_factory=Orientation)
    velocity: Velocity = Field(default_factory=Velocity)
    timestamp: float = Field(default_factory=time.time)
    frame_id: str = "world_enu"


class BatteryStatus(BaseModel):
    percentage: float = 100.0
    voltage_v: float = 16.8
    current_a: float = 0.0
    healthy: bool = True


class GPSStatus(BaseModel):
    fix_type: str = "SIM_GROUND_TRUTH"  # e.g. "NO_FIX", "FIX_2D", "FIX_3D", "SIM_GROUND_TRUTH"
    satellites: int = 12
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    valid: bool = True


class VehicleState(BaseModel):
    connected: bool = False
    armed: bool = False
    flight_mode: str = "MANUAL"  # e.g. "MANUAL", "POSCTL", "ALTCTL", "OFFBOARD", "LAND", "SIMULATION"
    landed: bool = True
    vehicle_type: str = "quadcopter"
    status_text: str = "READY"


class SensorHealth(BaseModel):
    imu: str = "NOMINAL"       # "NOMINAL", "DEGRADED", "FAIL", "DISCONNECTED"
    camera: str = "NOMINAL"
    mag: str = "NOMINAL"
    baro: str = "NOMINAL"
    lidar: str = "N/A"


class CameraTelemetry(BaseModel):
    state: str = "IDLE"        # "IDLE", "CONNECTING", "ACTIVE", "ERROR", "DISCONNECTED"
    source: str = "none"       # "gazebo", "synthetic", "webcam", "file"
    width: int = 640
    height: int = 360
    fps: float = 0.0
    frames_captured: int = 0
    frames_streamed: int = 0
    error: Optional[str] = None


class PerformanceMetrics(BaseModel):
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    capture_fps: float = 0.0
    stream_fps: float = 0.0
    telemetry_hz: float = 0.0
    latency_ms: float = 0.0


class TrajectoryPoint(BaseModel):
    x: float
    y: float
    z: float
    timestamp: float


class TelemetryFrame(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    simulator: str = "none"    # "gazebo", "px4", "blender", "mock", "none"
    connection_state: str = "DISCONNECTED"  # "IDLE", "CONNECTING", "CONNECTED", "DEGRADED", "DISCONNECTED", "ERROR"
    pose: Pose = Field(default_factory=Pose)
    vehicle: VehicleState = Field(default_factory=VehicleState)
    battery: BatteryStatus = Field(default_factory=BatteryStatus)
    gps: GPSStatus = Field(default_factory=GPSStatus)
    sensors: SensorHealth = Field(default_factory=SensorHealth)
    camera: CameraTelemetry = Field(default_factory=CameraTelemetry)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    trajectory: List[TrajectoryPoint] = Field(default_factory=list)
    components: Dict[str, str] = Field(default_factory=dict)
    active_topics: List[str] = Field(default_factory=list)
    diagnostic_messages: List[str] = Field(default_factory=list)


class SimulationInfo(BaseModel):
    simulator_name: str = "none"
    version: str = "unknown"
    world_name: str = "default"
    model_name: str = "quadcopter"
    connected: bool = False
    state: str = "IDLE"
    active_topics: List[str] = Field(default_factory=list)
    available_worlds: List[str] = Field(default_factory=list)
    available_models: List[str] = Field(default_factory=list)
    error: Optional[str] = None
