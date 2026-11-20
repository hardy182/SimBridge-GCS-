"""Pytest fixtures for SimBridge GCS tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from simbridge.api.app import create_app
from simbridge.config import AppConfig


@pytest.fixture
def test_config() -> AppConfig:
    cfg = AppConfig()
    cfg.active_simulator = "mock"
    cfg.server.host = "127.0.0.1"
    cfg.server.port = 8000
    cfg.telemetry.rate_hz = 50.0
    cfg.stream.jpeg_quality = 50
    return cfg


@pytest.fixture
def app(test_config: AppConfig):
    return create_app(config=test_config)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
