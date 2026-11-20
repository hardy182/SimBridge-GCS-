"""Video streaming subsystem, frame buffer, and multi-source video capture."""

from __future__ import annotations

import math
import site
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, Tuple
import cv2
import numpy as np


class LatestFrameBuffer:
    """Thread-safe condition-variable buffer storing the newest frame and sequence ID."""

    def __init__(self) -> None:
        self._lock = threading.Condition()
        self.frame: Optional[np.ndarray] = None
        self.frame_id: int = 0
        self.timestamp: float = 0.0
        self.meta: Dict[str, Any] = {}

    def publish(self, frame: np.ndarray, meta: Optional[Dict[str, Any]] = None) -> int:
        with self._lock:
            self.frame = frame.copy()
            self.frame_id += 1
            self.timestamp = time.time()
            self.meta = dict(meta or {})
            self._lock.notify_all()
            return self.frame_id

    def get_latest(self) -> Tuple[Optional[np.ndarray], int, float, Dict[str, Any]]:
        with self._lock:
            return self.frame, self.frame_id, self.timestamp, self.meta

    def wait_new(
        self, last_seen_id: int, timeout: float = 0.05
    ) -> Tuple[Optional[np.ndarray], int, float, Dict[str, Any]]:
        with self._lock:
            if self.frame_id > last_seen_id:
                return self.frame, self.frame_id, self.timestamp, self.meta
            self._lock.wait(timeout)
            return self.frame, self.frame_id, self.timestamp, self.meta


class BaseVideoSource(ABC):
    """Abstract interface for simulation or camera video sources."""

    @abstractmethod
    def read(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


class SyntheticVideoSource(BaseVideoSource):
    """Generates synthetic aerospace test pattern and telemetry HUD."""

    def __init__(self, width: int = 640, height: int = 360, fps: float = 30.0) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self._opened = True
        self._frame_seq = 0
        self._start_time = time.time()

    def is_opened(self) -> bool:
        return self._opened

    def release(self) -> None:
        self._opened = False

    def read(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        if not self._opened:
            return None, {}

        self._frame_seq += 1
        t = time.time() - self._start_time

        # Create dark background
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:] = (18, 24, 34)  # Deep blue-gray

        # Draw grid
        grid_spacing = 40
        for x in range(0, self.width, grid_spacing):
            cv2.line(img, (x, 0), (x, self.height), (28, 38, 54), 1)
        for y in range(0, self.height, grid_spacing):
            cv2.line(img, (0, y), (self.width, y), (28, 38, 54), 1)

        # Draw animated artificial horizon
        cx, cy = self.width // 2, self.height // 2
        roll = math.sin(t * 0.8) * 15.0  # deg
        pitch = math.cos(t * 0.5) * 20.0  # px offset

        rad = math.radians(roll)
        dx = int(math.cos(rad) * 120)
        dy = int(math.sin(rad) * 120)
        center_y = int(cy + pitch)

        # Horizon line
        cv2.line(img, (cx - dx, center_y - dy), (cx + dx, center_y + dy), (59, 130, 246), 2)
        # Pitch ticks
        for tick in [-30, -15, 15, 30]:
            py = int(center_y + tick)
            cv2.line(img, (cx - 20, py), (cx + 20, py), (34, 197, 94), 1)

        # Center reticle
        cv2.circle(img, (cx, cy), 6, (20, 184, 166), 1)
        cv2.line(img, (cx - 15, cy), (cx - 6, cy), (20, 184, 166), 2)
        cv2.line(img, (cx + 6, cy), (cx + 15, cy), (20, 184, 166), 2)
        cv2.line(img, (cx, cy - 15), (cx, cy - 6), (20, 184, 166), 2)
        cv2.line(img, (cx, cy + 6), (cx, cy + 15), (20, 184, 166), 2)

        meta = {
            "source": "synthetic",
            "frame_id": self._frame_seq,
            "width": self.width,
            "height": self.height,
            "timestamp": time.time(),
        }
        return img, meta


class WebcamVideoSource(BaseVideoSource):
    """OpenCV V4L2 webcam capture source."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 360) -> None:
        self.device_index = device_index
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(device_index)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._frame_seq = 0

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def release(self) -> None:
        if self.cap.isOpened():
            self.cap.release()

    def read(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        if not self.cap.isOpened():
            return None, {}
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None, {}
        self._frame_seq += 1
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        meta = {
            "source": f"webcam:{self.device_index}",
            "frame_id": self._frame_seq,
            "width": self.width,
            "height": self.height,
            "timestamp": time.time(),
        }
        return frame, meta


class GazeboVideoSource(BaseVideoSource):
    """Subscribes to Gazebo Sim camera images using native gz.transport."""

    def __init__(
        self,
        topic: str = "/camera/image",
        width: int = 640,
        height: int = 360,
        stale_timeout_s: float = 2.0,
    ) -> None:
        self.topic = topic
        self.width = width
        self.height = height
        self.stale_timeout_s = stale_timeout_s

        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_meta: Dict[str, Any] = {}
        self._frames_received = 0
        self._last_received_time = 0.0
        self._is_opened = False
        self._node = None
        self._sub = None
        self._last_error: Optional[str] = None

        self._connect()

    def _connect(self) -> bool:
        site.addsitedir("/usr/lib/python3/dist-packages")
        try:
            from gz.transport import Node
            from gz.msgs.image_pb2 import Image

            self._node = Node()
            self._sub = self._node.subscribe(Image, self.topic, self._on_image)
            self._is_opened = bool(self._sub)
            if not self._is_opened:
                self._last_error = f"Failed to subscribe to Gazebo topic {self.topic}"
            return self._is_opened
        except Exception as e:
            self._last_error = f"Gazebo transport init error: {e}"
            self._is_opened = False
            return False

    def _on_image(self, msg: Any) -> None:
        w = int(getattr(msg, "width", 0))
        h = int(getattr(msg, "height", 0))
        raw_data = getattr(msg, "data", b"")
        fmt = getattr(msg, "pixel_format_type", 0)

        if not raw_data or w <= 0 or h <= 0:
            return

        try:
            # Multi-format decode
            # 3 = RGB_INT8, 4 = RGBA_INT8, 5 = BGR_INT8, 6 = BGRA_INT8, 1 = L_INT8
            if fmt == 3:  # RGB
                arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w, 3))
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            elif fmt == 5:  # BGR
                bgr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w, 3))
            elif fmt == 4:  # RGBA
                arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w, 4))
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif fmt == 6:  # BGRA
                arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w, 4))
                bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            elif fmt == 1:  # Grayscale
                arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w))
                bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            else:
                arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((h, w, -1))
                if arr.shape[2] == 3:
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                else:
                    bgr = arr

            if bgr.shape[1] != self.width or bgr.shape[0] != self.height:
                bgr = cv2.resize(bgr, (self.width, self.height))

            with self._lock:
                self._latest_frame = bgr
                self._frames_received += 1
                self._last_received_time = time.time()
                self._latest_meta = {
                    "source": "gazebo",
                    "topic": self.topic,
                    "frame_id": self._frames_received,
                    "width": self.width,
                    "height": self.height,
                    "timestamp": self._last_received_time,
                }
        except Exception as e:
            self._last_error = f"Image decode error: {e}"

    def is_opened(self) -> bool:
        return self._is_opened

    def release(self) -> None:
        if self._node and self._sub:
            try:
                self._node.unsubscribe(self.topic)
            except Exception:
                pass
        self._is_opened = False

    def read(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        with self._lock:
            if self._latest_frame is None:
                return None, {"error": self._last_error or "Waiting for Gazebo frames"}
            if time.time() - self._last_received_time > self.stale_timeout_s:
                return self._latest_frame, {
                    "stale": True,
                    "age_s": time.time() - self._last_received_time,
                    **self._latest_meta,
                }
            return self._latest_frame, dict(self._latest_meta)


def draw_hud_overlay(
    frame: np.ndarray,
    frame_id: int,
    source_name: str,
    fps: float,
    mode_text: str = "SIM",
    extra_text: Optional[str] = None,
) -> np.ndarray:
    """Renders non-intrusive aerospace HUD overlay onto frame."""
    out = frame.copy()
    h, w = out.shape[:2]

    cv2.rectangle(out, (0, 0), (w, 24), (11, 18, 32), -1)
    cv2.line(out, (0, 24), (w, 24), (36, 48, 74), 1)

    ts = time.strftime("%H:%M:%S")
    left_str = f"SIMBRIDGE | {source_name.upper()} | #{frame_id:05d} | {fps:.1f} FPS"
    right_str = f"{mode_text} | {ts}"

    cv2.putText(out, left_str, (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 184, 166), 1, cv2.LINE_AA)
    cv2.putText(out, right_str, (w - 140, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (148, 163, 184), 1, cv2.LINE_AA)

    if extra_text:
        cv2.putText(out, extra_text, (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (59, 130, 246), 1, cv2.LINE_AA)

    return out


def mjpeg_generator(
    frame_buffer: LatestFrameBuffer,
    stop_event: threading.Event,
    jpeg_quality: int = 80,
    target_fps: float = 30.0,
    overlay_enabled: bool = True,
    max_frames: Optional[int] = None,
) -> Generator[bytes, None, None]:
    """Generates a continuous multipart MJPEG HTTP stream."""
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    last_id = 0
    target_dt = 1.0 / max(1.0, target_fps)
    last_loop_t = time.perf_counter()
    frames_yielded = 0

    while not stop_event.is_set():
        if max_frames is not None and frames_yielded >= max_frames:
            break

        frame, frame_id, ts, meta = frame_buffer.wait_new(last_id, timeout=0.08)

        if frame is None:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            frame[:] = (17, 24, 39)
            cv2.putText(
                frame,
                "WAITING FOR CAMERA STREAM...",
                (140, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (148, 163, 184),
                1,
                cv2.LINE_AA,
            )
            frame_id = last_id + 1

        last_id = frame_id

        if overlay_enabled and frame is not None:
            src = str(meta.get("source", "stream"))
            frame = draw_hud_overlay(frame, frame_id, src, target_fps)

        ok, jpg = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
        )
        frames_yielded += 1

        now = time.perf_counter()
        elapsed = now - last_loop_t
        if elapsed < target_dt:
            time.sleep(target_dt - elapsed)
        last_loop_t = time.perf_counter()
