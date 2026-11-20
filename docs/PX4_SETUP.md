# SimBridge GCS — PX4 SITL Integration Guide

## Overview
SimBridge GCS connects to PX4 Software-In-The-Loop (SITL) via MAVLink.

## Launching PX4 SITL
From your PX4-Autopilot repository:
```bash
cd ~/PX4-Autopilot
make px4_sitl gz_x500
```
This starts PX4 SITL broadcasting MAVLink packets on local UDP ports:
- Port `14550`: GCS default UDP port.
- Port `14540`: Offboard / API default port.

## Connecting in SimBridge GCS
1. Open the GCS Dashboard at `http://localhost:8000`.
2. Click **Connect / Setup**.
3. Select **PX4 SITL**.
4. Ensure the connection endpoint is set to `udp:127.0.0.1:14550`.
5. Click **Connect Simulator**.

## Monitored Telemetry
- Position (`LOCAL_POSITION_NED` converted to ENU)
- Attitude (`ATTITUDE`: Roll, Pitch, Yaw)
- Battery & System Status (`SYS_STATUS`)
- GPS Fix (`GPS_RAW_INT`)
- Flight Modes (Decoded from `HEARTBEAT` custom mode bits)
