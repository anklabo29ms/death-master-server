# 📡 TÀI LIỆU REST API (API REFERENCE)

> **Dự án**: `Death Proxy Scanner V1.0.0`  
> **Master Server**: `https://death-proxy-scanner-legit.vercel.app` (Hoặc máy chủ chạy `server.py`)  
> **Định dạng dữ liệu**: Toàn bộ payload gửi và nhận đều chuẩn hóa theo `application/json; charset=utf-8`.

---

## 🔐 1. XÁC THỰC KHÓA BẢN QUYỀN (AUTHENTICATION)

### `POST /api/auth`
Kiểm tra tính hợp lệ của khóa bản quyền (`deathkey`). Hỗ trợ cả khóa VIP vĩnh viễn và khóa Stateless 24h.

#### Request Body:
```json
{
  "key": "DEATH-VIP-LIFETIME-DEMO"
}
```

#### Response Thành công (HTTP 200 - Khóa VIP):
```json
{
  "status": "success",
  "valid": true,
  "type": "vip",
  "expires_at": "Vĩnh viễn",
  "days_left": 9999,
  "message": "Khóa VIP vĩnh viễn hợp lệ!"
}
```

#### Response Thành công (HTTP 200 - Khóa Free 24h):
```json
{
  "status": "success",
  "valid": true,
  "type": "stateless_24h",
  "expires_at": "2026-09-26T12:00:00Z",
  "days_left": 1,
  "message": "Khóa Free 24h hợp lệ!"
}
```

#### Response Thất bại (HTTP 401):
```json
{
  "status": "error",
  "valid": false,
  "message": "Key không tồn tại hoặc đã hết hạn!"
}
```

---

## 🔑 2. HỆ THỐNG CẤP KHÓA 4 BƯỚC (KEY GENERATION PIPELINE)

### `GET /api/getkey/init`
Khởi tạo phiên cấp khóa, trả về câu hỏi toán học Captcha và tham số Proof of Work (PoW).

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "captcha_id": "dcap_1727230000_a1b2c3d4",
  "challenge": "45 + 18 = ?",
  "difficulty": 3,
  "pow_target_prefix": "000"
}
```

---

### `POST /api/getkey/verify`
Xác minh kết quả của từng bước. Được gọi lần lượt qua 4 liên kết.

#### Tham số (Có thể gửi qua Query Params hoặc JSON Body):
| Tham số | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `token` | String | Token phiên hiện tại (Bắt đầu bằng `dgk_...`) |
| `captcha_id` | String | ID Captcha (Chỉ dùng ở Bước 1) |
| `captcha_answer` | String/Number | Đáp án phép tính toán học (Bước 1) |
| `pow_nonce` | Number/String | Số nonce giải mã băm SHA-256 (Bước 1) |
| `discord_verified` | Number (1/0) | Xác nhận đã tham gia Discord (Bước 2) |
| `test_bypass` | Number (1/0) | Cờ kiểm thử nội bộ (Chỉ hoạt động ở localhost) |

#### Response Chuyển bước (HTTP 200 - Bước 1 $\rightarrow$ Bước 2):
```json
{
  "status": "ok",
  "next_step": 2,
  "next_token": "dgk_eyJzdGVwIjoy...d8f7a9",
  "next_url": "/getkey/middle?step=2&token=dgk_..."
}
```

#### Response Cấp khóa hoàn tất (HTTP 200 - Bước 4):
```json
{
  "status": "ok",
  "step": 4,
  "key": "DEATH-24H-ABCD1234EFGH5678",
  "expires_in_hours": 24,
  "message": "Khóa của bạn đã được tạo thành công!"
}
```

---

## ⚡ 3. PHÂN PHÁI NHIỆM VỤ & THU THẬP KẾT QUẢ (TASKS & TELEMETRY)

### `GET /api/tasks?limit=200`
Lấy danh sách các proxy cần kiểm tra từ Master Server. Nếu bộ đệm rỗng, server sẽ tự động nạp tức thì từ kho hạt giống `seeds.py` (0ms).

#### Headers:
- `X-Death-Key`: Khóa bản quyền hợp lệ (Tùy chọn nếu chạy trong mạng nội bộ).

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "count": 200,
  "tasks": [
    "103.152.112.120:80",
    "185.199.229.156:7492",
    "45.140.88.22:9191"
  ]
}
```

---

### `POST /api/submit`
Client gửi kết quả sau khi kiểm tra xong một lô proxy, đồng thời đóng vai trò là gói tin **Heartbeat** đồng bộ số liệu mỗi 2 giây.

#### Request Body:
```json
{
  "client_id": "client_node_win_8888",
  "delta_checked": 50,
  "delta_live": 12,
  "total_checked": 1250,
  "total_live": 340,
  "live_proxies": [
    {
      "proxy": "103.152.112.120:80",
      "proto": "http",
      "latency_ms": 142.5,
      "country": "VN",
      "anonymity": "elite",
      "isp": "VNPT Corp"
    }
  ]
}
```

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "accepted_live": 1,
  "server_total_checked": 1250,
  "server_total_live": 340
}
```

---

### `GET /api/stats`
Lấy số liệu thống kê thời gian thực của toàn bộ mạng lưới để hiển thị lên Web Dashboard.

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "total_checked": 1250,
  "total_live": 340,
  "live_rate_pct": 27.2,
  "active_workers": 3,
  "scan_speed_req_s": 420.5,
  "breakdown": {
    "http": 180,
    "socks4": 60,
    "socks5": 100,
    "elite": 210,
    "residential": 85
  }
}
```

---

### `GET /api/live_proxies`
Lấy danh sách các proxy sống mới nhất được phát hiện trong mạng lưới (Hỗ trợ phân trang và giới hạn số lượng).

#### Query Params:
- `limit`: Số lượng proxy cần lấy (Mặc định `50`, tối đa `500`).
- `proto`: Lọc theo giao thức (`http`, `socks4`, `socks5`).

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "total": 50,
  "proxies": [
    {
      "proxy": "103.152.112.120:80",
      "proto": "http",
      "latency_ms": 142.5,
      "country": "VN",
      "anonymity": "elite",
      "discovered_at": 1727230500
    }
  ]
}
```

---

## 👑 4. QUẢN TRỊ DÀNH CHO ADMIN (ADMIN MANAGEMENT)

### `GET /api/admin/keys`
Liệt kê danh sách tất cả các khóa VIP hiện có trong hệ thống. (Yêu cầu gửi Header `X-Admin-Secret` khớp với `ADMIN_SECRET` hoặc chạy từ localhost).

#### Headers:
- `X-Admin-Secret`: Chuỗi bí mật quản trị của server.

#### Response (HTTP 200):
```json
{
  "status": "ok",
  "keys_count": 5,
  "keys": {
    "DEATH-VIP-LIFETIME-DEMO": {
      "type": "vip",
      "created_at": 1727180000,
      "note": "Khách hàng VIP"
    }
  },
  "whitelist": ["127.0.0.1", "::1"]
}
```
