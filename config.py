"""
Cấu hình thông số phần cứng và kênh điều khiển cho PCA9685 & 4 Servo cánh tay gắp.
"""

# Địa chỉ I2C mặc định của PCA9685
I2C_ADDRESS = 0x40

# Tần số PWM cho Servo tiêu chuẩn (50Hz = chu kỳ 20ms)
PWM_FREQUENCY = 50

# Cấu hình chân OE (Output Enable) trên Raspberry Pi (Tùy chọn)
OE_PIN = None  # Đặt số chân BCM (ví dụ: 17) nếu nối OE với GPIO, hoặc None nếu nối thẳng xuống GND

# -------------------------------------------------------------------------
# CẤU HÌNH DẢI XUNG AN TOÀN CHO TỪNG SERVO (Đơn vị: microseconds)
# Khắc phục lỗi servo quay liên tục do tràn dải xung:
# - Dải an toàn tiêu chuẩn cho SG90 / MG90S / MG996R là 600us đến 2400us
# -------------------------------------------------------------------------
SERVO_CONFIG = {
    "BASE": {
        "channel": 0,
        "name": "Servo Quay Chân (Đế)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 0,
        "max_angle": 180,
        "home": 90,
        "is_continuous": False,  # Đặt True nếu bạn dùng servo xoay 360 độ liên tục
        "stop_pulse_360": 1500,  # Xung dừng cho servo 360 độ (thường từ 1480us - 1520us)
    },
    "LEFT": {
        "channel": 1,
        "name": "Servo Trái (Khớp Vai)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "is_continuous": False,
    },
    "RIGHT": {
        "channel": 2,
        "name": "Servo Phải (Khớp Khuỷu)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "is_continuous": False,
    },
    "GRIPPER": {
        "channel": 3,
        "name": "Servo Tay Gắp (Kẹp)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 0,
        "max_angle": 180,
        "home": 60,
        # Góc mở và đóng thực tế (sử dụng calibrate.py để xác định chính xác theo khung cơ khí của bạn)
        "open_angle": 30,    # Góc mở hoàn toàn ngàm kẹp
        "close_angle": 130,  # Góc siết kẹp chặt giữ vật thể (tăng lên nếu chưa kẹp chặt)
        "is_continuous": False,
    },
}
