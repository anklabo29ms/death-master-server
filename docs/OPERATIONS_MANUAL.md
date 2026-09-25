# 🛠️ CẨM NANG VẬN HÀNH & TRIỂN KHAI (OPERATIONS MANUAL)

> **Dự án**: `Death Proxy Scanner V1.0.0`  
> **Thương hiệu**: `Created By ! Death Silence - Discord: @qyk3`  
> **Tài liệu**: Hướng dẫn cài đặt, cấu hình, chạy tool, quản lý bản quyền và triển khai hạ tầng.

---

## 💻 1. YÊU CẦU HỆ THỐNG (SYSTEM PREREQUISITES)

- **Hệ điều hành**: Windows 10/11, Linux (Ubuntu 20.04+, Debian 11+), macOS.
- **Python**: Phiên bản `3.10` trở lên (Khuyến nghị `3.12`).
- **Thư viện phụ thuộc**:
  ```bash
  pip install aiohttp rich colorama
  ```
  *(Hoặc cài đặt qua file có sẵn: `pip install -r requirements.txt`)*

---

## ⚡ 2. HƯỚNG DẪN VẬN HÀNH WORKER CLIENT (`client.py`)

### A. Khởi Chạy Nhanh:
Chỉ cần chạy lệnh duy nhất:
```powershell
python client.py
```
- Nếu trong thư mục đã có tệp **`deathkey`** hợp lệ: Tool sẽ tự động chạy quy trình kiểm tra tiền trạm (Pre-Flight Diagnostics) và bắt đầu quét ngay.
- Nếu chưa có tệp hoặc tệp rỗng: Tool sẽ dừng lại và hiển thị bảng hướng dẫn cùng ô nhập trực quan:
  ```text
  ┌─────────────────────────────────────────────────────────────┐
  │ [!] CHƯA TÌM THẤY TỆP KHÓA 'deathkey'                        │
  │ • Lấy Key Free 24h tự động tại:                             │
  │   https://death-proxy-scanner-legit.vercel.app/getkey       │
  │ • Hoặc nhập trực tiếp bên dưới (Tool sẽ tự lưu vào deathkey)│
  └─────────────────────────────────────────────────────────────┘
  👉 Nhập Death Key của bạn: 
  ```

### B. Các Tham Số Dòng Lệnh Nâng Cao (CLI Arguments):
| Tham số | Ý nghĩa | Mặc định | Ví dụ |
| :--- | :--- | :--- | :--- |
| `--server` | Địa chỉ Master Server | `https://death-proxy-scanner-legit.vercel.app` | `--server http://127.0.0.1:8000` |
| `--target` | Endpoint mục tiêu để ping | `http://1.1.1.1/cdn-cgi/trace` | `--target https://httpbin.org/ip` |
| `--concurrency` | Số luồng quét song song | `500` | `--concurrency 1000` |
| `--key` | Khóa bản quyền truyền trực tiếp | Đọc từ `deathkey` | `--key DEATH-VIP-MYKEY-1234` |

*Ví dụ chạy với cấu hình tùy biến:*
```powershell
python client.py --concurrency 1000 --target http://1.1.1.1/cdn-cgi/trace
```

### C. Phím Tắt & Tương Tác Chuột Trong Khi Quét:
Trong khi tool đang chạy, bạn có thể điều khiển trực tiếp trên Terminal:
- `Phím Space`: Tạm dừng (Pause) hoặc Tiếp tục (Resume) quét.
- `Phím +`: Tăng thêm **+50 luồng** quét song song.
- `Phím -`: Giảm bớt **-50 luồng** quét.
- `Phím Q`: Dừng quét an toàn, lưu toàn bộ proxy còn trong hàng đợi và thoát tool.
- **Click Chuột**: Bạn có thể dùng chuột bấm trực tiếp vào các nút `[ Space: || Tạm Dừng ]`, `[ +: +50 Luồng ]`, `[ -: -50 Luồng ]`, `[ Q: ✕ Thoát ]` trên thanh điều khiển dưới đáy màn hình!

---

## 👑 3. HƯỚNG DẪN VẬN HÀNH MASTER SERVER

### A. Chạy Local / Dedicated VPS / Linux Server:
```bash
# Sử dụng script tự động (tự cài thư viện và khởi động)
bash start.sh

# Hoặc khởi chạy thủ công bằng Python:
python server.py --host 0.0.0.0 --port 8000
```

### B. Triển Khai Trên Pterodactyl Panel (Gói 3GB RAM / 15GB SSD):
1. **Startup Command**:
   ```bash
   python server.py --host 0.0.0.0 --port {{SERVER_PORT}}
   ```
2. **Environment Variables**:
   - `PORT`: Đặt bằng port được cấp trên panel (VD: `25565` hoặc `8000`).
   - `MASTER_SECRET_SALT`: Đặt chuỗi bí mật của bạn (VD: `DeathSuperSecretHMACSalt998877`).
   - `TARGET_URL`: Endpoint ping mặc định (VD: `http://1.1.1.1/cdn-cgi/trace`).

### C. Triển Khai Lên Vercel Serverless:
Mã nguồn thư mục `server/` đã được tối ưu hóa cho Vercel qua file cấu hình `server/vercel.json`:
- Đẩy code lên GitHub:
  ```powershell
  cd server
  git push origin main
  ```
- Vercel sẽ tự động build và triển khai endpoint `/api/index.py` trong vòng dưới 30 giây.

---

## 🔑 4. QUẢN LÝ BẢN QUYỀN & KHÓA (LICENSE KEY MANAGEMENT)

### A. Phân Loại Khóa:
1. **Khóa Miễn Phí 24h (`DEATH-24H-...`)**:
   - Người dùng tự lấy tự động qua hệ thống 4 bước tại:  
     `https://death-proxy-scanner-legit.vercel.app/getkey`
   - Khóa có giá trị trong đúng 24 giờ kể từ thời điểm cấp.
   - Được tự động giải mã và kiểm tra hạn sử dụng bằng thuật toán HMAC mà không cần lưu vào database.
2. **Khóa VIP Vĩnh Viễn (`DEATH-VIP-...`)**:
   - Dành cho khách hàng mua VIP qua Discord `@qyk3`.
   - Được lưu trữ vĩnh viễn trong tệp `keys.json` trên Master Server:
     ```json
     {
       "keys": {
         "DEATH-VIP-LIFETIME-DEMO": {
           "type": "vip",
           "created_at": 1727180000,
           "expires_at": null,
           "note": "Khách hàng VIP"
         }
       },
       "whitelist": ["127.0.0.1", "::1"]
     }
     ```

### B. Thêm Khóa VIP Thủ Công:
Mở tệp `server/keys.json` (và bản sao `keys.json` ở root) và thêm mã khóa mới vào mục `"keys"`. Khóa này có hiệu lực ngay lập tức mà không cần khởi động lại server.

---

## 📁 5. CẤU TRÚC TỆP KẾT QUẢ PROXY ĐẦU RA (OUTPUT FILES)

Sau khi quét, client sẽ tự động lưu và phân loại proxy vào các tệp text trong thư mục chạy:

| Tên tệp | Nội dung & Định dạng | Mục đích sử dụng |
| :--- | :--- | :--- |
| **`goodproxies.txt`** | Danh sách IP:Port tất cả proxy sống | Nạp vào các tool bot/crawler chung |
| **`elite_proxies.txt`** | Proxy ẩn danh cao cấp (Elite / High Anonymous) | Dùng cho scraping dữ liệu nhạy cảm |
| **`residential_proxies.txt`** | Proxy mạng dân cư / ISP (Viettel, VNPT, Comcast...) | Vượt mặt Cloudflare, chống ban tài khoản |
| **`live_http.txt`** | Proxy giao thức HTTP / HTTPS | Sử dụng cho web requests / trình duyệt |
| **`live_socks4.txt`** | Proxy giao thức SOCKS4 | Dùng cho game client / phần mềm cũ |
| **`live_socks5.txt`** | Proxy giao thức SOCKS5 hỗ trợ UDP / DNS Remote | Dùng cho proxy tools, VPN, Telegram |
| **`live_detailed.txt`** | Báo cáo chi tiết định dạng JSON Lines | Chứa đầy đủ: Latency, Country, ISP, Anonymity |
