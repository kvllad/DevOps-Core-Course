# DevOps Info Service (FastAPI)

## Overview
This service exposes system and runtime information for DevOps learning labs. It provides a main endpoint with detailed metadata and a simple health check for monitoring.

## Prerequisites
- Python 3.11+
- pip

## Installation
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Application
```bash
python app.py
# Or with custom config
PORT=8080 python app.py
HOST=127.0.0.1 PORT=3000 DEBUG=true python app.py
```

## API Endpoints
- `GET /` - Service and system information
- `GET /health` - Health check

## Configuration
| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Port to listen on |
| `DEBUG` | `False` | Enables auto-reload when `true` |
