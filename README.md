# 🤖 Điều Khiển Tay Gắp Robot 4 Bậc Tự Do (4-DOF Robotic Arm) với PCA9685 & Python

Dự án cung cấp mã nguồn Python hoàn chỉnh và tài liệu hướng dẫn chi tiết để điều khiển cánh tay robot 4 bậc tự do (4-DOF Arm) sử dụng module giao tiếp I2C PWM **PCA9685** kết nối với **Raspberry Pi** hoặc máy tính nhúng.

---

## 📌 1. Sơ Đồ Đấu Dây Phần Cứng (Wiring Diagram)

Module **PCA9685** giao tiếp qua chuẩn I2C, giúp giảm số chân GPIO cần dùng xuống chỉ còn 2 chân (SDA, SCL) trong khi có thể điều khiển mượt mà tới 16 Servo với độ phân giải PWM 12-bit.

### 🔌 Bảng kết nối các chân PCA9685 với Raspberry Pi & Nguồn Ngoài:

| Chân PCA9685 | Chức năng | Nối tới | Ghi chú quan trọng |
| :--- | :--- | :--- | :--- |
| **VCC** | Nguồn nuôi chip logic | Chân **3.3V** hoặc **5V** (Pin 1 hoặc 2 trên RPi) | Cấp điện cho chip PCA9685 hoạt động |
| **GND** | Nối Mass (Ground) | Chân **GND** (Pin 6 trên RPi) **+ Cực Âm (-) Nguồn Ngoài** | **BẮT BUỘC** phải nối chung GND của RPi và nguồn cấp Servo |
| **SDA** | I2C Data | Chân **SDA / GPIO 2** (Pin 3 trên RPi) | Tín hiệu dữ liệu I2C |
| **SCL / SCK** | I2C Clock | Chân **SCL / GPIO 3** (Pin 5 trên RPi) | Tín hiệu xung nhịp I2C |
| **OE** | Output Enable | Nối **GND** (hoặc GPIO trên RPi để tắt/bật) | Tích cực mức THẤP (**LOW** = Bật xuất xung PWM, **HIGH** = Ngắt ngõ ra/thả trôi servo) |
| **V+** (Cọc vít xanh) | Nguồn động lực cho Servo | **Cực Dương (+) Nguồn Ngoài 5V - 6V (2A - 5A)** | ⚠️ **KHÔNG DÙNG 5V CỦA RASPBERRY PI** vì dòng khởi động của 4 servo sẽ gây sập nguồn RPi! |

---

## 🦾 2. Phân Bổ Kênh Servo Trên PCA9685

Các servo được cắm vào các hàng chân 3-pin (GND - V+ - PWM) trên bo mạch PCA9685:

| Kênh (Channel) | Tên Servo | Chức năng | Dải góc an toàn |
| :---: | :--- | :--- | :---: |
| **0** | **Servo Quay Chân (Đế xoay)** | Xoay toàn bộ thân cánh tay sang trái/phải | `0° - 180°` (Home: `90°`) |
| **1** | **Servo Trái (Khớp vai)** | Nâng hạ cánh tay chính (vai) | `10° - 170°` (Home: `90°`) |
| **2** | **Servo Phải (Khớp khuỷu)** | Vươn ra xa / co lại cánh tay phụ | `10° - 170°` (Home: `90°`) |
| **3** | **Servo Tay Gắp (Kẹp)** | Đóng/mở ngàm kẹp giữ vật thể | `40°` (Mở) - `110°` (Đóng) |

---

## 🚀 3. Cài Đặt và Chuẩn Bị Môi Trường

### Bước 1: Kích hoạt giao tiếp I2C trên Raspberry Pi
```bash
sudo raspi-config
```
> Chọn `Interface Options` -> `I2C` -> `Enable` -> `Yes`. Sau đó khởi động lại Raspberry Pi:
```bash
sudo reboot
```

### Bước 2: Kiểm tra nhận diện module PCA9685
Chạy lệnh quét địa chỉ I2C:
```bash
sudo apt-get install -y i2c-tools
sudo i2cdetect -y 1
```
*Bạn sẽ thấy địa chỉ `40` (và `70`) xuất hiện trong bảng ma trận.*

### Bước 3: Cài đặt các thư viện Python cần thiết
```bash
pip install -r requirements.txt
```

---

## 💻 4. Hướng Dẫn Sử Dụng Mã Nguồn

### 1. Chạy thử nghiệm nhanh (Simple Example)
Tệp `simple_example.py` chứa mã nguồn ngắn gọn, dễ hiểu để kiểm tra nhanh từng chuyển động cơ bản:
```bash
python simple_example.py
```

### 2. Chạy chương trình điều khiển tương tác (Main Interactive Menu)
Tệp `main.py` cung cấp menu dòng lệnh với đầy đủ các tính năng:
```bash
python main.py
```

**Các tính năng trong Menu:**
- `[1]` Về vị trí chuẩn (Home: 90°, 90°, 90°, 60°)
- `[2]` Chạy chu trình mẫu Tự động Gắp và Đặt (Pick & Place Sequence)
- `[3] - [5]` Điều khiển góc độc lập từng khớp (Đế, Khớp Trái, Khớp Phải)
- `[6]` Đóng / Mở nhanh kẹp tay gắp
- `[7]` Nhập góc tùy ý cho cả 4 khớp cùng lúc
- `[8]` Chạy kiểm tra quét góc tự động (Auto Sweep Calibration)

---

## 📂 5. Cấu Trúc Thư Mục Dự Án

```
├── arm_controller.py     # Lớp đối tượng RoboticArm (tính toán chuyển động mượt, an toàn)
├── config.py             # Cấu hình địa chỉ I2C, kênh servo, dải xung và góc giới hạn
├── main.py               # Menu giao diện dòng lệnh tương tác điều khiển
├── simple_example.py     # Ví dụ ngắn gọn chạy thử nghiệm
├── requirements.txt      # Danh sách thư viện phụ thuộc
├── .gitignore            # Bỏ qua các tệp tạm của Python
└── README.md             # Hướng dẫn chi tiết sử dụng và đấu nối
```

---

## ⚡ 6. Lưu Ý Kỹ Thuật Quan Trọng

1. **Chuyển động mượt (Smooth Motion):**
   - Đổi góc tức thì (`instant angle`) ở tốc độ cao có thể làm hỏng bánh răng nhựa của các dòng servo như SG90 hoặc gây giật mạnh.
   - Module `arm_controller.py` đã tích hợp thuật toán chia nhỏ bước di chuyển (`move_smooth` / `move_all_smooth`) giúp cánh tay robot di chuyển mềm mại và êm ái.

2. **Chân OE (Output Enable):**
   - Nếu nối chân `OE` vào một chân GPIO của Raspberry Pi (cấu hình trong `config.py`), bạn có thể lập trình để ngắt nguồn điều khiển PWM khi cánh tay không hoạt động nhằm tiết kiệm điện và chống nóng servo.
   - Nếu không dùng GPIO, hãy nối chân `OE` xuống `GND`.
