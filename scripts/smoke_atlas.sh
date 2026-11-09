#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
source "$ROOT/ros2_ws/install/setup.bash"
export SMARTCAR_MODEL_ROOT="$ROOT/models"
ros2 launch smartcar_bringup replay.launch.py images:="${1:?image directory required}"

