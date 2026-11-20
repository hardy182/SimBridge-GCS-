"""Integration tests for FastAPI REST routes and dashboard serving."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_html_serving(client: AsyncClient):
    res = await client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "SIMBRIDGE GCS" in res.text
    assert "Simulation Viewport" in res.text
    assert "Vehicle Telemetry" in res.text


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "active_simulator" in data


@pytest.mark.asyncio
async def test_telemetry_endpoint(client: AsyncClient):
    res = await client.get("/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "pose" in data
    assert "vehicle" in data
    assert "battery" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_detect_endpoint(client: AsyncClient):
    res = await client.get("/api/detect")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert "gazebo" in data["tools"]
    assert "px4" in data["tools"]
    assert "blender" in data["tools"]


@pytest.mark.asyncio
async def test_connect_and_disconnect(client: AsyncClient):
    # Connect to mock
    conn_res = await client.post("/api/connect", json={"simulator": "mock"})
    assert conn_res.status_code == 200
    assert conn_res.json()["status"] == "connected"

    # Verify telemetry reflects connection
    t_res = await client.get("/telemetry")
    assert t_res.json()["simulator"] == "mock"

    # Disconnect
    disc_res = await client.post("/api/disconnect")
    assert disc_res.status_code == 200
    assert disc_res.json()["status"] == "disconnected"


@pytest.mark.asyncio
async def test_video_feed_snapshot(client: AsyncClient):
    await client.post("/api/connect", json={"simulator": "mock"})
    res = await client.get("/video_feed?snapshot=true")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert len(res.content) > 100


@pytest.mark.asyncio
async def test_video_feed_bounded_stream(client: AsyncClient):
    await client.post("/api/connect", json={"simulator": "mock"})
    res = await client.get("/video_feed?max_frames=1")
    assert res.status_code == 200
    assert "multipart/x-mixed-replace; boundary=frame" in res.headers["content-type"]
    assert b"--frame" in res.content
