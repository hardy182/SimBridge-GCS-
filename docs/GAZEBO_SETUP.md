# SimBridge GCS — Gazebo Sim Integration Guide

## Supported Versions
- Gazebo Sim (Harmonic / Ionic / Fortress)
- Uses `gz.transport` Python bindings and CLI utilities.

## Discovery & Topic Mapping

### 1. Pose Telemetry Topics
SimBridge GCS subscribes to Gazebo dynamic and static pose vectors:
- Default Dynamic Pose: `/world/{world_name}/dynamic_pose/info`
- Default Static Pose: `/world/{world_name}/pose/info`

### 2. Camera Sensor Integration
Add an SDF camera sensor to your robot model:
```xml
<sensor name="camera" type="camera">
  <always_on>1</always_on>
  <update_rate>30</update_rate>
  <topic>/camera/image</topic>
  <camera>
    <horizontal_fov>1.396</horizontal_fov>
    <image>
      <width>640</width>
      <height>360</height>
      <format>R8G8B8</format>
    </image>
  </camera>
</sensor>
```

### 3. Gazebo Partition Settings
If using custom partitions:
```bash
export GZ_PARTITION=my_custom_partition
```
SimBridge GCS automatically detects and honors `GZ_PARTITION`.
