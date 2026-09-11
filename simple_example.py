"""
Ví dụ cơ bản điều khiển 4 Servo tay gắp sử dụng PCA9685 với thư viện adafruit-circuitpython-servokit.

Sơ đồ kết nối phần cứng:
- VCC -> Chân 3.3V hoặc 5V (Raspberry Pi Pin 1 hoặc Pin 2)
- GND -> Chân GND (Raspberry Pi Pin 6) và Nối chung với GND nguồn ngoài
- SDA -> Chân SDA (Raspberry Pi Pin 3 - GPIO 2)
- SCL / SCK -> Chân SCL (Raspberry Pi Pin 5 - GPIO 3)
- OE  -> Nối GND (hoặc thả nổi nếu mạch có trở kéo xuống)
- V+  -> Cực dương (+) Nguồn ngoài 5V-6V (Tối thiểu 2A - 5A cho 4 Servo)

Phân bổ kênh Servo:
- Kênh 0: Servo quay chân (Đế xoay)
- Kênh 1: Servo trái (Khớp vai)
- Kênh 2: Servo phải (Khớp khuỷu)
- Kênh 3: Servo tay gắp (Kẹp)
"""

import time
from adafruit_servokit import ServoKit

# 1. Khởi tạo PCA9685 với 16 kênh, địa chỉ mặc định 0x40
kit = ServoKit(channels=16, address=0x40)

# 2. Cấu hình dải xung PWM chuẩn (500us - 2500us cho góc 0° - 180°)
for channel in range(4):
    kit.servo[channel].set_pulse_width_range(500, 2500)
    kit.servo[channel].actuation_range = 180

# 3. Định nghĩa các kênh servo
CH_BASE = 0      # Servo quay chân
CH_LEFT = 1      # Servo trái
CH_RIGHT = 2     # Servo phải
CH_GRIPPER = 3   # Servo tay gắp

def set_arm_pose(base, left, right, gripper):
    """Hàm đặt góc trực tiếp cho 4 servo."""
    kit.servo[CH_BASE].angle = base
    kit.servo[CH_LEFT].angle = left
    kit.servo[CH_RIGHT].angle = right
    kit.servo[CH_GRIPPER].angle = gripper
    print(f"-> Base: {base}°, Left: {left}°, Right: {right}°, Gripper: {gripper}°")

def main():
    print("=== BẮT ĐẦU CHẠY THỬ NGHIỆM TAY GẮP ROBOT ===")

    # 1. Đưa tất cả về vị trí góc ban đầu (Home: 90 độ)
    print("1. Đưa toàn bộ servo về vị trí 90 độ (Home)...")
    set_arm_pose(base=90, left=90, right=90, gripper=60)
    time.sleep(2)

    # 2. Thử nghiệm quay chân (Base Servo)
    print("2. Test servo quay chân (Trái 45° -> Phải 135° -> Giữa 90°)...")
    kit.servo[CH_BASE].angle = 45
    time.sleep(1)
    kit.servo[CH_BASE].angle = 135
    time.sleep(1)
    kit.servo[CH_BASE].angle = 90
    time.sleep(1)

    # 3. Thử nghiệm khớp vai và khớp khuỷu (Left & Right Servos)
    print("3. Test khớp tay nâng hạ...")
    kit.servo[CH_LEFT].angle = 120
    kit.servo[CH_RIGHT].angle = 70
    time.sleep(1.5)
    kit.servo[CH_LEFT].angle = 90
    kit.servo[CH_RIGHT].angle = 90
    time.sleep(1)

    # 4. Thử nghiệm kẹp và nhả tay gắp (Gripper)
    print("4. Test mở và đóng kẹp tay gắp...")
    kit.servo[CH_GRIPPER].angle = 40   # Mở kẹp
    time.sleep(1)
    kit.servo[CH_GRIPPER].angle = 110  # Đóng kẹp
    time.sleep(1)
    kit.servo[CH_GRIPPER].angle = 60   # Trạng thái vừa
    time.sleep(1)

    print("=== HOÀN THÀNH THỬ NGHIỆM! ===")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình bởi người dùng.")
