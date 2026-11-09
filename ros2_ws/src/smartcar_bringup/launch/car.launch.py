from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params = PathJoinSubstitution([FindPackageShare("smartcar_bringup"), "config", "car_params.yaml"])
    model_root = LaunchConfiguration("model_root")
    backend = LaunchConfiguration("backend")
    lane_model = LaunchConfiguration("lane_model")
    yolo_model = LaunchConfiguration("yolo_model")
    source = LaunchConfiguration("source")
    dry_run = LaunchConfiguration("dry_run")
    return LaunchDescription([
        DeclareLaunchArgument("model_root", default_value=EnvironmentVariable("SMARTCAR_MODEL_ROOT", default_value="/opt/smart_car/models")),
        DeclareLaunchArgument("backend", default_value="om"),
        DeclareLaunchArgument("lane_model", default_value=PathJoinSubstitution([model_root, "lane", "lanenet_hnet_finetune_unified_310b1.om"])),
        DeclareLaunchArgument("yolo_model", default_value=PathJoinSubstitution([model_root, "landmark", "yolov5_incremental_v3_310b1.om"])),
        DeclareLaunchArgument("source", default_value="/dev/video0"),
        DeclareLaunchArgument("dry_run", default_value="true"),
        Node(package="smartcar_nodes", executable="camera_node", parameters=[params, {"source": source}]),
        Node(package="smartcar_nodes", executable="lane_node", parameters=[params, {"backend": backend, "model_path": lane_model}]),
        Node(package="smartcar_nodes", executable="yolo_node", parameters=[params, {"backend": backend, "model_path": yolo_model}]),
        Node(package="smartcar_nodes", executable="decision_node", parameters=[params]),
        Node(package="smartcar_nodes", executable="chassis_node", parameters=[params, {"dry_run": dry_run}]),
    ])

