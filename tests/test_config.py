"""Unit tests for configuration validation and loading."""

import os
from pathlib import Path
import pytest
from simbridge.config import AppConfig, load_config, save_config


def test_default_config_loading():
    cfg = load_config()
    assert isinstance(cfg, AppConfig)
    assert cfg.server.port == 8050
    assert cfg.stream.width == 640
    assert cfg.stream.height == 360
    assert cfg.gazebo.model_name == "quadcopter"
    assert cfg.px4.baud == 57600


def test_custom_config_save_and_load(tmp_path: Path):
    custom_cfg = AppConfig()
    custom_cfg.server.port = 9050
    custom_cfg.active_simulator = "gazebo"
    custom_cfg.gazebo.world_name = "test_world"

    test_file = tmp_path / "custom.yaml"
    save_config(custom_cfg, test_file)
    assert test_file.exists()

    loaded = load_config(test_file)
    assert loaded.server.port == 9050
    assert loaded.active_simulator == "gazebo"
    assert loaded.gazebo.world_name == "test_world"


def test_env_var_overrides(monkeypatch):
    monkeypatch.setenv("SIMBRIDGE_PORT", "8888")
    monkeypatch.setenv("SIMBRIDGE_DEFAULT_SIMULATOR", "px4")
    monkeypatch.setenv("GAZEBO_CAMERA_TOPIC", "/uav/cam")

    cfg = load_config()
    assert cfg.server.port == 8888
    assert cfg.active_simulator == "px4"
    assert cfg.gazebo.camera_topic == "/uav/cam"
