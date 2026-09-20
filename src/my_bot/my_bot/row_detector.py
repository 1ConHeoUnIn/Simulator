import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class RowDetector(Node):
    def __init__(self):
        super().__init__('row_detector')
        self.bridge = CvBridge()

        # Đăng ký nhận ảnh từ camera
        self.sub_image = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        # Xuất ảnh kèm các vạch nhận diện lên topic để xem trên rqt_image_view
        self.pub_debug_image = self.create_publisher(
            Image,
            '/camera/row_detected',
            10
        )

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        height, width, _ = frame.shape
        debug_frame = frame.copy()

        # 1. Chuyển đổi màu sang không gian HSV để lọc mảng xanh lá
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # 2. Quét từ 20% chiều cao trở xuống để thấy trọn vẹn hai bên tường cây
        roi_start_y = int(height * 0.2)
        roi_mask = mask[roi_start_y:height, :]

        # 3. Luôn vẽ vạch tâm robot (màu xanh dương) ở chính giữa màn hình
        mid_screen = width // 2
        cv2.line(debug_frame, (mid_screen, 0), (mid_screen, height), (255, 0, 0), 2)

        # 4. Tìm các đường viền cây xanh
        contours, _ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        left_x = []
        right_x = []

        for cnt in contours:
            if cv2.contourArea(cnt) > 800:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"]) + roi_start_y

                    # Đánh dấu tâm vùng nhận diện cây
                    cv2.circle(debug_frame, (cx, cy), 6, (0, 255, 255), -1)

                    if cx < mid_screen:
                        left_x.append(cx)
                    else:
                        right_x.append(cx)

        # 5. Nếu phát hiện luống ở cả 2 bên -> vẽ vạch tim màu đỏ
        if left_x and right_x:
            lx = max(left_x)
            rx = min(right_x)
            target_center = (lx + rx) // 2

            cv2.line(debug_frame, (target_center, roi_start_y), (target_center, height), (0, 0, 255), 3)
            cv2.putText(debug_frame, "STATUS: TRACKING", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        else:
            cv2.putText(debug_frame, "STATUS: SEARCHING", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        # 6. Bắn ảnh debug ra ROS 2
        out_msg = self.bridge.cv2_to_imgmsg(debug_frame, encoding='bgr8')
        out_msg.header = msg.header
        self.pub_debug_image.publish(out_msg)

def main(args=None):
    rclpy.init(args=args)
    node = RowDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()