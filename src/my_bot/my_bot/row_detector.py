#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
import math

class SmartRowArbiter(Node):
    def __init__(self):
        super().__init__('smart_row_arbiter')
        
        # 1. Subscribers
        self.image_sub = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.pose_sub = self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.pose_callback, 10)
        self.nav_cmd_sub = self.create_subscription(Twist, '/cmd_vel_nav', self.nav_cmd_callback, 10)
        
        # 2. Publishers
        self.image_pub = self.create_publisher(Image, '/camera/row_detected', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.bridge = CvBridge()
        
        # Trạng thái hệ thống: NAV_MODE | ALIGNING | BACKING | ROW_TRACKING
        self.state = "NAV_MODE"
        self.last_nav_cmd = Twist()
        
        # Tọa độ và góc hiện tại của robot
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        
        # Tham số luống cây (World toạ độ Y của cửa luống khoảng Y: -1.0 đến 0.5)
        # Các rãnh đi nằm giữa các luống: X = -3.3, -1.1, 1.1, 3.3
        self.aisle_x_targets = [-3.3, -1.1, 1.1, 3.3]
        
        # Cảm biến
        self.cam_error = 0.0
        self.cam_valid = False
        self.lidar_error = 0.0
        self.lidar_valid = False
        self.min_dist_obstacle = 999.0
        
        # Tham số điều khiển
        self.linear_speed = 0.25
        self.kp_cam = 0.0025
        self.kp_lidar = 0.8
        self.w_cam = 0.6
        self.w_lidar = 0.4
        
        # Quản lý thời gian lùi mồi
        self.backing_start_time = None
        
        # Timer 20Hz
        self.timer = self.create_timer(0.05, self.control_loop)

    def nav_cmd_callback(self, msg: Twist):
        self.last_nav_cmd = msg

    def pose_callback(self, msg: PoseWithCovarianceStamped):
        pos = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.robot_x = pos.x
        self.robot_y = pos.y
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.robot_yaw = math.atan2(siny_cosp, cosy_cosp)

    def scan_callback(self, msg: LaserScan):
        angles = np.linspace(msg.angle_min, msg.angle_max, len(msg.ranges))
        ranges = np.array(msg.ranges)
        
        valid_mask = (ranges >= 0.15) & (ranges <= 3.5) & (~np.isnan(ranges))
        left_mask = valid_mask & (angles > np.radians(15)) & (angles < np.radians(90))
        right_mask = valid_mask & (angles > np.radians(-90)) & (angles < np.radians(-15))
        
        left_ranges = ranges[left_mask]
        right_ranges = ranges[right_mask]
        
        front_mask = valid_mask & (angles > np.radians(-20)) & (angles < np.radians(20))
        if np.any(front_mask):
            self.min_dist_obstacle = np.min(ranges[front_mask])
        else:
            self.min_dist_obstacle = 999.0

        if len(left_ranges) > 0 and len(right_ranges) > 0:
            d_left = np.mean(left_ranges)
            d_right = np.mean(right_ranges)
            self.lidar_error = d_right - d_left
            self.lidar_valid = True
        else:
            self.lidar_valid = False

    def image_callback(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            return

        height, width, _ = cv_image.shape
        mid_screen = width // 2

        roi_start_y = int(height * 0.40)
        roi_end_y = int(height * 0.90)
        roi = cv_image[roi_start_y:roi_end_y, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.cam_valid = False
        if contours:
            valid_contours = [c for c in contours if cv2.contourArea(c) > 1500]
            if valid_contours:
                best_c = min(valid_contours, key=lambda c: abs(cv2.moments(c)["m10"] / (cv2.moments(c)["m00"] + 1e-5) - mid_screen))
                M = cv2.moments(best_c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"]) + roi_start_y
                    self.cam_error = cx - mid_screen
                    self.cam_valid = True
                    cv2.circle(cv_image, (cx, cy), 8, (0, 0, 255), -1)

        cv2.line(cv_image, (mid_screen, 0), (mid_screen, height), (255, 0, 0), 2)
        cv2.putText(cv_image, f"STATE: {self.state} (CAM:{self.cam_valid}|LIDAR:{self.lidar_valid})", 
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8'))

    def is_near_entry(self):
        # Khu vực cửa luống: Y nằm trong khoảng -1.5 đến 0.0 và X gần một trong các lối đi
        if -1.5 <= self.robot_y <= 0.0:
            for ax in self.aisle_x_targets:
                if abs(self.robot_x - ax) < 0.6:
                    return True
        return False

    def control_loop(self):
        twist = Twist()
        
        # 1. Trạng thái đi theo Nav2 toàn cục
        if self.state == "NAV_MODE":
            # Nếu xe đi đến gần cửa luống -> Kích hoạt chuỗi căn chỉnh
            if self.is_near_entry():
                self.get_logger().info("Đã đến cửa luống -> Chuyển sang ALIGNING (Xoay hướng)")
                self.state = "ALIGNING"
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                self.cmd_vel_pub.publish(twist)
                return
            else:
                # Chuyển tiếp lệnh từ Nav2
                self.cmd_vel_pub.publish(self.last_nav_cmd)
                return

        # 2. Trạng thái xoay hướng đầu xe thẳng vào luống (Góc yaw lý tưởng ~ pi/2 = 1.57 rad)
        elif self.state == "ALIGNING":
            target_yaw = 1.5708
            yaw_error = target_yaw - self.robot_yaw
            
            # Chuẩn hóa góc sai số về [-pi, pi]
            yaw_error = math.atan2(math.sin(yaw_error), math.cos(yaw_error))
            
            if abs(yaw_error) > 0.08:
                twist.linear.x = 0.0
                twist.angular.z = float(np.clip(1.2 * yaw_error, -0.6, 0.6))
            else:
                self.get_logger().info("Đã xoay thẳng -> Chuyển sang BACKING (Lùi mồi tìm cây)")
                self.state = "BACKING"
                self.backing_start_time = self.get_clock().now()
            self.cmd_vel_pub.publish(twist)
            return

        # 3. Trạng thái lùi nhẹ để hai cảm biến ôm trọn cây đầu tiên
        elif self.state == "BACKING":
            elapsed = (self.get_clock().now() - self.backing_start_time).nanoseconds / 1e9
            # Lùi nhẹ trong 2 giây hoặc đến khi cả 2 cảm biến bắt được cây
            if elapsed < 2.0 and not (self.cam_valid and self.lidar_valid):
                twist.linear.x = -0.12
                twist.angular.z = 0.0
            else:
                self.get_logger().info("Cảm biến đã nhận diện vững vàng -> Chuyển sang ROW_TRACKING")
                self.state = "ROW_TRACKING"
            self.cmd_vel_pub.publish(twist)
            return

        # 4. Trạng thái tự hành bám luống cục bộ
        elif self.state == "ROW_TRACKING":
            # Nếu đi hết chiều dài luống (Y > 9.5m) hoặc mất cả 2 cảm biến liên tục ở cuối hàng -> Trả quyền cho Nav2
            if self.robot_y > 9.5:
                self.get_logger().info("Hết luống cây -> Trả quyền lại cho Nav2")
                self.state = "NAV_MODE"
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                self.cmd_vel_pub.publish(twist)
                return

            # Xử lý bám tâm luống
            if self.min_dist_obstacle < 0.4:
                twist.linear.x = 0.0
                twist.angular.z = 0.0
            elif self.cam_valid and self.lidar_valid:
                w = - (self.w_cam * self.kp_cam * self.cam_error + self.w_lidar * self.kp_lidar * self.lidar_error)
                twist.linear.x = self.linear_speed
                twist.angular.z = float(np.clip(w, -1.0, 1.0))
            elif self.cam_valid:
                w = - (self.kp_cam * self.cam_error)
                twist.linear.x = self.linear_speed
                twist.angular.z = float(np.clip(w, -1.0, 1.0))
            elif self.lidar_valid:
                w = - (self.kp_lidar * self.lidar_error)
                twist.linear.x = self.linear_speed
                twist.angular.z = float(np.clip(w, -1.0, 1.0))
            else:
                twist.linear.x = 0.12
                twist.angular.z = 0.0

            self.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = SmartRowArbiter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop_msg = Twist()
        node.cmd_vel_pub.publish(stop_msg)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()