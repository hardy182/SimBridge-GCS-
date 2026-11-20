# SimBridge GCS — Source Repository Extraction Audit

**Target System:** SimBridge GCS (Standalone Open-Source Robotics Simulation Dashboard)  
**Source Repository:** `/home/harshdeep-singh/GPS Den FF/GPS-denied-full-fledge/`  
**Destination Repository:** `/home/harshdeep-singh/Projects/SimBridge-GCS/`  
**Audit Date:** November 2026  
**Status:** Complete & Verified  

---

## 1. Executive Summary

This audit assesses the software assets in the GPS-DENIED quadcopter research repository to extract and generalize its real-time telemetry dashboard, video streaming subsystem, and simulation adapters into **SimBridge GCS**—an independent, modular open-source monitoring platform for Gazebo Sim, PX4 SITL, and Blender 3D asset workflows.

The source repository contains a functional FastAPI backend and HTML GCS interface alongside extensive project-specific autonomy algorithms (visual odometry, YOLO tactical classification, factor graph pose optimization, obstacle avoidance, and A* trajectory planning). The audit identifies components that are production-ready and reusable, separates them from autonomy code that must be excluded, and outlines the target standalone architecture.

---

## 2. Key Component Investigation

### 2.1 `python/dashboard_html.py`
- **Current Role:** Provides a single-file HTML5/CSS3/JavaScript aerospace dashboard served directly by FastAPI.
- **Visual Design:** Dark aerospace theme (`#0b1220` background, `#111827` panels, `#24304a` borders, `#3b82f6` accents).
- **Core Elements:**
  - Status bar with operating mode, Gazebo/PX4/Vehicle health pills, and collapsible event log.
  - Primary flight display: Attitude artificial horizon (roll/pitch gyro), altitude, linear velocity, position vector.
  - Camera viewport: Live MJPEG stream (`/video_feed`), status badges, resolution/FPS metrics, source switcher.
  - 2D Canvas Map: Real-time trajectory plotting, path overlays, obstacle points, and vehicle heading indicator.
  - Diagnostics & latency panel: CPU, RAM, frame capture/stream counters, and pipeline timing.
  - Transport: Primary WebSocket connection (`/ws/telemetry`) with 10 Hz HTTP polling fallback (`/telemetry`) and 5s `/health` watchdog.
- **GPS-Denied Couplings to Remove:**
  - Hardcoded GPS-denied project branding and tactical combat references.
  - YOLO tactical target detection badges and class lists (`yoloTag`, `yoloList`, combat vehicle detections).
  - Specialized ESKF/VIO confidence metrics and loop closure drift counters (`pgoHealth`, `eskfConf`).
  - Tactical autonomous replanning indicators (`astarStatus`, `valEstErr`).
- **Verdict for SimBridge GCS:** **REUSABLE (Refactored)**. Retain the dark aerospace layout, telemetry horizon, camera viewport, canvas map, and communication fallbacks. Generalize indicators to support Gazebo, PX4 SITL, and Blender workflows with dynamic connection controls.

### 2.2 `python/main.py`
- **Current Role:** 1553-line monolith initializing camera drivers, YOLO perception models, ORB visual odometry, sensor hubs, FastAPI endpoints, and background capture threads.
- **Analysis:**
  - *Reusable subsystems:*
    - `LatestFrameBuffer`: Thread-safe condition-variable buffer providing snapshot isolation between camera producers and MJPEG consumers.
    - `mjpeg_generator`: High-throughput boundary-separated multipart JPEG generator with dynamic FPS calculation.
    - `/health`, `/telemetry`, `/video_feed`, and `/ws/telemetry` endpoint design and JSON sanitization.
    - Camera switching state management.
  - *Tightly coupled components (Exclude):*
    - YOLOv8 inference thread and tactical classifier initialization.
    - Visual Odometry (ORB feature tracking) and pose-graph optimization hooks.
    - Smartphone sensor bridge ingestion (`/api/phone_sensors`).
    - Autonomy control, MPC trajectory follower, and collision avoidance pipelines.
- **Verdict for SimBridge GCS:** **SELECTIVE EXTRACTION**. Do not copy `main.py`. Re-implement a modular FastAPI backend with clean routing, pluggable connection lifecycle management, and isolated background tasks.

### 2.3 `python/utils/video_source.py`
- **Current Role:** Camera source abstractions including synthetic image generators, local webcams, video files, and Gazebo Transport subscribers.
- **Analysis:**
  - `GazeboVideoSource`: Subscribes directly to Gazebo Transport using Python bindings (`gz.transport.Node`, `gz.msgs.image_pb2.Image`). Handles multi-format pixel decoding (`RGB_INT8`, `BGR_INT8`, `RGBA_INT8`, `BGRA_INT8`, `L_INT8`) into NumPy arrays without process spawning.
  - `SyntheticVideoSource` & `WebcamVideoSource`: Well-tested fallbacks for offline testing and camera streaming.
  - *System binding isolation:* Employs `site.addsitedir('/usr/lib/python3/dist-packages')` to load Ubuntu's Gazebo bindings at the end of `sys.path`, preventing virtualenv library shadowing (e.g. `typing_extensions`).
- **Verdict for SimBridge GCS:** **HIGHLY REUSABLE**. Port directly into `simbridge.core.video` and `simbridge.adapters.gazebo` with enhanced reconnection logic and customizable topic configuration.

### 2.4 `python/adapters/gazebo_vehicle_adapter.py`
- **Current Role:** Bridge to Gazebo physics, world state, and entity poses.
- **Analysis:**
  - Subscribes to dynamic world pose topics (`/world/{world_name}/dynamic_pose/info` and `/pose/info`) via `gz.transport.Node` with a subprocess CLI fallback (`gz topic -e`).
  - Converts quaternion orientation `(w, x, y, z)` to Euler angles (roll, pitch, yaw) in degrees.
  - Tracks vehicle presence via timestamp watchdog (<3.0s window).
  - Contains legacy motor velocity actuators (`/command/motor_speed`) that are not needed for a passive monitoring dashboard.
- **Verdict for SimBridge GCS:** **REUSABLE WITH GENERALIZATION**. Separate passive monitoring from active control. Support runtime world discovery, model discovery, configurable partition names, and dynamic topic mapping.

### 2.5 Other Adapters (`mavlink_adapter.py`, `simulator_adapter.py`, `factory.py`)
- **`mavlink_adapter.py`:**
  - Uses `pymavlink.mavutil` to parse MAVLink streams (`ATTITUDE`, `SYS_STATUS`, `GPS_RAW_INT`, `LOCAL_POSITION_NED`).
  - Working baseline for PX4 SITL communication. Needs expansion for flight mode decoding (armed/disarmed, NAV_STATE, LAND, POSCTL, OFFBOARD) and robust connection heartbeat recovery.
- **`simulator_adapter.py`:**
  - Simple wrapper around synthetic video source with simulated battery degradation. Useful pattern for mock testing.
- **`factory.py`:**
  - Adapter instantiation factory based on dictionary configuration. Needs replacement with a typed `ConnectionManager` supporting runtime profile switching without server restarts.

---

## 3. Classification of Existing Components

| Component | Status in Source Repo | SimBridge GCS Action | Rationale |
|---|---|---|---|
| Dark UI & CSS theme | Verified & Active | **Port & Modernize** | Established, clean aerospace aesthetic suited for simulation GCS |
| Camera MJPEG Streamer | Verified & Active | **Extract into Core** | Latency-optimized multipart streaming with zero-copy snapshot buffer |
| Gazebo Transport Video Subscriber | Verified & Active | **Extract into Gazebo Adapter** | Direct C++ protobuf binding with multi-pixel-format conversion |
| Gazebo Pose Subscriber | Verified & Active | **Extract into Gazebo Adapter** | Multi-topic world pose extraction with Euler conversion |
| MAVLink Receiver | Partially Verified | **Refactor into PX4 Adapter** | Basic packet listening functional; requires SITL flight mode & status decoding |
| YOLOv8 Object Classifier | Verified & Active | **Exclude** | Autonomy/tactical target perception; not part of general simulation monitor |
| Visual Odometry (ORB) | Verified & Active | **Exclude** | Complex autonomy stack; simulator ground truth is primary in monitoring |
| Phone Sensor Bridge | Prototype | **Exclude** | Hardware research prototype irrelevant to standard simulation workflows |
| Factor Graph SLAM / PGO | Verified & Active | **Exclude** | Specific to GPS-denied state estimation; high compute overhead |
| Motor Command Publisher | Prototype | **Exclude** | GCS is passive/monitoring by design; prevents accidental flight commands |

---

## 4. Required Data Contracts & Schemas

SimBridge GCS defines normalized data contracts decoupling the dashboard UI from specific simulator transport protocols:

1. **`SimulatorState`**:
   - Connection status (`IDLE`, `CONNECTING`, `CONNECTED`, `DEGRADED`, `DISCONNECTED`, `ERROR`).
   - Active adapter type (`gazebo`, `px4`, `blender`, `mock`).
   - Sim time, real-time factor (RTF), and tick latency.
2. **`VehiclePose`**:
   - Position: `(x, y, z)` in meters (ENU / NED converted to standard ENU visualization).
   - Orientation: Euler angles `(roll, pitch, yaw)` in degrees and quaternion `(w, x, y, z)`.
   - Linear and angular velocities: `(vx, vy, vz)` m/s, `(wx, wy, wz)` deg/s.
3. **`VehicleState`**:
   - Armed status, flight mode (e.g. `MANUAL`, `ALTCTL`, `POSCTL`, `AUTO`, `OFFBOARD`).
   - Battery remaining percentage and voltage.
   - GPS fix status / satellite count (or simulated GPS state).
4. **`EnvironmentDiagnostics`**:
   - Discovered Gazebo topics, worlds, models, and sensors.
   - Host resource usage: CPU %, RAM usage (MB), capture FPS, stream FPS.
   - Camera metrics: resolution, active source, frame sequence counter.

---

## 5. Architectural Strategy for SimBridge GCS

1. **No-Code Web UI:** Users select a simulator target, choose pre-configured profiles or override connection strings/topics via UI modal, and connect/disconnect dynamically without editing source code.
2. **Pluggable Adapter Model:** Standard abstract base class `BaseSimulatorAdapter` allowing any simulation backend to supply normalized telemetry and video.
3. **Environment Isolation:** Standalone Python virtual environment (`.venv`), modern `pyproject.toml`, clean `requirements.txt`, setup scripts, and self-contained test harnesses.
4. **Safety-First Architecture:** Pure monitoring and diagnostic inspection with no automatic command transmission or arming capabilities.
5. **Clear Separation of Blender:** Documented and verified as a 3D asset modeling, collision hull generation, and visual world creation pipeline, with a dedicated inspection interface rather than a physics engine.

---

## 6. Audit Conclusion

The GPS-DENIED repository contains robust, verified low-level components for Gazebo Transport image decoding, pose streaming, and MJPEG broadcasting. Extracting these into a dedicated, unbundled architecture while excising tactical autonomy modules produces a fast, lightweight, and extensible simulation monitoring platform.
