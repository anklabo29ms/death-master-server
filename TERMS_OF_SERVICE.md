# 📜 TERMS OF SERVICE & ACCEPTABLE USE POLICY (TOS / AUP)
## BỘ ĐIỀU KHOẢN DỊCH VỤ & CHÍNH SÁCH SỬ DỤNG CHẤP NHẬN ĐƯỢC
**Project**: `Death Proxy Scanner V1.0.0`  
**Author**: `! Death Silence` | **Contact / Abuse Reporting**: `Discord: @qyk3` | **Official Server**: `https://discord.gg/2zuwDpJaNP`  
**Effective Date**: `2026-09-23`

---

## 🌐 1. TECHNICAL CLASSIFICATION FOR HOSTING PROVIDERS (DÀNH CHO ĐƠN VỊ CUNG CẤP HOSTING / VPS)

> **TO ALL HOSTING PROVIDERS, DATA CENTERS, AND NETWORK ADMINISTRATORS:**  
> This software is a **Distributed Network Latency Benchmark & Accessibility Diagnostics Orchestrator** designed for benign network performance testing and connectivity diagnostics (e.g., verifying routing path reachability to communication platforms like Discord).

### Key Architectural Safety Guarantees for Server Hosts:
1. **ZERO OUTBOUND PORT SCANNING ON SERVER**:  
   The Master Server application (`server.py`) **DOES NOT** perform any port scanning, mass TCP SYN handshakes, ICMP sweeps, or automated probing against arbitrary IP addresses. The server acts exclusively as an incoming REST API / WebSocket coordination hub, listening on its designated port (default: `5000`).
2. **NO NETWORK FLOODING OR ABUSE**:  
   Outbound network activity on the server host is strictly limited to periodic, low-frequency HTTP GET requests downloading public, open-source proxy lists from reputable sources (e.g., GitHub raw repositories). Bandwidth consumption is minimal (< 50 KB/s), causing zero NAT saturation or socket exhaustion.
3. **DISTRIBUTED CLIENT-SIDE WORKLOAD**:  
   All proxy health checks and latency evaluations are strictly offloaded to remote client worker nodes (`client.py`) executed on client computers. Live proxy lists are stored locally on the client's device, not burdening the hosting server with heavy I/O or network connections.
4. **CLOUD & REVERSE PROXY FAIR USAGE (VERCEL / CLOUDFLARE COMPLIANCE)**:  
   When deployed behind edge reverse proxies (such as Vercel Edge Network, Cloudflare, or AWS CloudFront), the application operates in full compliance with host terms: requests are short-lived, client IP addresses are accurately attributed using platform headers (`X-Vercel-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP`), and persistent socket connections gracefully fall back to HTTP polling.

---

## 🛡️ 2. ACCEPTABLE USE POLICY (CHÍNH SÁCH SỬ DỤNG CHẤP NHẬN ĐƯỢC)

### ✅ Cho Phép & Khuyến Khích (Permitted & Authorized Use):
* **Chẩn đoán mạng & Kiểm tra định tuyến (Network Diagnostics)**: Kiểm tra khả năng kết nối và đo độ trễ (latency ms) tới các dịch vụ mạng công cộng (như Discord, Cloudflare, HttpBin) nhằm mục đích khắc phục sự cố nghẽn mạng hoặc vượt qua tường lửa mạng nội bộ (trường học, ký túc xá).
* **Nghiên cứu & Học tập (Educational & Research Purpose)**: Kiểm thử hiệu năng mạng bất đồng bộ (AsyncIO, aiohttp) và nghiên cứu độ trễ của các nút mạng trung gian.
* **Tự do truy cập Internet hợp pháp**: Giúp người dùng tại các khu vực bị bóp băng thông quốc tế có thể kết nối ổn định tới các nền tảng giao tiếp mở.

### 🚫 Nghiêm Cấm Tuyệt Đối (Strictly Prohibited & Zero-Tolerance):
Người dùng và các bên vận hành **tuyệt đối không được** sử dụng công cụ hoặc danh sách proxy phát sinh vào các mục đích sau:
1. **Tấn công từ chối dịch vụ (DDoS / DoS)** hoặc gửi lưu lượng độc hại làm tê liệt bất kỳ máy chủ nào.
2. **Dò quét mục tiêu trái phép**: Cấm đặt Target URL trỏ về các cổng thông tin chính phủ (`.gov`, `.mil`), hệ thống ngân hàng, tài chính, bệnh viện hoặc cơ sở hạ tầng trọng yếu.
3. **Đánh cắp danh tính & Brute-force**: Cấm sử dụng proxy để bẻ khóa mật khẩu, credential stuffing, spam tin nhắn rác hoặc chiếm đoạt tài khoản.
4. **Dò quét dải IP nội bộ**: Cấm quét các dải IP riêng tư theo chuẩn RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1/8`).

---

## ⚖️ 3. LIMITATION OF LIABILITY & DISCLAIMER (TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM)

1. **Công nghệ Lưỡng dụng (Dual-Use Technology)**:  
   Tương tự như các công cụ mạng tiêu chuẩn (`curl`, `ping`, `nmap`, `wireshark`), phần mềm này là công cụ trung tính. Tác giả (`! Death Silence`) và đơn vị cung cấp hạ tầng máy chủ (Hosting/VPS) **không chịu bất kỳ trách nhiệm pháp lý nào** đối với hành vi sử dụng sai mục đích của người dùng cuối.
2. **Trách nhiệm người dùng**:  
   Người dùng tự chịu 100% trách nhiệm trước pháp luật địa phương và quốc tế đối với lưu lượng truy cập phát sinh từ máy cá nhân của mình.
3. **Quyền đình chỉ dịch vụ**:  
   Quản trị viên có toàn quyền thu hồi giấy phép (`License Key`), cấm địa chỉ IP (`IP Ban`) và chấm dứt quyền truy cập của bất kỳ người dùng nào có dấu hiệu vi phạm chính sách này mà không cần báo trước.

---

## 📬 4. ABUSE REPORTING & CONTACT (LIÊN HỆ BÁO CÁO LẠM DỤNG)

Nếu bất kỳ quản trị viên mạng hoặc nhà cung cấp hosting nào phát hiện lưu lượng bất thường nghi ngờ xuất phát từ công cụ này, xin vui lòng liên hệ ngay để chúng tôi hỗ trợ xử lý và chặn IP lạm dụng trong vòng 24 giờ:

* **Discord Liên Hệ**: `@qyk3`
* **Kênh Hỗ Trợ Kỹ Thuật**: Direct Message qua Discord `@qyk3`
* **Máy Chủ Discord Chính Thức**: `https://discord.gg/2zuwDpJaNP`
