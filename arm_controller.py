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
    SERVO_CONFIG,
    DETACH_SETTLE_TIME,
    AUTO_DETACH_BASE,
    AUTO_DETACH_ALL
)


class RoboticArm:
    """
    Lớp điều khiển cánh tay gắp 4 bậc tự do qua PCA9685.
    
    Hỗ trợ:
      - Đảo chiều quay (reverse_direction) cho từng servo độc lập.
      - Tự động ngắt xung (auto_detach) chống trôi/quay tiếp khi đã đến góc.
      - Chuyển động mượt mà (smooth motion interpolation).
    """

    def __init__(self, i2c_address: int = I2C_ADDRESS, oe_pin: Optional[int] = OE_PIN):
        self.i2c_address = i2c_address
        self.oe_pin = oe_pin
        self.oe_gpio_initialized = False

        self._init_oe_pin()

        if ServoKit is None:
            raise ImportError(
                "Chưa cài đặt thư viện adafruit-circuitpython-servokit. "
                "Vui lòng chạy: pip install adafruit-circuitpython-servokit"
            )

        print(f"[PCA9685] Đang kết nối I2C tại địa chỉ 0x{self.i2c_address:02X}...")
        self.kit = ServoKit(channels=16, address=self.i2c_address, frequency=PWM_FREQUENCY)

        # Cấu hình dải xung chuẩn an toàn cho từng servo
        for key, cfg in SERVO_CONFIG.items():
            ch = cfg["channel"]
            self.kit.servo[ch].set_pulse_width_range(cfg["min_pulse"], cfg["max_pulse"])
            self.kit.servo[ch].actuation_range = 180

        # Lưu góc logic hiện tại của các servo
        self.current_angles: Dict[str, float] = {
            key: cfg["home"] for key, cfg in SERVO_CONFIG.items()
        }

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

    def _calculate_hardware_angle(self, servo_key: str, logical_angle: float) -> float:
        """
        Tính toán góc phần cứng thực tế gửi xuống servo dựa trên cấu hình đảo chiều (reverse_direction).
        """
        cfg = SERVO_CONFIG[servo_key]
        if cfg.get("reverse_direction", False):
            # Đảo ngược góc: 0 -> 180, 180 -> 0
            return 180.0 - logical_angle
        return logical_angle

    def _clamp_angle(self, servo_key: str, angle: float) -> float:
        """Kiểm tra và giới hạn góc quay logic trong khoảng an toàn."""
        cfg = SERVO_CONFIG[servo_key]
        min_a, max_a = cfg["min_angle"], cfg["max_angle"]
        if angle < min_a:
            print(f"[Cảnh báo] {cfg['name']}: Góc {angle}° < {min_a}°. Tự động gán = {min_a}°")
            return float(min_a)
        if angle > max_a:
            print(f"[Cảnh báo] {cfg['name']}: Góc {angle}° > {max_a}°. Tự động gán = {max_a}°")
            return float(max_a)
        return float(angle)

    def detach_servo(self, servo_key: str):
        """
        Ngắt xung PWM cho một servo cụ thể để dừng quay hoàn toàn và chống rung nóng.
        """
        servo_key = servo_key.upper()
        if servo_key in SERVO_CONFIG:
            ch = SERVO_CONFIG[servo_key]["channel"]
            try:
                self.kit.servo[ch].fraction = None
            except Exception:
                try:
                    self.kit._pca.channels[ch].duty_cycle = 0
                except Exception:
                    pass

    def set_angle_instant(self, servo_key: str, angle: float, auto_detach: Optional[bool] = None):
        """Đặt góc ngay lập tức cho 1 servo."""
        servo_key = servo_key.upper()
        if servo_key not in SERVO_CONFIG:
            raise ValueError(f"Tên servo không hợp lệ: {servo_key}.")

        target_angle = self._clamp_angle(servo_key, angle)
        hw_angle = self._calculate_hardware_angle(servo_key, target_angle)
        channel = SERVO_CONFIG[servo_key]["channel"]
        
        self.kit.servo[channel].angle = hw_angle
        self.current_angles[servo_key] = target_angle

        # Kiểm tra tự động ngắt xung
        should_detach = auto_detach if auto_detach is not None else SERVO_CONFIG[servo_key].get("auto_detach", False)
        if should_detach or AUTO_DETACH_ALL or (servo_key == "BASE" and AUTO_DETACH_BASE):
            time.sleep(DETACH_SETTLE_TIME)
            self.detach_servo(servo_key)

    def move_smooth(
        self,
        servo_key: str,
        target_angle: float,
        speed: float = 1.0,
        steps: int = 30,
        auto_detach: Optional[bool] = None
    ):
        """
        Di chuyển 1 servo mượt mà từ góc hiện tại tới góc đích.
        """
        servo_key = servo_key.upper()
        target_angle = self._clamp_angle(servo_key, target_angle)
        current_angle = self.current_angles[servo_key]

        if abs(target_angle - current_angle) < 0.5:
            return

        channel = SERVO_CONFIG[servo_key]["channel"]
        delta = (target_angle - current_angle) / steps
        delay = max(0.005, (0.03 / max(0.1, speed)))

        for step in range(1, steps + 1):
            inter_angle = current_angle + (delta * step)
            hw_angle = self._calculate_hardware_angle(servo_key, inter_angle)
            self.kit.servo[channel].angle = hw_angle
            time.sleep(delay)

        final_hw_angle = self._calculate_hardware_angle(servo_key, target_angle)
        self.kit.servo[channel].angle = final_hw_angle
        self.current_angles[servo_key] = target_angle

        # Tự động ngắt xung nếu được cấu hình (ngăn xoay tiếp / quay trôi)
        should_detach = auto_detach if auto_detach is not None else SERVO_CONFIG[servo_key].get("auto_detach", False)
        if should_detach or AUTO_DETACH_ALL or (servo_key == "BASE" and AUTO_DETACH_BASE):
            time.sleep(DETACH_SETTLE_TIME)
            self.detach_servo(servo_key)

    def move_all_smooth(
        self,
        base: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
        gripper: Optional[float] = None,
        speed: float = 1.0,
        steps: int = 40,
        detach_base_after: bool = True
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
                hw_a = self._calculate_hardware_angle(k, curr)
                self.kit.servo[SERVO_CONFIG[k]["channel"]].angle = hw_a
            time.sleep(delay)

        for k in targets:
            final_hw = self._calculate_hardware_angle(k, targets[k])
            self.kit.servo[SERVO_CONFIG[k]["channel"]].angle = final_hw
            self.current_angles[k] = targets[k]

        # Ngắt xung cho servo chân đế sau khi di chuyển đồng thời để đế dừng cố định
        if "BASE" in targets and (detach_base_after or AUTO_DETACH_BASE or SERVO_CONFIG["BASE"].get("auto_detach", False)):
            time.sleep(DETACH_SETTLE_TIME)
            self.detach_servo("BASE")

    # --- Các hàm điều khiển nhanh ---

    def set_base(self, angle: float, smooth: bool = True, speed: float = 1.0):
        if smooth:
            self.move_smooth("BASE", angle, speed=speed)
        else:
            self.set_angle_instant("BASE", angle)

    def set_left(self, angle: float, smooth: bool = True, speed: float = 1.0):
        if smooth:
            self.move_smooth("LEFT", angle, speed=speed)
        else:
            self.set_angle_instant("LEFT", angle)

    def set_right(self, angle: float, smooth: bool = True, speed: float = 1.0):
        if smooth:
            self.move_smooth("RIGHT", angle, speed=speed)
        else:
            self.set_angle_instant("RIGHT", angle)

    def set_gripper(self, angle: float, smooth: bool = True, speed: float = 1.2):
        if smooth:
            self.move_smooth("GRIPPER", angle, speed=speed, auto_detach=False)
        else:
            self.set_angle_instant("GRIPPER", angle, auto_detach=False)

    def open_gripper(self, smooth: bool = True):
        open_a = SERVO_CONFIG["GRIPPER"].get("open_angle", 30)
        print(f"[Tay Gắp] Mở kẹp ({open_a}°)...")
        self.set_gripper(open_a, smooth=smooth)

    def close_gripper(self, smooth: bool = True):
        close_a = SERVO_CONFIG["GRIPPER"].get("close_angle", 135)
        print(f"[Tay Gắp] Đóng kẹp chặt ({close_a}°)...")
        self.set_gripper(close_a, smooth=smooth)

    # --- Tư thế chuẩn ---

    def home(self, speed: float = 1.0):
        """Đưa cánh tay về vị trí chuẩn."""
        print("[Robotic Arm] Đang về vị trí Home...")
        self.move_all_smooth(
            base=SERVO_CONFIG["BASE"]["home"],
            left=SERVO_CONFIG["LEFT"]["home"],
            right=SERVO_CONFIG["RIGHT"]["home"],
            gripper=SERVO_CONFIG["GRIPPER"]["home"],
            speed=speed
        )

    def rest(self, speed: float = 0.8):
        """Đưa cánh tay về trạng thái nghỉ."""
        print("[Robotic Arm] Đang về vị trí nghỉ...")
        self.move_all_smooth(
            base=90,
            left=45,
            right=140,
            gripper=SERVO_CONFIG["GRIPPER"].get("open_angle", 30),
            speed=speed
        )

    def pick_and_place_demo(self):
        """Kịch bản mẫu: Gắp và Đặt."""
        print("\n--- BẮT ĐẦU CHU TRÌNH GẮP VÀ ĐẶT (PICK & PLACE DEMO) ---")
        self.home(speed=1.0)
        time.sleep(0.5)

        # Mở kẹp & Quay về điểm A
        self.open_gripper()
        self.set_base(45, speed=1.0)
        time.sleep(0.3)

        # Hạ tay xuống gắp vật
        print("[Hành động] Hạ tay gắp vật tại điểm A...")
        self.move_all_smooth(left=130, right=60, speed=0.8)
        time.sleep(0.5)

        # Kẹp chặt vật thể
        self.close_gripper()
        time.sleep(0.5)

        # Nâng vật lên
        print("[Hành động] Nâng vật lên...")
        self.move_all_smooth(left=80, right=100, speed=0.8)
        time.sleep(0.3)

        # Quay sang điểm B
        print("[Hành động] Di chuyển sang điểm B...")
        self.set_base(135, speed=0.9)
        time.sleep(0.3)

        # Hạ tay tại điểm B
        print("[Hành động] Hạ tay tại điểm B...")
        self.move_all_smooth(left=130, right=60, speed=0.8)
        time.sleep(0.5)

        # Mở kẹp thả vật
        self.open_gripper()
        time.sleep(0.5)

        # Rút tay và về Home
        print("[Hành động] Rút tay và quay về Home...")
        self.move_all_smooth(left=80, right=100, speed=0.8)
        self.home(speed=1.0)
        print("--- HOÀN THÀNH CHU TRÌNH DEMO ---\n")

    def cleanup(self):
        print("[Robotic Arm] Đang dọn dẹp và tắt kết nối...")
        for key in SERVO_CONFIG:
            self.detach_servo(key)
        self.disable_outputs()
        if self.oe_gpio_initialized:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
