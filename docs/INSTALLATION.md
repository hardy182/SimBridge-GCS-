# SimBridge GCS — Installation Guide

## System Requirements
- Linux (Ubuntu 22.04 LTS or 24.04 LTS recommended)
- Python 3.10+ (Tested on Python 3.14)
- Modern web browser (Chrome, Chromium, Firefox)

## Quick Start

1. Clone or navigate to the repository:
```bash
cd /home/harshdeep-singh/Projects/SimBridge-GCS
```

2. Run the environment setup script:
```bash
./setup.sh
```

3. Launch the dashboard:
```bash
./run.sh
```

4. Open `http://localhost:8000` in your browser.

## Virtual Environment Setup Manually
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```
