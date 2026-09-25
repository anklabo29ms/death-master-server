# 🤖 CẨM NANG BÀN GIAO CHO AI TIẾP QUẢN (AI HANDOVER GUIDE)

> **Dành riêng cho**: AI Agent (Claude, GPT, Antigravity, Cursor, Windsurf) hoặc Kỹ sư tiếp quản dự án.  
> **Dự án**: `Death Proxy Scanner V1.0.0`  
> **Tác giả dự án**: `! Death Silence` (Discord: `@qyk3`)  
> **Ngày lập hồ sơ**: `25/09/2026`

---

## ⚡ 1. TRIẾT LÝ VÀ PHONG CÁCH LÀM VIỆC CẦN TUÂN THỦ (CRITICAL RULES)

Hệ thống được phát triển theo triết lý **Vibe Coding với Kỷ luật Agentic** (quy định chi tiết tại [`AGENTS.md`](../AGENTS.md)):

1. **Hiểu về người dùng (User Profile)**:
   - Người dùng có hiểu biết cơ bản về lập trình, tập trung vào kết quả thực tế, thẩm mỹ cyberpunk và tốc độ thực thi.
   - **Tuyệt đối không hỏi các câu hỏi kỹ thuật dông dài** kiểu *"bạn muốn dùng thuật toán gì"* hay *"cho tôi xem traceback"*. Khi người dùng báo lỗi (kể cả nói vắn tắt *"lỗi gì ấy"*, *"tool đứng im"*), bạn phải **tự phân tích code, tự tái hiện lỗi, tự sửa và tự kiểm tra lại bằng lệnh test ngầm**.
   - Bàn giao luôn kèm **lệnh chạy 1 dòng đơn giản nhất** (VD: `python client.py`).

2. **Kỷ luật Bảo Hiểm Mã Nguồn (Anti-Breakage & Backward Compatibility)**:
   - Thêm tính năng mới **tuyệt đối không được làm hỏng tính năng cũ đang chạy mượt mà**.
   - Các file cấu hình người dùng như `deathkey`, `keys.json`, `sources.txt`, `config.json` phải luôn được bảo tồn, tự động merge dữ liệu chứ không ghi đè làm mất khóa hay nguồn proxy cũ.
   - Mọi tham số mới truyền vào hàm bắt buộc phải có giá trị mặc định (`default_value`).

3. **Kỹ thuật phòng thủ Windows & Mạng (Defensive Engineering)**:
   - Terminal Windows rất dễ lỗi font tiếng Việt và emoji. Luôn duy trì:
     ```python
     if sys.platform == "win32":
         os.system("chcp 65001 >nul 2>&1")
     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
     ```
   - Không dùng emoji cờ quốc gia kép (như 🇺🇸, 🇩🇪) trong bảng Rich vì chúng có độ rộng không chuẩn trên PowerShell/CMD, gây vỡ toác viền bảng `│`. Luôn dùng Text Badge: `[VN]`, `[US]`, `[DE]`, `[GB]`.
   - Mọi socket / HTTP request bắt buộc phải có `timeout` rõ ràng.

---

## 📂 2. CẤU TRÚC THƯ MỤC & HỆ THỐNG HAI KHO GIT (DUAL-GIT SYSTEM)

Dự án có cấu trúc 2 tầng cần đặc biệt lưu ý để tránh chỉnh sửa sai chỗ:

```text
delightful-hopper/                   <-- THƯ MỤC GỐC DỰ ÁN (Root Workspace)
├── .agents/skills/                  <-- Bộ kỹ năng tự động hóa của Agentic Assistant
├── client.py                        <-- FILE CHÍNH CỦA CLIENT (Worker Node TUI)
├── client/client.py                 <-- Bản sao đồng bộ của client.py
├── server.py                        <-- Bản sao server local / standalone
├── seeds.py                         <-- Kho 3,000 proxy hạt giống nạp 0ms
├── getkey_middle.html               <-- Giao diện Captcha + PoW + Countdown
├── dashboard.html                   <-- Giao diện Web Dashboard Cyberpunk
├── deathkey                         <-- Tệp chứa khóa bản quyền thực tế của client
├── tests/
│   └── test_system_integrity.py     <-- Bộ test tự động kiểm tra toàn vẹn hệ thống
├── docs/                            <-- Thư mục tài liệu tổng hợp (bạn đang đọc)
└── server/                          <-- ⚠️ KHO GIT TRIỂN KHAI VERCEL / GITHUB RIÊNG BIỆT!
    ├── .git/                        <-- Git repo độc lập
    ├── api/
    │   └── index.py                 <-- Vercel Serverless Handler (WSGI)
    ├── server.py                    <-- Core logic của Master Server
    ├── seeds.py                     <-- Kho hạt giống proxy trên server
    ├── getkey.html / getkey_*.html  <-- Bộ HTML quy trình cấp khóa 4 bước
    ├── dashboard.html               <-- Web Dashboard cho server
    └── vercel.json                  <-- Cấu hình định tuyến Serverless Vercel
```

### ⚠️ QUY TẮC ĐỒNG BỘ FILE BẮT BUỘC:
- Thư mục con `server/` là một Git repository riêng biệt kết nối với 2 remote GitHub của người dùng:
  - `origin`: `https://github.com/anklabo29ms/death-proxy-scanner-legit.git` (Repo chính tự động deploy lên Vercel)
  - `backup`: `https://github.com/anklabo29ms/death-master-server.git` (Repo sao lưu)
- **Khi chỉnh sửa file server**: Bạn phải cập nhật đồng bộ cả ở root và trong `server/` (ví dụ: `server.py` $\leftrightarrow$ `server/server.py`, `seeds.py` $\leftrightarrow$ `server/seeds.py`, `getkey_middle.html` $\leftrightarrow$ `server/getkey_middle.html`).
- **Sau khi chỉnh sửa xong**: Phải chạy lệnh commit và push ở cả thư mục `server/` lên 2 remote:
  ```powershell
  cd server
  git add .
  git commit -m "feat/fix: ..."
  git push origin main
  git push backup main
  cd ..
  ```

---

## 🔍 3. DANH SÁCH BẪY KỸ THUẬT & BÀI HỌC XƯƠNG MÁU (GOTCHAS & PITFALLS)

Dưới đây là các lỗi sâu cực kỳ nguy hiểm đã được xử lý xong, bạn **tuyệt đối không được revert hay sửa đổi làm tái diễn**:

### 💣 Bẫy 1: Vercel Rewrite nuốt mất Query Parameter
- **Hiện tượng trước đây**: Người dùng giải Captcha xong ở Link 1 thì frontend bị báo *"Lỗi kết nối máy chủ xác minh!"* và không chuyển được sang Link 2.
- **Nguyên nhân**: File `vercel.json` rewrite toàn bộ request về `/api/index.py?__orig_path=/$1`. Khi client gọi `/api/getkey/verify?token=XYZ&pow_nonce=42`, toàn bộ chuỗi query nằm trong `__orig_path` mà Vercel không tự động tách ra vào biến môi trường `QUERY_STRING`. Kết quả là `query.get("token")` bị rỗng $\rightarrow$ HTTP 400.
- **Giải pháp đang áp dụng**: Trong `server/api/index.py` (hàm `parse_url_parts`), code sử dụng `urllib.parse.urlsplit` và `urllib.parse.parse_qs` trên `__orig_path` để giải nén lại toàn bộ query parameter bị thiếu. **Đừng bao giờ xóa logic này!**

### 💣 Bẫy 2: HMAC Salt bị lệch giữa các Container Serverless
- **Hiện tượng**: Token tạo ở container Lambda này nhưng khi sang bước sau rơi vào container Lambda khác lại báo chữ ký HMAC không hợp lệ.
- **Nguyên nhân**: Sử dụng chuỗi secret sinh ngẫu nhiên khi khởi động tiến trình.
- **Giải pháp đang áp dụng**: Khai báo hằng số môi trường `MASTER_SECRET_SALT = os.environ.get("MASTER_SECRET_SALT") or "DeathSuperSecretHMACSalt998877"` thống nhất trong cả `server.py` và `api/index.py`.

### 💣 Bẫy 3: Web Crypto API bị vô hiệu hóa trên Non-HTTPS / LAN IP
- **Hiện tượng**: Chạy test cục bộ bằng IP LAN (VD: `http://192.168.1.5:8000`) thì Captcha PoW bị treo cứng, không tính toán được nonce.
- **Nguyên nhân**: Trình duyệt hiện đại vô hiệu hóa `window.crypto.subtle` trên môi trường không phải HTTPS hoặc localhost.
- **Giải pháp đang áp dụng**: Trong `getkey_middle.html` đã tích hợp sẵn thư viện **Pure-JavaScript SHA-256 fallback**. Nếu `crypto.subtle` là `undefined`, code tự động chuyển sang JS thuần để tính toán PoW trong ~30ms.

### 💣 Bẫy 4: Lỗi Whitelist làm lộ lỗ hổng Bypass Link 2 (Discord)
- **Hiện tượng**: Bất kỳ ai chạy trên localhost hoặc IP có trong Whitelist đều bị bỏ qua bước tham gia Discord, dẫn đến Link 2 mất tác dụng.
- **Nguyên nhân**: Code cũ viết `disc_ok = sess.get("discord_verified") or is_ip_whitelisted(client_ip)`.
- **Giải pháp đang áp dụng**: Whitelist chỉ được phép miễn trừ thời gian chờ 300 giây của Linkvertise, **tuyệt đối không được phép miễn trừ bước xác thực tham gia Discord**.

### 💣 Bẫy 5: Vercel Lambda Freeze Background Threads $\rightarrow$ Task Starvation
- **Hiện tượng**: Tool client quét được 1 lúc thì đứng im, không nhận được thêm proxy nào dù tín hiệu server vẫn báo Online.
- **Nguyên nhân**: Vercel Serverless đóng băng luồng cào proxy ngầm ngay khi request kết thúc. Khi task buffer cạn, việc cào từ GitHub bên ngoài bị timeout 10s.
- **Giải pháp đang áp dụng**: Tích hợp sẵn `seeds.py` chứa **3,000 proxy sống**. Khi buffer cạn, server nạp lại 1,200 proxy trong 0ms. Đồng thời `client.py` có hàm dự phòng `fallback_client_harvest()` để tự cấp proxy nếu server tạm thời bận.

### 💣 Bẫy 6: Lỗi Terminal "Thải Rác" & Rách Khung Viền
- **Hiện tượng**: Màn hình console nhấp nháy, mỗi lần vẽ lại thì nút bấm bị nhân bản xuống đáy, viền bảng bị lệch toác.
- **Nguyên nhân**:
  1. Vẽ quá 24 dòng làm terminal Windows bị cuộn (scroll), lệnh `\033[H` đưa con trỏ về đầu nhưng dòng cũ bị trôi ra ngoài buffer.
  2. Không có lệnh xóa sạch vùng dưới con trỏ (`\033[J`).
  3. Emoji quốc kỳ 2 byte làm sai lệch bộ đếm độ rộng cell của Windows Console.
- **Giải pháp đang áp dụng**:
  - Dùng **Alternate Screen Buffer (`\033[?1049h`)** để vẽ trên màn hình ảo riêng.
  - Chuỗi vẽ nguyên tử: `\033[H` (về gốc) + `frame` + `\033[J` (quét sạch toàn bộ ký tự thừa bên dưới).
  - Tự động co giãn theo kích thước cửa sổ Windows: `num_proxies = min(12, max(2, lines - fixed_lines - 1))`. Chiều cao bảng luôn $\le 22$ dòng trên màn hình chuẩn 24 dòng.
  - Thay icon cờ bằng badge text an toàn: `[VN]`, `[US]`, `[DE]`.

---

## 🛡️ 4. KIỂM THỬ TRƯỚC KHI BÀN GIAO (VERIFICATION SUITE)

Bất kỳ khi nào bạn can thiệp vào code, hãy chạy lệnh kiểm thử tự động sau để đảm bảo 100% không làm gãy kiến trúc:

```powershell
python tests/test_system_integrity.py
```

Kết quả hợp lệ bắt buộc phải in ra:
```text
=== 1. TEST HMAC SECRET CONSISTENCY ===: PASSED
=== 2. TEST VERCEL REWRITE QUERY EXTRACTION ===: PASSED
=== 3. TEST 4-LINK FLOW & DISCORD ENFORCEMENT ===: PASSED
=== 4. TEST SEED PROXY PROVISIONING (0ms TASK DISPATCH) ===: PASSED
=== 5. TEST CUMULATIVE METRIC AGGREGATION ===: PASSED
=== 6. TEST KHÔNG CÒN BIẾN CHƯA ĐỊNH NGHĨA TRONG HANDLER TRỌNG YẾU ===: PASSED
=== 7. TEST TEST_BYPASS CHỈ CÓ HIỆU LỰC TỪ LOCALHOST ===: PASSED
=== 8. TEST /API/SUBMIT CHẠY ĐƯỢC THẬT (KHÔNG CÒN 500) ===: PASSED
========================================
🎉 ALL 8 ARCHITECTURAL TESTS PASSED 100%!
========================================
```

---

## 📋 5. NHỮNG TÍNH NĂNG TIỀM NĂNG CÓ THỂ MỞ RỘNG (IF REQUESTED)

Nếu người dùng yêu cầu phát triển thêm, đây là danh sách gợi ý nâng cấp theo thứ tự ưu tiên:
1. **Xuất kết quả đa định dạng**: Bổ sung endpoint xuất proxy theo định dạng JSON API, CSV hoặc định dạng Clash/V2Ray proxy provider.
2. **Cơ chế GeoIP Offline**: Nhúng cơ chế GeoIP nhẹ để tra cứu Quốc gia/ISP ngay trên client mà không cần gọi API ngoài (tránh bị rate-limit khi quét 2,000 req/s).
3. **Phân quyền Key Nâng Cao**: Thêm hạn mức số luồng tối đa cho từng loại Key (Free Key: 300 luồng, VIP Key: 2,000 luồng).
