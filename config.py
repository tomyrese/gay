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
# TỰ ĐỘNG NGẮT XUNG (AUTO-DETACH) KHI ĐÃ ĐẾN VỊ TRÍ
# Giải quyết triệt để vấn đề: "Chân đế quay đúng vị trí nhưng vẫn quay tiếp"
# Khi bật tính năng này: Sau khi servo quay đến góc đích, code sẽ tự động
# ngắt xung PWM (duty_cycle = 0 / angle = None) để servo dừng hẳn, không bị quay trôi.
# -------------------------------------------------------------------------
AUTO_DETACH_BASE = True     # Tự động ngắt xung cho Servo chân đế sau khi quay xong
AUTO_DETACH_ALL = False     # Tự động ngắt xung cho tất cả các khớp sau khi quay xong
DETACH_SETTLE_TIME = 0.4    # Thời gian chờ (giây) để servo đến vị trí trước khi ngắt xung

# -------------------------------------------------------------------------
# PHÂN BỔ KÊNH VÀ ĐẢO CHIỀU SERVO (SERVO CONFIGURATION)
# ĐÃ ĐẢO NGƯỢC KÊNH VÀ CHIỀU CỦA SERVO LEFT VÀ RIGHT THEO YÊU CẦU:
# - Servo Trái (Left):  Kênh 2 (Đảo chiều reverse_direction = True)
# - Servo Phải (Right): Kênh 1 (Đảo chiều reverse_direction = True)
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
        "reverse_direction": False, # Đặt True nếu muốn đổi chiều quay trái/phải của đế
        "auto_detach": True,        # Tự ngắt xung sau khi quay để không bị quay tiếp
    },
    "LEFT": {
        "channel": 2,               # ĐÃ ĐẢO: Kênh 2 (trước là 1)
        "name": "Servo Trái (Khớp Vai)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "reverse_direction": True,  # ĐÃ ĐẢO CHIỀU QUAY (180 - angle)
        "auto_detach": False,
    },
    "RIGHT": {
        "channel": 1,               # ĐÃ ĐẢO: Kênh 1 (trước là 2)
        "name": "Servo Phải (Khớp Khuỷu)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 10,
        "max_angle": 170,
        "home": 90,
        "reverse_direction": True,  # ĐÃ ĐẢO CHIỀU QUAY (180 - angle)
        "auto_detach": False,
    },
    "GRIPPER": {
        "channel": 3,
        "name": "Servo Tay Gắp (Kẹp)",
        "min_pulse": 600,
        "max_pulse": 2400,
        "min_angle": 0,
        "max_angle": 180,
        "home": 60,
        "open_angle": 30,           # Góc mở rộng kẹp
        "close_angle": 135,         # Góc kẹp chặt vật
        "reverse_direction": False, # Đặt True nếu kẹp bị đảo ngược mở/đóng
        "auto_detach": False,       # Giữ xung PWM để duy trì lực ép giữ vật
    },
}
