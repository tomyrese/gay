import time
from gpiozero import DigitalOutputDevice, PWMOutputDevice
from gpiozero import DistanceSensor

PWM_FREQ = 1000

# ==================== TB6612 TRÁI (TB_L) ====================
STBY_L = DigitalOutputDevice(27)   # Pin 13
AIN1_L = DigitalOutputDevice(5)    # Pin 29
AIN2_L = DigitalOutputDevice(6)    # Pin 31
PWMA_L = PWMOutputDevice(13, frequency=PWM_FREQ)  # Pin 33

BIN1_L = DigitalOutputDevice(26)   # Pin 37
BIN2_L = DigitalOutputDevice(22)   # Pin 15
PWMB_L = PWMOutputDevice(19, frequency=PWM_FREQ)  # Pin 35

# ==================== TB6612 PHẢI (TB_R) ====================
STBY_R = DigitalOutputDevice(21)   # Pin 40
PWMA_R = PWMOutputDevice(12, frequency=PWM_FREQ)  # Pin 32
AIN1_R = DigitalOutputDevice(16)   # Pin 36
AIN2_R = DigitalOutputDevice(20)   # Pin 38

PWMB_R = PWMOutputDevice(18, frequency=PWM_FREQ)  # Pin 12
BIN1_R = DigitalOutputDevice(23)   # Pin 16
BIN2_R = DigitalOutputDevice(24)   # Pin 18

# ==================== CẢM BIẾN SIÊU ÂM HC-SR04 (phía trước) ====================
# LƯU Ý: không dùng GPIO2/GPIO3 vì 2 chân này có điện trở kéo lên vật lý
# (không khớp với pull_up=False mặc định của DistanceSensor).
# TRIG -> GPIO17 (chân 11), ECHO -> GPIO4 (chân 7)
TRIG_PIN = 17   # GPIO17 - TRIG (chân ra)
ECHO_PIN = 4    # GPIO4 - ECHO (chân vào)
sensor = DistanceSensor(echo=ECHO_PIN, trigger=TRIG_PIN, max_distance=2.0)


def do_khoang_cach():
    try:
        return sensor.distance * 100  # đơn vị cm
    except Exception:
        return 999.0


def drive_channel(in1, in2, pwm, speed):
    speed = max(-1.0, min(1.0, speed))
    if speed > 0:
        in1.on()
        in2.off()
        pwm.value = speed
    elif speed < 0:
        in1.off()
        in2.on()
        pwm.value = abs(speed)
    else:
        in1.off()
        in2.off()
        pwm.value = 0.0


def set_left(speed):
    drive_channel(AIN1_L, AIN2_L, PWMA_L, speed)
    drive_channel(BIN1_L, BIN2_L, PWMB_L, speed)


def set_right(speed):
    drive_channel(AIN1_R, AIN2_R, PWMA_R, speed)
    drive_channel(BIN1_R, BIN2_R, PWMB_R, speed)


def dung():
    set_left(0)
    set_right(0)


# Tốc độ mặc định nhẹ nhàng (35%)
SLOW_SPEED = 0.35


def tien(speed=SLOW_SPEED):
    set_left(speed)
    set_right(speed)


def lui(speed=SLOW_SPEED):
    set_left(-speed)
    set_right(-speed)


def quay_trai(speed=SLOW_SPEED):
    set_left(-speed)
    set_right(speed)


def quay_phai(speed=SLOW_SPEED):
    set_left(speed)
    set_right(-speed)


# ==================== LOGIC LÁI XE TRÁNH TRƯỚC VẬT/NGƯỜI ====================
STOP_DISTANCE_CM = 30.0   # Khoảng cách an toàn: < 30cm thì dừng
SAFE_DISTANCE_CM = 50.0   # Khoảng cách phục hồi: đủ xa mới chạy lại
BW_TAKE_OFF = 0.04        # Bỏ qua 4 chu kỳ đọc đầu để cảm biến ổn định
READ_INTERVAL = 0.05      # 50ms giữa mỗi lần đọc khoảng cách


def main():
    STBY_L.on()
    STBY_R.on()
    print("TB6612 sẵn sàng.")

    for _ in range(3):
        do_khoang_cach()
        time.sleep(BW_TAKE_OFF)

    print(f"Chạy xe tự động. Dừng khi vật/người gần hơn {STOP_DISTANCE_CM:.0f} cm.")
    try:
        while True:
            distance = do_khoang_cach()
            print(f"Khoảng cách: {distance:6.1f} cm")

            if distance < STOP_DISTANCE_CM:
                dung()
                print(">>> Phát hiện vật/người phía trước - DỪNG XE!")
                while distance < SAFE_DISTANCE_CM:
                    distance = do_khoang_cach()
                    time.sleep(READ_INTERVAL)
                print(">>> Đường đã thoáng, chạy tiếp.")
            else:
                tien()

            time.sleep(READ_INTERVAL)
    except KeyboardInterrupt:
        print("\nDừng bằng Ctrl+C.")
    finally:
        dung()
        STBY_L.off()
        STBY_R.off()
        print("Hoàn thành.")


if __name__ == "__main__":
    main()