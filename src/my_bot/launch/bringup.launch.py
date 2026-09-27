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

    # 1. Khởi động Gazebo và mô hình robot
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'sim.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 2. Khởi động Nav2
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'navigation.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 3. Khởi động rosbridge WebSocket server
    rosbridge_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource([
            os.path.join(rosbridge_share, 'launch', 'rosbridge_websocket_launch.xml')
        ])
    )

    # 4. Quản lý lưu trữ thông số vườn
    farm_manager_node = Node(
        package=package_name,
        executable='farm_manager',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # 5. Bộ não điều phối bám luống tự động
    row_detector_node = Node(
        package=package_name,
        executable='row_detector',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # 6. Mở trực tiếp màn hình Camera quan sát nhận diện
    camera_view_node = Node(
        package='rqt_image_view',
        executable='rqt_image_view',
        arguments=['/camera/row_detected'],
        output='screen'
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
        camera_view_node,
    ])