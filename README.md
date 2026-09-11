# 🤖 Điều Khiển Tay Gắp Robot 4 Bậc Tự Do (4-DOF Robotic Arm) với PCA9685 & Python

Dự án cung cấp mã nguồn Python điều khiển độc lập từng khớp, không chạy vòng lặp ngầm, chống rung nóng servo và hỗ trợ cân chỉnh toàn diện.

---

## 📌 1. Sơ Đồ Đấu Nối Chân Phần Cứng (Wiring Diagram)

| Chân PCA9685 | Chức năng | Nối tới | Ghi chú quan trọng |
| :--- | :--- | :--- | :--- |
| **VCC** | Nguồn nuôi chip logic | Chân **3.3V** hoặc **5V** (Pin 1 hoặc 2 trên RPi) | Nuôi IC logic PCA9685 |
| **GND** | Mass / Ground | Chân **GND** (Pin 6 trên RPi) **+ Cực Âm (-) Nguồn Ngoài** | ⚠️ **BẮT BUỘC** nối chung GND của RPi và nguồn cấp Servo |
| **SDA** | I2C Data | Chân **SDA / GPIO 2** (Pin 3 trên RPi) | Giao tiếp I2C |
| **SCL / SCK** | I2C Clock | Chân **SCL / GPIO 3** (Pin 5 trên RPi) | Giao tiếp I2C |
| **OE** | Output Enable | Nối **GND** (hoặc GPIO trên RPi) | Tích cực mức THẤP (**LOW** = Xuất xung, **HIGH** = Thả trôi) |
| **V+** (Cọc vít xanh) | Nguồn động lực cho Servo | **Cực Dương (+) Nguồn Ngoài 5V - 6V (3A - 5A)** | ⚠️ **KHÔNG DÙNG 5V CỦA RPI** vì khi kẹp tải nặng sẽ gây sập nguồn RPi! |

---

## 🦾 2. Phân Bổ Kênh Servo (Nhìn Từ Mặt Trước Cánh Tay)

| Kênh (Channel) | Tên Servo | Vai trò chính | Dải góc an toàn |
| :---: | :--- | :--- | :---: |
| **0** | **Servo Quay Chân Đế** | Xoay toàn bộ cánh tay sang trái/phải | `0° - 180°` |
| **1** | **Servo Left (Trái)** | **NÂNG HẠ CÁNH TAY** chính | `10° - 170°` |
| **2** | **Servo Right (Phải)** | **ĐIỀU KHIỂN GÓC CỦA CÁNH TAY** (Vươn/gập) | `10° - 170°` |
| **3** | **Servo Tay Gắp** | Đóng/mở ngàm kẹp giữ vật thể | `30°` (Mở) — `135°` (Kẹp) |

---

## 🛠️ 3. Điểm Cải Tiến Đã Khắc Phục Hoàn Toàn

1. **Không tự động chạy hay lặp lại:**
   - Khi khởi động, toàn bộ servo giữ nguyên vị trí, không tự động chạy demo hoặc di chuyển các servo chưa được chọn.
2. **Điều khiển độc lập từng khớp:**
   - Khi chọn điều khiển Servo Left (Nâng hạ) hoặc Servo Right (Góc tay), chương trình chỉ gửi tín hiệu cho đúng servo đó, không làm rung giật các servo khác.
3. **Chống chân đế tự quay tiếp (Auto-Detach):**
   - Khi chân đế quay đến góc đích, xung PWM sẽ tự động ngắt sau 0.35s giúp chân đế dừng khựng đúng vị trí.
4. **Tùy biến nhanh không cần sửa code (Trong Menu `main.py`):**
   - `[7]` Đổi chiều quay (Invert) trực tiếp.
   - `[8]` Hoán đổi kênh Left <-> Right nhanh nếu cắm nhầm dây.
   - `[9]` Thả lỏng toàn bộ cánh tay (ngắt xung PWM để chống nóng servo).

---

## 💻 4. Hướng Dẫn Sử Dụng

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Điều khiển tương tác từng khớp độc lập
python main.py

# 3. Hoặc kiểm tra đơn giản từng kênh một
python simple_example.py

# 4. Cân chỉnh tay đòn và lực kẹp
python calibrate.py
```
