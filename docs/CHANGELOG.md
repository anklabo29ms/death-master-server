# 📜 NHẬT KÝ NÂNG CẤP & SỬA LỖI (CHANGELOG)

Tất cả các thay đổi, sửa đổi kiến trúc và cập nhật tính năng của dự án **Death Proxy Scanner** được ghi chép chi tiết dưới đây.

---

## 🚀 [V1.0.0] — 2026-09-24 & 2026-09-25 (BẢN PHÁT HÀNH TOÀN DIỆN HIỆN TẠI)

### 💎 Các Tính Năng Nổi Bật Mới Thêm:
- **Tệp Khóa Bản Quyền `deathkey` Chuẩn Hóa**:
  - Quy định tên tệp khóa duy nhất là `deathkey` (hoặc `deathkey.txt`).
  - Tự động phát hiện nếu chưa có khóa: Cho phép người dùng nhập trực tiếp tại giao diện Terminal và **tự động lưu vào tệp `deathkey`**.
  - Hỗ trợ nạp khóa qua tham số CLI `--key` hoặc biến môi trường `DEATHKEY`.
- **Hệ Thống Chẩn Đoán Tiền Trạm (Pre-Flight Diagnostics)**:
  - Tự động chạy trước khi vào vòng lặp quét chính:
    1. Kiểm tra kết nối Internet toàn cầu (Cloudflare / Google DNS).
    2. Đo độ trễ RTT tới Master Server.
    3. Kiểm tra tính hợp lệ và thời hạn còn lại của khóa `deathkey`.
    4. Thử nghiệm độ phản hồi của Target URL.
    5. Kiểm tra quyền ghi file đối với các tệp kết quả.
- **Kho Proxy Hạt Giống 0ms (`seeds.py`)**:
  - Nhúng sẵn hơn 3,000 proxy thật vào hệ thống, giải quyết triệt để vấn đề cạn kiệt nhiệm vụ trên Serverless.
- **Đồng Bộ Dữ Liệu Lũy Tích (Monotonic Cumulative Sync)**:
  - Client gửi Heartbeat 2.0s/lần với số liệu tích lũy `total_checked` và `total_live`. Server Dashboard cập nhật theo hàm `max()`, không bao giờ bị nhảy lùi số liệu.
- **Bộ Kiểm Thử Tự Động Toàn Vẹn Hệ Thống (`tests/test_system_integrity.py`)**:
  - Tự động kiểm tra 5 tiêu chí kiến trúc: Đồng nhất HMAC Salt, Bóc tách Vercel Query, Luồng 4 bước & Discord Guard, Cấp phát hạt giống 0ms, Đồng bộ Metric. Đạt tỷ lệ 5/5 (100%).

---

### 🐛 Các Sửa Lỗi Sâu Cực Kỳ Quan Trọng (Deep Bug Fixes):

#### 1. Sửa Lỗi Captcha Link 1: *"Lỗi kết nối máy chủ xác minh!"* & Không Thể Gen Key
- **Commit**: `a730858`
- **Nguyên nhân**: File `vercel.json` rewrite toàn bộ request về `/api/index.py?__orig_path=/$1`. Các tham số query string (`?token=...&pow_nonce=...`) bị giữ lại bên trong `__orig_path` thay vì đưa vào dictionary `query`. Endpoint `/api/getkey/verify` không tìm thấy `token`, trả lỗi HTTP 400 khiến frontend báo lỗi kết nối ảo.
- **Khắc phục**:
  - Thêm logic phân tích lại `__orig_path` bằng `urllib.parse.urlsplit` và `parse_qs` trong `api/index.py`.
  - Bổ sung thư viện SHA-256 Pure-JavaScript fallback trong `getkey_middle.html` cho các môi trường không có HTTPS.
  - Đồng nhất `MASTER_SECRET_SALT` cố định chống lệch chữ ký token giữa các container Lambda.

#### 2. Sửa Lỗi Bypass Xác Thực Discord Tại Link 2
- **Commit**: `a730858`
- **Nguyên nhân**: Kiểm tra IP Whitelist nội bộ (`127.0.0.1`) bị ghép chung vào điều kiện Discord: `sess.get("discord_verified") or is_whitelisted`. Người dùng chạy ở localhost hoặc IP whitelist tự động được xác nhận Discord mà không cần tham gia server.
- **Khắc phục**: Tách biệt hoàn toàn `is_ip_whitelisted` khỏi `discord_verified`. Whitelist chỉ được miễn trừ 300 giây thời gian chờ của Linkvertise, bắt buộc phải tham gia Discord mới được cấp khóa.

#### 3. Sửa Lỗi Quét Proxy Bị Đứng Im / Treo Cứng
- **Commit**: `a730858`
- **Nguyên nhân**: Vercel Serverless đóng băng luồng cào ngầm. Khi task buffer hết, server cố kết nối 10 link ngoài bị timeout 10 giây. Client không nhận được task nên chuyển sang trạng thái nhàn rỗi.
- **Khắc phục**: Cấp phát tức thì 1,200 proxy từ kho hạt giống `seeds.py` (0ms). Bổ sung hàm tự cào dự phòng `fallback_client_harvest()` trên client.

#### 4. Sửa Lỗi Màn Hình Terminal "Thải Rác", Lặp Nút & Rách Viền Bảng
- **Commit**: `d45aea5`, `dd85459`
- **Nguyên nhân**: Số dòng bảng vẽ vượt quá chiều cao 24 dòng của console Windows gây cuộn màn hình; thiếu lệnh xóa rác `\033[J`; Emoji quốc kỳ 2-cell gây sai lệch căn lề Rich table.
- **Khắc phục**:
  - Chuyển sang Alternate Screen Buffer (`\033[?1049h`).
  - Dùng chuỗi nguyên tử `\033[H + frame + \033[J`.
  - Tự động co giãn theo kích thước thực tế của console: `num_proxies = min(12, max(2, lines - fixed_lines - 1))`.
  - Thay thế emoji cờ bằng Text Badge an toàn `[VN]`, `[US]`, `[DE]`.

---

## 📦 [V0.9.0] — 2026-09-24

### Tính năng:
- Thiết kế lại toàn bộ giao diện Web Dashboard theo phong cách Cyberpunk Dark Mode (`#07090e`) với hiệu ứng Matrix Code Rain Canvas bằng WebGL.
- Tích hợp điều khiển bàn phím (Phím Space, `+`, `-`, `Q`) và bắt sự kiện click chuột qua chuỗi thoát VT100 SGR trên Terminal Client.
- Đồng bộ dữ liệu Live Proxy thời gian thực lên Dashboard.

---

## 📦 [V0.8.0] — 2026-09-23

### Tính năng:
- Ra mắt hệ thống cấp khóa 4 bước Stateless Token (Math Captcha, Discord Server Join, Linkvertise Task, Cấp Key 24h).
- Triển khai kiến trúc Master Server chạy tương thích cả trên Vercel Serverless (`api/index.py`) và Linux VPS (`server.py`).
- Quản lý tệp danh sách nguồn cào proxy `sources.txt` hỗ trợ hơn 100 nguồn GitHub công khai.

---

## 📦 [V0.5.0] — 2026-09-20

### Tính năng:
- Tách biệt kiến trúc Client - Server.
- Nâng cấp bộ kiểm tra proxy sang thư viện bất đồng bộ `aiohttp`, hỗ trợ kiểm tra đồng thời tới 1,000 socket song song.
- Tự động phân loại proxy thành 4 nhóm: HTTP/HTTPS, SOCKS4, SOCKS5, Elite / Residential.

---

## 📦 [V0.1.0] — 2026-09-18

### Khởi đầu:
- Bản thử nghiệm ban đầu (Proof of Concept) của công cụ quét proxy đơn luồng.
