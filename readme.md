HƯỚNG DẪN CÀI ĐẶT VÀ KHỞI CHẠY MÔ PHỎNG ROBOT TRÊN GAZEBO & NAV2 (ROS 2 HUMBLE)
PHẦN 1: CÀI ĐẶT CÁC CÔNG CỤ VÀ GÓI PHỤ THUỘC
Mở Terminal và chạy lần lượt các lệnh sau để cài đặt toàn bộ gói cần thiết (Gazebo ROS, xacro, Joint State Publisher GUI, Teleop, SLAM Toolbox, Nav2):"
        "
        sudo apt update
        sudo apt install -y \
        ros-humble-gazebo-ros-pkgs \
        ros-humble-xacro \
        ros-humble-joint-state-publisher-gui \
        ros-humble-teleop-twist-keyboard \
        ros-humble-slam-toolbox \
        ros-humble-nav2-bringup \
        ros-humble-nav2-map-server
        "
PHẦN 2: TẠO WORKSPACE VÀ CLONE REPOSITORY TỪ GITHUB
# 1. Trở về thư mục Home
        "
        cd ~
        "
# 2. Clone repo về và đặt tên thư mục là robot_ws
        "
        git clone https://github.com/1ConHeoUnIn/Simulator.git robot_ws
        "
# 3. Đi vào workspace và build
        "
        cd ~/robot_ws
        colcon build --symlink-install
        source install/setup.bash
        "

Kết quả dự kiến sau khi build:
Starting >>> my_bot
Finished <<< my_bot [x.xx s]
Summary: 1 package finished [x.xx s]

PHẦN 3: CÁC CHẾ ĐỘ CHẠY HỆ THỐNG
CHẾ ĐỘ 1: KIỂM TRA MÔ HÌNH ROBOT TRÊN RVIZ2 (URDF/RSP)
Dùng để kiểm tra trực quan khớp nối xe và hiển thị URDF trước khi chạy mô phỏng vật lý.

Terminal 1 — Khởi động Robot State Publisher:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot rsp.launch.py
        "
Kết quả in ra: Các segment base_footprint, base_link, chassis, left_wheel, right_wheel, fl_caster_wheel,... được nhận diện thành công.

Terminal 2 — Bật thanh trượt điều khiển khớp ảo:

        "
        source ~/robot_ws/install/setup.bash
        ros2 run joint_state_publisher_gui joint_state_publisher_gui
        "

Terminal 3 — Mở RViz2 để xem robot:
        "
        rviz2
        "

Các bước thiết lập trên RViz2:Mục Global Options -> Đổi Fixed Frame thành base_link.  Bấm nút Add (hoặc Ctrl + N) -> Chọn display RobotModel -> Bấm OK.  Trong bảng điều khiển của RobotModel, tìm dòng Description Topic, chọn giá trị /robot_description.  Kết quả: Mô hình 3D xe có bánh xanh dương và thân trắng hiện rõ trên lưới grid.  

CHẾ ĐỘ 2: CHẠY GAZEBO & LÁI XE THỬ BẰNG BÀN PHÍM
Dùng để đưa robot vào môi trường mô phỏng vật lý (thế giới khu vườn obstacles.world).

Terminal 1 — Khởi chạy Gazebo và Spawn robot:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot sim.launch.py
        "

Terminal 2 — Bật bộ điều khiển lái xe bằng phím:
        "
        ros2 run teleop_twist_keyboard teleop_twist_keyboard
        "
Cách điều khiển: Nhấn giữ i (tiến), , (lùi), j (quay trái), l (quay phải), k (dừng). Xe trong Gazebo sẽ lăn bánh theo lệnh.

Kiểm tra nhanh sensor (tùy chọn mở thêm terminal):
Kiểm tra LiDAR: 
        "
        ros2 topic echo /scan --once
        "
Kiểm tra IMU: 
        "
        ros2 topic echo /imu/data --once 
        "

CHẾ ĐỘ 3: CHẠY QUÉT BẢN ĐỒ (SLAM MAPPING) VÀ LƯU MAP
Dùng khi muốn tự tay lái xe đi quét lại toàn bộ khu vườn và lưu thành file .yaml + .pgm. 
Do khi pull xuống từ github đã có sẵn map rồi, nếu như có nhu cầu thay đổi map và quét lại thì làm bước này:

Terminal 1 — Mở môi trường Gazebo:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot sim.launch.py
        "

Terminal 2 — Chạy SLAM Toolbox:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch slam_toolbox online_async_launch.py slam_params_file:=./src/my_bot/config/mapper_params_online_async.yaml use_sim_time:=true
        "
Terminal 3 — Mở RViz2 hiển thị bản đồ quét:
        "
        ros2 run rviz2 rviz2 --ros-args -p use_sim_time:=true
        "
Thao tác trên RViz2:Đổi Fixed Frame thành map.  Bấm Add -> chọn LaserScan -> đặt Topic là /scan.  Bấm Add -> chọn Map -> đặt Topic là /map.


Terminal 4 — Bật bộ điều khiển lái xe bằng phím, lái xe đi quét bản đồ:
        "
        ros2 run teleop_twist_keyboard teleop_twist_keyboard
        "
Lái xe chạy vòng quanh sân vườn cho đến khi bản đồ hiển thị khép kín trên RViz2.  

Terminal 5 — Xuất và lưu bản đồ (khi đã quét xong):
        "
        mkdir -p ~/robot_ws/src/my_bot/maps
        cd ~/robot_ws/src/my_bot/maps
        ros2 run nav2_map_server map_saver_cli -f my_farm_map
        "
Kết quả: Trong thư mục maps sinh ra 2 file my_farm_map.pgm và my_farm_map.yaml. Nhớ chạy lại colcon build --symlink-install để cập nhật map vào thư mục install nếu có sửa đổi!


CHẾ ĐỘ 4: DẪN ĐƯỜNG TỰ ĐỘNG VỚI NAV2 (AUTONOMOUS NAVIGATION)Chế độ hoàn chỉnh nhất: Load bản đồ đã quét sẵn, tự định vị AMCL, lập quỹ đạo tránh vật cản tĩnh và động.  

Terminal 1 — Chạy mô phỏng Gazebo:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot sim.launch.py
        "

Terminal 2 — Khởi động ngăn xếp dẫn đường Nav2:
        "
        source ~/robot_ws/install/setup.bash
        ros2 launch my_bot navigation.launch.py
        "
(Nav2 sẽ nạp cấu hình nav2_params.yaml cùng bản đồ my_farm_map.yaml, tự động khởi tạo vị trí ban đầu của robot tại góc nhà kho).  

Terminal 3 — Mở giao diện điều khiển RViz2 của Nav2:
        "
        ros2 run rviz2 rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz --ros-args -p use_sim_time:=true
        "
Cách ra lệnh cho xe tự chạy:
1. Quan sát trên RViz2: Bản đồ hiện viền màu hồng/xanh (costmap) xung quanh các bức tường, luống cây và cụm hạt định vị màu xanh lá bao quanh xe.  
2. Bấm vào công cụ Nav2 Goal trên thanh công cụ phía trên đỉnh RViz2.  
3. Click chuột vào vị trí bất kỳ trên bản đồ (giữ chuột và kéo để chọn hướng xoay đầu của robot).  
4. Kết quả quan sát được: Một đường line màu đỏ/xanh (Global Path) xuất hiện nối từ robot tới điểm đích. Robot trong Gazebo sẽ tự động tăng tốc, bẻ lái tránh vật cản và di chuyển tới đúng vị trí yêu cầu.  
5. Thử nghiệm tránh vật cản: Thả một khối hình hộp/trụ bất kỳ trên thanh công cụ Gazebo chắn đường đi -> Robot sẽ tự động tính toán lại đường đi vòng qua vật cản để tới đích.