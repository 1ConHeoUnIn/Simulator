Giai đoạn 1: Dọn dẹp thư mục và Build mới toàn bộ
Mở Terminal 1 và chạy chuỗi lệnh sau để  biên dịch sạch sẽ workspace:
        "

        # 1. Xóa sạch các thư mục build cũ
        cd ~/robot_ws


        # 2. Biên dịch lại toàn bộ workspace và nạp môi trường
        colcon build --symlink-install
        source install/setup.bash

        "
Giai đoạn 2: Quét tạo bản đồ mới (SLAM Mode)

Terminal 1: Khởi động hệ thống SLAM
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot slam_mapping.launch.py
        "

Terminal 2: Lái xe quét quanh các luống cây
        "
        source ~/robot_ws/install/setup.bash
        ros2 run teleop_twist_keyboard teleop_twist_keyboard
        "

Terminal 3: Lưu bản đồ tĩnh sau khi quét xong
        "
        cd ~/robot_ws/src/my_bot/maps
        ros2 run nav2_map_server map_saver_cli -f my_farm_map
        "

Giai đoạn 3: Phủ mô đất và cập nhật bản đồ tĩnh
Terminal 1: Chạy script đè luống đất theo cấu hình vườn
        "
        cd ~/robot_ws/src/my_bot/maps
        python3 generate_map.py
        "

Terminal 1: Nạp bản đồ mới vào thư mục cài đặt (install)
        "
        cd ~/robot_ws
        colcon build --symlink-install --packages-select my_bot
        source install/setup.bash
        "

Giai đoạn 4: Vận hành tự hành (Navigation Mode)
Terminal 1: Khởi động toàn bộ hệ thống vận hành
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot bringup.launch.py
        "

Terminal 2: Mở RViz2 giám sát điều hướng
        "
        ros2 run rviz2 rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz --ros-args -p use_sim_time:=true
        "
Mở Web UI điều khiển:

Mở trình duyệt, mở file: 
        "
        /home/heo/robot_ws/src/hmmm/index.html
        "
