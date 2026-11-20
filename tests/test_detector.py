"""Unit tests for tool discovery and environment detection."""

from simbridge.core.detector import EnvironmentDetector, SystemEnvironment, ToolInfo


def test_gazebo_detection():
    gz = EnvironmentDetector.detect_gazebo()
    assert isinstance(gz, ToolInfo)
    assert gz.name == "Gazebo Sim"
    # Gazebo binary was verified on system
    assert gz.installed is True
    assert gz.path is not None


def test_blender_detection():
    blender = EnvironmentDetector.detect_blender()
    assert isinstance(blender, ToolInfo)
    assert blender.name == "Blender"
    # Blender binary was verified on system
    assert blender.installed is True


def test_px4_detection():
    px4 = EnvironmentDetector.detect_px4()
    assert isinstance(px4, ToolInfo)
    assert px4.name == "PX4 SITL"
    # PX4 directory is present at /home/harshdeep-singh/PX4-Autopilot
    assert px4.installed is True


def test_gazebo_python_bindings_check():
    has_bindings = EnvironmentDetector.check_gazebo_bindings()
    assert has_bindings is True


def test_detect_all():
    env = EnvironmentDetector.detect_all()
    assert isinstance(env, SystemEnvironment)
    assert "gazebo" in env.tools
    assert "px4" in env.tools
    assert "blender" in env.tools
    assert env.gazebo_bindings_available is True
