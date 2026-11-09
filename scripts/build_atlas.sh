#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]; then source /usr/local/Ascend/ascend-toolkit/set_env.sh; fi
python3 -m pip install -e "$ROOT"
cd "$ROOT/ros2_ws"
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
colcon test --event-handlers console_direct+
colcon test-result --verbose

