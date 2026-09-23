#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy
import json
import os

class FarmManager(Node):
    def __init__(self):
        super().__init__('farm_manager')

        # Đường dẫn file cấu hình nội bộ
        self.config_dir = os.path.expanduser('~/robot_ws/src/my_bot/maps')
        self.active_file = os.path.join(self.config_dir, 'active_farm.json')
        os.makedirs(self.config_dir, exist_ok=True)

        # QoS Transient Local để giữ tin nhắn cho Web vừa kết nối
        latching_qos = QoSProfile(depth=1)
        latching_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        # Publisher phát cấu hình hiện tại lên Web
        self.current_pub = self.create_publisher(String, '/farm_config/current', latching_qos)

        # Subscriber nhận cấu hình cập nhật từ Web
        self.save_sub = self.create_subscription(String, '/farm_config/save', self.save_callback, 10)

        # Đọc và gửi cấu hình sẵn có
        self.publish_current_config()
        self.get_logger().info('Farm Manager đã sẵn sàng phục vụ lưu trữ cấu hình!')

    def publish_current_config(self):
        msg = String()
        if os.path.exists(self.active_file):
            try:
                with open(self.active_file, 'r') as f:
                    data = json.load(f)
                msg.data = json.dumps(data)
                self.get_logger().info('Đã tải cấu hình hiện có từ robot.')
            except Exception as e:
                self.get_logger().error(f'Lỗi đọc file cấu hình: {e}')
                msg.data = json.dumps({"status": "EMPTY"})
        else:
            msg.data = json.dumps({"status": "EMPTY"})

        self.current_pub.publish(msg)

    def save_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
            with open(self.active_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f'Đã lưu thành công cấu hình vào {self.active_file}')
            # Phát lại cấu hình mới nhất
            self.publish_current_config()
        except Exception as e:
            self.get_logger().error(f'Lỗi khi lưu cấu hình: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = FarmManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()