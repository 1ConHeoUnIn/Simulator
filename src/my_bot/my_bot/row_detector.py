#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import numpy as np

class RowDetector(Node):
    def __init__(self):
        super().__init__('row_detector')
        
        # Subscriber nhận ảnh từ Camera
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        
        # Subscriber nhận dữ liệu LiDAR
        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        
        # Publishers
        self.image_pub = self.create_publisher(Image, '/camera/row_detected', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.bridge = CvBridge()
        
        # Tham số điều khiển
        self.linear_speed = 0.25      # Tốc độ khi bám luống (m/s)
        self.approach_speed = 0.12    # Tốc độ tiến mồi khi tìm luống (m/s)
        self.kp_cam = 0.0025          # Hệ số lái Camera
        self.kp_lidar = 0.8           # Hệ số lái LiDAR
        
        # Trọng số kết hợp
        self.w_cam = 0.6
        self.w_lidar = 0.4
        
        # Trạng thái cảm biến
        self.cam_error = 0.0
        self.cam_valid = False
        
        self.lidar_error = 0.0
        self.lidar_valid = False
        self.min_dist_obstacle = 999.0
        
        # Timer điều khiển 20Hz
        self.timer = self.create_timer(0.05, self.control_loop)

    def scan_callback(self, msg: LaserScan):
        angles = np.linspace(msg.angle_min, msg.angle_max, len(msg.ranges))
        ranges = np.array(msg.ranges)
        
        # Lọc các điểm hợp lệ trong tầm 0.15m đến 3.5m
        valid_mask = (ranges >= 0.15) & (ranges <= 3.5) & (~np.isnan(ranges))
        
        # Mở rộng vùng quét: Trái (15° -> 90°), Phải (-90° -> -15°)
        left_mask = valid_mask & (angles > np.radians(15)) & (angles < np.radians(90))
        right_mask = valid_mask & (angles > np.radians(-90)) & (angles < np.radians(-15))
        
        left_ranges = ranges[left_mask]
        right_ranges = ranges[right_mask]
        
        # Kiểm tra vật cản trực diện phía trước (-20° -> 20°)
        front_mask = valid_mask & (angles > np.radians(-20)) & (angles < np.radians(20))
        if np.any(front_mask):
            self.min_dist_obstacle = np.min(ranges[front_mask])
        else:
            self.min_dist_obstacle = 999.0

        if len(left_ranges) > 0 and len(right_ranges) > 0:
            d_left = np.mean(left_ranges)
            d_right = np.mean(right_ranges)
            # Sai số lệch tâm
            self.lidar_error = d_right - d_left
            self.lidar_valid = True
        else:
            self.lidar_valid = False

    def image_callback(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Lỗi nạp ảnh: {e}')
            return

        height, width, _ = cv_image.shape
        mid_screen = width // 2

        # Quét vùng 40% - 90% chiều cao ảnh
        roi_start_y = int(height * 0.40)
        roi_end_y = int(height * 0.90)
        roi = cv_image[roi_start_y:roi_end_y, :]

        # Chuyển xám và nhị phân hóa tự động bằng Otsu
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Tìm đường viền
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.cam_valid = False
        if contours:
            # Lọc các contour đủ lớn
            valid_contours = [c for c in contours if cv2.contourArea(c) > 1500]
            if valid_contours:
                # Chọn contour ở gần giữa nhất
                best_c = min(valid_contours, key=lambda c: abs(cv2.moments(c)["m10"] / (cv2.moments(c)["m00"] + 1e-5) - mid_screen))
                M = cv2.moments(best_c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"]) + roi_start_y
                    
                    self.cam_error = cx - mid_screen
                    self.cam_valid = True
                    
                    # Vẽ tâm đường phát hiện từ camera
                    cv2.circle(cv_image, (cx, cy), 8, (0, 0, 255), -1)
                    cv2.line(cv_image, (cx, roi_start_y), (cx, roi_end_y), (0, 0, 255), 2)

        # Vẽ đường tâm của robot
        cv2.line(cv_image, (mid_screen, 0), (mid_screen, height), (255, 0, 0), 2)
        
        # Trạng thái hiển thị
        if self.cam_valid or self.lidar_valid:
            status_txt = "TRACKING"
            color = (0, 255, 0)
        else:
            status_txt = "APPROACHING"
            color = (0, 255, 255)

        cv2.putText(cv_image, f"MODE: {status_txt} (CAM:{self.cam_valid} | LIDAR:{self.lidar_valid})", 
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8'))

    def control_loop(self):
        twist = Twist()
        
        # Vật cản phía trước quá gần -> Phanh khẩn cấp
        if self.min_dist_obstacle < 0.4:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_vel_pub.publish(twist)
            return

        # Tính toán vận tốc theo từng trường hợp
        if self.cam_valid and self.lidar_valid:
            w = - (self.w_cam * self.kp_cam * self.cam_error + self.w_lidar * self.kp_lidar * self.lidar_error)
            twist.linear.x = self.linear_speed
            twist.angular.z = float(np.clip(w, -1.0, 1.0))
        elif self.cam_valid and not self.lidar_valid:
            w = - (self.kp_cam * self.cam_error)
            twist.linear.x = self.linear_speed
            twist.angular.z = float(np.clip(w, -1.0, 1.0))
        elif not self.cam_valid and self.lidar_valid:
            w = - (self.kp_lidar * self.lidar_error)
            twist.linear.x = self.linear_speed
            twist.angular.z = float(np.clip(w, -1.0, 1.0))
        else:
            # Chưa bắt được luống -> Tiến thẳng từ từ để tiếp cận cửa luống
            twist.linear.x = self.approach_speed
            twist.angular.z = 0.0

        self.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = RowDetector()
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