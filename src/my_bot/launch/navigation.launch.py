import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    package_name = 'my_bot'

    # Đường dẫn tới map và file cấu hình
    map_file = os.path.join(
        get_package_share_directory(package_name), 'maps', 'my_farm_map.yaml'
    )
    params_file = os.path.join(
        get_package_share_directory(package_name), 'config', 'nav2_params.yaml'
    )

    # Gọi launch file chuẩn từ nav2_bringup
    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch'
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_launch_dir, 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'params_file': params_file,
            'use_sim_time': 'true',
        }.items(),
    )

    return LaunchDescription([
        nav2,
    ])