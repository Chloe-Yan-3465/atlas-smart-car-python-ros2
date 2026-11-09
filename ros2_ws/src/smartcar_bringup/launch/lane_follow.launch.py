from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params = PathJoinSubstitution([FindPackageShare("smartcar_bringup"), "config", "car_params.yaml"])
    root = LaunchConfiguration("model_root")
    return LaunchDescription([
        DeclareLaunchArgument("model_root", default_value=EnvironmentVariable("SMARTCAR_MODEL_ROOT", default_value="/opt/smart_car/models")),
        DeclareLaunchArgument("source", default_value="/dev/video0"), DeclareLaunchArgument("dry_run", default_value="true"),
        Node(package="smartcar_nodes", executable="camera_node", parameters=[params, {"source": LaunchConfiguration("source")}]),
        Node(package="smartcar_nodes", executable="lane_node", parameters=[params, {"model_path": PathJoinSubstitution([root, "lane", "lanenet_hnet_finetune_unified_310b1.om"])}]),
        Node(package="smartcar_nodes", executable="decision_node", parameters=[params]),
        Node(package="smartcar_nodes", executable="chassis_node", parameters=[params, {"dry_run": LaunchConfiguration("dry_run")}]),
    ])

