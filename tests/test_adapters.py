"""Unit tests for simulator adapter implementations and lifecycle."""

import math
from simbridge.adapters.base import BaseSimulatorAdapter
from simbridge.adapters.blender import BlenderAdapter
from simbridge.adapters.factory import create_adapter
from simbridge.adapters.gazebo import GazeboAdapter
from simbridge.adapters.mock import MockSimulatorAdapter
from simbridge.adapters.px4 import PX4Adapter, decode_px4_mode
from simbridge.core.contracts import TelemetryFrame


def test_factory_creation():
    mock_ad = create_adapter("mock")
    assert isinstance(mock_ad, MockSimulatorAdapter)
    assert mock_ad.name == "mock"

    gz_ad = create_adapter("gazebo", {"gazebo": {"world_name": "my_world"}})
    assert isinstance(gz_ad, GazeboAdapter)
    assert gz_ad.world_name == "my_world"

    px4_ad = create_adapter("px4", {"px4": {"connection": "udp:127.0.0.1:14550"}})
    assert isinstance(px4_ad, PX4Adapter)
    assert px4_ad.connection_string == "udp:127.0.0.1:14550"

    blender_ad = create_adapter("blender")
    assert isinstance(blender_ad, BlenderAdapter)


def test_mock_adapter_lifecycle():
    adapter = MockSimulatorAdapter(config={"speed": 2.0, "altitude": 5.0})
    assert adapter.is_connected() is False

    ok = adapter.connect()
    assert ok is True
    assert adapter.is_connected() is True
    assert adapter.connection_state == "CONNECTED"

    # Telemetry check
    telemetry = adapter.get_telemetry()
    assert isinstance(telemetry, TelemetryFrame)
    assert telemetry.simulator == "mock"
    assert telemetry.connection_state == "CONNECTED"
    assert telemetry.pose.position.z >= 4.0  # Around altitude 5.0

    # Video source check
    vsrc = adapter.get_video_source()
    assert vsrc is not None
    assert vsrc.is_opened() is True

    frame, meta = vsrc.read()
    assert frame is not None
    assert frame.shape == (360, 640, 3)

    # Disconnect
    adapter.disconnect()
    assert adapter.is_connected() is False
    assert adapter.connection_state == "DISCONNECTED"


def test_gazebo_euler_conversion():
    # Test yaw 90 degrees: w = cos(45) = 0.7071, z = sin(45) = 0.7071
    w = math.cos(math.radians(45))
    z = math.sin(math.radians(45))
    r, p, y = GazeboAdapter._quat_to_euler(w, 0.0, 0.0, z)
    assert abs(r) < 0.1
    assert abs(p) < 0.1
    assert abs(y - 90.0) < 0.1

    # Test pitch 30 degrees
    w = math.cos(math.radians(15))
    y_q = math.sin(math.radians(15))
    r, p, y = GazeboAdapter._quat_to_euler(w, 0.0, y_q, 0.0)
    assert abs(p - 30.0) < 0.1


def test_px4_flight_mode_decoding():
    # Main mode 1: MANUAL (1 << 16 = 65536)
    assert decode_px4_mode(1 << 16) == "MANUAL"
    # Main mode 2: ALTCTL (2 << 16 = 131072)
    assert decode_px4_mode(2 << 16) == "ALTCTL"
    # Main mode 3: POSCTL (3 << 16 = 196608)
    assert decode_px4_mode(3 << 16) == "POSCTL"
    # Main mode 4, sub-mode 4: AUTO_MISSION ((4 << 16) | (4 << 24))
    assert decode_px4_mode((4 << 16) | (4 << 24)) == "AUTO_MISSION"


def test_blender_adapter_inspection():
    adapter = BlenderAdapter()
    ok = adapter.connect()
    assert ok is True
    assert adapter.is_connected() is True

    info = adapter.get_info()
    assert info.simulator_name == "Blender 3D Asset Pipeline"

    telemetry = adapter.get_telemetry()
    assert telemetry.simulator == "blender"
    assert telemetry.vehicle.flight_mode == "ASSET_INSPECTION"

    adapter.disconnect()
    assert adapter.is_connected() is False
