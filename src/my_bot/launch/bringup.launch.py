import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource, AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'my_bot'
    pkg_share = get_package_share_directory(package_name)
    rosbridge_share = get_package_share_directory('rosbridge_server')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # 1. Gọi file mô phỏng Gazebo (gồm cả robot_state_publisher và spawn xe)
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'sim.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 2. Gọi hệ thống dẫn đường Nav2
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'navigation.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 3. Gọi WebSocket bridge kết nối Web (rosbridge)
    rosbridge_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource([
            os.path.join(rosbridge_share, 'launch', 'rosbridge_websocket_launch.xml')
        ])
    )

    # 4. Node quản lý thông số vườn (Farm Manager)
    farm_manager_node = Node(
        package=package_name,
        executable='farm_manager',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # 5. Node bám luống tự động (Row Detector / Arbiter)
    row_detector_node = Node(
        package=package_name,
        executable='row_detector',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Sử dụng thời gian mô phỏng Gazebo nếu true'
        ),
        sim_launch,
        nav_launch,
        rosbridge_launch,
        farm_manager_node,
        row_detector_node,
    ])