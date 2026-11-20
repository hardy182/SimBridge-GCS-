"""Integration tests validating live system tool detection and environment."""

import shutil
import site
import subprocess
from simbridge.core.detector import EnvironmentDetector


def test_live_gazebo_installation():
    gz_bin = shutil.which("gz")
    assert gz_bin is not None
    info = EnvironmentDetector.detect_gazebo()
    assert info.installed is True


def test_live_gazebo_python_bindings_import():
    site.addsitedir("/usr/lib/python3/dist-packages")
    from gz.transport import Node
    from gz.msgs.image_pb2 import Image
    from gz.msgs.pose_v_pb2 import Pose_V

    node = Node()
    assert node is not None


def test_live_blender_installation():
    blender_bin = shutil.which("blender")
    assert blender_bin is not None
    info = EnvironmentDetector.detect_blender()
    assert info.installed is True
    assert "Blender" in (info.version or "")


def test_live_px4_directory():
    info = EnvironmentDetector.detect_px4()
    assert info.installed is True
    assert "PX4-Autopilot" in (info.path or "")
