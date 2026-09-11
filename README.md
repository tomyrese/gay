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

## 🦾 2. Phân Bổ Kênh Servo Trên PCA9685

| Kênh (Channel) | Tên Servo | Dải góc an toàn | Góc chuẩn (Home) |
| :---: | :--- | :---: | :---: |
| **0** | **Servo Quay Chân (Đế xoay)** | `0° - 180°` | `90°` |
| **1** | **Servo Trái (Khớp vai)** | `10° - 170°` | `90°` |
| **2** | **Servo Phải (Khớp khuỷu)** | `10° - 170°` | `90°` |
| **3** | **Servo Tay Gắp (Kẹp)** | `0° - 180°` | `30°` (Mở) — `130°` (Kẹp chặt) |

---

## 🛠️ 3. Công Cụ Cân Chỉnh & Khắc Phục Sự Cố (`calibrate.py`)

Chạy công cụ hỗ trợ:
```bash
python calibrate.py
```

### Chức năng:
1. **Chế độ cân cữ cơ khí (Zero Alignment - 90°):** Đưa toàn bộ servo về góc 90° trước khi siết ốc tay đòn cơ khí.
2. **Cân chỉnh tay gắp từng độ (+1°, -1°, +5°, -5°):** Tìm góc đóng/mở chuẩn xác nhất sao cho kẹp vật thật chặt mà không bị nóng servo.
3. **Kiểm tra Servo 360°:** Phát hiện xem servo có bị nhầm loại quay liên tục 360 độ hoặc bị gãy chốt chặn bên trong hay không.

---

## 💻 4. Hướng Dẫn Chạy Các File

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

---

## ⚠️ 5. Khắc Phục Các Hiện Tượng Thường Gặp

### ❌ Hiện tượng 1: Servo quay liên tục không dừng lại
1. **Do dùng nhầm Servo 360°:** Servo 360° không thể điều khiển vị trí góc cố định mà dùng để điều khiển vận tốc. Hãy thay bằng Servo 180° (Position Control).
2. **Do dải xung quá rộng:** Code đã được cập nhật dải xung an toàn `600µs – 2400µs` trong `config.py` để tránh servo bị quá cữ biến trở.
3. **Do mất GND chung:** Kiểm tra xem cực Âm (-) của nguồn ngoài đã được nối chung vào chân GND của Raspberry Pi chưa.

### ❌ Hiện tượng 2: Tay gắp kẹp không chặt / lỏng lẻo
1. **Lắp sai góc tay đòn:** Hãy chạy `python calibrate.py` -> chọn `[1]` để đưa servo về `90°`, sau đó tháo ốc tay đòn kẹp và gắn lại ở vị trí trung gian rồi siết ốc.
2. **Góc kẹp chưa đủ sâu:** Mở `config.py` và tăng `close_angle` lên `130` hoặc `140` (tùy theo cơ cấu kẹp của bạn).
3. **Nguồn cấp yếu (Tụt áp):** Khi kẹp vật, dòng điện tăng vọt. Hãy đảm bảo nguồn cấp cho cọc `V+` đạt từ **5V - 6V (tối thiểu 3A - 5A)** và dây nối đủ to.
