#!/bin/bash

cd "$(dirname "$0")/../server" || exit 1
uv run pytest ../tests/server