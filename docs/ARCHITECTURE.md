# 🏗️ BẢN THIẾT KẾ KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

> **Dự án**: `Death Proxy Scanner V1.0.0`  
> **Thương hiệu**: `Created By ! Death Silence - Discord: @qyk3`  
> **Tài liệu**: Bản vẽ kỹ thuật chuyên sâu về luồng dữ liệu, giao thức mạng và mô hình phân tán.

---

## 🌐 1. TỔNG QUAN MÔ HÌNH PHÂN TÁN (DISTRIBUTED TOPOLOGY)

Hệ thống hoạt động theo mô hình **Master - Worker** (Máy chủ điều phối trung tâm - Cụm nút thợ quét phân tán):

```mermaid
flowchart TD
    subgraph MasterServer["👑 Master Server (Dual Mode: Vercel / VPS)"]
        direction TB
        API_GATEWAY["API Gateway / WSGI Router\n(server.py / api/index.py)"]
        KEY_SYSTEM["Stateless 4-Step Key Engine\n(HMAC-SHA256, PoW, Discord)"]
        TASK_DISPATCH["Task Dispatcher & Buffer\n(1,200 Seed Replenishment)"]
        METRICS_DB["Cumulative Telemetry Store\n(State.checked_total, live_total)"]
        WEB_HUD["Cyberpunk Web Dashboard\n(Matrix Canvas + Realtime HUD)"]
    end

    subgraph ClientNode["⚡ Worker Client Node (client.py)"]
        direction TB
        PREFLIGHT["Pre-Flight Diagnostic System\n(Net Check, Ping, Key Verify)"]
        HARVEST_FALLBACK["Fallback Client Harvester\n(3,000 Offline Seeds)"]
        SCANNER_POOL["Async TCP Scanner Pool\n(500 - 2,000 aiohttp Coroutines)"]
        TUI_ENGINE["Aesthetic TUI Engine\n(Alt Buffer, VT100 Mouse & Keys)"]
        TELEMETRY_HEARTBEAT["Heartbeat Submitter\n(Every 2.0s Monotonic Sync)"]
    end

    subgraph TargetInternet["🌍 Public Internet & Target"]
        TARGET_URL["Target Endpoint\n(Cloudflare CDN / Custom Ping)"]
        DISCORD_API["Discord API & Guild\n(https://discord.gg/2zuwDpJaNP)"]
        SOURCES_REPOS["Public Proxy Repos\n(GitHub / Raw Sources)"]
    end

    ClientNode -->|"1. Pre-flight Key Auth"| KEY_SYSTEM
    ClientNode -->|"2. Fetch Batch Tasks"| TASK_DISPATCH
    TASK_DISPATCH -.->|"Cold-start fallback"| SOURCES_REPOS
    ClientNode -->|"3. High-concurrency Probe"| TARGET_URL
    ClientNode -->|"4. Heartbeat & Metrics (2s)"| METRICS_DB
    MasterServer -->|"Verify Membership"| DISCORD_API
    WEB_HUD -->|"Live Monitoring"| METRICS_DB
```

---

## 🔑 2. CƠ CHẾ CẤP KHÓA 4 BƯỚC STATELESS (4-STEP KEY GENERATION PIPELINE)

Hệ thống cấp khóa không đòi hỏi cơ sở dữ liệu nặng nề (SQL/Redis) mà sử dụng cơ chế **HMAC-SHA256 Stateless Token** tự kiểm chứng:

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant Step1 as Link 1: Math Captcha + PoW
    participant Step2 as Link 2: Discord Join
    participant Step3 as Link 3: Linkvertise 300s
    participant Step4 as Link 4: Nhận Khóa 24h
    participant Master as Master Server

    User->>Step1: Truy cập /getkey
    Master-->>Step1: Sinh Math Challenge + PoW Target (d=3)
    Step1->>Step1: Tính SHA-256 Nonce (WebCrypto / Pure-JS)
    User->>Step1: Giải toán & Gửi kết quả
    Step1->>Master: POST /api/getkey/verify
    Master-->>User: Cấp Token chuyển tiếp (Step 2, giữ nguyên created_at)

    User->>Step2: Nhảy sang Link 2 (/getkey/middle?step=2)
    User->>User: Bấm tham gia Discord (@qyk3 / 2zuwDpJaNP)
    Step2->>Master: Xác nhận đã vào Server Discord
    Master-->>User: Cấp Token chuyển tiếp (Step 3)

    User->>Step3: Nhảy sang Linkvertise (Rút gọn link)
    Note over User,Step3: Phải chờ tối thiểu 300 giây (5 phút)
    User->>Step3: Hoàn thành nhiệm vụ quảng cáo
    Step3->>Master: POST /api/getkey/verify kèm Token

    User->>Step4: Nhảy sang /getkey/end
    Master->>Master: Kiểm tra HMAC, Discord Status & Delta Time >= 300s
    Master-->>Step4: Xuất chuỗi Death Key 24h: DEATH-24H-...
    Step4-->>User: Hiển thị Khóa & Nút 1-Click Copy
```

### Chi tiết cấu trúc Token Stateless:
- Token được định dạng dưới dạng: `dgk_<base64_payload>.<hmac_signature>`
- Payload chứa:
  - `step`: Bước hiện tại (1, 2, 3, 4).
  - `client_ip`: Địa chỉ IP của người dùng (chống chia sẻ token sang máy khác).
  - `created_at`: Mốc thời gian ban đầu lúc giải Captcha (bảo toàn xuyên suốt qua cả 4 bước).
  - `discord_verified`: Trạng thái đã xác minh Discord (`True`/`False`).
  - `expires_at`: Hạn dùng của token chuyển tiếp (15 phút).
- Chữ ký HMAC: `HMAC_SHA256(payload, MASTER_SECRET_SALT)` đảm bảo người dùng không thể can thiệp sửa đổi dữ liệu token.

---

## ⚡ 3. KHO HẠT GIỐNG PROXY 0MS (SEED HARVESTER ENGINE)

Một trong những cải tiến kiến trúc mang tính đột phá của V1.0.0 là **loại bỏ hoàn toàn nguy cơ đói nhiệm vụ (Task Starvation)** trên Serverless:

```text
[HTTP Request /api/tasks]
         │
         ▼
Bộ đệm Task Buffer còn đủ (>= 200)?
   ├── CÓ ──> Trả ngay 200-500 proxy cho Client (Thời gian: < 5ms)
   └── KHÔNG:
         │
         ├── BƯỚC 1 (0ms TỨC THÌ):
         │   Nạp ngay 1,200 proxy ngẫu nhiên từ kho SEED_PROXIES (seeds.py)
         │   vào Task Buffer.
         │
         └── BƯỚC 2 (NGẦM / DỰ PHÒNG):
             Khởi chạy luồng cào proxy từ 10 repo nguồn công khai trên GitHub.
             Nếu Vercel timeout mạng ngoài -> BƯỚC 1 đã bảo vệ hệ thống 100%!
```

- **Kho `seeds.py`**: Chứa hơn 3,000 proxy đa dạng giao thức (HTTP, HTTPS, SOCKS4, SOCKS5) từ hơn 40 quốc gia, được đóng gói trực tiếp dưới dạng mảng Python, nạp thẳng vào RAM khi khởi động.
- **Client Fallback**: Nếu đường truyền tới Master Server bị gián đoạn, `client.py` tự động kích hoạt `fallback_client_harvest()` để tiếp tục quét cục bộ mà không gián đoạn công việc của người dùng.

---

## 🖥️ 4. KIẾN TRÚC GIAO DIỆN TERMINAL CHỐNG RÁC (RESPONSIVE TUI ENGINE)

Hệ thống TUI của Client được thiết kế trên nền tảng kỹ thuật terminal hiện đại:

```text
+-------------------------------------------------------------------------+
|                        ALTERNATE SCREEN BUFFER                          |
|                       Escape Sequence: \033[?1049h                       |
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Nhảy con trỏ về góc trái trên: \033[H                                |
|  2. Lấy kích thước thực tế: cols, lines = shutil.get_terminal_size()    |
|  3. Tính toán số dòng hiển thị động:                                    |
|     max_rows = min(12, max(2, lines - fixed_rows - 1))                  |
|  4. Bảng điều khiển viền bo tròn (Box.ROUNDED) với chiều rộng co giãn  |
|  5. Chuẩn hóa Badge quốc gia an toàn: [VN], [US], [DE] (Không lỗi font) |
|  6. Xóa sạch mọi ký tự rác từ con trỏ tới đáy màn hình: \033[J           |
|                                                                         |
+-------------------------------------------------------------------------+
|                      VT100 MOUSE & KEYBOARD LISTENER                    |
|  - Bắt phím Space, +, -, Q qua msvcrt (Windows) / termios (Linux)       |
|  - Bắt tọa độ click chuột qua Escape Sequence \033[<0;col;lineM          |
|  - Tự động chuẩn hóa tỷ lệ tọa độ click theo chiều rộng thực tế         |
+-------------------------------------------------------------------------+
```

---

## 📊 5. CƠ CHẾ ĐỒNG BỘ SỐ LIỆU ĐƠN ĐIỆU (MONOTONIC TELEMETRY SYNC)

Để tránh hiện tượng số liệu proxy quét được bị nhảy giật lùi khi các container Serverless khác nhau tiếp nhận request:

1. **Client gửi Heartbeat 2 giây/lần**:
   - Gói tin chứa cả `delta` (số proxy vừa quét được trong 2s qua) và `total_checked`, `total_live` (tổng tích lũy từ lúc mở tool).
2. **Server tổng hợp dữ liệu**:
   - `server.state.checked_total = max(server.state.checked_total, client_total_checked)`
   - `server.state.live_total = max(server.state.live_total, client_total_live)`
3. **Web Dashboard hiển thị**:
   - Canvas Matrix Code Rain chạy nền mượt mà 60 FPS bằng WebGL/HTML5 Canvas.
   - Thống kê thời gian thực: Tốc độ quét (req/s), tỷ lệ sống (Live Rate %), phân bố theo giao thức (HTTP/SOCKS) và quốc gia.
