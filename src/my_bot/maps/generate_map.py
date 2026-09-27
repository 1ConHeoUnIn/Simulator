#!/usr/bin/env python3
import os
import json
import yaml
import numpy as np
from PIL import Image

MAPS_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(MAPS_DIR, "active_farm.json")
BASE_MAP_PGM = os.path.join(MAPS_DIR, "my_farm_map.pgm")
BASE_MAP_YAML = os.path.join(MAPS_DIR, "my_farm_map.yaml")

def main():
    # 1. Kiểm tra cấu hình active_farm.json
    if not os.path.exists(CONFIG_FILE):
        print("[LỖI] Không tìm thấy active_farm.json! Vui lòng lưu cấu hình từ Web trước.")
        return

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    if config.get("status") == "EMPTY":
        print("[THÔNG BÁO] Cấu hình đang ở trạng thái EMPTY.")
        print("-> Giữ nguyên bản đồ SLAM gốc, không đè thêm mô đất nào.")
        return

    # 2. Đọc file thông số bản đồ SLAM vừa quét
    if not os.path.exists(BASE_MAP_PGM) or not os.path.exists(BASE_MAP_YAML):
        print("[LỖI] Chưa có bản đồ SLAM gốc (my_farm_map.pgm / yaml)!")
        print("-> Hãy chạy SLAM và lưu map trước bằng map_saver_cli.")
        return

    with open(BASE_MAP_YAML, 'r') as f:
        map_metadata = yaml.safe_load(f)

    resolution = float(map_metadata['resolution'])
    origin = map_metadata['origin']
    origin_x = float(origin[0])
    origin_y = float(origin[1])

    # Đọc ảnh map SLAM
    base_img = Image.open(BASE_MAP_PGM).convert('L')
    map_data = np.array(base_img)
    height_px, width_px = map_data.shape

    # Hàm chuyển tọa độ mét (world) sang tọa độ pixel trên ảnh
    def world_to_pixel(x, y):
        px = int((x - origin_x) / resolution)
        py = int(height_px - 1 - (y - origin_y) / resolution)
        return px, py

    # 3. Trích xuất thông số người dùng nhập từ Web
    num_beds = int(config['numBeds'])
    bed_w = float(config['bedWidth'])
    aisle_w = float(config['aisleWidth'])
    first_bed_x = float(config['firstBedX'])
    bed_start_y = float(config['bedStartY'])
    bed_len = float(config['bedLength'])
    bed_end_y = bed_start_y + bed_len

    pitch = bed_w + aisle_w
    print(f"[*] Đang xử lý: {num_beds} luống, rộng {bed_w}m, rãnh {aisle_w}m, chiều dài {bed_len}m")

    # 4. Tính toán hình học và tô đen tuyệt đối (giá trị 0) cho từng mô đất
    for i in range(num_beds):
        cx = first_bed_x + i * pitch
        x_min = cx - (bed_w / 2.0)
        x_max = cx + (bed_w / 2.0)

        px_start, py_bottom = world_to_pixel(x_min, bed_start_y)
        px_end, py_top = world_to_pixel(x_max, bed_end_y)

        # Chuẩn hóa khoảng pixel
        x0 = max(0, min(px_start, px_end))
        x1 = min(width_px, max(px_start, px_end))
        y0 = max(0, min(py_top, py_bottom))
        y1 = min(height_px, max(py_top, py_bottom))

        # Đè màu đen (0 = vật cản) lên đúng vùng mô đất trên map SLAM
        map_data[y0:y1, x0:x1] = 0
        print(f"  + Luống #{i+1}: Tâm X = {cx:.2f}m -> Khóa pixel [{x0}:{x1}, {y0}:{y1}]")

    # 5. Lưu đè lại ảnh PGM đã được bịt kín luống đất
    result_img = Image.fromarray(map_data)
    result_img.save(BASE_MAP_PGM)
    print("[THÀNH CÔNG] Đã tích hợp các luống đất vào bản đồ SLAM thành công!")

if __name__ == '__main__':
    main()