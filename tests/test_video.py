"""Unit tests for video buffer, HUD overlay, and MJPEG streaming."""

import threading
import time
import numpy as np
from simbridge.core.video import (
    LatestFrameBuffer,
    SyntheticVideoSource,
    draw_hud_overlay,
    mjpeg_generator,
)


def test_frame_buffer_publish_and_retrieve():
    buf = LatestFrameBuffer()
    dummy = np.zeros((100, 100, 3), dtype=np.uint8)

    frame_id = buf.publish(dummy, {"source": "unit_test"})
    assert frame_id == 1

    frame, fid, ts, meta = buf.get_latest()
    assert fid == 1
    assert meta["source"] == "unit_test"
    assert frame.shape == (100, 100, 3)

    # Wait new returns immediately if ID is higher
    f2, fid2, ts2, meta2 = buf.wait_new(0, timeout=0.1)
    assert fid2 == 1


def test_synthetic_video_source():
    src = SyntheticVideoSource(width=320, height=240, fps=15.0)
    assert src.is_opened() is True

    frame, meta = src.read()
    assert frame is not None
    assert frame.shape == (240, 320, 3)
    assert meta["source"] == "synthetic"
    assert meta["frame_id"] == 1

    src.release()
    assert src.is_opened() is False


def test_draw_hud_overlay():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    hud = draw_hud_overlay(frame, frame_id=42, source_name="test_cam", fps=29.9, mode_text="ARMED")
    assert hud.shape == (360, 640, 3)
    # Check that overlay modified top bar pixels
    assert np.any(hud[:24, :, :] > 0)


def test_mjpeg_generator_output():
    buf = LatestFrameBuffer()
    stop_event = threading.Event()

    # Pre-populate a frame
    dummy = np.zeros((180, 320, 3), dtype=np.uint8)
    buf.publish(dummy)

    gen = mjpeg_generator(buf, stop_event, jpeg_quality=70, target_fps=20.0)

    # Read first 2 chunks
    chunk1 = next(gen)
    chunk2 = next(gen)

    assert b"--frame" in chunk1
    assert b"Content-Type: image/jpeg" in chunk1
    assert b"--frame" in chunk2

    stop_event.set()
