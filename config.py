"""
Cấu hình chuẩn cho mạch điều khiển PCA9685 và 4 Servo Cánh Tay Robot.

Chức năng các Servo (Nhìn từ mặt trước của cánh tay):
1. BASE    (Kênh 0): Servo Quay Chân Đế (Quay trái / phải)
2. LEFT    (Kênh 1): Servo Trái (Nâng hạ cánh tay chính)
3. RIGHT   (Kênh 2): Servo Phải (Điều khiển góc / vươn gập cánh tay)
4. GRIPPER (Kênh 3): Servo Tay Gắp (Đóng / Mở kẹp)
"""

# Địa chỉ I2C mặc định của PCA9685
I2C_ADDRESS = 0x40

# Tần số PWM cho Servo (50Hz = chu kỳ 20ms)
PWM_FREQUENCY = 50

# Chân OE (Output Enable) trên Raspberry Pi (Tùy chọn, None nếu nối GND)
OE_PIN = None

# Tự động ngắt xung PWM sau khi quay xong để chống rung lắc, chống nóng và chống trôi servo
AUTO_DETACH_DEFAULT = True
DETACH_DELAY = 0.35  # Thời gian chờ servo đến đích trước khi ngắt xung (giây)

# -------------------------------------------------------------------------
# CẤU HÌNH CHI TIẾT 4 SERVO
# -------------------------------------------------------------------------
SERVO_CONFIG = {
    "BASE": {
        "channel": 0,
        "name": "Servo Quay Chân (Đế Xoay)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 0,
        "max_angle": 180,
        "home": 90,
        "reversed": False,      # Đổi thành True nếu quay ngược hướng mong muốn
        "auto_detach": True,    # Luôn ngắt xung để đế dừng khựng đúng vị trí, không quay tiếp
    },
    "LEFT": {
        "channel": 1,
        "name": "Servo Trái (Nâng Hạ Cánh Tay)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "reversed": False,      # Đổi thành True nếu muốn đảo chiều nâng/hạ
        "auto_detach": False,   # Giữ xung nếu muốn cánh tay giữ vị trí trên không mà không bị sụp
    },
    "RIGHT": {
        "channel": 2,
        "name": "Servo Phải (Điều Khiển Góc Cánh Tay)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "reversed": False,      # Đổi thành True nếu muốn đảo chiều góc vươn
        "auto_detach": False,   # Giữ xung để giữ góc cánh tay
    },
    "GRIPPER": {
        "channel": 3,
        "name": "Servo Tay Gắp (Kẹp Vật)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 0,
        "max_angle": 180,
        "home": 60,
        "open_angle": 30,       # Góc mở ngàm kẹp
        "close_angle": 135,     # Góc kẹp chặt vật
        "reversed": False,
        "auto_detach": False,   # Giữ xung để duy trì lực ép giữ vật không bị rơi
    },
}
