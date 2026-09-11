"
cd ~/robot_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch my_bot sim.launch.py
"

control
"
ros2 run teleop_twist_keyboard teleop_twist_keyboard
"


Slam
"
source ~/robot_ws/install/setup.bash
ros2 launch slam_toolbox online_async_launch.py slam_params_file:=./src/my_bot/config/mapper_params_online_async.yaml use_sim_time:=true
"

Rvizz 2 with sync time 
"
ros2 run rviz2 rviz2 --ros-args -p use_sim_time:=true
"