from setuptools import find_packages, setup

setup(
    name="smartcar_nodes",
    version="1.0.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/smartcar_nodes"]),
        ("share/smartcar_nodes", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Smart Car Team",
    maintainer_email="maintainer@example.com",
    description="ROS 2 adapters for atlas-smart-car",
    license="MIT",
    entry_points={"console_scripts": [
        "camera_node=smartcar_nodes.camera_node:main",
        "lane_node=smartcar_nodes.lane_node:main",
        "yolo_node=smartcar_nodes.yolo_node:main",
        "decision_node=smartcar_nodes.decision_node:main",
        "chassis_node=smartcar_nodes.chassis_node:main",
    ]},
)

