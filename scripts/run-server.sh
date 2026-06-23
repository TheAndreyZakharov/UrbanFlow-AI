#!/bin/bash

cd "$(dirname "$0")/../server" || exit 1

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000