"""Simulator connection manager and lifecycle orchestrator."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
import psutil
from simbridge.adapters.base import BaseSimulatorAdapter
from simbridge.adapters.factory import create_adapter
from simbridge.config import AppConfig
from simbridge.core.contracts import SimulationInfo, TelemetryFrame
from simbridge.core.video import LatestFrameBuffer


class ConnectionManager:
    """Manages simulator adapter lifecycle, background camera capture, and telemetry dispatch."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.active_adapter_type: str = "none"
        self.adapter: Optional[BaseSimulatorAdapter] = None
        self.frame_buffer = LatestFrameBuffer()

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._camera_thread: Optional[threading.Thread] = None
        self._last_telemetry: Optional[TelemetryFrame] = None
        self._cached_telemetry_time = 0.0

        # Performance monitoring
        self._proc = psutil.Process()
        self._stream_frames_served = 0
        self._capture_frames_count = 0
        self._last_fps_calc_time = time.perf_counter()
        self._calculated_capture_fps = 0.0

        # Auto-connect if initial simulator is configured
        initial_sim = self.config.active_simulator.lower()
        if initial_sim and initial_sim != "none":
            self.connect(initial_sim)

    def connect(self, simulator_type: str, custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """Connect to a designated simulator profile."""
        with self._lock:
            # Cleanly disconnect existing adapter first
            self._disconnect_internal()

            t = str(simulator_type).lower().strip()
            self.active_adapter_type = t

            merged_cfg = self.config.model_dump()
            if custom_config:
                if t in custom_config:
                    merged_cfg[t].update(custom_config[t])
                else:
                    merged_cfg[t].update(custom_config)

            self.adapter = create_adapter(t, merged_cfg)
            ok = self.adapter.connect()

            # Start camera producer thread
            self._stop_event.clear()
            self._camera_thread = threading.Thread(
                target=self._camera_producer_loop,
                daemon=True,
                name=f"simbridge-cam-{t}",
            )
            self._camera_thread.start()

            print(f"[ConnectionManager] Connected to {t} (success={ok})")
            return ok

    def disconnect(self) -> None:
        """Disconnect currently active simulator."""
        with self._lock:
            self._disconnect_internal()
            self.active_adapter_type = "none"

    def _disconnect_internal(self) -> None:
        self._stop_event.set()
        if self._camera_thread and self._camera_thread.is_alive():
            self._camera_thread.join(timeout=1.5)
            self._camera_thread = None

        if self.adapter:
            try:
                self.adapter.disconnect()
            except Exception as e:
                print(f"[ConnectionManager] Disconnect error: {e}")
            self.adapter = None

    def _camera_producer_loop(self) -> None:
        """Dedicated camera acquisition thread pacing reads and updating the frame buffer."""
        target_fps = float(self.config.stream.target_fps)
        target_dt = 1.0 / max(1.0, target_fps)
        frames_in_sec = 0

        while not self._stop_event.is_set():
            t0 = time.perf_counter()
            adapter = self.adapter
            if not adapter or not adapter.is_connected():
                time.sleep(0.1)
                continue

            v_src = adapter.get_video_source()
            if v_src and v_src.is_opened():
                try:
                    frame, meta = v_src.read()
                    if frame is not None:
                        self.frame_buffer.publish(frame, meta)
                        self._capture_frames_count += 1
                        frames_in_sec += 1
                except Exception as e:
                    time.sleep(0.05)

            now = time.perf_counter()
            elapsed_sec = now - self._last_fps_calc_time
            if elapsed_sec >= 1.0:
                self._calculated_capture_fps = frames_in_sec / elapsed_sec
                frames_in_sec = 0
                self._last_fps_calc_time = now

            dt = time.perf_counter() - t0
            if dt < target_dt:
                time.sleep(target_dt - dt)

    def get_telemetry(self) -> TelemetryFrame:
        """Return the current telemetry frame with injected host metrics."""
        adapter = self.adapter
        if adapter:
            frame = adapter.get_telemetry()
        else:
            frame = TelemetryFrame(
                simulator="none",
                connection_state="DISCONNECTED",
                components={"backend": "ONLINE", "simulator": "DISCONNECTED", "vehicle": "OFFLINE"},
            )

        # Inject host system metrics
        try:
            mem = self._proc.memory_info()
            frame.performance.cpu_percent = round(psutil.cpu_percent(), 1)
            frame.performance.ram_mb = round(mem.rss / (1024 * 1024), 1)
            frame.performance.capture_fps = round(self._calculated_capture_fps, 1)
        except Exception:
            pass

        return frame

    def get_info(self) -> SimulationInfo:
        if self.adapter:
            return self.adapter.get_info()
        return SimulationInfo(
            simulator_name="None",
            version="N/A",
            state="IDLE",
            connected=False,
        )

    def get_status(self) -> Dict[str, Any]:
        """Summary status for /health endpoint."""
        adapter = self.adapter
        conn = adapter.is_connected() if adapter else False
        state = adapter.connection_state if adapter else "IDLE"
        err = adapter.last_error if adapter else None

        return {
            "status": "healthy",
            "active_simulator": self.active_adapter_type,
            "connected": conn,
            "state": state,
            "error": err,
            "capture_fps": round(self._calculated_capture_fps, 1),
            "frames_captured": self._capture_frames_count,
        }
