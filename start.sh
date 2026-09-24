#!/bin/bash
# =====================================================================
# SCRIPT KHỞI CHẠY PROXY SCANNER TRÊN PTERODACTYL PANEL
# Thương hiệu: Death Proxy Scanner V1.0.0 - By ! Death Silence (@qyk3)
# Discord chính thức: https://discord.gg/2zuwDpJaNP
# =====================================================================

echo "=========================================================="
echo "⚡ DEATH PROXY SCANNER V1.0.0 - BY ! DEATH SILENCE (@qyk3) ⚡"
echo "🌐 Discord Hỗ Trợ: https://discord.gg/2zuwDpJaNP"
echo "=========================================================="

# 1. Tự động kiểm tra và cập nhật code mới nhất từ Git (nếu có repo)
if [ -d ".git" ]; then
    echo "[GIT] Đang kiểm tra bản cập nhật mới nhất từ Git..."
    git config --global --add safe.directory /home/container 2>/dev/null || true
    git pull --no-edit origin main 2>/dev/null || git pull --no-edit origin master 2>/dev/null || echo "[GIT] Đang chạy bản hiện tại."
fi

# 2. Cài đặt các gói thư viện
if [ -f "requirements.txt" ]; then
    echo "[PIP] Kiểm tra thư viện phụ thuộc..."
    pip install --no-cache-dir -r requirements.txt
fi

# 3. Khởi chạy công cụ (Mặc định chạy server.py, có thể cấu hình ENTRY_FILE)
ENTRY="${ENTRY_FILE:-server.py}"
echo "[RUN] Khởi chạy: python $ENTRY..."
python "$ENTRY"
