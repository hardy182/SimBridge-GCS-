"""PX4 SITL MAVLink Adapter for SimBridge GCS."""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Dict, List, Optional
from pymavlink import mavutil
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
from simbridge.core.video import BaseVideoSource, SyntheticVideoSource, WebcamVideoSource

# PX4 Custom Main Modes
PX4_CUSTOM_MAIN_MODES = {
    1: "MANUAL",
    2: "ALTCTL",
    3: "POSCTL",
    4: "AUTO",
    5: "ACRO",
    6: "OFFBOARD",
    7: "STABILIZED",
    8: "RATTITUDE",
}

# PX4 Auto Sub-modes
PX4_CUSTOM_SUB_MODES_AUTO = {
    1: "AUTO_READY",
    2: "AUTO_TAKEOFF",
    3: "AUTO_LOITER",
    4: "AUTO_MISSION",
    5: "AUTO_RTL",
    6: "AUTO_LAND",
    7: "AUTO_RTGS",
    8: "AUTO_FOLLOW_TARGET",
    9: "AUTO_PRECLAND",
}


def decode_px4_mode(custom_mode: int) -> str:
    """Decode PX4 custom mode bitmask into human-readable flight mode string."""
    main_mode = (custom_mode >> 16) & 0xFF
    sub_mode = (custom_mode >> 24) & 0xFF

    if main_mode == 4:  # AUTO
        return PX4_CUSTOM_SUB_MODES_AUTO.get(sub_mode, "AUTO")
    return PX4_CUSTOM_MAIN_MODES.get(main_mode, f"MODE_{main_mode}")


class PX4Adapter(BaseSimulatorAdapter):
    """Interfaces with PX4 SITL over MAVLink."""

    def __init__(self, name: str = "px4", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self.connection_string = str(self.config.get("connection", "udp:127.0.0.1:14550")).strip()
        self.baud = int(self.config.get("baud", 57600))
        self.heartbeat_timeout_s = float(self.config.get("heartbeat_timeout_s", 3.0))
        self.camera_source_type = str(self.config.get("camera_source", "synthetic")).strip()

        self._master: Optional[mavutil.mavfile] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._listen_thread: Optional[threading.Thread] = None
        self._last_heartbeat_time = 0.0

        # Telemetry cache
        self._pose = Pose()
        self._battery = BatteryStatus()
        self._gps = GPSStatus()
        self._vehicle_state = VehicleState()
        self._sensor_health = SensorHealth()
        self._trajectory: List[TrajectoryPoint] = []
        self._max_traj_points = 300
        self.video_source: Optional[BaseVideoSource] = None

    def connect(self) -> bool:
        self._connection_state = "CONNECTING"
        self._stop_event.clear()

        try:
            print(f"[PX4] Connecting to MAVLink endpoint: {self.connection_string}...")
            self._master = mavutil.mavlink_connection(self.connection_string, baud=self.baud)
            # Non-blocking or short-timeout check
            hb = self._master.wait_heartbeat(timeout=1.5)
            if hb:
                self._last_heartbeat_time = time.time()
                self._connected = True
                self._connection_state = "CONNECTED"
                print("[PX4] Heartbeat received! System active.")
            else:
                # Still start listener thread in case SITL starts up right after
                self._connected = True
                self._connection_state = "CONNECTING"
                print("[PX4] Connection established; waiting for initial heartbeat...")

            # Start background message listener
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True, name="px4-mavlink-rx")
            self._listen_thread.start()

            # Initialize camera source
            if self.camera_source_type == "webcam":
                self.video_source = WebcamVideoSource(device_index=0, width=640, height=360)
            elif self.camera_source_type != "none":
                self.video_source = SyntheticVideoSource(width=640, height=360, fps=30.0)

            return True
        except Exception as e:
            self._last_error = f"MAVLink connection error: {e}"
            self._connection_state = "ERROR"
            self._connected = False
            return False

    def _listen_loop(self) -> None:
        """Background thread reading incoming MAVLink packets."""
        while not self._stop_event.is_set():
            if not self._master:
                time.sleep(0.1)
                continue

            try:
                msg = self._master.recv_match(blocking=True, timeout=0.1)
                if not msg:
                    continue

                msg_type = msg.get_type()
                now = time.time()

                with self._lock:
                    if msg_type == "HEARTBEAT":
                        self._last_heartbeat_time = now
                        self._connected = True
                        self._connection_state = "CONNECTED"

                        # Decode armed status
                        armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                        mode_str = decode_px4_mode(msg.custom_mode)
                        self._vehicle_state.armed = armed
                        self._vehicle_state.flight_mode = mode_str
                        self._vehicle_state.connected = True
                        self._vehicle_state.status_text = "ARMED" if armed else "DISARMED"

                    elif msg_type == "ATTITUDE":
                        # roll, pitch, yaw in radians -> convert to degrees
                        r = math.degrees(msg.roll)
                        p = math.degrees(msg.pitch)
                        y = (math.degrees(msg.yaw) + 360.0) % 360.0

                        self._pose.orientation.roll = round(r, 2)
                        self._pose.orientation.pitch = round(p, 2)
                        self._pose.orientation.yaw = round(y, 2)
                        self._pose.velocity.roll_rate = round(math.degrees(msg.rollspeed), 2)
                        self._pose.velocity.pitch_rate = round(math.degrees(msg.pitchspeed), 2)
                        self._pose.velocity.yaw_rate = round(math.degrees(msg.yawspeed), 2)
                        self._pose.timestamp = now

                    elif msg_type == "LOCAL_POSITION_NED":
                        # Convert NED (North-East-Down) to standard ENU (East-North-Up)
                        # East = y, North = x, Up = -z
                        enu_x = float(msg.y)
                        enu_y = float(msg.x)
                        enu_z = float(-msg.z)

                        self._pose.position.x = round(enu_x, 3)
                        self._pose.position.y = round(enu_y, 3)
                        self._pose.position.z = round(enu_z, 3)

                        self._pose.velocity.vx = round(float(msg.vy), 2)
                        self._pose.velocity.vy = round(float(msg.vx), 2)
                        self._pose.velocity.vz = round(float(-msg.vz), 2)
                        self._pose.timestamp = now

                        self._trajectory.append(TrajectoryPoint(x=enu_x, y=enu_y, z=enu_z, timestamp=now))
                        if len(self._trajectory) > self._max_traj_points:
                            self._trajectory.pop(0)

                    elif msg_type == "SYS_STATUS":
                        batt_rem = msg.battery_remaining
                        volt = msg.voltage_battery / 1000.0 if msg.voltage_battery != -1 else 16.8
                        curr = msg.current_battery / 100.0 if msg.current_battery != -1 else 0.0

                        self._battery.percentage = float(batt_rem) if batt_rem != -1 else 100.0
                        self._battery.voltage_v = round(volt, 2)
                        self._battery.current_a = round(curr, 2)
                        self._battery.healthy = (self._battery.percentage > 15.0)

                    elif msg_type == "GPS_RAW_INT":
                        fix = msg.fix_type
                        fix_names = {
                            0: "NO_GPS",
                            1: "NO_FIX",
                            2: "FIX_2D",
                            3: "FIX_3D",
                            4: "DGPS",
                            5: "RTK_FLOAT",
                            6: "RTK_FIXED",
                        }
                        self._gps.fix_type = fix_names.get(fix, f"FIX_{fix}")
                        self._gps.satellites = int(msg.satellites_visible)
                        self._gps.lat = float(msg.lat) / 1e7
                        self._gps.lon = float(msg.lon) / 1e7
                        self._gps.alt = float(msg.alt) / 1000.0
                        self._gps.valid = (fix >= 2)

                    elif msg_type == "HIGHRES_IMU":
                        self._sensor_health.imu = "NOMINAL"
                        self._sensor_health.mag = "NOMINAL"
                        self._sensor_health.baro = "NOMINAL"

            except Exception:
                time.sleep(0.05)

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._listen_thread:
            self._listen_thread.join(timeout=1.5)
            self._listen_thread = None

        if self._master:
            try:
                self._master.close()
            except Exception:
                pass
            self._master = None

        if self.video_source:
            self.video_source.release()
            self.video_source = None

        self._connected = False
        self._connection_state = "DISCONNECTED"

    def get_video_source(self) -> Optional[BaseVideoSource]:
        return self.video_source

    def is_connected(self) -> bool:
        if not self._connected or not self._master:
            return False
        # Check heartbeat staleness
        return (time.time() - self._last_heartbeat_time) < self.heartbeat_timeout_s

    def get_telemetry(self) -> TelemetryFrame:
        now = time.time()
        alive = self.is_connected()

        with self._lock:
            pose = self._pose
            veh = self._vehicle_state
            batt = self._battery
            gps = self._gps
            sens = self._sensor_health
            traj = list(self._trajectory)

        cam_telemetry = CameraTelemetry(
            state="ACTIVE" if self.video_source and self.video_source.is_opened() else "IDLE",
            source=self.camera_source_type,
            width=640,
            height=360,
            fps=30.0 if self.video_source else 0.0,
        )

        components = {
            "backend": "CONNECTED",
            "simulator": "CONNECTED" if alive else "WAITING_HEARTBEAT",
            "vehicle": "ONLINE" if alive else "OFFLINE",
            "camera": "ACTIVE" if self.video_source else "OFFLINE",
            "stream": "ACTIVE",
        }

        return TelemetryFrame(
            timestamp=now,
            simulator="px4",
            connection_state="CONNECTED" if alive else "CONNECTING",
            pose=pose,
            vehicle=veh,
            battery=batt,
            gps=gps,
            sensors=sens,
            camera=cam_telemetry,
            performance=PerformanceMetrics(telemetry_hz=20.0),
            trajectory=traj,
            components=components,
            active_topics=["MAVLINK_ATTITUDE", "MAVLINK_LOCAL_POSITION_NED", "MAVLINK_SYS_STATUS", "MAVLINK_GPS_RAW_INT"],
            diagnostic_messages=[
                f"Endpoint: {self.connection_string}",
                f"Flight Mode: {veh.flight_mode}",
                f"Armed: {veh.armed}",
                f"Heartbeat Age: {now - self._last_heartbeat_time:.1f}s" if self._last_heartbeat_time > 0 else "Waiting for heartbeat",
            ],
        )

    def get_info(self) -> SimulationInfo:
        return SimulationInfo(
            simulator_name="PX4 SITL",
            version="MAVLink 2.0",
            world_name="SITL Default",
            model_name="x500_quad",
            connected=self.is_connected(),
            state=self._connection_state,
            active_topics=["HEARTBEAT", "ATTITUDE", "LOCAL_POSITION_NED", "SYS_STATUS", "GPS_RAW_INT"],
            available_worlds=["default", "baylands", "empty"],
            available_models=["x500", "standard_vtol", "plane"],
            error=self._last_error,
        )
