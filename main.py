"""
Chương trình chính điều khiển cánh tay gắp 4 bậc tự do qua PCA9685.

Chức năng các khớp (Nhìn từ mặt trước):
- Servo Base    (Kênh 0): Quay chân đế
- Servo Left    (Kênh 1): Nâng hạ cánh tay
- Servo Right   (Kênh 2): Điều khiển góc của cánh tay
- Servo Gripper (Kênh 3): Tay gắp kẹp/mở
"""

import sys
from arm_controller import RoboticArm
from config import SERVO_CONFIG


def print_menu():
    print("\n" + "=" * 60)
    print("        ĐIỀU KHIỂN CÁNH TAY ROBOT 4-DOF (PCA9685)")
    print("=" * 60)
    print(f" [1] Chân Đế (Quay Trái / Phải)          -> Kênh {SERVO_CONFIG['BASE']['channel']}")
    print(f" [2] Servo Left (NÂNG HẠ CÁNH TAY)       -> Kênh {SERVO_CONFIG['LEFT']['channel']}")
    print(f" [3] Servo Right (ĐIỀU KHIỂN GÓC CÁNH TAY)-> Kênh {SERVO_CONFIG['RIGHT']['channel']}")
    print(f" [4] Servo Tay Gắp (Kẹp / Mở)            -> Kênh {SERVO_CONFIG['GRIPPER']['channel']}")
    print("-" * 60)
    print(" [5] Về vị trí chuẩn (Home: 90°, 90°, 90°, 60°)")
    print(" [6] Nhập góc điều khiển cả 4 Servo cùng lúc")
    print(" [7] Đảo chiều quay (Invert) Servo Left hoặc Right")
    print(" [8] Hoán đổi Kênh (Swap Channels) giữa Left <-> Right")
    print(" [9] Thả lỏng toàn bộ (Ngắt xung PWM - Chống nóng servo)")
    print(" [0] Thoát chương trình")
    print("=" * 60)


def control_single_servo(arm: RoboticArm, key: str):
    info = SERVO_CONFIG[key]
    ch = info["channel"]
    min_a = info["min_angle"]
    max_a = info["max_angle"]
    curr = arm.current_angles[key]

    print(f"\n>>> ĐIỀU KHIỂN {info['name'].upper()} (KÊNH {ch}) <<<")
    print(f"Giới hạn: {min_a}° đến {max_a}° | Góc hiện tại: {curr}°")
    
    val_str = input(f"Nhập góc muốn quay tới ({min_a} - {max_a}) hoặc 'b' để quay lại: ").strip()
    if val_str.lower() == 'b' or not val_str:
        return

    try:
        angle = float(val_str)
        # Di chuyển duy nhất servo được chọn
        arm.move_servo(key, angle, smooth=True)
        print(f"-> Đã di chuyển {info['name']} tới {angle}° thành công!")
    except ValueError:
        print("[Lỗi] Vui lòng nhập số thực hợp lệ.")


def control_gripper_menu(arm: RoboticArm):
    print("\n>>> ĐIỀU KHIỂN TAY GẮP (GRIPPER) <<<")
    print(" [1] Mở ngàm kẹp")
    print(" [2] Đóng kẹp chặt giữ vật")
    print(" [3] Nhập góc kẹp tùy chỉnh (0° - 180°)")
    print(" [b] Quay lại")

    choice = input("Lựa chọn: ").strip().lower()
    if choice == '1':
        arm.open_gripper()
    elif choice == '2':
        arm.close_gripper()
    elif choice == '3':
        control_single_servo(arm, "GRIPPER")


def set_all_4_servos(arm: RoboticArm):
    print("\n>>> NHẬP GÓC ĐIỀU KHIỂN 4 KHỚP <<<")
    try:
        b_str = input(f"1. Góc Chân Đế (0-180) [Hiện tại {arm.current_angles['BASE']}°]: ").strip()
        l_str = input(f"2. Góc Nâng Hạ Left (10-170) [Hiện tại {arm.current_angles['LEFT']}°]: ").strip()
        r_str = input(f"3. Góc Tay Right (10-170) [Hiện tại {arm.current_angles['RIGHT']}°]: ").strip()
        g_str = input(f"4. Góc Tay Gắp (0-180) [Hiện tại {arm.current_angles['GRIPPER']}°]: ").strip()

        b = float(b_str) if b_str else None
        l = float(l_str) if l_str else None
        r = float(r_str) if r_str else None
        g = float(g_str) if g_str else None

        arm.move_all(base=b, left=l, right=r, gripper=g, smooth=True)
        print("-> Đã điều khiển 4 khớp thành công!")
    except ValueError:
        print("[Lỗi] Giá trị nhập vào không hợp lệ.")


def toggle_invert_menu():
    print("\n>>> CÀI ĐẶT ĐẢO CHIỀU QUAY (INVERT DIRECTION) <<<")
    print(f" [1] Servo Left (Nâng hạ)   - Hiện tại: reversed = {SERVO_CONFIG['LEFT'].get('reversed', False)}")
    print(f" [2] Servo Right (Góc tay)  - Hiện tại: reversed = {SERVO_CONFIG['RIGHT'].get('reversed', False)}")
    print(f" [3] Servo Base (Chân đế)   - Hiện tại: reversed = {SERVO_CONFIG['BASE'].get('reversed', False)}")
    print(" [b] Quay lại")

    c = input("Chọn servo muốn đổi chiều: ").strip()
    mapping = {'1': 'LEFT', '2': 'RIGHT', '3': 'BASE'}
    if c in mapping:
        k = mapping[c]
        SERVO_CONFIG[k]["reversed"] = not SERVO_CONFIG[k].get("reversed", False)
        print(f"-> Đã đổi {SERVO_CONFIG[k]['name']}: reversed = {SERVO_CONFIG[k]['reversed']}")


def main():
    try:
        arm = RoboticArm()
    except Exception as e:
        print(f"\n[Lỗi kết nối PCA9685] {e}")
        print("Kiểm tra lại dây cắm I2C (SDA, SCL), nguồn VCC và lệnh: sudo i2cdetect -y 1")
        sys.exit(1)

    try:
        while True:
            print_menu()
            choice = input("Nhập lựa chọn của bạn (0-9): ").strip()

            if choice == "1":
                control_single_servo(arm, "BASE")
            elif choice == "2":
                control_single_servo(arm, "LEFT")
            elif choice == "3":
                control_single_servo(arm, "RIGHT")
            elif choice == "4":
                control_gripper_menu(arm)
            elif choice == "5":
                arm.home()
            elif choice == "6":
                set_all_4_servos(arm)
            elif choice == "7":
                toggle_invert_menu()
            elif choice == "8":
                arm.swap_left_right_channels()
            elif choice == "9":
                arm.release_all()
            elif choice == "0":
                print("Đang thoát chương trình...")
                break
            else:
                print("Lựa chọn không hợp lệ, vui lòng chọn từ 0 đến 9.")

    except KeyboardInterrupt:
        print("\nĐã dừng chương trình (Ctrl+C).")
    finally:
        arm.cleanup()
        print("Đã ngắt kết nối an toàn. Tạm biệt!")


if __name__ == "__main__":
    main()
