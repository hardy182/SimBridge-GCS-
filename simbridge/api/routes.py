"""REST and WebSocket API routes for SimBridge GCS."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, Optional
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from simbridge.api.dashboard_html import DASHBOARD_HTML
from simbridge.core.detector import EnvironmentDetector
from simbridge.core.video import mjpeg_generator

router = APIRouter()


class ConnectRequest(BaseModel):
    simulator: str
    world_name: Optional[str] = None
    model_name: Optional[str] = None
    dynamic_pose_topic: Optional[str] = None
    camera_topic: Optional[str] = None
    partition: Optional[str] = None
    connection: Optional[str] = None
    baud: Optional[int] = None
    executable_path: Optional[str] = None
    asset_dir: Optional[str] = None


@router.get("/", response_class=HTMLResponse)
async def get_dashboard() -> HTMLResponse:
    """Serve the primary GCS dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


@router.get("/health")
async def get_health(request: Request) -> Dict[str, Any]:
    """Return system and connection health summary."""
    manager = request.app.state.manager
    return manager.get_status()


@router.get("/telemetry")
async def get_telemetry(request: Request) -> Dict[str, Any]:
    """Return latest normalized telemetry snapshot."""
    manager = request.app.state.manager
    frame = manager.get_telemetry()
    return frame.model_dump()


@router.get("/api/detect")
async def detect_environment() -> Dict[str, Any]:
    """Query installed simulation tooling and running processes."""
    env = EnvironmentDetector.detect_all()
    return env.model_dump()


@router.get("/api/info")
async def get_simulation_info(request: Request) -> Dict[str, Any]:
    """Return active simulator context, topics, and models."""
    manager = request.app.state.manager
    info = manager.get_info()
    return info.model_dump()


@router.get("/api/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """Return current configuration."""
    manager = request.app.state.manager
    return manager.config.model_dump()


@router.post("/api/connect")
async def connect_simulator(req: ConnectRequest, request: Request) -> Dict[str, Any]:
    """Connect to a designated simulator profile."""
    manager = request.app.state.manager
    custom_opts = {k: v for k, v in req.model_dump().items() if v is not None and k != "simulator"}
    ok = manager.connect(req.simulator, custom_config=custom_opts)
    if not ok:
        err = manager.adapter.last_error if manager.adapter else "Failed to connect"
        return {"status": "error", "message": err, "simulator": req.simulator}
    return {"status": "connected", "simulator": req.simulator}


@router.post("/api/disconnect")
async def disconnect_simulator(request: Request) -> Dict[str, Any]:
    """Disconnect currently active simulator."""
    manager = request.app.state.manager
    manager.disconnect()
    return {"status": "disconnected"}


@router.get("/video_feed")
async def video_feed(
    request: Request,
    snapshot: bool = False,
    max_frames: Optional[int] = None,
) -> Response:
    """MJPEG streaming and snapshot capture endpoint."""
    manager = request.app.state.manager
    jpeg_quality = int(manager.config.stream.jpeg_quality)
    target_fps = float(manager.config.stream.target_fps)

    if snapshot:
        frame, frame_id, ts, meta = manager.frame_buffer.get_latest()
        if frame is None:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            frame[:] = (17, 24, 39)
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        ok, jpg = cv2.imencode(".jpg", frame, encode_params)
        return Response(content=jpg.tobytes(), media_type="image/jpeg")

    stop_event = threading.Event()
    gen = mjpeg_generator(
        frame_buffer=manager.frame_buffer,
        stop_event=stop_event,
        jpeg_quality=jpeg_quality,
        target_fps=target_fps,
        max_frames=max_frames,
    )
    return StreamingResponse(gen, media_type="multipart/x-mixed-replace; boundary=frame")


@router.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket) -> None:
    """High-frequency (20 Hz) WebSocket telemetry broadcast."""
    await websocket.accept()
    manager = websocket.app.state.manager
    rate_hz = float(manager.config.telemetry.rate_hz)
    dt = 1.0 / max(1.0, rate_hz)

    try:
        while True:
            frame = manager.get_telemetry()
            await websocket.send_json(frame.model_dump())
            await asyncio.sleep(dt)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        pass
