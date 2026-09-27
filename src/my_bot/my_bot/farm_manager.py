#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty
from rclpy.qos import QoSProfile, DurabilityPolicy
import json
import os

class FarmManager(Node):
    def __init__(self):
        super().__init__('farm_manager')

        # Thư mục lưu cấu hình vườn
        self.config_dir = os.path.expanduser('~/robot_ws/src/my_bot/maps')
        self.active_file = os.path.join(self.config_dir, 'active_farm.json')
        os.makedirs(self.config_dir, exist_ok=True)

        latching_qos = QoSProfile(depth=1)
        latching_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        # Topic phát cấu hình hiện tại
        self.current_pub = self.create_publisher(String, '/farm_config/current', latching_qos)

        # Topic nhận yêu cầu lưu từ Web
        self.save_sub = self.create_subscription(String, '/farm_config/save', self.save_callback, 10)

        # Topic nhận yêu cầu gửi lại cấu hình từ Web (khi Web vừa F5)
        self.req_sub = self.create_subscription(Empty, '/farm_config/request', self.request_callback, 10)

        # Phát cấu hình có sẵn khi khởi động
        self.publish_current_config()
        self.get_logger().info('Farm Manager đã sẵn sàng phục vụ lưu trữ cấu hình!')

    def publish_current_config(self):
        msg = String()
        if os.path.exists(self.active_file):
            try:
                with open(self.active_file, 'r') as f:
                    data = json.load(f)
                msg.data = json.dumps(data)
                self.get_logger().info('Đã đọc và phát active_farm.json lên Web.')
            except Exception as e:
                self.get_logger().error(f'Lỗi đọc active_farm.json: {e}')
                msg.data = json.dumps({"status": "EMPTY"})
        else:
            msg.data = json.dumps({"status": "EMPTY"})

        self.current_pub.publish(msg)

    def request_callback(self, msg: Empty):
        self.get_logger().info('Nhận tín hiệu yêu cầu nạp cấu hình từ Web -> Phát lại!')
        self.publish_current_config()

    def save_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
            with open(self.active_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f'Đã lưu thành công cấu hình vào {self.active_file}')
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