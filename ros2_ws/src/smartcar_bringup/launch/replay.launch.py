from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    images = LaunchConfiguration("images")
    return LaunchDescription([
        DeclareLaunchArgument("images", description="Image directory used as a looping camera source"),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare("smartcar_bringup"), "launch", "car.launch.py"])), launch_arguments={"source": images, "dry_run": "true"}.items()),
    ])

