"""Unit tests for normalized telemetry contracts and schemas."""

import time
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


def test_pose_instantiation():
    pos = Position(x=1.2, y=-3.4, z=5.6)
    orient = Orientation(roll=10.0, pitch=-5.0, yaw=90.0)
    vel = Velocity(vx=1.0, vy=0.5, vz=-0.2)
    pose = Pose(position=pos, orientation=orient, velocity=vel)

    assert pose.position.x == 1.2
    assert pose.orientation.yaw == 90.0
    assert pose.velocity.vx == 1.0
    assert pose.frame_id == "world_enu"


def test_telemetry_frame_serialization():
    frame = TelemetryFrame(
        simulator="mock",
        connection_state="CONNECTED",
        pose=Pose(position=Position(x=10.0, y=20.0, z=30.0)),
        vehicle=VehicleState(connected=True, armed=True, flight_mode="AUTO"),
        battery=BatteryStatus(percentage=88.5, voltage_v=15.9),
        gps=GPSStatus(satellites=16, valid=True),
        sensors=SensorHealth(imu="NOMINAL", camera="NOMINAL"),
        trajectory=[TrajectoryPoint(x=1.0, y=2.0, z=3.0, timestamp=time.time())],
    )

    data = frame.model_dump()
    assert data["simulator"] == "mock"
    assert data["connection_state"] == "CONNECTED"
    assert data["pose"]["position"]["x"] == 10.0
    assert data["vehicle"]["armed"] is True
    assert data["battery"]["percentage"] == 88.5
    assert len(data["trajectory"]) == 1


def test_simulation_info():
    info = SimulationInfo(
        simulator_name="Gazebo Sim",
        version="10.6.0",
        world_name="baylands",
        model_name="quadcopter",
        connected=True,
        active_topics=["/world/baylands/dynamic_pose/info", "/camera/image"],
    )
    d = info.model_dump()
    assert d["simulator_name"] == "Gazebo Sim"
    assert len(d["active_topics"]) == 2
