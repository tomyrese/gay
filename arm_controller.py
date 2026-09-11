"""
Module điều khiển tay gắp robot 4 bậc tự do (4-DOF Robotic Arm) với PCA9685.

Chức năng các khớp (Nhìn từ mặt trước):
- Servo Base    (Kênh 0): Quay chân đế
- Servo Left    (Kênh 1): Nâng hạ cánh tay
- Servo Right   (Kênh 2): Điều khiển góc cánh tay
- Servo Gripper (Kênh 3): Tay gắp kẹp/mở
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
    DETACH_DELAY,
    AUTO_DETACH_DEFAULT
)


class RoboticArm:
    """
    Lớp điều khiển cánh tay gắp 4 bậc tự do qua PCA9685.
    Không tự động di chuyển servo khi khởi động để đảm bảo an toàn.
    """

    def __init__(self, i2c_address: int = I2C_ADDRESS, oe_pin: Optional[int] = OE_PIN):
        self.i2c_address = i2c_address
        self.oe_pin = oe_pin
        self.oe_gpio_initialized = False

        self._init_oe_pin()

        if ServoKit is None:
            raise ImportError(
                "Chưa cài đặt thư viện adafruit-circuitpython-servokit.\n"
                "Vui lòng chạy lệnh: pip install adafruit-circuitpython-servokit"
            )

        print(f"[PCA9685] Đang kết nối I2C tại địa chỉ 0x{self.i2c_address:02X}...")
        self.kit = ServoKit(channels=16, address=self.i2c_address, frequency=PWM_FREQUENCY)

        # Cấu hình dải xung an toàn cho từng servo
        for key, cfg in SERVO_CONFIG.items():
            ch = cfg["channel"]
            self.kit.servo[ch].set_pulse_width_range(cfg["min_pulse"], cfg["max_pulse"])
            self.kit.servo[ch].actuation_range = 180

        # Khởi tạo góc logic hiện tại (lưu giá trị gần nhất)
        self.current_angles: Dict[str, float] = {
            key: cfg["home"] for key, cfg in SERVO_CONFIG.items()
        }

        self.enable_outputs()
        print("[PCA9685] Khởi tạo thành công! (Tất cả servo đang ở trạng thái chờ)")

    def _init_oe_pin(self):
        """Khởi tạo chân Output Enable (OE) nếu có trên Raspberry Pi."""
        if self.oe_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.oe_pin, GPIO.OUT)
                self.oe_gpio_initialized = True
                print(f"[PCA9685] Đã cấu hình chân OE tại GPIO {self.oe_pin}")
            except Exception as e:
                print(f"[Cảnh báo] Không thể khởi tạo GPIO cho chân OE: {e}")

    def enable_outputs(self):
        """Bật ngõ ra PWM trên PCA9685 (Chân OE = LOW)."""
        if self.oe_gpio_initialized and self.oe_pin is not None:
            import RPi.GPIO as GPIO
            GPIO.output(self.oe_pin, GPIO.LOW)

    def disable_outputs(self):
        """Tắt ngõ ra PWM trên PCA9685 (Chân OE = HIGH)."""
        if self.oe_gpio_initialized and self.oe_pin is not None:
            import RPi.GPIO as GPIO
            GPIO.output(self.oe_pin, GPIO.HIGH)

    def _get_hardware_angle(self, servo_key: str, logical_angle: float) -> float:
        """Tính toán góc thực tế dựa theo cờ đảo chiều (reversed)."""
        cfg = SERVO_CONFIG[servo_key]
        if cfg.get("reversed", False):
            return 180.0 - logical_angle
        return float(logical_angle)

    def _clamp_angle(self, servo_key: str, angle: float) -> float:
        """Giới hạn góc trong khoảng min_angle - max_angle an toàn."""
        cfg = SERVO_CONFIG[servo_key]
        min_a, max_a = cfg["min_angle"], cfg["max_angle"]
        if angle < min_a:
            print(f"[Cảnh báo] {cfg['name']}: Góc {angle}° < {min_a}°. Tự động lấy {min_a}°")
            return float(min_a)
        if angle > max_a:
            print(f"[Cảnh báo] {cfg['name']}: Góc {angle}° > {max_a}°. Tự động lấy {max_a}°")
            return float(max_a)
        return float(angle)

    def release_servo(self, servo_key: str):
        """Ngắt xung PWM cho 1 servo (thả lỏng, chống nóng và chống trôi)."""
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

    def release_all(self):
        """Ngắt xung toàn bộ 4 servo."""
        for key in SERVO_CONFIG:
            self.release_servo(key)
        print("[PCA9685] Đã ngắt xung thả lỏng toàn bộ servo.")

    def move_servo(
        self,
        servo_key: str,
        angle: float,
        smooth: bool = False,
        speed: float = 1.0,
        detach: Optional[bool] = None
    ):
        """
        Di chuyển DUY NHẤT một servo chỉ định, không tác động đến các servo khác.
        
        :param servo_key: 'BASE', 'LEFT', 'RIGHT', 'GRIPPER'
        :param angle: Góc mong muốn (0 - 180 độ)
        :param smooth: True nếu muốn di chuyển mượt mà từng bước
        :param speed: Tốc độ di chuyển khi smooth=True
        :param detach: Tự động ngắt xung sau khi di chuyển xong
        """
        servo_key = servo_key.upper()
        if servo_key not in SERVO_CONFIG:
            raise ValueError(f"Không tìm thấy servo: {servo_key}")

        target_angle = self._clamp_angle(servo_key, angle)
        ch = SERVO_CONFIG[servo_key]["channel"]
        current_angle = self.current_angles[servo_key]

        # Di chuyển mượt hoặc di chuyển ngay lập tức
        if smooth and abs(target_angle - current_angle) > 1.0:
            steps = 20
            delta = (target_angle - current_angle) / steps
            delay = max(0.005, 0.02 / max(0.1, speed))
            for step in range(1, steps + 1):
                inter = current_angle + (delta * step)
                hw_a = self._get_hardware_angle(servo_key, inter)
                self.kit.servo[ch].angle = hw_a
                time.sleep(delay)
        else:
            hw_a = self._get_hardware_angle(servo_key, target_angle)
            self.kit.servo[ch].angle = hw_a

        self.current_angles[servo_key] = target_angle

        # Kiểm tra ngắt xung sau khi quay
        should_detach = detach if detach is not None else SERVO_CONFIG[servo_key].get("auto_detach", False)
        if should_detach:
            time.sleep(DETACH_DELAY)
            self.release_servo(servo_key)

    # --- CÁC HÀM ĐIỀU KHIỂN TỪNG KHỚP CỤ THỂ ---

    def rotate_base(self, angle: float, smooth: bool = False):
        """Điều khiển Servo Quay Chân (Đế xoay ngang)."""
        print(f"[Đế Xoay] Quay tới góc: {angle}°")
        self.move_servo("BASE", angle, smooth=smooth, detach=True)

    def lift_arm(self, angle: float, smooth: bool = False):
        """Điều khiển Servo Trái (Nâng / Hạ cánh tay)."""
        print(f"[Nâng Hạ] Đặt góc nâng: {angle}°")
        self.move_servo("LEFT", angle, smooth=smooth, detach=False)

    def tilt_arm(self, angle: float, smooth: bool = False):
        """Điều khiển Servo Phải (Điều chỉnh góc vươn / khuỷu cánh tay)."""
        print(f"[Góc Cánh Tay] Đặt góc vươn: {angle}°")
        self.move_servo("RIGHT", angle, smooth=smooth, detach=False)

    def set_gripper(self, angle: float, smooth: bool = False):
        """Điều khiển Servo Tay Gắp (Kẹp vật)."""
        print(f"[Tay Gắp] Đặt góc kẹp: {angle}°")
        self.move_servo("GRIPPER", angle, smooth=smooth, detach=False)

    def open_gripper(self):
        """Mở ngàm kẹp."""
        open_a = SERVO_CONFIG["GRIPPER"].get("open_angle", 30)
        print(f"[Tay Gắp] Mở kẹp ({open_a}°)...")
        self.move_servo("GRIPPER", open_a, smooth=False, detach=False)

    def close_gripper(self):
        """Đóng kẹp chặt giữ vật thể."""
        close_a = SERVO_CONFIG["GRIPPER"].get("close_angle", 135)
        print(f"[Tay Gắp] Đóng kẹp chặt ({close_a}°)...")
        self.move_servo("GRIPPER", close_a, smooth=False, detach=False)

    def move_all(
        self,
        base: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
        gripper: Optional[float] = None,
        smooth: bool = True
    ):
        """Điều khiển phối hợp cả 4 khớp cùng lúc."""
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

        if smooth:
            steps = 25
            start_angles = {k: self.current_angles[k] for k in targets}
            deltas = {k: (targets[k] - start_angles[k]) / steps for k in targets}
            delay = 0.02
            for s in range(1, steps + 1):
                for k in targets:
                    curr = start_angles[k] + (deltas[k] * s)
                    ch = SERVO_CONFIG[k]["channel"]
                    hw_a = self._get_hardware_angle(k, curr)
                    self.kit.servo[ch].angle = hw_a
                time.sleep(delay)

        for k in targets:
            ch = SERVO_CONFIG[k]["channel"]
            hw_a = self._get_hardware_angle(k, targets[k])
            self.kit.servo[ch].angle = hw_a
            self.current_angles[k] = targets[k]

        # Tự động ngắt xung chân đế để không quay tiếp
        if "BASE" in targets and SERVO_CONFIG["BASE"].get("auto_detach", True):
            time.sleep(DETACH_DELAY)
            self.release_servo("BASE")

    def home(self):
        """Đưa toàn bộ 4 servo về vị trí Home chuẩn."""
        print("[Robotic Arm] Đưa cánh tay về vị trí Home (90°, 90°, 90°, 60°)...")
        self.move_all(
            base=SERVO_CONFIG["BASE"]["home"],
            left=SERVO_CONFIG["LEFT"]["home"],
            right=SERVO_CONFIG["RIGHT"]["home"],
            gripper=SERVO_CONFIG["GRIPPER"]["home"],
            smooth=True
        )

    def swap_left_right_channels(self):
        """Hoán đổi kênh giữa Servo Left và Servo Right nếu cắm nhầm dây."""
        ch_left = SERVO_CONFIG["LEFT"]["channel"]
        ch_right = SERVO_CONFIG["RIGHT"]["channel"]
        SERVO_CONFIG["LEFT"]["channel"] = ch_right
        SERVO_CONFIG["RIGHT"]["channel"] = ch_left
        print(f"[Cấu hình] Đã đổi: Servo Left -> Kênh {ch_right} | Servo Right -> Kênh {ch_left}")

    def cleanup(self):
        """Dọn dẹp và ngắt toàn bộ xung."""
        self.release_all()
        self.disable_outputs()
        if self.oe_gpio_initialized:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
