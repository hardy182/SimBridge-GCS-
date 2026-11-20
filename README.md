# SimBridge GCS

A lightweight, standalone Ground Control Station (GCS) and robotics simulation monitor for **Gazebo Sim**, **PX4 SITL**, and **Blender 3D** workflows.

---

## Features

- **Dark Aerospace Dashboard**: Real-time artificial horizon, altitude, velocity vectors, battery indicators, and 2D trajectory tracking.
- **Gazebo Sim Integration**: Connects via native `gz.transport` C++ Python bindings to ingest high-rate dynamic pose vectors and decode multi-format camera streams.
- **PX4 SITL Integration**: MAVLink telemetry decoder mapping NED local coordinates to ENU, vehicle armed states, and flight modes without sending hazardous arming commands.
- **Blender 3D Asset Support**: Environment tool detection and model workflow guidance for Gazebo visual/collision meshes.
- **Low-Latency Video**: MJPEG boundary-separated camera stream (`/video_feed`) with thread-safe snapshot isolation and aerospace HUD overlay.
- **No-Code Web UI Setup**: Built-in modal detects installed robotics packages and switches active simulation profiles dynamically.

---

## Quick Start

### 1. Run Setup Script
```bash
./setup.sh
```

### 2. Launch the Dashboard
```bash
./run.sh
```
Then visit **http://localhost:8050** in your browser.

---

## Running Tests
```bash
source .venv/bin/activate
pytest tests -v
```

---

## Documentation
- [System Architecture](docs/ARCHITECTURE.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Gazebo Sim Setup](docs/GAZEBO_SETUP.md)
- [PX4 SITL Setup](docs/PX4_SETUP.md)
- [Blender Workflow](docs/BLENDER_WORKFLOW.md)
