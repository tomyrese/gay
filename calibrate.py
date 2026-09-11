"""
Công cụ kiểm tra & Cân chỉnh góc (Calibration Tool) cho PCA9685 và 4 Servo.

Chức năng:
1. Đưa tất cả servo về góc 90° để tháo/gắn lại tay đòn cơ khí (Servo Horn Alignment).
2. Tinh chỉnh góc tay gắp từng độ (+1°, -1°, +5°, -5°) để tìm góc kẹp chặt nhất.
3. Kiểm tra servo quay liên tục (phân biệt servo 180° và 360°).
4. Kiểm tra nguồn cấp và thử tải.
"""

import sys
import time

try:
    from adafruit_servokit import ServoKit
except ImportError:
    print("Vui lòng cài đặt thư viện: pip install adafruit-circuitpython-servokit")
    sys.exit(1)

from config import I2C_ADDRESS, PWM_FREQUENCY, SERVO_CONFIG


def init_kit():
    kit = ServoKit(channels=16, address=I2C_ADDRESS, frequency=PWM_FREQUENCY)
    for key, cfg in SERVO_CONFIG.items():
        ch = cfg["channel"]
        kit.servo[ch].set_pulse_width_range(cfg["min_pulse"], cfg["max_pulse"])
        kit.servo[ch].actuation_range = 180
    return kit


def zero_alignment_mode(kit):
    """Đưa toàn bộ 4 servo về đúng 90 độ để lắp ráp tay đòn."""
    print("\n" + "=" * 60)
    print(">>> CHẾ ĐỘ CĂN CHỈNH TAY ĐÒN CƠ KHÍ (SERVO HORN ALIGNMENT) <<<")
    print("=" * 60)
    print("Đang phát xung 90 độ (1500us) cho cả 4 kênh...")
    for key, cfg in SERVO_CONFIG.items():
        ch = cfg["channel"]
        kit.servo[ch].angle = 90
        print(f" -> Kênh {ch} ({cfg['name']}): 90°")
    
    print("\n[HƯỚNG DẪN CƠ KHÍ]:")
    print("1. Tháo ốc gắn tay đòn (càng nhựa) của các servo ra.")
    print("2. Trong lúc servo đang giữ góc 90°, gắn tay đòn vào trục sao cho:")
    print("   - Khớp chân đế: Hướng thẳng về phía trước.")
    print("   - Khớp vai (Trái) & Khớp khuỷu (Phải): Tạo góc vuông 90° cân đối.")
    print("   - Khớp tay gắp: Ở vị trí trung gian giữa mở và đóng.")
    print("3. Siết chặt ốc giữ tay đòn.")
    input("\nNhấn Enter để quay lại menu chính...")


def calibrate_gripper(kit):
    """Cân chỉnh từng bước góc kẹp của tay gắp."""
    ch = SERVO_CONFIG["GRIPPER"]["channel"]
    angle = 60.0
    kit.servo[ch].angle = angle

    print("\n" + "=" * 60)
    print(">>> CÂN CHỈNH GÓC TAY GẮP (GRIPPER CALIBRATION) <<<")
    print("=" * 60)
    print("Phím điều khiển:")
    print("  [w] / [s] : Tăng / Giảm +1°")
    print("  [e] / [d] : Tăng / Giảm +5°")
    print("  [o]       : Đặt làm GÓC MỞ (Open Angle)")
    print("  [c]       : Đặt làm GÓC ĐÓNG KẸP CHẶT (Close Angle)")
    print("  [t]       : Thử nghiệm kẹp và nhả theo 2 góc đã chọn")
    print("  [q]       : Thoát ra Menu")
    print("=" * 60)

    open_a = SERVO_CONFIG["GRIPPER"]["open_angle"]
    close_a = SERVO_CONFIG["GRIPPER"]["close_angle"]

    while True:
        print(f"\n[Tay Gắp Kênh {ch}] Góc hiện tại: {angle:0.1f}° | Đang nhớ: Mở={open_a}° - Kẹp chặt={close_a}°")
        cmd = input("Nhập lệnh (w/s/e/d/o/c/t/q hoặc nhập số góc trực tiếp): ").strip().lower()

        if cmd == 'q':
            break
        elif cmd == 'w':
            angle = min(180.0, angle + 1.0)
        elif cmd == 's':
            angle = max(0.0, angle - 1.0)
        elif cmd == 'e':
            angle = min(180.0, angle + 5.0)
        elif cmd == 'd':
            angle = max(0.0, angle - 5.0)
        elif cmd == 'o':
            open_a = angle
            print(f">> ĐÃ LƯU GÓC MỞ = {open_a}°")
            continue
        elif cmd == 'c':
            close_a = angle
            print(f">> ĐÃ LƯU GÓC KẸP CHẶT = {close_a}°")
            continue
        elif cmd == 't':
            print(f"\n-> Đang thử Mở ({open_a}°)...")
            kit.servo[ch].angle = open_a
            time.sleep(1.5)
            print(f"-> Đang thử Kẹp Chặt ({close_a}°)... Hãy đặt vật vào xem kẹp có chắc không!")
            kit.servo[ch].angle = close_a
            time.sleep(2)
            angle = close_a
            continue
        else:
            try:
                val = float(cmd)
                if 0 <= val <= 180:
                    angle = val
                else:
                    print("Góc phải từ 0 đến 180 độ!")
                    continue
            except ValueError:
                print("Lệnh không hợp lệ!")
                continue

        kit.servo[ch].angle = angle

    print("\n" + "-" * 50)
    print(f"KẾT QUẢ CÂN CHỈNH CHO FILE config.py:")
    print(f'  "open_angle": {int(open_a)},')
    print(f'  "close_angle": {int(close_a)},')
    print("-" * 50)
    input("Nhấn Enter để quay lại...")


def test_continuous_rotation(kit):
    """Kiểm tra xem servo có phải là loại 360 độ quay liên tục hay không."""
    print("\n" + "=" * 60)
    print(">>> KIỂM TRA SERVO 360° QUAY LIÊN TỤC <<<")
    print("=" * 60)
    print("Chọn kênh servo bạn muốn kiểm tra (0=Chân đế, 1=Trái, 2=Phải, 3=Tay gắp):")
    try:
        ch = int(input("Kênh (0-3): ").strip())
    except ValueError:
        return

    print(f"\nĐang phát góc 90° (Điểm dừng 1500us cho kênh {ch})...")
    kit.servo[ch].angle = 90
    print("Quan sát servo:")
    print(" - Nếu là Servo 180°: Nó sẽ quay tới vị trí chính giữa và ĐỨNG YÊN.")
    print(" - Nếu là Servo 360°: Nó sẽ dừng quay (hoặc quay rất chậm nếu bị trôi điểm dừng).")

    time.sleep(1)
    ans = input("\nBạn có muốn thử quay góc 120° (quay nhẹ) trong 1.5 giây rồi dừng về 90° không? (y/n): ")
    if ans.lower() == 'y':
        print("-> Đang phát 120°...")
        kit.servo[ch].angle = 120
        time.sleep(1.5)
        print("-> Trả về 90° (Dừng)...")
        kit.servo[ch].angle = 90
        time.sleep(1)

    print("\n[KẾT LUẬN]:")
    print("Nếu servo của bạn cứ quay vòng tròn liên tục mà không có điểm dừng cơ khí:")
    print("=> Đó là SERVO 360 ĐỘ (Continuous Rotation Servo) hoặc đã bị GÃY BIẾN TRỞ BÊN TRONG.")
    print("=> Đối với cánh tay robot, bạn cần thay bằng SERVO 180 ĐỘ (Góc cố định).")
    input("\nNhấn Enter để quay lại...")


def main():
    try:
        kit = init_kit()
    except Exception as e:
        print(f"Lỗi khởi tạo PCA9685: {e}")
        return

    while True:
        print("\n" + "=" * 55)
        print("     CÔNG CỤ CÂN CHỈNH & KHẮC PHỤC SỰ CỐ SERVO")
        print("=" * 55)
        print(" [1] Đưa toàn bộ về 90° để tháo/gắn lại tay đòn cơ khí")
        print(" [2] Cân chỉnh góc kẹp tay gắp (Khắc phục kẹp không chặt)")
        print(" [3] Kiểm tra chẩn đoán lỗi Servo bị xoay liên tục (360°)")
        print(" [0] Thoát")
        print("=" * 55)

        c = input("Chọn chức năng (0-3): ").strip()
        if c == '1':
            zero_alignment_mode(kit)
        elif c == '2':
            calibrate_gripper(kit)
        elif c == '3':
            test_continuous_rotation(kit)
        elif c == '0':
            break


if __name__ == "__main__":
    main()
