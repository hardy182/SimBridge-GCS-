# Contributing to SimBridge GCS

We welcome contributions to SimBridge GCS!

## Development Setup

1. Fork and clone the repository.
2. Initialize the virtual environment:
   ```bash
   ./setup.sh
   ```
3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
4. Run the test suite:
   ```bash
   pytest tests -v
   ```

## Pull Request Guidelines
- Write tests for new adapters or endpoints.
- Maintain the decoupled architecture: do not bundle external simulator binaries.
- Keep safety checks in place: monitoring only, no autonomous arming or flight commands.
