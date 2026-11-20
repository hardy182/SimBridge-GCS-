# SimBridge GCS — Blender 3D Workflow Guide

## Role in the Pipeline
Blender serves as a 3D modeling, asset creation, and world geometry preparation environment. It is not a real-time physics simulator; instead, it generates the visual and collision meshes imported into Gazebo Sim.

## Exporting Models for Gazebo

### Recommended Formats
- **GLTF / GLB (`.glb`)**: Preferred format for modern Gazebo PBR materials and compact distribution.
- **Collada (`.dae`)**: Supported for textured visual meshes.
- **STL / OBJ**: Suitable for simplified collision hulls.

### Preparation Checklist
1. **Coordinate System**: Ensure `+Z` is Up and `+X` is Forward.
2. **Scale & Units**: Apply all transforms (`Ctrl+A` -> Apply All Transforms) with Metric units ($1.0 \text{ unit} = 1.0 \text{ meter}$).
3. **Collision Simplification**: Use convex collision hulls rather than high-poly render meshes.
4. **Origin Alignment**: Place the object origin at the vehicle Center of Mass (CoM).

## SDF Model Inclusion Example
```xml
<visual name="visual">
  <geometry>
    <mesh>
      <uri>model://my_robot/meshes/visual.glb</uri>
    </mesh>
  </geometry>
</visual>
<collision name="collision">
  <geometry>
    <mesh>
      <uri>model://my_robot/meshes/collision.stl</uri>
    </mesh>
  </geometry>
</collision>
```
