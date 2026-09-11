"""
Chương trình chính (Interactive CLI Menu) điều khiển cánh tay gắp 4 bậc tự do qua PCA9685.
"""

import sys
import time
from arm_controller import RoboticArm
from config import SERVO_LIMITS, CHANNELS, GRIPPER_OPEN_ANGLE, GRIPPER_CLOSE_ANGLE


def print_menu():
    print("\n" + "=" * 50)
    print("      ĐIỀU KHIỂN TAY GẮP ROBOT 4-DOF (PCA9685)")
    print("=" * 50)
    print(" [1] Về vị trí chuẩn (Home Pose: 90, 90, 90, 60)")
    print(" [2] Chạy chu trình mẫu (Pick & Place Demo)")
    print(" [3] Điều khiển Servo Quay Chân (Đế)")
    print(" [4] Điều khiển Servo Khớp Trái (Vai)")
    print(" [5] Điều khiển Servo Khớp Phải (Khuỷu)")
    print(" [6] Đóng / Mở Tay Gắp (Gripper)")
    print(" [7] Nhập góc tùy chỉnh cho cả 4 Servo")
    print(" [8] Chạy chế độ quét góc tự động (Auto Sweep Test)")
    print(" [0] Thoát chương trình")
    print("=" * 50)


def test_single_servo(arm: RoboticArm, key: str):
    info = SERVO_LIMITS[key]
    print(f"\n--- {info['name']} (Kênh {CHANNELS[key]}) ---")
    print(f"Giới hạn góc: {info['min']}° đến {info['max']}° | Góc hiện tại: {arm.current_angles[key]}°")
    try:
        val_str = input(f"Nhập góc mong muốn ({info['min']} - {info['max']}) hoặc 'b' để quay lại: ").strip()
        if val_str.lower() == 'b':
            return
        angle = float(val_str)
        arm.move_smooth(key, angle, speed=1.0)
        print(f"-> Đã đặt {info['name']} = {angle}°")
    except ValueError:
        print("Giá trị nhập vào không hợp lệ!")


def manual_4_servos(arm: RoboticArm):
    print("\n--- NHẬP GÓC ĐIỀU KHIỂN CẢ 4 SERVO ---")
    try:
        b_str = input(f"Góc Servo Chân (0-180) [Hiện tại: {arm.current_angles['BASE']}°]: ").strip()
        l_str = input(f"Góc Servo Trái (10-170) [Hiện tại: {arm.current_angles['LEFT']}°]: ").strip()
        r_str = input(f"Góc Servo Phải (10-170) [Hiện tại: {arm.current_angles['RIGHT']}°]: ").strip()
        g_str = input(f"Góc Tay Gắp ({SERVO_LIMITS['GRIPPER']['min']}-{SERVO_LIMITS['GRIPPER']['max']}) [Hiện tại: {arm.current_angles['GRIPPER']}°]: ").strip()

        b = float(b_str) if b_str else None
        l = float(l_str) if l_str else None
        r = float(r_str) if r_str else None
        g = float(g_str) if g_str else None

        arm.move_all_smooth(base=b, left=l, right=r, gripper=g, speed=1.0)
        print("-> Đã cập nhật tọa độ cánh tay thành công!")
    except ValueError:
        print("Lỗi: Vui lòng nhập số thực hợp lệ.")


def sweep_test(arm: RoboticArm):
    print("\n--- CHẠY KIỂM TRA QUÉT GÓC TỰ ĐỘNG ---")
    print("Kiểm tra tuần tự từng servo...")
    
    # Base sweep
    print("1. Quét đế xoay 45° -> 135° -> 90°...")
    arm.move_smooth("BASE", 45, speed=0.8)
    time.sleep(0.3)
    arm.move_smooth("BASE", 135, speed=0.8)
    time.sleep(0.3)
    arm.move_smooth("BASE", 90, speed=0.8)

    # Left / Right sweep
    print("2. Quét khớp tay nâng hạ...")
    arm.move_all_smooth(left=120, right=70, speed=0.8)
    time.sleep(0.5)
    arm.move_all_smooth(left=70, right=120, speed=0.8)
    time.sleep(0.5)
    arm.move_all_smooth(left=90, right=90, speed=0.8)

    # Gripper sweep
    print("3. Quét đóng mở kẹp...")
    arm.open_gripper()
    time.sleep(0.5)
    arm.close_gripper()
    time.sleep(0.5)
    arm.set_gripper(60)

    print("Kiểm tra hoàn tất!")


def main():
    try:
        arm = RoboticArm()
    except Exception as e:
        print(f"\n[Lỗi kết nối] Không thể kết nối với PCA9685: {e}")
        print("Vui lòng kiểm tra dây nối I2C (SDA, SCL), nguồn VCC và bật I2C trên thiết bị (raspi-config).")
        sys.exit(1)

    try:
        # Tự động về vị trí Home khi bắt đầu
        arm.home()

        while True:
            print_menu()
            choice = input("Nhập lựa chọn của bạn (0-8): ").strip()

            if choice == "1":
                arm.home()
            elif choice == "2":
                arm.pick_and_place_demo()
            elif choice == "3":
                test_single_servo(arm, "BASE")
            elif choice == "4":
                test_single_servo(arm, "LEFT")
            elif choice == "5":
                test_single_servo(arm, "RIGHT")
            elif choice == "6":
                print("\n[1] Mở kẹp  |  [2] Đóng kẹp  |  [3] Nhập góc tùy chỉnh")
                sub = input("Lựa chọn: ").strip()
                if sub == "1":
                    arm.open_gripper()
                elif sub == "2":
                    arm.close_gripper()
                elif sub == "3":
                    test_single_servo(arm, "GRIPPER")
            elif choice == "7":
                manual_4_servos(arm)
            elif choice == "8":
                sweep_test(arm)
            elif choice == "0":
                print("Đang thoát chương trình...")
                break
            else:
                print("Lựa chọn không hợp lệ, vui lòng chọn từ 0 đến 8.")

    except KeyboardInterrupt:
        print("\nNhận lệnh ngắt từ bàn phím (Ctrl+C).")
    finally:
        arm.cleanup()
        print("Đã giải phóng tài nguyên. Tạm biệt!")


if __name__ == "__main__":
    main()
