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

    # 1. Gazebo mô phỏng
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'sim.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 2. SLAM Toolbox chế độ tạo map online async
    slam_params_file = os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ]),
        launch_arguments={
            'slam_params_file': slam_params_file,
            'use_sim_time': use_sim_time
        }.items()
    )

    # 3. RViz2 để quan sát bản đồ quét trực tiếp
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['--ros-args', '-p', 'use_sim_time:=true']
    )

    # 4. rosbridge WebSocket kết nối Web
    rosbridge_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource([
            os.path.join(rosbridge_share, 'launch', 'rosbridge_websocket_launch.xml')
        ])
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        sim_launch,
        slam_launch,
        rviz_node,
        rosbridge_launch
    ])