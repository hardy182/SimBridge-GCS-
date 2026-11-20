# SimBridge GCS — System Architecture

## 1. High-Level Design

SimBridge GCS provides a decoupled monitoring and integration layer for open-source robotics simulation:

```
+-----------------------------------------------------------+
|                   SimBridge GCS Web UI                    |
|   (Dark Aerospace Theme, Attitude Horizon, Map, Stream)   |
+-----------------------------------------------------------+
                              ^
            WebSocket (20 Hz) | MJPEG (/video_feed) | REST
                              v
+-----------------------------------------------------------+
|                     FastAPI Backend                       |
|          ConnectionManager & LatestFrameBuffer            |
+-----------------------------------------------------------+
                              |
      +-----------------------+-----------------------+
      |                       |                       |
      v                       v                       v
+---------------+     +---------------+     +---------------+
| GazeboAdapter |     |  PX4Adapter   |     |BlenderAdapter |
| (gz.transport)|     |   (MAVLink)   |     |(Asset Pipeline|
+---------------+     +---------------+     +---------------+
      |                       |                       |
      v                       v                       v
 Gazebo Sim              PX4 SITL             3D Assets (.blend)
```

## 2. Core Subsystems

### 2.1 Connection Manager
The `ConnectionManager` dynamically handles adapter lifecycles. Users can switch between Gazebo Sim, PX4 SITL, Blender 3D, and Mock Simulation without restarting the server process.

### 2.2 Telemetry Ingestion Contract
Normalized telemetry (`TelemetryFrame`) isolates the frontend from simulator-specific wire formats:
- Position & Orientation: ENU coordinate convention.
- Velocity: Linear ($v_x, v_y, v_z$) and angular rates.
- System State: Armed status, custom flight modes, battery level, GPS fix.
- Sensor Health: Status indicators for IMU, camera, and ancillary sensors.

### 2.3 Video Pipeline
- `LatestFrameBuffer`: Lock-protected condition variable decoupling camera producers from MJPEG consumers.
- Gazebo Transport decoding: Direct multi-format pixel conversion (`RGB_INT8`, `BGR_INT8`, `RGBA_INT8`, `BGRA_INT8`, `L_INT8`).
- HUD Overlay: Monotonic sequence indexing, capture rate, and telemetry indicators rendered onto video frames.
