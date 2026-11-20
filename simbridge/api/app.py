"""FastAPI application factory for SimBridge GCS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simbridge.api.routes import router
from simbridge.config import AppConfig, load_config
from simbridge.core.manager import ConnectionManager


def create_app(config: Optional[AppConfig] = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_config = config or load_config()

    manager = ConnectionManager(config=app_config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        app.state.manager = manager
        yield
        # Shutdown
        manager.disconnect()

    app = FastAPI(
        title="SimBridge GCS",
        description="Standalone open-source robotics simulation dashboard for Gazebo, PX4 SITL, and Blender workflows.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Attach manager to app.state immediately
    app.state.manager = manager

    # Enable CORS for local cross-origin development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app
