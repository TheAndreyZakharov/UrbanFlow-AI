# UrbanFlow AI Server

Backend for UrbanFlow AI.

## Responsibilities

- Import OpenStreetMap data.
- Normalize roads, buildings, signals, crossings and infrastructure.
- Build city graph.
- Run traffic simulation sessions.
- Apply editor patches.
- Generate traffic events.
- Expose API for frontend.
- Provide simulation state for future AI controller.

## Run

```bash
../scripts/run-server.sh