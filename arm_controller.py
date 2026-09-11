"""
Module điều khiển tay gắp robot 4 bậc tự do (4-DOF Robotic Arm)
sử dụng module mở rộng PWM I2C PCA9685.
"""

import time
import sys
from typing import Optional, Dict

try:
    from adafruit_servokit import ServoKit
except ImportError:
    ServoKit = None

from config import (
    I2C_ADDRESS,
    PWM_FREQUENCY,
    OE_PIN,
    SERVO_MIN_PULSE,
    SERVO_MAX_PULSE,
    CHANNELS,
    SERVO_LIMITS,
    GRIPPER_OPEN_ANGLE,
    GRIPPER_CLOSE_ANGLE
)


class RoboticArm:
    """
    Lớp điều khiển cánh tay gắp 4 bậc tự do qua PCA9685.
    
    Phân bổ kênh:
        - Kênh 0: Servo quay chân (Đế)
        - Kênh 1: Servo trái (Vai)
        - Kênh 2: Servo phải (Khuỷu)
        - Kênh 3: Servo tay gắp (Kẹp)
    """

    def __init__(self, i2c_address: int = I2C_ADDRESS, oe_pin: Optional[int] = OE_PIN):
        """
        Khởi tạo kết nối PCA9685 và thiết lập các góc mặc định.
        """
        self.i2c_address = i2c_address
        self.oe_pin = oe_pin
        self.oe_gpio_initialized = False

        # Khởi tạo chân OE (nếu được cấu hình và chạy trên Linux / Raspberry Pi)
        self._init_oe_pin()

        # Khởi tạo Adafruit ServoKit (16 kênh)
        if ServoKit is None:
            raise ImportError(
                "Chưa cài đặt thư viện adafruit-circuitpython-servokit. "
                "Vui lòng chạy: pip install adafruit-circuitpython-servokit"
            )

        print(f"[PCA9685] Đang khởi tạo kết nối I2C tại địa chỉ 0x{self.i2c_address:02X}...")
        self.kit = ServoKit(channels=16, address=self.i2c_address, frequency=PWM_FREQUENCY)

        # Cấu hình dải xung cho 4 servo
        for key, ch in CHANNELS.items():
            self.kit.servo[ch].set_pulse_width_range(SERVO_MIN_PULSE, SERVO_MAX_PULSE)
            self.kit.servo[ch].actuation_range = 180

        # Lưu góc hiện tại của các servo
        self.current_angles: Dict[str, float] = {
            "BASE": SERVO_LIMITS["BASE"]["home"],
            "LEFT": SERVO_LIMITS["LEFT"]["home"],
            "RIGHT": SERVO_LIMITS["RIGHT"]["home"],
            "GRIPPER": SERVO_LIMITS["GRIPPER"]["home"],
        }

        # Bật ngõ ra OE (kéo xuống LOW)
        self.enable_outputs()

        print("[PCA9685] Khởi tạo thành công 4 kênh Servo!")

    def _init_oe_pin(self):
        """Khởi tạo chân Output Enable (OE) nếu có trên Raspberry Pi."""
        if self.oe_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.oe_pin, GPIO.OUT)
                self.oe_gpio_initialized = True
                print(f"[PCA9685] Đã cấu hình chân OE tại GPIO {self.oe_pin} (BCM)")
            except Exception as e:
                print(f"[Cảnh báo] Không thể khởi tạo GPIO cho chân OE: {e}")

    def enable_outputs(self):
        """Bật ngõ ra PWM trên PCA9685 (Chân OE = LOW)."""
        if self.oe_gpio_initialized and self.oe_pin is not None:
            import RPi.GPIO as GPIO
            GPIO.output(self.oe_pin, GPIO.LOW)
            print("[PCA9685] Đã bật ngõ ra servo (OE = LOW).")

    def disable_outputs(self):
        """Tắt ngõ ra PWM trên PCA9685 (Chân OE = HIGH) để thả lỏng servo / ngắt tải."""
        if self.oe_gpio_initialized and self.oe_pin is not None:
            import RPi.GPIO as GPIO
            GPIO.output(self.oe_pin, GPIO.HIGH)
            print("[PCA9685] Đã ngắt ngõ ra servo (OE = HIGH).")

    def _clamp_angle(self, servo_key: str, angle: float) -> float:
        """Kiểm tra và giới hạn góc quay trong khoảng an toàn."""
        limits = SERVO_LIMITS[servo_key]
        min_a, max_a = limits["min"], limits["max"]
        if angle < min_a:
            print(f"[Cảnh báo] {limits['name']}: Góc {angle}° nhỏ hơn giới hạn {min_a}°. Tự động gán = {min_a}°")
            return float(min_a)
        if angle > max_a:
            print(f"[Cảnh báo] {limits['name']}: Góc {angle}° lớn hơn giới hạn {max_a}°. Tự động gán = {max_a}°")
            return float(max_a)
        return float(angle)

    def set_angle_instant(self, servo_key: str, angle: float):
        """
        Đặt góc ngay lập tức cho 1 servo (không làm mượt).
        Thích hợp cho kiểm tra nhanh hoặc thay đổi góc nhỏ.
        """
        servo_key = servo_key.upper()
        if servo_key not in CHANNELS:
            raise ValueError(f"Tên servo không hợp lệ: {servo_key}. Chọn một trong {list(CHANNELS.keys())}")

        target_angle = self._clamp_angle(servo_key, angle)
        channel = CHANNELS[servo_key]
        self.kit.servo[channel].angle = target_angle
        self.current_angles[servo_key] = target_angle

    def move_smooth(self, servo_key: str, target_angle: float, speed: float = 1.0, steps: int = 30):
        """
        Di chuyển 1 servo một cách mượt mà từ góc hiện tại tới góc đích.
        
        :param servo_key: 'BASE', 'LEFT', 'RIGHT', 'GRIPPER'
        :param target_angle: Góc cần đến (độ)
        :param speed: Hệ số tốc độ (càng lớn càng nhanh, 1.0 = chuẩn)
        :param steps: Số bước chia nhỏ hành trình (nhiều bước = mượt hơn)
        """
        servo_key = servo_key.upper()
        target_angle = self._clamp_angle(servo_key, target_angle)
        current_angle = self.current_angles[servo_key]

        if abs(target_angle - current_angle) < 0.5:
            return

        channel = CHANNELS[servo_key]
        delta = (target_angle - current_angle) / steps
        delay = max(0.005, (0.03 / max(0.1, speed)))

        for step in range(1, steps + 1):
            inter_angle = current_angle + (delta * step)
            self.kit.servo[channel].angle = inter_angle
            time.sleep(delay)

        self.kit.servo[channel].angle = target_angle
        self.current_angles[servo_key] = target_angle

    def move_all_smooth(
        self,
        base: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
        gripper: Optional[float] = None,
        speed: float = 1.0,
        steps: int = 40
    ):
        """
        Điều khiển đồng thời cả 4 servo chuyển động mượt mà cùng lúc.
        """
        targets = {}
        if base is not None:
            targets["BASE"] = self._clamp_angle("BASE", base)
        if left is not None:
            targets["LEFT"] = self._clamp_angle("LEFT", left)
        if right is not None:
            targets["RIGHT"] = self._clamp_angle("RIGHT", right)
        if gripper is not None:
            targets["GRIPPER"] = self._clamp_angle("GRIPPER", gripper)

        if not targets:
            return

        start_angles = {k: self.current_angles[k] for k in targets}
        deltas = {k: (targets[k] - start_angles[k]) / steps for k in targets}
        delay = max(0.005, (0.025 / max(0.1, speed)))

        for step in range(1, steps + 1):
            for k in targets:
                curr = start_angles[k] + (deltas[k] * step)
                self.kit.servo[CHANNELS[k]].angle = curr
            time.sleep(delay)

        for k in targets:
            self.kit.servo[CHANNELS[k]].angle = targets[k]
            self.current_angles[k] = targets[k]

    # --- Các hàm điều khiển nhanh từng servo cụ thể ---

    def set_base(self, angle: float, smooth: bool = True, speed: float = 1.0):
        """Điều khiển Servo quay chân (Đế)."""
        if smooth:
            self.move_smooth("BASE", angle, speed=speed)
        else:
            self.set_angle_instant("BASE", angle)

    def set_left(self, angle: float, smooth: bool = True, speed: float = 1.0):
        """Điều khiển Servo cánh tay trái (Khớp vai)."""
        if smooth:
            self.move_smooth("LEFT", angle, speed=speed)
        else:
            self.set_angle_instant("LEFT", angle)

    def set_right(self, angle: float, smooth: bool = True, speed: float = 1.0):
        """Điều khiển Servo cánh tay phải (Khớp khuỷu)."""
        if smooth:
            self.move_smooth("RIGHT", angle, speed=speed)
        else:
            self.set_angle_instant("RIGHT", angle)

    def set_gripper(self, angle: float, smooth: bool = True, speed: float = 1.2):
        """Điều khiển Servo kẹp tay gắp."""
        if smooth:
            self.move_smooth("GRIPPER", angle, speed=speed)
        else:
            self.set_angle_instant("GRIPPER", angle)

    def open_gripper(self, smooth: bool = True):
        """Mở rộng tay gắp để chuẩn bị đón vật."""
        print("[Tay Gắp] Mở kẹp...")
        self.set_gripper(GRIPPER_OPEN_ANGLE, smooth=smooth)

    def close_gripper(self, smooth: bool = True):
        """Đóng tay gắp để kẹp giữ vật thể."""
        print("[Tay Gắp] Đóng kẹp...")
        self.set_gripper(GRIPPER_CLOSE_ANGLE, smooth=smooth)

    # --- Các tư thế chuẩn (Presets) ---

    def home(self, speed: float = 1.0):
        """Đưa cánh tay về vị trí chuẩn (Home Pose)."""
        print("[Robotic Arm] Đang về vị trí Home (90, 90, 90, 60)...")
        self.move_all_smooth(
            base=SERVO_LIMITS["BASE"]["home"],
            left=SERVO_LIMITS["LEFT"]["home"],
            right=SERVO_LIMITS["RIGHT"]["home"],
            gripper=SERVO_LIMITS["GRIPPER"]["home"],
            speed=speed
        )

    def rest(self, speed: float = 0.8):
        """Đưa cánh tay về trạng thái nghỉ (gập gọn)."""
        print("[Robotic Arm] Đang về vị trí nghỉ (Rest Pose)...")
        self.move_all_smooth(base=90, left=45, right=140, gripper=GRIPPER_OPEN_ANGLE, speed=speed)

    def pick_and_place_demo(self):
        """Kịch bản mẫu: Gắp vật thể từ điểm A (bên trái) và đặt sang điểm B (bên phải)."""
        print("\n--- BẮT ĐẦU CHU TRÌNH GẮP VÀ ĐẶT (PICK & PLACE DEMO) ---")
        
        # 1. Về vị trí Home
        self.home(speed=1.0)
        time.sleep(0.5)

        # 2. Mở kẹp & Quay về điểm A (Trái: 45 độ)
        self.open_gripper()
        self.set_base(45, speed=1.0)
        time.sleep(0.3)

        # 3. Hạ tay xuống gắp vật
        print("[Hành động] Hạ tay gắp vật tại điểm A...")
        self.move_all_smooth(left=130, right=60, speed=0.8)
        time.sleep(0.5)

        # 4. Kẹp vật thể
        self.close_gripper()
        time.sleep(0.5)

        # 5. Nâng vật lên cao
        print("[Hành động] Nâng vật lên...")
        self.move_all_smooth(left=80, right=100, speed=0.8)
        time.sleep(0.3)

        # 6. Quay chân sang điểm B (Phải: 135 độ)
        print("[Hành động] Di chuyển sang điểm B...")
        self.set_base(135, speed=0.9)
        time.sleep(0.3)

        # 7. Hạ tay xuống điểm đặt
        print("[Hành động] Hạ tay tại điểm B...")
        self.move_all_smooth(left=130, right=60, speed=0.8)
        time.sleep(0.5)

        # 8. Mở kẹp thả vật
        self.open_gripper()
        time.sleep(0.5)

        # 9. Rút tay lên và về Home
        print("[Hành động] Rút tay và quay về Home...")
        self.move_all_smooth(left=80, right=100, speed=0.8)
        self.home(speed=1.0)
        print("--- HOÀN THÀNH CHU TRÌNH DEMO ---\n")

    def cleanup(self):
        """Giải phóng tài nguyên và ngắt nguồn PWM nếu cần."""
        print("[Robotic Arm] Đang dọn dẹp và tắt kết nối...")
        self.disable_outputs()
        if self.oe_gpio_initialized:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
