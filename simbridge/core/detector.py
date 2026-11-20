"""Environment and installed simulation tooling detection."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    name: str
    installed: bool = False
    path: Optional[str] = None
    version: Optional[str] = None
    running: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemEnvironment(BaseModel):
    python_version: str
    python_path: str
    in_virtualenv: bool
    gazebo_bindings_available: bool
    tools: Dict[str, ToolInfo] = Field(default_factory=dict)
    active_processes: List[Dict[str, Any]] = Field(default_factory=list)


class EnvironmentDetector:
    """Discovers installed robotics tools and active simulator processes."""

    @staticmethod
    def detect_gazebo() -> ToolInfo:
        info = ToolInfo(name="Gazebo Sim")
        gz_bin = shutil.which("gz")
        if gz_bin:
            info.installed = True
            info.path = gz_bin
            try:
                res = subprocess.run(
                    [gz_bin, "sim", "--versions"],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                )
                if res.returncode == 0 and res.stdout.strip():
                    info.version = res.stdout.strip().splitlines()[0]
                else:
                    info.version = "Harmonic/Ionic"
            except Exception:
                info.version = "Installed (gz CLI)"

            # Check if gz sim process is running
            running_procs = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if "gz" in proc.info.get("name", "") or "gz sim" in cmdline or "ign gazebo" in cmdline:
                        running_procs.append({"pid": proc.info["pid"], "cmdline": cmdline[:80]})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            info.running = len(running_procs) > 0
            info.details["running_processes"] = running_procs

            # Check Gazebo Transport topics if available
            try:
                t_res = subprocess.run(
                    [gz_bin, "topic", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if t_res.returncode == 0:
                    topics = [t.strip() for t in t_res.stdout.splitlines() if t.strip()]
                    info.details["active_topics"] = topics
                    info.details["topic_count"] = len(topics)
            except Exception:
                info.details["active_topics"] = []
        return info

    @staticmethod
    def detect_px4() -> ToolInfo:
        info = ToolInfo(name="PX4 SITL")
        # Check standard PX4 installation directories
        home = Path.home()
        candidates = [
            home / "PX4-Autopilot",
            home / "src" / "PX4-Autopilot",
            Path("/opt/PX4-Autopilot"),
        ]

        found_dir: Optional[Path] = None
        for cand in candidates:
            if cand.exists() and (cand / "build" / "px4_sitl_default").exists():
                found_dir = cand
                break
            elif cand.exists():
                found_dir = cand

        if found_dir:
            info.installed = True
            info.path = str(found_dir)
            sitl_bin = found_dir / "build" / "px4_sitl_default" / "bin" / "px4"
            if sitl_bin.exists():
                info.version = "SITL Built (px4_sitl_default)"
                info.details["sitl_binary"] = str(sitl_bin)
            else:
                info.version = "Source repo (SITL build not compiled)"

        # Check running PX4 process
        running_procs = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if "px4" in proc.info.get("name", "").lower() or "px4_sitl" in cmd:
                    running_procs.append({"pid": proc.info["pid"], "cmdline": cmd[:80]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        info.running = len(running_procs) > 0
        info.details["running_processes"] = running_procs
        return info

    @staticmethod
    def detect_blender() -> ToolInfo:
        info = ToolInfo(name="Blender")
        blender_bin = shutil.which("blender")
        if blender_bin:
            info.installed = True
            info.path = blender_bin
            try:
                res = subprocess.run(
                    [blender_bin, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
                if res.stdout:
                    first_line = res.stdout.strip().splitlines()[0]
                    info.version = first_line
            except Exception:
                info.version = "Installed (CLI)"

        # Check running Blender process
        running_procs = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if "blender" in proc.info.get("name", "").lower():
                    running_procs.append({"pid": proc.info["pid"], "cmdline": cmd[:80]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        info.running = len(running_procs) > 0
        info.details["running_processes"] = running_procs
        return info

    @classmethod
    def check_gazebo_bindings(cls) -> bool:
        """Verify whether gz.transport and gz.msgs can be imported."""
        try:
            import site
            site.addsitedir("/usr/lib/python3/dist-packages")
            from gz.transport import Node  # noqa: F401
            from gz.msgs.image_pb2 import Image  # noqa: F401
            return True
        except Exception:
            return False

    @classmethod
    def detect_all(cls) -> SystemEnvironment:
        gz_info = cls.detect_gazebo()
        px4_info = cls.detect_px4()
        blender_info = cls.detect_blender()

        active_procs = []
        for p in (gz_info.details.get("running_processes", []) +
                  px4_info.details.get("running_processes", []) +
                  blender_info.details.get("running_processes", [])):
            active_procs.append(p)

        in_venv = (sys.prefix != sys.base_prefix) or ("VIRTUAL_ENV" in os.environ)

        return SystemEnvironment(
            python_version=sys.version.split()[0],
            python_path=sys.executable,
            in_virtualenv=in_venv,
            gazebo_bindings_available=cls.check_gazebo_bindings(),
            tools={
                "gazebo": gz_info,
                "px4": px4_info,
                "blender": blender_info,
            },
            active_processes=active_procs,
        )
