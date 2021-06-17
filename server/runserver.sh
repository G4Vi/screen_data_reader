#!/bin/bash
SERVERLOC=$(dirname "$0")
source "$SERVERLOC/../.venv/bin/activate"
exec "$SERVERLOC/server.py"
