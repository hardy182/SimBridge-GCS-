"""Command-line interface for SimBridge GCS."""

from __future__ import annotations

import argparse
import sys
import uvicorn
from simbridge.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SimBridge GCS — Standalone Robotics Simulation Dashboard"
    )
    parser.add_argument("--host", type=str, default=None, help="Host address to bind to (e.g. 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (e.g. 8000)")
    parser.add_argument("--config", type=str, default=None, help="Path to custom YAML configuration file")
    parser.add_argument("--simulator", type=str, default=None, help="Initial simulator (mock, gazebo, px4, blender)")
    parser.add_argument("--log-level", type=str, default="info", help="Uvicorn log level (debug, info, warning, error)")

    args = parser.parse_args()

    # Load configuration
    cfg = load_config(args.config)
    if args.host:
        cfg.server.host = args.host
    if args.port:
        cfg.server.port = args.port
    if args.simulator:
        cfg.active_simulator = args.simulator
    if args.log_level:
        cfg.server.log_level = args.log_level

    print("==========================================================")
    print("                 SIMBRIDGE GCS DASHBOARD                  ")
    print("==========================================================")
    print(f"  Web Dashboard: http://{cfg.server.host}:{cfg.server.port}")
    print(f"  API Docs:      http://{cfg.server.host}:{cfg.server.port}/docs")
    print(f"  Simulator:     {cfg.active_simulator.upper()}")
    print("==========================================================")

    from simbridge.api.app import create_app
    app = create_app(config=cfg)

    uvicorn.run(
        app,
        host=cfg.server.host,
        port=cfg.server.port,
        log_level=cfg.server.log_level,
    )


if __name__ == "__main__":
    main()
