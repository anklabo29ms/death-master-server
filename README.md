# 💀 DEATH PROXY SCANNER — MASTER SERVER (VERCEL & STANDALONE READY)

> **Tác giả:** `! Death Silence` • **Discord Hỗ Trợ:** `@qyk3`  
> **Máy chủ Discord chính thức:** `https://discord.gg/2zuwDpJaNP`  
> **Bản quyền:** `Death Proxy Scanner V1.0.0`

---

## 🚀 CÁCH 1: TRIỂN KHAI LÊN VERCEL (MIỄN PHÍ 100%, 24/7 ONLINE)

Thư mục `server/` này đã được cấu hình chuẩn Vercel Serverless Function (`@vercel/python` + `vercel.json` + `api/index.py`):

1. **Đưa mã nguồn lên GitHub**:
   - Tạo 1 repository mới trên GitHub (ví dụ: `death-master-server`).
   - Copy toàn bộ nội dung bên trong thư mục `server/` này và commit/push lên repository đó.
2. **Kết nối với Vercel**:
   - Đăng nhập vào [vercel.com](https://vercel.com).
   - Bấm **"Add New Project"** $\rightarrow$ Chọn Repository GitHub bạn vừa tạo.
   - Giữ nguyên cấu hình mặc định (Root Directory: `./`, Framework: Other).
   - Bấm **"Deploy"**!
3. **Hoàn tất**:
   - Vercel sẽ cấp cho bạn một domain HTTPS (ví dụ: `https://death-master-server.vercel.app`).
   - Mọi trang web (`/`, `/terms`, `/hosting-aup`, `/getkey`, `/s/{code}`) và toàn bộ REST API (`/api/*`) sẽ hoạt động ngay lập tức 24/7!
   - Sử dụng domain Vercel này để điền vào Client (`client.py`) hoặc chia sẻ cho người dùng.

---

## 💻 CÁCH 2: CHẠY TRỰC TIẾP TRÊN MÁY TÍNH / VPS / PTERODACTYL (STANDALONE)

Nếu bạn muốn chạy trên máy cá nhân, VPS Linux, hoặc Server Pterodactyl:

### Trên Windows:
Nhấp đúp chuột vào file **`start.bat`** hoặc mở PowerShell chạy:
```powershell
python server.py
```

### Trên Linux / Ubuntu / VPS:
```bash
chmod +x start.sh
./start.sh
```

---

## 🌐 DANH SÁCH ENDPOINTS CỦA MASTER SERVER

- 🏠 **Dashboard Giám Sát**: `http://localhost:5000/` (hoặc `https://your-domain.vercel.app/`)
- 📜 **Điều Khoản Dịch Vụ**: `http://localhost:5000/terms`
- 🛡️ **Cam Kết Hosting (AUP)**: `http://localhost:5000/hosting-aup`
- 🔑 **Cổng Nhận Key Free 24h (Link 1)**: `http://localhost:5000/getkey`
- 🔗 **Rút Gọn Link Tự Chủ (Link 2)**: `http://localhost:5000/s/{code}`
- ⭐ **Đối Soát Chống Bypass (Link 3)**: `http://localhost:5000/getkey/middle`
- 🎉 **Cổng Cấp Key (Link 4)**: `http://localhost:5000/getkey/end`
- 📊 **API Thống Kê**: `http://localhost:5000/api/stats`

---

## ⚙️ BIẾN MÔI TRƯỜNG (ENVIRONMENT VARIABLES) TÙY CHỌN

| Biến Môi Trường | Mặc Định | Mô Tả |
| :--- | :--- | :--- |
| `PORT` hoặc `SERVER_PORT` | `5000` | Cổng HTTP mà Master Server lắng nghe |
| `PING_TARGET` | `http://1.1.1.1/cdn-cgi/trace` | Link đích mặc định để các worker kiểm tra proxy sống |
| `VERCEL` | Tự động | Tự động chuyển vùng ghi `keys.json` sang `/tmp` khi ở môi trường serverless |
