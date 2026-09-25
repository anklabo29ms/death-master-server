# 💀 DEATH PROXY SCANNER V1.0.0 — DOCUMENTATION SUITE

> **Thương hiệu chính thức**: `Death Proxy Scanner V1.0.0 - Created By ! Death Silence - Discord: @qyk3`  
> **Tác giả**: `! Death Silence` • **Discord Hỗ Trợ**: `@qyk3`  
> **Máy chủ Discord chính thức**: [https://discord.gg/2zuwDpJaNP](https://discord.gg/2zuwDpJaNP)  
> **Production Server (Vercel)**: [https://death-proxy-scanner-legit.vercel.app](https://death-proxy-scanner-legit.vercel.app)  
> **GitHub Repos**:  
> - Primary: `https://github.com/anklabo29ms/death-proxy-scanner-legit.git`  
> - Backup: `https://github.com/anklabo29ms/death-master-server.git`

---

## 📚 MỤC LỤC TÀI LIỆU DỰ ÁN (DOCUMENTATION INDEX)

Thư mục `docs/` chứa toàn bộ tài liệu kỹ thuật, kiến trúc, hướng dẫn vận hành, nhật ký thay đổi và cẩm nang bàn giao đặc biệt dành cho các AI Agent / Lập trình viên tiếp quản dự án.

| Tài liệu | Mô tả chi tiết | Đối tượng |
| :--- | :--- | :--- |
| **[AI_HANDOVER_GUIDE.md](AI_HANDOVER_GUIDE.md)** | **CẨM NANG BÀN GIAO CHO AI TIẾP QUẢN**: Quy tắc cốt lõi, bẫy kỹ thuật (gotchas), cấu trúc 2 repo git, trạng thái hiện tại, danh sách việc cần lưu ý. | **BẮT BUỘC ĐỌC ĐẦU TIÊN** |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | **BẢN THIẾT KẾ KIẾN TRÚC HỆ THỐNG**: Topology Server-Client, luồng cấp khóa 4 bước, cơ chế HMAC, kho hạt giống proxy 0ms, kiến trúc TUI đa luồng. | Developers, Architects |
| **[CHANGELOG.md](CHANGELOG.md)** | **NHẬT KÝ NÂNG CẤP & SỬA LỖI**: Lịch sử chi tiết từ v0.1 đến v1.0.0, phân tích nguyên nhân gốc và giải pháp cho các lỗi sâu (Vercel query loss, Discord bypass, TUI ghosting...). | All |
| **[OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)** | **CẨM NANG VẬN HÀNH & TRIỂN KHAI**: Hướng dẫn chạy Client, Server (Local / VPS / Pterodactyl / Vercel), quản lý khóa bản quyền `deathkey`, phân loại proxy đầu ra. | DevOps, SysAdmin, Users |
| **[API_REFERENCE.md](API_REFERENCE.md)** | **TÀI LIỆU REST API ĐẦY ĐỦ**: Chi tiết các endpoint xác thực, cấp phát nhiệm vụ (`/api/tasks`), nhận kết quả (`/api/submit`), quản trị admin và telemetry realtime. | API Integrators |

---

## ⚡ TỔNG QUAN NHANH VỀ DỰ ÁN (EXECUTIVE SUMMARY)

**Death Proxy Scanner V1.0.0** là giải pháp phân tán cao cấp dành cho việc thu thập (scraping), kiểm tra (testing) và phân loại (classifying) proxy tốc độ cực cao với kiến trúc **Master Server - Worker Client**:

1. **Master Server (Dual-Engine)**:
   - Chạy được ở chế độ **Serverless trên Vercel** (`api/index.py`) không tốn chi phí máy chủ.
   - Chạy được ở chế độ **Dedicated Server** (`server.py`) trên VPS Linux, Windows Server hoặc Pterodactyl Panel (3GB RAM).
   - Tích hợp sẵn hệ thống cấp bản quyền **Stateless Key 24h** qua quy trình 4 liên kết bảo mật (Captcha PoW + Discord Verification + Linkvertise Time Wait + Key Issuance).
   - Tích hợp kho **3,000 Seed Proxies** nạp 0ms, không bao giờ bị cạn kiệt nhiệm vụ dù mạng ngoài gặp sự cố.
   - Web Dashboard phong cách **Cyberpunk Dark Mode** với hiệu ứng Matrix Canvas, HUD dock hiển thị thời gian thực.

2. **Worker Client (`client.py`)**:
   - Sử dụng thư viện `aiohttp` và `asyncio` bất đồng bộ siêu tốc, quét đồng thời từ **500 đến 2,000 luồng**.
   - Bắt buộc kiểm tra tệp khóa bản quyền **`deathkey`**; tự động nhắc người dùng nhập và lưu nếu chưa có.
   - Quy trình chẩn đoán tiền trạm **Pre-Flight Diagnostics** kiểm tra Internet, Master Server Ping, tình trạng khóa và quyền ghi file.
   - Terminal UI hiện đại bằng `rich`: Chạy trên **Alternate Screen Buffer (`\033[?1049h`)**, tự động co giãn theo kích thước cửa sổ Windows, **không bị trôi rác màn hình**, hỗ trợ phím tắt (`Space`, `+`, `-`, `Q`) và click chuột tương tác trực tiếp.

---

## 🚀 LỆNH KHỞI ĐỘNG NHANH 1 DÒNG

### 1. Dành cho Client (Người dùng quét proxy):
```powershell
# Chạy trực tiếp (Client sẽ tự kiểm tra tệp deathkey hoặc hỏi nhập)
python client.py

# Hoặc truyền sẵn Key và số luồng tùy chỉnh
python client.py --server https://death-proxy-scanner-legit.vercel.app --key "DEATH-VIP-..." --concurrency 500
```

### 2. Dành cho Master Server (Chạy máy chủ độc lập):
```bash
# Trên Linux / VPS / Pterodactyl
bash start.sh

# Trên Windows
python server.py --host 0.0.0.0 --port 8000
```

---

## 🛡️ BẢN QUYỀN & THÔNG TIN LIÊN HỆ
- Mọi thắc mắc kỹ thuật, yêu cầu cấp khóa VIP hoặc báo cáo sự cố, vui lòng liên hệ trực tiếp qua Discord:
  - **Author Discord**: `@qyk3`
  - **Support Server**: [discord.gg/2zuwDpJaNP](https://discord.gg/2zuwDpJaNP)
