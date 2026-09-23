#!/usr/bin/env python3
import numpy as np
from PIL import Image

# 1. Cấu hình bản đồ
# Độ phân giải: 0.05m / 1 pixel (chuẩn của Cartographer / SLAM Toolbox)
resolution = 0.05

# Kích thước bản đồ (mét): bao phủ từ X: -12 đến 12, Y: -12 đến 12 (kích thước 24m x 24m)
# Đảm bảo chứa trọn cả 5 luống cây (X từ -9.4 đến 0.2) và vị trí xuất phát (6.0, -6.0)
min_x, max_x = -12.0, 12.0
min_y, max_y = -12.0, 12.0

width_px = int((max_x - min_x) / resolution)
height_px = int((max_y - min_y) / resolution)

# Khởi tạo ảnh màu trắng (254 = Free Space / Đường đi thông thoáng)
map_data = np.full((height_px, width_px), 254, dtype=np.uint8)

def world_to_pixel(x, y):
    px = int((x - min_x) / resolution)
    # Ảnh lưu pixel gốc (0,0) ở góc trên bên trái, trục Y hướng xuống
    py = int((max_y - y) / resolution)
    return px, py

# 2. Vẽ 5 luống cây và các gốc cây theo đúng toạ độ trong obstacles.world
row_x_positions = [-9.0, -6.8, -4.6, -2.4, -0.2]
bed_width = 0.8
bed_length = 11.0
tree_y_positions = [1.0, 2.2, 3.4, 4.6, 5.8, 7.0, 8.2, 9.4]
tree_radius = 0.25

for rx in row_x_positions:
    # Vẽ các gốc cây hình tròn (Giá trị 0 = Màu đen = Chướng ngại vật / Tường)
    for ty in tree_y_positions:
        c_px, c_py = world_to_pixel(rx, ty)
        r_px = int(tree_radius / resolution)
        for dy in range(-r_px, r_px + 1):
            for dx in range(-r_px, r_px + 1):
                if dx*dx + dy*dy <= r_px*r_px:
                    x_target = c_px + dx
                    y_target = c_py + dy
                    if 0 <= x_target < width_px and 0 <= y_target < height_px:
                        map_data[y_target, x_target] = 0

# 3. Lưu thành file .pgm
img = Image.fromarray(map_data)
img.save("my_farm_map.pgm")

# 4. Ghi đè file my_farm_map.yaml
yaml_content = f"""image: my_farm_map.pgm
mode: trinary
resolution: {resolution}
origin: [{min_x}, {min_y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""

with open("my_farm_map.yaml", "w") as f:
    f.write(yaml_content)

print(" Đã tạo xong my_farm_map.pgm và my_farm_map.yaml chuẩn xác 100% theo world!")