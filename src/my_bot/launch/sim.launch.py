import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node


def generate_launch_description():

    package_name = 'my_bot'

    # 1. Gọi lại rsp.launch.py với use_sim_time = true
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory(package_name), 'launch', 'rsp.launch.py'
            )
        ]),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    # Đường dẫn đến file world vừa tạo
    world_path = os.path.join(
        get_package_share_directory(package_name), 'worlds', 'obstacles.world'
    )

    # 2. Gọi Gazebo kèm file thế giới khu vườn và nhà kho
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py'
            )
        ]),
        launch_arguments={'world': world_path}.items()
    )

    # 3. Node thả (spawn) robot vào thế giới ảo
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                   '-entity', 'my_bot',
                   '-x', '6.0',
                   '-y', '-6.0',
                   '-z', '0.1',
                   '-Y', '1.5708'],
        output='screen'
    )

    return LaunchDescription([
        rsp,
        gazebo,
        spawn_entity,
    ])