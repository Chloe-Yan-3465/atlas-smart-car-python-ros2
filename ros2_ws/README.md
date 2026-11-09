# ROS 2 Humble 工作空间

```bash
cd /opt/smart_car
python3 -m pip install -e .
source /opt/ros/humble/setup.bash
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
export SMARTCAR_MODEL_ROOT=/opt/smart_car/models
ros2 launch smartcar_bringup car.launch.py dry_run:=true
```

确认感知和决策话题后才可切换 `dry_run:=false`。图片回放使用：

```bash
ros2 launch smartcar_bringup replay.launch.py images:=/path/to/images
```

