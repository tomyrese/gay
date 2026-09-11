"""
Ví dụ cơ bản điều khiển 4 Servo tay gắp sử dụng PCA9685.
Đã cấu hình dải xung an toàn (600us - 2400us) để chống servo quay liên tục.
"""

import time
from adafruit_servokit import ServoKit

# 1. Khởi tạo PCA9685 với 16 kênh, địa chỉ 0x40
kit = ServoKit(channels=16, address=0x40)

# 2. Cấu hình dải xung an toàn (600us - 2400us) cho 4 kênh servo
for channel in range(4):
    kit.servo[channel].set_pulse_width_range(600, 2400)
    kit.servo[channel].actuation_range = 180

# 3. Định nghĩa các kênh servo
CH_BASE = 0      # Servo quay chân (Đế)
CH_LEFT = 1      # Servo trái (Vai)
CH_RIGHT = 2     # Servo phải (Khuỷu)
CH_GRIPPER = 3   # Servo tay gắp (Kẹp)

# Góc mở và đóng thực tế của kẹp
GRIPPER_OPEN = 30     # Góc mở rộng kẹp
GRIPPER_CLOSE = 130   # Góc kẹp chặt giữ vật (tăng lên 140 nếu cần kẹp chặt hơn)

def set_arm_pose(base, left, right, gripper):
    kit.servo[CH_BASE].angle = base
    kit.servo[CH_LEFT].angle = left
    kit.servo[CH_RIGHT].angle = right
    kit.servo[CH_GRIPPER].angle = gripper
    print(f"-> Base: {base}°, Left: {left}°, Right: {right}°, Gripper: {gripper}°")

def main():
    print("=== BẮT ĐẦU CHẠY THỬ NGHIỆM TAY GẮP ROBOT ===")

    # 1. Đưa tất cả về vị trí góc Home (90, 90, 90, 60)
    print("1. Đưa toàn bộ servo về vị trí Home...")
    set_arm_pose(base=90, left=90, right=90, gripper=60)
    time.sleep(2)

    # 2. Thử nghiệm quay chân (Base Servo)
    print("2. Test servo quay chân (45° -> 135° -> 90°)...")
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
    print(f"4. Test mở ({GRIPPER_OPEN}°) và kẹp chặt ({GRIPPER_CLOSE}°)...")
    kit.servo[CH_GRIPPER].angle = GRIPPER_OPEN   # Mở rộng
    time.sleep(1.5)
    kit.servo[CH_GRIPPER].angle = GRIPPER_CLOSE  # Kẹp chặt
    time.sleep(2)
    kit.servo[CH_GRIPPER].angle = 60             # Về trạng thái vừa
    time.sleep(1)

    print("=== HOÀN THÀNH THỬ NGHIỆM! ===")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình bởi người dùng.")
