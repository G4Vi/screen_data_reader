#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$DIR/.venv/bin/activate"
exec $DIR/screen_data_reader.py "$@"
