# 🤖 Điều Khiển Tay Gắp Robot 4 Bậc Tự Do (4-DOF Robotic Arm) với PCA9685 & Python

Dự án cung cấp mã nguồn Python hoàn chỉnh, công cụ cân chỉnh chuyên dụng (`calibrate.py`) và tài liệu hướng dẫn xử lý sự cố cho cánh tay robot 4 bậc tự do (4-DOF Arm) sử dụng module **PCA9685** kết nối với **Raspberry Pi**.

---

## 📌 1. Sơ Đồ Đấu Dây Phần Cứng (Wiring Diagram)

| Chân PCA9685 | Chức năng | Nối tới | Ghi chú quan trọng |
| :--- | :--- | :--- | :--- |
| **VCC** | Nguồn nuôi chip logic | Chân **3.3V** hoặc **5V** (Pin 1 hoặc 2 trên RPi) | Nuôi IC logic PCA9685 |
| **GND** | Nối Mass (Ground) | Chân **GND** (Pin 6 trên RPi) **+ Cực Âm (-) Nguồn Ngoài** | ⚠️ **BẮT BUỘC** nối chung GND của RPi và nguồn cấp Servo |
| **SDA** | I2C Data | Chân **SDA / GPIO 2** (Pin 3 trên RPi) | Tín hiệu dữ liệu I2C |
| **SCL / SCK** | I2C Clock | Chân **SCL / GPIO 3** (Pin 5 trên RPi) | Tín hiệu xung nhịp I2C |
| **OE** | Output Enable | Nối **GND** (hoặc GPIO trên RPi) | Tích cực mức THẤP (**LOW** = Bật ngõ ra PWM, **HIGH** = Thả trôi/ngắt tải) |
| **V+** (Cọc vít xanh) | Nguồn động lực cho Servo | **Cực Dương (+) Nguồn Ngoài 5V - 6V (3A - 5A)** | ⚠️ **KHÔNG DÙNG 5V CỦA RPI** vì khi kẹp vật ăn dòng lớn sẽ gây sập nguồn RPi! |

---

## 🦾 2. Phân Bổ Kênh Servo Trên PCA9685 (Đã đảo kênh Left & Right)

| Kênh (Channel) | Tên Servo | Dải góc | Đảo chiều quay (Reverse) | Ghi chú |
| :---: | :--- | :---: | :---: | :--- |
| **0** | **Servo Quay Chân (Đế xoay)** | `0° - 180°` | `False` | Tích hợp **Auto-Detach** (Tự ngắt xung khi đến nơi để dừng hẳn) |
| **1** | **Servo Phải (Khớp khuỷu)** | `10° - 170°` | `True (180° - θ)` | Đã đổi sang Kênh 1 & đảo chiều |
| **2** | **Servo Trái (Khớp vai)** | `10° - 170°` | `True (180° - θ)` | Đã đổi sang Kênh 2 & đảo chiều |
| **3** | **Servo Tay Gắp (Kẹp)** | `0° - 180°` | `False` | `30°` (Mở) — `135°` (Kẹp chặt) |

---

## ⚡ 3. Giải Pháp Xử Lý Các Hiện Tượng Vừa Cập Nhật

### 1. Hiện tượng "Chân đế quay đúng vị trí nhưng vẫn quay tiếp":
- **Nguyên nhân:** PCA9685 tiếp tục phát tín hiệu PWM sau khi lệnh gửi đi. Nếu servo đế là loại 360° hoặc biến trở bị trôi nhẹ, nó sẽ tiếp tục quay mà không dừng lại.
- **Giải pháp:** Đã kích hoạt tính năng **`AUTO_DETACH_BASE = True`** trong `config.py` và `arm_controller.py`. Khi servo chân đế quay đến đúng góc đích, hệ thống sẽ tự động ngắt xung PWM (`fraction = None`), giúp chân đế **dừng lại ngay lập tức và cố định vị trí**.

### 2. Đảo ngược Servo Left và Right:
- Đã hoán đổi: **Servo Phải = Kênh 1**, **Servo Trái = Kênh 2**.
- Đã kích hoạt chế độ **`reverse_direction = True`** (`180 - angle`) cho cả hai khớp nâng hạ giúp chiều nâng/hạ hoạt động đúng theo trực giác và chuyển động đối xứng.

---

## 🛠️ 4. Công Cụ Cân Chỉnh & Kiểm Tra (`calibrate.py`)

```bash
python calibrate.py
```

### Chức năng:
1. **Chế độ căn cữ cơ khí (Zero Alignment - 90°):** Đưa toàn bộ servo về góc 90° trước khi siết ốc tay đòn cơ khí.
2. **Cân chỉnh tay gắp từng độ (+1°, -1°, +5°, -5°):** Tìm góc đóng/mở chuẩn xác nhất sao cho kẹp vật thật chặt.
3. **Kiểm tra Servo 360°:** Kiểm tra servo đế có bị trôi hoặc nhầm loại 360 độ hay không.

---

## 💻 5. Hướng Dẫn Chạy Các File

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Cân chỉnh tay đòn & góc kẹp
python calibrate.py

# 3. Chạy thử nghiệm nhanh
python simple_example.py

# 4. Giao diện điều khiển đầy đủ (Menu CLI)
python main.py
```
