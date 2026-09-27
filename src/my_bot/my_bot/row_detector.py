#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraMonitor(Node):
    def __init__(self):
        super().__init__('row_detector')
        
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        self.image_pub = self.create_publisher(
            Image,
            '/camera/row_detected',
            10
        )
        self.bridge = CvBridge()
        self.get_logger().info('Camera Monitor sẵn sàng phục vụ quan sát trực tiếp!')

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            return

        h, w, _ = frame.shape
        mid_x = w // 2

        # Vẽ tâm lái ngắm góc nhìn robot
        cv2.line(frame, (mid_x, 0), (mid_x, h), (255, 0, 0), 2)
        cv2.putText(frame, "CHE DO: GIAM SAT CAMERA", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        self.image_pub.publish(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))

def main(args=None):
    rclpy.init(args=args)
    node = CameraMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()