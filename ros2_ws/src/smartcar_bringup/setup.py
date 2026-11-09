from glob import glob
from setuptools import setup

setup(
    name="smartcar_bringup", version="1.0.0", packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/smartcar_bringup"]),
        ("share/smartcar_bringup", ["package.xml"]),
        ("share/smartcar_bringup/launch", glob("launch/*.launch.py")),
        ("share/smartcar_bringup/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"], zip_safe=True,
    maintainer="Smart Car Team", maintainer_email="maintainer@example.com",
    description="Smart car launch package", license="MIT",
)

