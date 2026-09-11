"""
Ví dụ cơ bản điều khiển 4 Servo tay gắp sử dụng PCA9685.
Đã cập nhật:
- Hoán đổi kênh: Servo Trái (Kênh 2), Servo Phải (Kênh 1)
- Chống chân đế quay trôi: Tự ngắt xung (detach) chân đế sau khi đã quay tới góc đích.
"""

import time
from adafruit_servokit import ServoKit

# 1. Khởi tạo PCA9685
kit = ServoKit(channels=16, address=0x40)

# 2. Cấu hình dải xung an toàn (600us - 2400us) cho 4 kênh
for channel in range(4):
    kit.servo[channel].set_pulse_width_range(600, 2400)
    kit.servo[channel].actuation_range = 180

# 3. Phân bổ kênh Servo (ĐÃ ĐẢO KÊNH LEFT & RIGHT THEO YÊU CẦU)
CH_BASE = 0      # Kênh 0: Servo quay chân (Đế)
CH_RIGHT = 1     # Kênh 1: Servo Phải (Khuỷu)
CH_LEFT = 2      # Kênh 2: Servo Trái (Vai)
CH_GRIPPER = 3   # Kênh 3: Servo Tay Gắp (Kẹp)

GRIPPER_OPEN = 30
GRIPPER_CLOSE = 135

def set_base_angle(angle):
    """Quay chân đế tới góc mong muốn và tự ngắt xung để dừng hẳn, không quay tiếp."""
    kit.servo[CH_BASE].angle = angle
    # Chờ 0.4s để servo quay tới nơi rồi ngắt xung PWM thả trôi
    time.sleep(0.4)
    kit.servo[CH_BASE].fraction = None

def set_arm_pose(base, left, right, gripper):
    """Đặt góc cho cả 4 servo (có đảo chiều góc cho Left và Right)."""
    # Đảo chiều góc (180 - angle) cho 2 khớp vai và khuỷu
    actual_left = 180 - left
    actual_right = 180 - right

    kit.servo[CH_BASE].angle = base
    kit.servo[CH_LEFT].angle = actual_left
    kit.servo[CH_RIGHT].angle = actual_right
    kit.servo[CH_GRIPPER].angle = gripper
    time.sleep(0.4)
    # Ngắt xung chân đế để đế đứng yên không bị xoay tiếp
    kit.servo[CH_BASE].fraction = None
    print(f"-> Base: {base}°, Left: {left}°, Right: {right}°, Gripper: {gripper}°")

def main():
    print("=== BẮT ĐẦU CHẠY THỬ NGHIỆM TAY GẮP ROBOT ===")

    # 1. Đưa tất cả về vị trí góc Home (90, 90, 90, 60)
    print("1. Đưa toàn bộ servo về vị trí Home...")
    set_arm_pose(base=90, left=90, right=90, gripper=60)
    time.sleep(1.5)

    # 2. Thử nghiệm quay chân (Base Servo)
    print("2. Test servo quay chân (45° -> 135° -> 90° và DỪNG HẲN)...")
    set_base_angle(45)
    time.sleep(1)
    set_base_angle(135)
    time.sleep(1)
    set_base_angle(90)
    time.sleep(1)

    # 3. Thử nghiệm khớp vai và khớp khuỷu (Left & Right Servos)
    print("3. Test khớp tay nâng hạ...")
    kit.servo[CH_LEFT].angle = 180 - 120
    kit.servo[CH_RIGHT].angle = 180 - 70
    time.sleep(1.5)
    kit.servo[CH_LEFT].angle = 180 - 90
    kit.servo[CH_RIGHT].angle = 180 - 90
    time.sleep(1)

    # 4. Thử nghiệm kẹp và nhả tay gắp (Gripper)
    print(f"4. Test mở ({GRIPPER_OPEN}°) và kẹp chặt ({GRIPPER_CLOSE}°)...")
    kit.servo[CH_GRIPPER].angle = GRIPPER_OPEN
    time.sleep(1.5)
    kit.servo[CH_GRIPPER].angle = GRIPPER_CLOSE
    time.sleep(2)
    kit.servo[CH_GRIPPER].angle = 60
    time.sleep(1)

    print("=== HOÀN THÀNH THỬ NGHIỆM! ===")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình bởi người dùng.")
