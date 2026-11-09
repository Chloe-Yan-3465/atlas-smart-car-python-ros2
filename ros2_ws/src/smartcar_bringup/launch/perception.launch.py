from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params = PathJoinSubstitution([FindPackageShare("smartcar_bringup"), "config", "car_params.yaml"])
    root, backend, source = LaunchConfiguration("model_root"), LaunchConfiguration("backend"), LaunchConfiguration("source")
    return LaunchDescription([
        DeclareLaunchArgument("model_root", default_value=EnvironmentVariable("SMARTCAR_MODEL_ROOT", default_value="/opt/smart_car/models")),
        DeclareLaunchArgument("backend", default_value="om"), DeclareLaunchArgument("source", default_value="/dev/video0"),
        Node(package="smartcar_nodes", executable="camera_node", parameters=[params, {"source": source}]),
        Node(package="smartcar_nodes", executable="lane_node", parameters=[params, {"backend": backend, "model_path": PathJoinSubstitution([root, "lane", "lanenet_hnet_finetune_unified_310b1.om"])}]),
        Node(package="smartcar_nodes", executable="yolo_node", parameters=[params, {"backend": backend, "model_path": PathJoinSubstitution([root, "landmark", "yolov5_incremental_v3_310b1.om"])}]),
    ])

