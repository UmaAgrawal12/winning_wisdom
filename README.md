# Winning Wisdom

This repository's canonical source code lives at the repo root.

## Canonical Layout

- `agents/` - content generation and scoring agents
- `config/` - persona and system configuration
- `frontend/` - web UI assets
- `integrations/` - external API integration clients
- `media_pipeline/` - voice/video generation pipeline
- `workflows/` - orchestration pipeline code
- `app.py` - FastAPI backend app entry
- `main.py` - CLI content generation entry

## Important Note About Duplicates

`python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload`
