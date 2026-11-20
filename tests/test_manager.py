"""Unit tests for ConnectionManager lifecycle, telemetry caching, and simulator switching."""

import time
from simbridge.config import AppConfig
from simbridge.core.contracts import TelemetryFrame
from simbridge.core.manager import ConnectionManager


def test_manager_initial_connection():
    cfg = AppConfig()
    cfg.active_simulator = "mock"
    manager = ConnectionManager(config=cfg)

    assert manager.active_adapter_type == "mock"
    assert manager.adapter is not None
    assert manager.adapter.is_connected() is True

    # Check status
    status = manager.get_status()
    assert status["active_simulator"] == "mock"
    assert status["connected"] is True
    assert status["state"] == "CONNECTED"

    # Give camera thread a moment to acquire frames
    time.sleep(0.1)
    frame, fid, ts, meta = manager.frame_buffer.get_latest()
    assert frame is not None

    manager.disconnect()
    assert manager.active_adapter_type == "none"
    assert manager.adapter is None


def test_manager_switching_simulators():
    cfg = AppConfig()
    cfg.active_simulator = "none"
    manager = ConnectionManager(config=cfg)

    # 1. Connect to mock
    ok1 = manager.connect("mock", {"mock": {"altitude": 4.0}})
    assert ok1 is True
    assert manager.active_adapter_type == "mock"
    t1 = manager.get_telemetry()
    assert t1.simulator == "mock"

    # 2. Switch to blender
    ok2 = manager.connect("blender")
    assert ok2 is True
    assert manager.active_adapter_type == "blender"
    t2 = manager.get_telemetry()
    assert t2.simulator == "blender"

    # 3. Disconnect
    manager.disconnect()
    assert manager.active_adapter_type == "none"
    t3 = manager.get_telemetry()
    assert t3.connection_state == "DISCONNECTED"
