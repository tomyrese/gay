"""
Mã nguồn điều khiển kiểm tra đơn giản và an toàn cho 4 Servo qua PCA9685.
Không tự động chạy vòng lặp; người dùng nhập góc trực tiếp cho từng servo.
"""

import time
from adafruit_servokit import ServoKit

# 1. Khởi tạo PCA9685
kit = ServoKit(channels=16, address=0x40)

# 2. Cấu hình dải xung an toàn
for ch in range(4):
    kit.servo[ch].set_pulse_width_range(600, 2400)
    kit.servo[ch].actuation_range = 180

# 3. Phân bổ kênh Servo (Nhìn từ mặt trước cánh tay)
CH_BASE    = 0   # Kênh 0: Servo Quay Chân Đế
CH_LEFT    = 1   # Kênh 1: Servo Left (NÂNG HẠ CÁNH TAY)
CH_RIGHT   = 2   # Kênh 2: Servo Right (ĐIỀU KHIỂN GÓC CÁNH TAY)
CH_GRIPPER = 3   # Kênh 3: Servo Tay Gắp (Kẹp / Mở)

def set_servo(channel, angle, detach_after=False):
    """Đặt góc cho 1 servo và tùy chọn ngắt xung chống trôi/nóng."""
    kit.servo[channel].angle = angle
    print(f"-> Kênh {channel} đã quay tới {angle}°")
    if detach_after:
        time.sleep(0.35)
        kit.servo[channel].fraction = None
        print(f"-> Đã ngắt xung Kênh {channel} để giữ cố định.")

def main():
    print("=" * 55)
    print("  KIỂM TRA TỪNG SERVO ĐỘC LẬP (KHÔNG CHẠY TỰ ĐỘNG)")
    print("=" * 55)
    print(f" 0: Chân Đế (Kênh {CH_BASE})")
    print(f" 1: Servo Left - Nâng Hạ Cánh Tay (Kênh {CH_LEFT})")
    print(f" 2: Servo Right - Điều Khiển Góc Cánh Tay (Kênh {CH_RIGHT})")
    print(f" 3: Servo Tay Gắp (Kênh {CH_GRIPPER})")
    print("=" * 55)

    while True:
        try:
            ch_str = input("\nChọn kênh muốn test (0, 1, 2, 3) hoặc 'q' để thoát: ").strip()
            if ch_str.lower() == 'q':
                break
            ch = int(ch_str)
            if ch not in [0, 1, 2, 3]:
                print("Chỉ chọn kênh từ 0 đến 3!")
                continue

            angle_str = input(f"Nhập góc cho kênh {ch} (0 - 180 độ): ").strip()
            angle = float(angle_str)
            if not (0 <= angle <= 180):
                print("Góc phải từ 0 đến 180 độ!")
                continue

            # Nếu là chân đế (ch=0), tự động ngắt xung để dừng hẳn không quay tiếp
            detach = (ch == CH_BASE)
            set_servo(ch, angle, detach_after=detach)

        except ValueError:
            print("Giá trị nhập vào không hợp lệ.")
        except KeyboardInterrupt:
            break

    # Giải phóng toàn bộ
    for ch in range(4):
        try:
            kit.servo[ch].fraction = None
        except Exception:
            pass
    print("\nĐã ngắt xung toàn bộ servo. Thoát chương trình.")

if __name__ == "__main__":
    main()
