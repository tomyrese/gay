"""
Cấu hình thông số phần cứng và kênh điều khiển cho PCA9685 & 4 Servo cánh tay gắp.
"""

# Địa chỉ I2C mặc định của PCA9685
I2C_ADDRESS = 0x40

# Tần số PWM cho Servo tiêu chuẩn (50Hz = chu kỳ 20ms)
PWM_FREQUENCY = 50

# Cấu hình chân OE (Output Enable) trên Raspberry Pi (Tùy chọn)
# Chân OE tích cực mức THẤP (LOW = Bật ngõ ra PWM, HIGH = Tắt / thả trôi servo)
# Nếu nối chân OE trực tiếp xuống GND thì đặt OE_PIN = None
OE_PIN = None  # Ví dụ: 17 nếu cắm vào BCM GPIO 17 (Chân vật lý 11)

# Độ rộng xung tối thiểu và tối đa (microseconds) cho Servo (SG90 / MG90S / MG996R)
# Thường nằm trong khoảng 500us (0 độ) đến 2500us (180 độ)
SERVO_MIN_PULSE = 500
SERVO_MAX_PULSE = 2500

# -------------------------------------------------------------
# PHÂN BỔ KÊNH SERVO TRÊN PCA9685 (0 - 15)
# -------------------------------------------------------------
CHANNELS = {
    "BASE": 0,       # Kênh 0: Servo quay chân (Đế xoay ngang)
    "LEFT": 1,       # Kênh 1: Servo cánh tay trái (Khớp vai / nâng hạ chính)
    "RIGHT": 2,      # Kênh 2: Servo cánh tay phải (Khớp khuỷu / vươn tới)
    "GRIPPER": 3,    # Kênh 3: Servo tay gắp (Kẹp / nhả vật thể)
}

# Giới hạn góc quay an toàn cho từng Servo (độ) để tránh va chạm cơ khí
SERVO_LIMITS = {
    "BASE": {"min": 0, "max": 180, "home": 90, "name": "Servo Quay Chân (Đế)"},
    "LEFT": {"min": 10, "max": 170, "home": 90, "name": "Servo Trái (Khớp Vai)"},
    "RIGHT": {"min": 10, "max": 170, "home": 90, "name": "Servo Phải (Khớp Khuỷu)"},
    "GRIPPER": {"min": 30, "max": 120, "home": 60, "name": "Servo Tay Gắp (Kẹp)"},
}

# Góc gắp và mở của tay gắp
GRIPPER_OPEN_ANGLE = 40    # Góc mở kẹp
GRIPPER_CLOSE_ANGLE = 110  # Góc đóng kẹp (tùy chỉnh vừa lực ép vật thể)
