"""Configuration system for SimBridge GCS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8050
    reload: bool = False
    log_level: str = "info"


class TelemetryConfig(BaseModel):
    rate_hz: float = 20.0
    history_size: int = 500
    stale_timeout_s: float = 3.0


class StreamConfig(BaseModel):
    enabled: bool = True
    width: int = 640
    height: int = 360
    jpeg_quality: int = 80
    target_fps: float = 30.0


class GazeboConfig(BaseModel):
    partition: str = ""
    world_name: str = "default"
    model_name: str = "quadcopter"
    dynamic_pose_topic: str = "/world/default/dynamic_pose/info"
    static_pose_topic: str = "/world/default/pose/info"
    camera_topic: str = "/camera/image"
    sub_timeout_s: float = 2.0


class PX4Config(BaseModel):
    connection: str = "udp:127.0.0.1:14550"
    baud: int = 57600
    system_id: int = 1
    component_id: int = 1
    heartbeat_timeout_s: float = 3.0
    camera_source: str = "synthetic"  # "synthetic", "webcam", "none"


class BlenderConfig(BaseModel):
    executable_path: str = "/usr/bin/blender"
    asset_dir: str = ""
    export_format: str = "gltf"


class MockConfig(BaseModel):
    pattern: str = "lissajous"
    speed: float = 1.0
    altitude: float = 3.5
    battery_drain_rate: float = 0.05
    camera_source: str = "synthetic"


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    stream: StreamConfig = Field(default_factory=StreamConfig)
    active_simulator: str = "mock"  # "none", "mock", "gazebo", "px4", "blender"
    gazebo: GazeboConfig = Field(default_factory=GazeboConfig)
    px4: PX4Config = Field(default_factory=PX4Config)
    blender: BlenderConfig = Field(default_factory=BlenderConfig)
    mock: MockConfig = Field(default_factory=MockConfig)


def get_default_config_path() -> Path:
    """Return default config path relative to package root."""
    base_dir = Path(__file__).resolve().parent.parent
    cfg_file = base_dir / "config" / "default.yaml"
    return cfg_file


def load_config(path: Optional[str | Path] = None) -> AppConfig:
    """Load configuration from a YAML file with fallback to defaults and env vars."""
    config_dict: Dict[str, Any] = {}

    target_path = Path(path) if path else get_default_config_path()
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_dict = loaded
        except Exception as e:
            print(f"[Config] Warning: Failed to parse {target_path}: {e}")

    # Environment variable overrides
    server_dict = config_dict.setdefault("server", {})
    if "SIMBRIDGE_HOST" in os.environ:
        server_dict["host"] = os.environ["SIMBRIDGE_HOST"]
    if "SIMBRIDGE_PORT" in os.environ:
        try:
            server_dict["port"] = int(os.environ["SIMBRIDGE_PORT"])
        except ValueError:
            pass

    if "SIMBRIDGE_DEFAULT_SIMULATOR" in os.environ:
        config_dict["active_simulator"] = os.environ["SIMBRIDGE_DEFAULT_SIMULATOR"]

    gz_dict = config_dict.setdefault("gazebo", {})
    if "GZ_PARTITION" in os.environ:
        gz_dict["partition"] = os.environ["GZ_PARTITION"]
    if "GAZEBO_CAMERA_TOPIC" in os.environ:
        gz_dict["camera_topic"] = os.environ["GAZEBO_CAMERA_TOPIC"]

    px4_dict = config_dict.setdefault("px4", {})
    if "PX4_MAVLINK_CONNECTION" in os.environ:
        px4_dict["connection"] = os.environ["PX4_MAVLINK_CONNECTION"]

    return AppConfig.model_validate(config_dict)


def save_config(config: AppConfig, path: str | Path) -> None:
    """Save an AppConfig instance to a YAML file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(), f, sort_keys=False)
