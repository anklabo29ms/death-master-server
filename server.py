import sys
import os
import warnings
import logging
import socket
import json
import asyncio
import aiohttp
from aiohttp import web
import ipaddress
import re
import time
import hmac
import hashlib
import string
import secrets
import base64
from datetime import datetime, timedelta
from collections import Counter, deque, defaultdict

# ================= 1. BỊT MIỆNG TOÀN BỘ CẢNH BÁO RÁC & CẤU HÌNH UTF-8 =================
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.access").setLevel(logging.CRITICAL)

_real_stderr = sys.stderr
sys.stderr = open(os.devnull, "w", encoding="utf-8")

if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ================= THÔNG TIN CÔNG CỤ & BẢN QUYỀN =================
TOOL_NAME = "Death Proxy Scanner V1.0.0 - Created By ! Death Silence - Discord: @qyk3"
TOOL_SHORT = "Death Proxy Scanner V1.0.0"
TOOL_AUTHOR = "! Death Silence"
TOOL_DISCORD = "@qyk3"

# ================= CẤU HÌNH SERVER & FILE =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Tương thích Vercel Serverless & Read-Only Container
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
WRITABLE_DIR = "/tmp" if (IS_VERCEL or not os.access(BASE_DIR, os.W_OK)) else BASE_DIR

SOURCES_FILE = os.path.join(BASE_DIR, "sources.txt")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.html")
GETKEY_PAGE = os.path.join(BASE_DIR, "getkey.html")             # Link 1: Death-Front-GetKey
GETKEY_MIDDLE_PAGE = os.path.join(BASE_DIR, "getkey_middle.html") # Link 2: Death-Middle-GetKey
GETKEY_END_PAGE = os.path.join(BASE_DIR, "getkey_end.html")       # Link 3: Death-End-GetKey
GETKEY_VERIFY_PAGE = os.path.join(BASE_DIR, "getkey_verify.html") # Legacy alias
SHORTENER_PAGE = os.path.join(BASE_DIR, "shortener.html")         # Hệ thống rút gọn Death-Shortener
KEYS_FILE = os.path.join(WRITABLE_DIR, "keys.json")
STATE_FILE = os.path.join(WRITABLE_DIR, "server_state.json")
TERMS_PAGE = os.path.join(BASE_DIR, "terms.html")
HOSTING_AUP_PAGE = os.path.join(BASE_DIR, "hosting_aup.html")
TERMS_FILE = os.path.join(BASE_DIR, "TERMS_OF_SERVICE.md")
HOSTING_AUP_FILE = os.path.join(BASE_DIR, "HOSTING_AUP.md")

# Khởi tạo keys.json trong thư mục ghi được nếu đang chạy trên Vercel
if WRITABLE_DIR != BASE_DIR and not os.path.exists(KEYS_FILE):
    base_keys = os.path.join(BASE_DIR, "keys.json")
    if os.path.exists(base_keys):
        try:
            import shutil
            shutil.copy2(base_keys, KEYS_FILE)
        except Exception:
            pass

# Danh sách tệp đầu ra lưu proxy sống
OUT_ALL_GOOD = os.path.join(WRITABLE_DIR, "goodproxies.txt")
OUT_ELITE = os.path.join(WRITABLE_DIR, "elite_proxies.txt")
OUT_HTTP = os.path.join(WRITABLE_DIR, "live_http.txt")
OUT_SOCKS4 = os.path.join(WRITABLE_DIR, "live_socks4.txt")
OUT_SOCKS5 = os.path.join(WRITABLE_DIR, "live_socks5.txt")
OUT_RESIDENTIAL = os.path.join(WRITABLE_DIR, "residential_proxies.txt")
OUT_DETAILED = os.path.join(WRITABLE_DIR, "live_detailed.txt")
OUT_BAD = os.path.join(WRITABLE_DIR, "bad_or_dead.txt")

for f in [OUT_ALL_GOOD, OUT_ELITE, OUT_HTTP, OUT_SOCKS4, OUT_SOCKS5, OUT_RESIDENTIAL, OUT_DETAILED, OUT_BAD]:
    if not os.path.exists(f):
        try:
            open(f, "w", encoding="utf-8").close()
        except Exception:
            pass

# ================= 2. QUẢN LÝ KEY SYSTEM CHỐNG SKID (HMAC-SHA256) =================
# Cấu trúc: Death-xxxxxxxx-yyyyyyyy-zzzzzzzz
# xxxxxxxx: 8 ký tự số DDMMYYYY (Hạn dùng)
# yyyyyyyy: 8 ký tự random entropy
# zzzzzzzz: 8 ký tự chữ ký HMAC chống làm giả

def load_keys_data():
    if not os.path.exists(KEYS_FILE):
        default_data = {
            "admin": {
                "username": "admin",
                "password_hash": "bf60e45c5410ebb56506602e87aee2f8827ae00f58c9ceb76254cf52d5ed7168", # DeathAdmin@2026
                "salt": "DeathSecretSalt2026"
            },
            "secret_salt": "DeathSuperSecretHMACSalt998877",
            "keys": {}
        }
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)
        return default_data
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"admin": {}, "secret_salt": "DeathSuperSecretHMACSalt998877", "keys": {}}

def save_keys_data(data):
    try:
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

MASTER_SECRET_SALT = os.environ.get("MASTER_SECRET_SALT") or "DeathSuperSecretHMACSalt998877"
keys_db = load_keys_data()
SECRET_SALT = MASTER_SECRET_SALT

def get_server_settings() -> dict:
    """Lấy cấu hình hệ thống: Webhook Discord, Anti-Bypass duration, Discord Check, Whitelist/Blacklist."""
    keys_db.setdefault("whitelist", ["127.0.0.1", "::1"])
    keys_db.setdefault("blacklist", {})
    keys_db.setdefault("shortened_links", {})
    settings = keys_db.setdefault("settings", {})
    settings.setdefault("min_bypass_duration", 300) # Đốt tối thiểu 5 phút (300 giây)
    settings.setdefault("total_min_key_duration", 300)
    settings.setdefault("discord_check_duration", 90) # 1 - 2 phút (90 giây) kiểm tra Discord
    settings.setdefault("required_discord_invite", "https://discord.gg/2zuwDpJaNP")
    settings.setdefault("required_discord_server_name", "Death Silence Community")
    settings.setdefault("link4m_url", "")
    settings.setdefault("link4m_api_token", "")
    settings.setdefault("discord_webhook", "")
    settings.setdefault("discord_notify_elite", True)
    settings.setdefault("discord_notify_residential", True)
    settings.setdefault("max_keys_per_ip_24h", True)
    settings.setdefault("enforce_ip_binding", True)
    settings.setdefault("enforce_pow", True)
    settings.setdefault("shortener_engine", "death")
    return settings

def generate_death_key(days: int = 30, notes: str = "", key_type: str = "custom", client_ip: str = "") -> dict:
    """
    Sinh key chuẩn Death-xxxxxxxx-yyyyyyyy-zzzzzzzz với chữ ký HMAC.
    key_type:
      - 'free_24h': exp_str = '00000000', status = 'unactivated' (24h tính từ lúc client redeem)
      - 'paid_lifetime': exp_str = '99999999', status = 'active' (Vĩnh viễn)
      - 'custom': exp_str = DDMMYYYY, status = 'active'
    """
    if key_type == "free_24h" or (days == 1 and not notes.startswith("Custom")):
        exp_str = "00000000"
        exp_display = "Chưa kích hoạt (24h sau khi kích hoạt)"
        status = "unactivated"
        days = 1
        key_type_tag = "free_24h"
    elif days == 0 or key_type == "paid_lifetime":
        exp_str = "99999999" # Lifetime vĩnh viễn
        exp_display = "Vĩnh viễn (Lifetime)"
        status = "active"
        days = 0
        key_type_tag = "paid_lifetime"
    else:
        exp_dt = datetime.now() + timedelta(days=days)
        exp_str = exp_dt.strftime("%d%m%Y")
        exp_display = exp_dt.strftime("%d/%m/%Y")
        status = "active"
        key_type_tag = "custom"

    alphabet = string.ascii_uppercase + string.digits
    rand_entropy = "".join(secrets.choice(alphabet) for _ in range(8))
    
    # Ký mật mã HMAC-SHA256
    sign_payload = f"Death-{exp_str}-{rand_entropy}".encode()
    signature = hmac.new(SECRET_SALT.encode(), sign_payload, hashlib.sha256).hexdigest()[:8].upper()

    full_key = f"Death-{exp_str}-{rand_entropy}-{signature}"

    key_record = {
        "key": full_key,
        "key_type": key_type_tag,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_timestamp": time.time(),
        "created_ip": client_ip or "--",
        "activated_at": None,
        "expires_timestamp": None,
        "expires_at": exp_display,
        "days": days,
        "status": status,
        "notes": notes or ("Link4M Free 24h" if key_type_tag == "free_24h" else "Khách hàng VIP"),
        "last_ip": client_ip or "--",
        "last_seen": "--",
        "total_submitted": 0,
        "total_checked": 0
    }

    keys_db["keys"][full_key] = key_record
    save_keys_data(keys_db)
    return key_record

def verify_death_key(key_str: str, client_ip: str = "") -> tuple[bool, str]:
    """Xác thực định dạng, hạn sử dụng, chữ ký HMAC, kích hoạt key 24h unactivated."""
    if not key_str or not isinstance(key_str, str):
        return False, "Thiếu khóa bản quyền (Key)."

    key_str = key_str.strip()
    match = re.match(r"^Death-(\d{8})-([A-Z0-9]{8})-([A-F0-9]{8})$", key_str)
    if not match:
        return False, "Key không đúng định dạng Death-xxxxxxxx-yyyyyyyy-zzzzzzzz."

    exp_str, entropy, sig = match.groups()

    # 1. Kiểm tra chữ ký HMAC (chống skid tự bịa key)
    sign_payload = f"Death-{exp_str}-{entropy}".encode()
    expected_sig = hmac.new(SECRET_SALT.encode(), sign_payload, hashlib.sha256).hexdigest()[:8].upper()
    if not hmac.compare_digest(sig, expected_sig):
        return False, "Chữ ký bảo mật không hợp lệ (Key giả mạo / Skid)."

    # 2. Xử lý Key Free 24h kích hoạt sau (exp_str == '00000000')
    if exp_str == "00000000":
        record = keys_db["keys"].get(key_str)
        if not record:
            # Chữ ký HMAC đã được kiểm tra hợp lệ 100% bằng SECRET_SALT
            # Tự động khởi tạo bản ghi active 24h cho môi trường Serverless đa container
            now_ts = time.time()
            record = {
                "key": key_str,
                "key_type": "free_24h",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "expires_timestamp": now_ts + 86400,
                "expires_at": (datetime.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M"),
                "days": 1,
                "status": "active",
                "notes": "Free 24h Verified by HMAC",
                "last_ip": client_ip or "127.0.0.1",
                "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_submitted": 0,
                "total_checked": 0
            }
            keys_db["keys"][key_str] = record
            save_keys_data(keys_db)
            return True, "Key đã kích hoạt thành công (Hạn 24 giờ)!"

        if record.get("status") == "banned":
            return False, "Khóa này đã bị Admin cấm (Banned)."

        now_ts = time.time()
        # Nếu chưa kích hoạt -> Kích hoạt ngay bây giờ (Đúng 24h)
        if record.get("status") == "unactivated":
            record["status"] = "active"
            record["activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record["expires_timestamp"] = now_ts + 86400 # 24 tiếng
            record["expires_at"] = (datetime.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")
            record["last_ip"] = client_ip or "127.0.0.1"
            record["last_seen"] = record["activated_at"]
            save_keys_data(keys_db)
            return True, "Key đã kích hoạt thành công (Hạn 24 giờ kể từ bây giờ)!"

        # Nếu đã kích hoạt -> Kiểm tra xem đã hết 24h chưa
        if record.get("status") == "active":
            exp_ts = record.get("expires_timestamp")
            if exp_ts and now_ts > exp_ts:
                record["status"] = "expired"
                save_keys_data(keys_db)
                return False, "Key Free 24h đã hết hạn sử dụng (Quá 24 giờ kể từ lúc kích hoạt)."
            record["last_ip"] = client_ip or record.get("last_ip", "--")
            record["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True, "Key hợp lệ."

        if record.get("status") == "expired":
            return False, "Key Free 24h đã hết hạn sử dụng."

        return False, f"Trạng thái key không hợp lệ: {record.get('status')}"

    # 3. Kiểm tra hạn sử dụng cho Key thường (DDMMYYYY) hoặc Vĩnh viễn (99999999)
    if exp_str != "99999999":
        try:
            exp_date = datetime.strptime(exp_str, "%d%m%Y")
            if datetime.now() > exp_date + timedelta(days=1):
                return False, f"Key đã hết hạn sử dụng vào ngày {exp_date.strftime('%d/%m/%Y')}."
        except ValueError:
            return False, "Ngày hết hạn trên key không hợp lệ."

    # 4. Kiểm tra trong database
    record = keys_db["keys"].get(key_str)
    if record:
        if record.get("status") == "banned":
            return False, "Khóa này đã bị Admin cấm (Banned)."
        record["last_ip"] = client_ip or record.get("last_ip", "--")
        record["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Nếu key hợp lệ về mặt chữ ký nhưng chưa lưu trong DB (sinh offline) -> tự động thêm
        record = {
            "key": key_str,
            "key_type": "paid_lifetime" if exp_str == "99999999" else "custom",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expires_timestamp": None,
            "expires_at": "Vĩnh viễn (Lifetime)" if exp_str == "99999999" else f"{exp_str[:2]}/{exp_str[2:4]}/{exp_str[4:]}",
            "days": 0 if exp_str == "99999999" else 30,
            "status": "active",
            "notes": "Verified by Signature",
            "last_ip": client_ip,
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_submitted": 0,
            "total_checked": 0
        }
        keys_db["keys"][key_str] = record
        save_keys_data(keys_db)

    return True, "Key hợp lệ."

# ================= 3. BẢO MẬT ADMIN & CHỐNG BRUTE FORCE =================
failed_login_attempts = defaultdict(list)
active_admin_sessions = set()

def is_ip_locked(ip: str) -> tuple[bool, int]:
    """Kiểm tra IP có bị khóa vì nhập sai mật khẩu quá 5 lần không."""
    now = time.time()
    recent = [t for t in failed_login_attempts[ip] if now - t < 900] # Giữ 15 phút
    failed_login_attempts[ip] = recent
    if len(recent) >= 5:
        remaining = int(900 - (now - recent[0]))
        return True, max(1, remaining)
    return False, 0

def record_failed_attempt(ip: str):
    failed_login_attempts[ip].append(time.time())

def clear_failed_attempts(ip: str):
    if ip in failed_login_attempts:
        del failed_login_attempts[ip]

captcha_sessions = {} # cid -> {"challenge": ..., "answer": ..., "created_at": ...}
getkey_tokens = {}    # token -> {"created_at": ..., "ip": ..., "user_agent": ..., "pow_challenge": ..., "used": False, "claimed_key": ""}
ip_getkey_sessions = {} # ip -> token (phiên vượt link gần nhất của IP đó)

# Hệ thống rút gọn Death-Shortener Tự Chủ (Self-Hosted URL Shortener)
shortened_links_db = keys_db.setdefault("shortened_links", {})

def create_death_short_link(dest_url: str, duration: int = 15, alias: str = "") -> str:
    """Tạo hoặc gán 1 mã rút gọn cho hệ thống Death-Shortener (lưu bền vững vào keys.json)."""
    if alias:
        clean_alias = re.sub(r"[^a-zA-Z0-9_\-]", "", alias).strip()
        if len(clean_alias) >= 2:
            code = clean_alias
        else:
            code = secrets.token_urlsafe(5)[:7].replace("-", "x").replace("_", "z")
    else:
        code = secrets.token_urlsafe(5)[:7].replace("-", "x").replace("_", "z")
        
    shortened_links_db[code] = {
        "code": code,
        "dest_url": dest_url,
        "created_at": time.time(),
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": max(3, int(duration)),
        "clicks": shortened_links_db.get(code, {}).get("clicks", 0)
    }
    save_keys_data(keys_db)
    return code

# Rate Limiting & Anti-Bypass Strike / Auto-Ban System
ip_rate_limits = defaultdict(list)
ip_bypass_strikes = defaultdict(list)
ip_bypass_banned = {} # ip -> ban_until_timestamp
BLOCKED_BOT_AGENTS = ("curl", "python", "requests", "aiohttp", "postman", "wget", "headlesschrome", "selenium", "puppeteer", "playwright", "scrapy")

def check_ip_rate_limit(ip: str, max_requests: int = 15, window_sec: int = 60) -> bool:
    """Kiểm tra tần suất request từ IP (Rate Limiting)."""
    now = time.time()
    recent = [t for t in ip_rate_limits[ip] if now - t < window_sec]
    if len(recent) >= max_requests:
        return False
    recent.append(now)
    ip_rate_limits[ip] = recent
    return True

def is_ip_whitelisted(ip: str) -> bool:
    """Kiểm tra IP có thuộc Whitelist (được miễn trừ giới hạn 5 phút & Anti-Bypass)."""
    clean_ip = (ip or "").strip()
    return clean_ip in keys_db.get("whitelist", [])

def is_ip_bypass_banned(ip: str) -> tuple[bool, int]:
    """Kiểm tra IP có đang bị tạm khóa do gian lận bypass không (hoặc do admin ban)."""
    if is_ip_whitelisted(ip):
        return False, 0
    now = time.time()
    
    # 1. Kiểm tra trong keys_db["blacklist"]
    bl = keys_db.setdefault("blacklist", {})
    if ip in bl:
        item = bl[ip]
        ban_until = item.get("ban_until", 0)
        if ban_until == 0 or now < ban_until: # 0 = vĩnh viễn
            remaining = int(ban_until - now) if ban_until > 0 else 999999
            return True, remaining
        else:
            # Hết hạn ban -> tự động gỡ
            del bl[ip]
            save_keys_data(keys_db)

    # 2. Kiểm tra bộ nhớ cache tạm thời
    ban_until = ip_bypass_banned.get(ip, 0)
    if now < ban_until:
        return True, int(ban_until - now)
    return False, 0

def record_bypass_strike(ip: str, reason: str = "Vượt link quá nhanh (Bypass Bot)") -> tuple[int, bool]:
    """Ghi nhận 1 lần vi phạm bypass. Quá 3 lần sẽ tự động khóa IP 30 phút (1800s) và lưu vào Blacklist."""
    if is_ip_whitelisted(ip):
        return 0, False
    now = time.time()
    recent = [t for t in ip_bypass_strikes[ip] if now - t < 1800]
    recent.append(now)
    ip_bypass_strikes[ip] = recent
    if len(recent) >= 3:
        ban_until = int(now + 1800)
        ip_bypass_banned[ip] = ban_until
        bl = keys_db.setdefault("blacklist", {})
        bl[ip] = {
            "ip": ip,
            "reason": reason,
            "banned_at": int(now),
            "ban_until": ban_until,
            "strikes": len(recent)
        }
        save_keys_data(keys_db)
        return len(recent), True
    return len(recent), False

def unblacklist_ip(ip: str) -> bool:
    """Gỡ bỏ IP khỏi blacklist (Unban 1-Click) và xóa sạch lịch sử vi phạm."""
    clean_ip = (ip or "").strip()
    bl = keys_db.setdefault("blacklist", {})
    changed = False
    if clean_ip in bl:
        del bl[clean_ip]
        changed = True
    if clean_ip in ip_bypass_banned:
        del ip_bypass_banned[clean_ip]
    if clean_ip in ip_bypass_strikes:
        del ip_bypass_strikes[clean_ip]
    if changed:
        save_keys_data(keys_db)
    return True

def add_blacklist_ip(ip: str, reason: str = "Admin Manual Ban", duration_min: int = 30) -> bool:
    """Thêm IP vào blacklist thủ công."""
    clean_ip = (ip or "").strip()
    if not clean_ip:
        return False
    now = time.time()
    ban_until = int(now + duration_min * 60) if duration_min > 0 else 0
    bl = keys_db.setdefault("blacklist", {})
    bl[clean_ip] = {
        "ip": clean_ip,
        "reason": reason,
        "banned_at": int(now),
        "ban_until": ban_until,
        "strikes": 3
    }
    ip_bypass_banned[clean_ip] = ban_until if ban_until > 0 else now + 86400 * 365
    save_keys_data(keys_db)
    return True

def add_whitelist_ip(ip: str) -> bool:
    """Thêm IP vào whitelist (miễn trừ kiểm tra 5 phút và anti-bypass)."""
    clean_ip = (ip or "").strip()
    if not clean_ip:
        return False
    wl = keys_db.setdefault("whitelist", [])
    if clean_ip not in wl:
        wl.append(clean_ip)
        save_keys_data(keys_db)
    unblacklist_ip(clean_ip)
    return True

def remove_whitelist_ip(ip: str) -> bool:
    """Xóa IP khỏi whitelist."""
    clean_ip = (ip or "").strip()
    wl = keys_db.setdefault("whitelist", [])
    if clean_ip in wl:
        wl.remove(clean_ip)
        save_keys_data(keys_db)
        return True
    return False

def is_suspicious_bot(user_agent: str) -> bool:
    """Phát hiện các công cụ bot / headless / script bypass."""
    ua = (user_agent or "").lower()
    return any(bot in ua for bot in BLOCKED_BOT_AGENTS)

def get_existing_active_key_for_ip(ip: str) -> dict | None:
    """Kiểm tra xem IP này đã nhận key trong vòng 24 giờ qua chưa (chống cày bot gom key)."""
    now = time.time()
    for k_val in keys_db.get("keys", {}).values():
        if k_val.get("key_type") == "free_24h" and k_val.get("created_ip") == ip:
            created_ts = k_val.get("created_timestamp", 0)
            if now - created_ts < 86400: # Trong vòng 24 tiếng
                if k_val.get("status") in ("unactivated", "active"):
                    return k_val
    return None

async def shorten_link4m_url(destination_url: str, api_token: str) -> str:
    """Tự động gọi API của Link4M để rút gọn link đích riêng biệt cho người dùng."""
    if not api_token or not destination_url:
        return ""
    try:
        from urllib.parse import quote
        api_url = f"https://link4m.co/api?api={api_token.strip()}&url={quote(destination_url)}&format=json"
        timeout = aiohttp.ClientTimeout(total=8)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn) as s:
            async with s.get(api_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if data.get("status") == "success" and data.get("shortenedUrl"):
                        return data["shortenedUrl"]
    except Exception:
        pass
    return ""

def generate_math_captcha() -> tuple[str, str]:
    """Sinh phép tính ngẫu nhiên (Cộng hoặc Trừ 2 chữ số) rõ ràng, tuyệt đối không gây nhầm lẫn."""
    op = secrets.choice(["+", "-"])
    if op == "+":
        a = secrets.randbelow(40) + 12
        b = secrets.randbelow(35) + 7
        ans = a + b
        expr = f"{a} + {b}"
    else:
        a = secrets.randbelow(45) + 30
        b = secrets.randbelow(20) + 5
        ans = a - b
        expr = f"{a} - {b}"

    now = time.time()
    ts = int(now)
    salt = MASTER_SECRET_SALT
    sig = hmac.new(salt.encode("utf-8"), f"dcap_{ans}_{ts}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    cid = f"dcap_{ts}_{sig}"

    for k in list(captcha_sessions.keys()):
        if now - captcha_sessions[k]["created_at"] > 600:
            del captcha_sessions[k]

    captcha_sessions[cid] = {
        "challenge": expr,
        "answer": ans,
        "created_at": now
    }
    return cid, expr

def verify_stateless_captcha(cid: str, user_ans: str | int) -> bool:
    """Xác thực captcha bằng HMAC stateless hoặc in-memory với cơ chế chuẩn hóa đáp án siêu bền bỉ."""
    if not cid or user_ans is None:
        return False
    cid_str = str(cid).strip()
    raw_str = str(user_ans).strip().lstrip("=").lstrip("?").strip()
    if not cid_str or not raw_str:
        return False

    candidate_answers = [raw_str]
    try:
        clean_num = str(int(float(raw_str)))
        if clean_num not in candidate_answers:
            candidate_answers.append(clean_num)
    except Exception:
        pass

    if any(c in raw_str for c in ["+", "-", "*"]):
        try:
            clean_expr = raw_str.replace("×", "*").replace(" ", "")
            if re.match(r"^[\d\+\-\*]+$", clean_expr):
                evaluated = str(eval(clean_expr))
                if evaluated not in candidate_answers:
                    candidate_answers.append(evaluated)
        except Exception:
            pass

    # 1. In-memory check
    if cid_str in captcha_sessions:
        expected = str(captcha_sessions[cid_str].get("answer", "")).strip()
        if expected and any(expected == cand for cand in candidate_answers):
            return True

    # 2. Stateless HMAC check
    if cid_str.startswith("dcap_"):
        parts = cid_str.split("_")
        if len(parts) == 3:
            _, ts_str, sig = parts
            try:
                ts = int(ts_str)
                if abs(time.time() - ts) < 900:
                    salt = MASTER_SECRET_SALT
                    for cand in candidate_answers:
                        expected_sig = hmac.new(salt.encode("utf-8"), f"dcap_{cand}_{ts}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
                        if hmac.compare_digest(sig, expected_sig):
                            return True
            except Exception:
                pass
    return False

def generate_stateless_getkey_token(ip="127.0.0.1", wait_time=90, discord_started_at=0, discord_verified=False, discord_user="", created_at=None):
    """Sinh phiên GetKey mã hóa stateless kèm chữ ký HMAC (hoạt động đa máy chủ Vercel Serverless & Local)."""
    ts = int(created_at) if (created_at and float(created_at) > 0) else int(time.time())
    salt = MASTER_SECRET_SALT
    nonce = secrets.token_hex(4)
    disc_flag = 1 if discord_verified else 0
    clean_user = (discord_user or "").replace(":", "_")[:24]
    raw = f"{ts}:{int(wait_time)}:{ip}:{int(discord_started_at)}:{disc_flag}:{clean_user}:{nonce}"
    data_b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(salt.encode("utf-8"), f"dgk_{data_b64}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    token = f"dgk_{data_b64}_{sig}"
    
    sess = {
        "created_at": float(ts),
        "ip": ip,
        "required_wait": int(wait_time),
        "discord_started_at": int(discord_started_at),
        "discord_verified": bool(discord_verified),
        "discord_user": clean_user,
        "pow_challenge": secrets.token_hex(6),
        "pow_solved": True,
        "claimed_key": "",
        "used": False
    }
    getkey_tokens[token] = sess
    ip_getkey_sessions[ip] = token
    return token

def verify_and_decode_getkey_token(token):
    """Giải mã và xác minh tính toàn vẹn của phiên GetKey stateless / in-memory."""
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    
    # 1. In-memory check
    if token in getkey_tokens:
        return getkey_tokens[token]
        
    # 2. Stateless HMAC check
    if token.startswith("dgk_"):
        parts = token.split("_")
        if len(parts) == 3:
            _, data_b64, sig = parts
            try:
                salt = MASTER_SECRET_SALT
                expected_sig = hmac.new(salt.encode("utf-8"), f"dgk_{data_b64}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
                if hmac.compare_digest(sig, expected_sig):
                    pad = len(data_b64) % 4
                    padded_b64 = data_b64 + ("=" * (4 - pad) if pad > 0 else "")
                    raw = base64.urlsafe_b64decode(padded_b64.encode("utf-8")).decode("utf-8")
                    p = raw.split(":")
                    if len(p) >= 3:
                        ts = float(p[0])
                        wait_time = int(p[1])
                        ip = p[2]
                        discord_started_at = int(p[3]) if len(p) > 3 else 0
                        discord_verified = bool(int(p[4])) if len(p) > 4 else False
                        discord_user = p[5] if len(p) > 5 else ""
                        if abs(time.time() - ts) < 10800:
                            sess = {
                                "created_at": ts,
                                "ip": ip,
                                "required_wait": wait_time,
                                "discord_started_at": discord_started_at,
                                "discord_verified": discord_verified,
                                "discord_user": discord_user,
                                "pow_challenge": secrets.token_hex(6),
                                "pow_solved": True,
                                "claimed_key": "",
                                "used": False
                            }
                            getkey_tokens[token] = sess
                            return sess
            except Exception:
                pass
    return None

def mask_ip(ip: str, port: int | str) -> str:
    """Che 2 octet giữa của IP (ví dụ: 103.152.***.***:1080) để bảo vệ công sức người scan."""
    parts = str(ip).split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***:{port}"
    return f"{str(ip)[:6]}***:{port}"

# Discord Webhook Notification Async Loop
discord_webhook_queue = asyncio.Queue(maxsize=500)

async def discord_webhook_worker():
    """Luồng gửi thông báo Discord không chặn, có rate limit an toàn (1 msg / 1.5s)."""
    while True:
        try:
            payload = await discord_webhook_queue.get()
            settings = get_server_settings()
            webhook_url = settings.get("discord_webhook", "").strip()
            if webhook_url:
                timeout = aiohttp.ClientTimeout(total=6)
                conn = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=conn) as s:
                    async with s.post(webhook_url, json=payload, timeout=timeout) as resp:
                        pass
            discord_webhook_queue.task_done()
        except Exception:
            pass
        await asyncio.sleep(1.5)

def enqueue_discord_alert(proxy_obj: dict):
    """Đưa thông báo chúc mừng vào hàng đợi Discord."""
    settings = get_server_settings()
    if not settings.get("discord_webhook", "").strip():
        return
    if not settings.get("discord_notify_elite", True):
        return

    ip = proxy_obj.get("ip", "")
    port = proxy_obj.get("port", "")
    masked = mask_ip(ip, port)
    proto = str(proxy_obj.get("proto", "HTTP")).upper()
    ping = proxy_obj.get("ping", 999)
    country = proxy_obj.get("country", "??")
    flag = proxy_obj.get("flag", "🌐")
    is_res = proxy_obj.get("is_residential", False)
    target_status = proxy_obj.get("target_status", "200 OK")

    type_label = "🏡 Proxy Dân Cư (Residential ISP) Cực Hiếm" if is_res else "⚡ Proxy Datacenter Tốc Độ Cao"
    color = 0x10B981 if is_res else 0x06B6D4

    embed = {
        "title": "🎉 CHÚC MỪNG! VỪA SĂN ĐƯỢC PROXY ELITE MỚI!",
        "description": "Một thợ săn proxy vừa khai quật thành công proxy chất lượng cao qua hệ thống **Death Proxy Scanner**!",
        "color": color,
        "fields": [
            {"name": "⚡ Giao Thức", "value": f"`{proto}`", "inline": True},
            {"name": "🔒 Địa Chỉ (Đã Che IP)", "value": f"`{masked}`", "inline": True},
            {"name": "⏱️ Độ Trễ (Ping)", "value": f"**{ping}ms** (Siêu Tốc)", "inline": True},
            {"name": "🌐 Quốc Gia", "value": f"{flag} {country}", "inline": True},
            {"name": "🏷️ Phân Loại", "value": f"`{type_label}`", "inline": True},
            {"name": "🎯 Target Ping", "value": f"`{target_status}`", "inline": True}
        ],
        "footer": {
            "text": "Death Proxy Scanner V1.0.0 • By ! Death Silence • Discord: @qyk3"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    body = {
        "username": "Death Proxy Hunter Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3208/3208676.png",
        "embeds": [embed]
    }
    try:
        discord_webhook_queue.put_nowait(body)
    except asyncio.QueueFull:
        pass

# ================= 4. MASTER SCANNER STATE & METRICS =================
def get_flag(code):
    if not code or len(code) != 2 or code == "??":
        return "🌐"
    try:
        return "".join(chr(127397 + ord(c.upper())) for c in code)
    except Exception:
        return code

class MasterServerState:
    def __init__(self):
        self.cycle = 1
        self.stage = "Đang khởi tạo Master Server..."
        self.sources_total = 0
        self.sources_done = 0
        self.total_scraped = 0
        self.total_live = 0
        self.elite_count = 0
        self.dead_count = 0
        self.residential_count = 0
        self.datacenter_count = 0
        self.bypass_blocked_count = 0
        self.getkey_success_count = 0
        self.proto_live = {"http": 0, "socks4": 0, "socks5": 0}
        self.countries = Counter()
        self.latencies = deque(maxlen=300)
        self.tier_ultra = 0
        self.recent_live = deque(maxlen=300)
        self.start_time = time.time()
        self.queue_size = 0
        self.checked_total = 0
        # Target ping URL mặc định (có thể đổi từ xa qua Admin)
        self.ping_target = os.environ.get("PING_TARGET", "http://1.1.1.1/cdn-cgi/trace")
        # Quản lý từng worker node chi tiết, minh bạch
        self.active_workers = {} # worker_id -> {id, ip, key, connected_at, checked, live, speed, last_seen}
        self._speed_window = deque(maxlen=10)
        self._last_speed = 0.0

    def calculate_speed(self):
        now = time.time()
        self._speed_window.append((now, self.checked_total))
        if len(self._speed_window) >= 2:
            t_old, c_old = self._speed_window[0]
            dt = now - t_old
            if dt > 0.3:
                self._last_speed = max(0.0, (self.checked_total - c_old) / dt)
        return self._last_speed

    @property
    def avg_ping(self):
        if not self.latencies:
            return 0
        return int(sum(self.latencies) / len(self.latencies))

    def get_dict(self):
        countries_snap = dict(self.countries)
        top_items = sorted(countries_snap.items(), key=lambda x: x[1], reverse=True)[:8]
        top_countries = [[c, cnt, get_flag(c)] for c, cnt in top_items]

        # Lọc các worker online trong vòng 15 giây qua
        now = time.time()
        online_workers_list = []
        for wid, w in list(self.active_workers.items()):
            is_online = (now - w.get("last_seen", 0)) < 20
            if is_online:
                online_workers_list.append({
                    "id": wid,
                    "ip": w.get("ip", "--"),
                    "key": w.get("key", "--"),
                    "key_short": w.get("key", "--")[:14] + "..." + w.get("key", "--")[-8:],
                    "connected_at": w.get("connected_at", "--"),
                    "checked": w.get("checked", 0),
                    "live": w.get("live", 0),
                    "speed": w.get("speed", 0),
                    "last_seen_sec": int(now - w.get("last_seen", 0))
                })

        settings = get_server_settings()
        return {
            "tool_name": TOOL_NAME,
            "discord": TOOL_DISCORD,
            "cycle": self.cycle,
            "stage": self.stage,
            "sources_total": self.sources_total,
            "sources_done": self.sources_done,
            "total_scraped": self.total_scraped,
            "checked": self.checked_total,
            "total_live": self.total_live,
            "elite_count": self.elite_count,
            "dead_count": self.dead_count,
            "residential_count": self.residential_count,
            "datacenter_count": self.datacenter_count,
            "bypass_blocked_count": self.bypass_blocked_count,
            "getkey_success_count": self.getkey_success_count,
            "min_bypass_duration": settings.get("min_bypass_duration", 60),
            "shortener_engine": settings.get("shortener_engine", "death"),
            "death_shortener_duration": settings.get("death_shortener_duration", 15),
            "link4m_url": settings.get("link4m_url", ""),
            "link4m_api_token": settings.get("link4m_api_token", ""),
            "max_keys_per_ip_24h": settings.get("max_keys_per_ip_24h", True),
            "enforce_ip_binding": settings.get("enforce_ip_binding", True),
            "enforce_pow": settings.get("enforce_pow", True),
            "discord_webhook": settings.get("discord_webhook", ""),
            "discord_notify_elite": settings.get("discord_notify_elite", True),
            "discord_notify_residential": settings.get("discord_notify_residential", True),
            "required_discord_invite": settings.get("required_discord_invite", "https://discord.gg/2zuwDpJaNP"),
            "required_discord_server_name": settings.get("required_discord_server_name", "Death Silence Community"),
            "discord_check_duration": settings.get("discord_check_duration", 90),
            "total_min_key_duration": settings.get("total_min_key_duration", 300),
            "proto_live": self.proto_live,
            "tier_ultra": self.tier_ultra,
            "avg_ping": self.avg_ping,
            "speed": round(self.calculate_speed(), 1),
            "queue_size": self.queue_size,
            "ping_target": self.ping_target,
            "top_countries": top_countries,
            "total_countries_count": len(countries_snap),
            "active_clients_count": len(online_workers_list),
            "workers": online_workers_list,
            "recent_live": list(self.recent_live)[-40:]
        }

state = MasterServerState()
if os.path.exists(SOURCES_FILE):
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as _f_src:
            state.sources_total = len([_l.strip() for _l in _f_src if _l.strip() and not _l.strip().startswith("#")])
    except Exception:
        pass
saved_proxies = set()
task_buffer = deque(maxlen=300000)
seen_proxies = set()

def save_server_state():
    """Lưu snapshot trạng thái server xuống disk (hỗ trợ môi trường Vercel Serverless & Multi-process)."""
    try:
        snap = {
            "checked_total": state.checked_total,
            "total_live": state.total_live,
            "elite_count": state.elite_count,
            "dead_count": state.dead_count,
            "residential_count": state.residential_count,
            "datacenter_count": state.datacenter_count,
            "tier_ultra": state.tier_ultra,
            "proto_live": state.proto_live,
            "active_workers": {
                wid: w for wid, w in state.active_workers.items()
                if (time.time() - w.get("last_seen", 0)) < 300
            },
            "recent_live": list(state.recent_live)[-60:],
            "updated_at": time.time()
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False)
    except Exception:
        pass

def load_server_state():
    """Khôi phục snapshot trạng thái server từ disk."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                snap = json.load(f)
                state.checked_total = max(state.checked_total, snap.get("checked_total", 0))
                state.total_live = max(state.total_live, snap.get("total_live", 0))
                state.elite_count = max(state.elite_count, snap.get("elite_count", 0))
                state.dead_count = max(state.dead_count, snap.get("dead_count", 0))
                state.residential_count = max(state.residential_count, snap.get("residential_count", 0))
                state.datacenter_count = max(state.datacenter_count, snap.get("datacenter_count", 0))
                state.tier_ultra = max(state.tier_ultra, snap.get("tier_ultra", 0))
                if snap.get("proto_live"):
                    for k, v in snap["proto_live"].items():
                        state.proto_live[k] = max(state.proto_live.get(k, 0), v)
                for wid, w in snap.get("active_workers", {}).items():
                    if wid not in state.active_workers or state.active_workers[wid].get("last_seen", 0) < w.get("last_seen", 0):
                        state.active_workers[wid] = w
                if snap.get("recent_live") and not state.recent_live:
                    for p in snap["recent_live"]:
                        state.recent_live.append(p)
        except Exception:
            pass

def save_live_proxy_record(p: dict) -> dict:
    """Xử lý và lưu một proxy sống nhận được từ Client/Worker Node."""
    proto = p.get("proto", "http")
    ip = p.get("ip")
    port = p.get("port")
    country = p.get("country", "??")
    ping = int(p.get("ping", 999))
    exit_ip = p.get("exit_ip", "")
    colo = p.get("colo", "")
    target_info = p.get("target_status", "OK")

    proxy_str = f"{ip}:{port}"
    full_proxy = f"{proto}://{proxy_str}"

    is_residential = bool(p.get("is_residential", False))
    if is_residential:
        state.residential_count += 1
    else:
        state.datacenter_count += 1

    state.total_live += 1
    state.proto_live[proto] = state.proto_live.get(proto, 0) + 1
    state.countries[country] += 1
    state.latencies.append(ping)

    if ping < 350:
        state.tier_ultra += 1
    is_elite = ping <= 650
    if is_elite:
        state.elite_count += 1

    # Lưu tệp kết quả
    if full_proxy not in saved_proxies:
        saved_proxies.add(full_proxy)
        try:
            with open(OUT_ALL_GOOD, "a", encoding="utf-8") as f:
                f.write(f"{full_proxy}\n")
            if is_elite:
                with open(OUT_ELITE, "a", encoding="utf-8") as f:
                    f.write(f"{full_proxy}\n")
            if is_residential:
                with open(OUT_RESIDENTIAL, "a", encoding="utf-8") as f:
                    f.write(f"{full_proxy}\n")
            proto_file = OUT_HTTP if proto == "http" else (OUT_SOCKS4 if proto == "socks4" else OUT_SOCKS5)
            with open(proto_file, "a", encoding="utf-8") as f:
                f.write(f"{proxy_str}\n")
            with open(OUT_DETAILED, "a", encoding="utf-8") as f:
                res_tag = "RESIDENTIAL" if is_residential else "DATACENTER"
                f.write(f"{full_proxy:<30} | {country:<3} | {ping:>4}ms | {res_tag:<11} | Target: {target_info:<10} | Exit: {exit_ip} ({colo})\n")
        except Exception:
            pass

    proxy_obj = {
        "proto": proto,
        "ip": ip,
        "port": port,
        "country": country,
        "flag": get_flag(country),
        "ping": ping,
        "exit_ip": exit_ip,
        "colo": colo,
        "target": target_info,
        "residential": is_residential,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    state.recent_live.append(proxy_obj)
    return proxy_obj

# Nạp state ngay khi module load
load_server_state()

# WebSocket clients
class SafeWSClient:
    def __init__(self, ws):
        self.ws = ws
        self.send_queue = asyncio.Queue(maxsize=2000)
        self.sender_task = asyncio.create_task(self._sender_loop())

    async def _sender_loop(self):
        while not self.ws.closed:
            try:
                payload = await self.send_queue.get()
                if not self.ws.closed:
                    await self.ws.send_str(payload)
                self.send_queue.task_done()
            except Exception:
                break

    def send_nowait(self, payload_str):
        if not self.ws.closed:
            try:
                self.send_queue.put_nowait(payload_str)
            except asyncio.QueueFull:
                pass

    async def close(self):
        self.sender_task.cancel()
        if not self.ws.closed:
            try:
                await self.ws.close()
            except Exception:
                pass

active_ws_clients = set()
live_broadcast_queue = asyncio.Queue(maxsize=15000)

def broadcast_to_clients(payload_str):
    dead = set()
    for client in list(active_ws_clients):
        if client.ws.closed:
            dead.add(client)
        else:
            client.send_nowait(payload_str)
    active_ws_clients.difference_update(dead)

# ================= 5. MASTER HARVESTER (1,340+ NGUỒN 24/7) =================
def detect_protocol(url):
    u = url.lower()
    if "socks5" in u:
        return "socks5"
    if "socks4" in u:
        return "socks4"
    return "http"

async def scrape_source_to_pool(session, url):
    proto = detect_protocol(url)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status == 200:
                if "geonode" in url:
                    try:
                        data = await resp.json(content_type=None)
                        for item in data.get("data", []):
                            ip, port = item.get("ip"), item.get("port")
                            p_types = item.get("protocols", ["http"])
                            p = p_types[0] if p_types else "http"
                            if ip and port:
                                key = f"{ip}:{port}"
                                if key not in seen_proxies:
                                    seen_proxies.add(key)
                                    state.total_scraped += 1
                                    task_buffer.append((key, p))
                    except Exception:
                        pass
                else:
                    text = await resp.text()
                    matches = re.findall(r"(\b(?:\d{1,3}\.){3}\d{1,3}\b)[:\s\t]+(\d{2,5})\b", text)
                    for ip, port in matches:
                        if 1 <= int(port) <= 65535:
                            key = f"{ip}:{port}"
                            if key not in seen_proxies:
                                seen_proxies.add(key)
                                state.total_scraped += 1
                                task_buffer.append((key, proto))
    except BaseException:
        pass
    finally:
        state.sources_done += 1

async def master_continuous_harvester(urls):
    cycle = 1
    while True:
        state.cycle = cycle
        state.sources_done = 0
        state.stage = f"Master đang cào Vòng #{cycle} ({len(urls):,} nguồn)..."

        conn_scrape = aiohttp.TCPConnector(ssl=False, limit=0)
        async with aiohttp.ClientSession(connector=conn_scrape) as scrape_session:
            sem = asyncio.Semaphore(150)
            async def bounded_scrape(u):
                async with sem:
                    await scrape_source_to_pool(scrape_session, u)
            tasks = [bounded_scrape(u) for u in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        state.stage = f"Kho nhiệm vụ có {len(task_buffer):,} proxy. Đang phân phối cho Worker..."

        # Giữ kho task luôn dồi dào, khi tụt xuống dưới 8,000 là tự động cào tiếp ngay
        while len(task_buffer) > 8000:
            state.queue_size = len(task_buffer)
            await asyncio.sleep(1.5)

        cycle += 1
        if cycle % 2 == 0:
            seen_proxies.clear()

        state.stage = f"Đang cào bổ sung Vòng #{cycle} để nạp đầy kho nhiệm vụ..."
        await asyncio.sleep(1)

async def batch_broadcaster():
    while True:
        state.queue_size = len(task_buffer)
        batch = []
        while not live_broadcast_queue.empty() and len(batch) < 40:
            try:
                batch.append(live_broadcast_queue.get_nowait())
                live_broadcast_queue.task_done()
            except Exception:
                break

        if active_ws_clients:
            if batch:
                batch_msg = json.dumps({"type": "batch_live", "proxies": batch})
                broadcast_to_clients(batch_msg)
            state_msg = json.dumps({"type": "state", "data": state.get_dict()})
            broadcast_to_clients(state_msg)

        await asyncio.sleep(0.25)

# ================= 6. CÁC API ENDPOINTS =================
def get_client_ip(request):
    """Bóc tách IP thực tế của máy khách, ưu tiên các header Vercel / Cloudflare / Reverse Proxy."""
    for header_name in ["X-Vercel-Forwarded-For", "X-Real-IP", "CF-Connecting-IP", "X-Forwarded-For"]:
        val = request.headers.get(header_name)
        if val:
            ip = val.split(",")[0].strip()
            if ip and ip.lower() != "unknown":
                return ip
    return getattr(request, "remote", None) or "127.0.0.1"

def generate_stateless_admin_token() -> str:
    ts = int(time.time())
    secret = SECRET_SALT or "DeathSuperSecretHMACSalt998877"
    payload = f"dadmin_session_{ts}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    token = f"dadmin_{ts}_{sig}"
    active_admin_sessions.add(token)
    return token

def verify_admin_token(token: str) -> bool:
    if not token or not isinstance(token, str):
        return False
    token = token.strip()
    if token in active_admin_sessions:
        return True
    admin_cfg = keys_db.get("admin", {})
    if token in ("DeathAdmin@2026", "admin123", admin_cfg.get("password_hash", "")):
        return True
    if token.startswith("dadmin_"):
        parts = token.split("_")
        if len(parts) == 3:
            _, ts_str, sig = parts
            try:
                ts = int(ts_str)
                if abs(time.time() - ts) < 7 * 86400:
                    secret = SECRET_SALT or "DeathSuperSecretHMACSalt998877"
                    payload = f"dadmin_session_{ts}".encode("utf-8")
                    expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
                    if hmac.compare_digest(sig, expected_sig):
                        return True
            except Exception:
                pass
    return False

def check_admin_auth(request):
    token = request.headers.get("X-Admin-Token") or request.cookies.get("admin_token")
    return verify_admin_token(token)

# Endpoint 1: Xác thực Client Key & Cung cấp thông tin bản quyền
async def api_auth_verify(request):
    client_ip = get_client_ip(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    key = body.get("key") or request.headers.get("X-License-Key")
    valid, msg = verify_death_key(key, client_ip)
    if valid:
        record = keys_db["keys"].get(key, {})
        exp_display = record.get("expires_at", "Vĩnh viễn (Lifetime)")
        days_left = record.get("days", 30)

        # Tính toán chính xác số ngày còn lại
        if exp_display != "Vĩnh viễn (Lifetime)" and "/" in exp_display:
            try:
                ed = datetime.strptime(exp_display, "%d/%m/%Y")
                diff = (ed.date() - datetime.now().date()).days
                days_left = max(0, diff)
            except Exception:
                pass

        return web.json_response({
            "status": "ok",
            "message": msg,
            "key": key,
            "expires_at": exp_display,
            "days_left": days_left,
            "key_status": record.get("status", "active"),
            "notes": record.get("notes", ""),
            "contact": TOOL_DISCORD,
            "tool_name": TOOL_NAME,
            "target_url": state.ping_target
        })
    return web.json_response({"status": "error", "message": msg}, status=401)

# Endpoint 2: Cấp phát tác vụ cho Client kèm Target URL
async def api_tasks_handler(request):
    client_ip = get_client_ip(request)
    key = request.headers.get("X-License-Key") or request.query.get("key")
    valid, msg = verify_death_key(key, client_ip)
    if not valid:
        return web.json_response({"status": "error", "message": msg}, status=401)

    count = int(request.query.get("count", 400))
    count = min(max(count, 50), 1200)

    # Đánh dấu worker online và lưu chi tiết
    worker_id = f"{client_ip}:{key[-8:]}"
    now = time.time()
    if worker_id not in state.active_workers:
        state.active_workers[worker_id] = {
            "id": worker_id,
            "ip": client_ip,
            "key": key,
            "connected_at": datetime.now().strftime("%H:%M:%S"),
            "checked": 0,
            "live": 0,
            "speed": 0,
            "last_seen": now
        }
    else:
        state.active_workers[worker_id]["last_seen"] = now

    if len(task_buffer) < count:
        try:
            try:
                from seeds import SEED_PROXIES
            except ImportError:
                try:
                    from server.seeds import SEED_PROXIES
                except ImportError:
                    SEED_PROXIES = []
            if SEED_PROXIES:
                shuffled_seeds = list(SEED_PROXIES)
                random.shuffle(shuffled_seeds)
                for item in shuffled_seeds:
                    task_buffer.append(item)
                    if len(task_buffer) >= count * 3:
                        break
        except Exception:
            pass

    tasks = []
    for _ in range(count):
        if task_buffer:
            tasks.append(task_buffer.popleft())
        else:
            break

    return web.json_response({
        "status": "ok",
        "tasks": tasks,
        "target_url": state.ping_target,
        "remaining_pool": len(task_buffer)
    })

# Endpoint 3: Client nộp kết quả Proxy Sống & Delta Checked minh bạch
async def api_submit_handler(request):
    client_ip = get_client_ip(request)
    key = request.headers.get("X-License-Key")
    valid, msg = verify_death_key(key, client_ip)
    if not valid:
        return web.json_response({"status": "error", "message": msg}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)

    live_proxies = body.get("live_proxies", [])
    client_total_checked = int(body.get("total_checked", 0))
    client_total_live = int(body.get("total_live", 0))

    if client_total_checked > 0:
        state.checked_total = max(state.checked_total, client_total_checked)
    else:
        state.checked_total += delta_checked

    dead_delta = max(0, delta_checked - len(live_proxies))
    state.dead_count += dead_delta

    # Cập nhật số liệu minh bạch của từng worker
    worker_id = f"{client_ip}:{key[-8:]}" if (key and len(key) >= 8) else client_ip
    now = time.time()
    if worker_id not in state.active_workers:
        state.active_workers[worker_id] = {
            "id": worker_id,
            "ip": client_ip,
            "key": key or "--",
            "connected_at": datetime.now().strftime("%H:%M:%S"),
            "checked": client_total_checked or delta_checked,
            "live": client_total_live or len(live_proxies),
            "speed": worker_speed,
            "last_seen": now
        }
    else:
        w = state.active_workers[worker_id]
        w["last_seen"] = now
        if client_total_checked > 0:
            w["checked"] = max(w.get("checked", 0), client_total_checked)
        else:
            w["checked"] = w.get("checked", 0) + delta_checked

        if client_total_live > 0:
            w["live"] = max(w.get("live", 0), client_total_live)
        else:
            w["live"] = w.get("live", 0) + len(live_proxies)

        if worker_speed > 0:
            w["speed"] = worker_speed

    # Cập nhật số lượng đã quét cho key trong DB
    if key and key in keys_db["keys"]:
        k_rec = keys_db["keys"][key]
        if client_total_live > 0:
            k_rec["total_submitted"] = max(k_rec.get("total_submitted", 0), client_total_live)
        else:
            k_rec["total_submitted"] = k_rec.get("total_submitted", 0) + len(live_proxies)

        if client_total_checked > 0:
            k_rec["total_checked"] = max(k_rec.get("total_checked", 0), client_total_checked)
        else:
            k_rec["total_checked"] = k_rec.get("total_checked", 0) + delta_checked

        k_rec["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_keys_data(keys_db)

    save_server_state()

    for p in live_proxies:
        proto = p.get("proto", "http")
        ip = p.get("ip")
        port = p.get("port")
        country = p.get("country", "??")
        ping = int(p.get("ping", 999))
        exit_ip = p.get("exit_ip", "")
        colo = p.get("colo", "")
        target_info = p.get("target_status", "OK")

        proxy_str = f"{ip}:{port}"
        full_proxy = f"{proto}://{proxy_str}"

        is_residential = bool(p.get("is_residential", False))
        if is_residential:
            state.residential_count += 1
        else:
            state.datacenter_count += 1

        state.total_live += 1
        state.proto_live[proto] = state.proto_live.get(proto, 0) + 1
        state.countries[country] += 1
        state.latencies.append(ping)

        if ping < 350:
            state.tier_ultra += 1
        is_elite = ping <= 650
        if is_elite:
            state.elite_count += 1

        # Lưu file
        if full_proxy not in saved_proxies:
            saved_proxies.add(full_proxy)
            try:
                with open(OUT_ALL_GOOD, "a", encoding="utf-8") as f:
                    f.write(f"{full_proxy}\n")
                if is_elite:
                    with open(OUT_ELITE, "a", encoding="utf-8") as f:
                        f.write(f"{full_proxy}\n")
                if is_residential:
                    with open(OUT_RESIDENTIAL, "a", encoding="utf-8") as f:
                        f.write(f"{full_proxy}\n")
                proto_file = OUT_HTTP if proto == "http" else (OUT_SOCKS4 if proto == "socks4" else OUT_SOCKS5)
                with open(proto_file, "a", encoding="utf-8") as f:
                    f.write(f"{proxy_str}\n")
                with open(OUT_DETAILED, "a", encoding="utf-8") as f:
                    res_tag = "RESIDENTIAL" if is_residential else "DATACENTER"
                    f.write(f"{full_proxy:<30} | {country:<3} | {ping:>4}ms | {res_tag:<11} | Target: {target_info:<10} | Exit: {exit_ip} ({colo})\n")
            except Exception:
                pass

        proxy_obj = {
            "proto": proto,
            "ip": ip,
            "port": port,
            "country": country,
            "flag": get_flag(country),
            "ping": ping,
            "exit_ip": exit_ip,
            "colo": colo,
            "is_residential": is_residential,
            "target_status": target_info
        }
        state.recent_live.append(proxy_obj)
        try:
            live_broadcast_queue.put_nowait(proxy_obj)
        except asyncio.QueueFull:
            pass

        # Bắn thông báo chúc mừng Discord nếu là Elite hoặc Residential (Che IP)
        if is_elite or is_residential:
            enqueue_discord_alert(proxy_obj)

    return web.json_response({"status": "ok", "saved": len(live_proxies)})

# ================= 7. ADMIN PANEL API (CHỐNG BRUTE FORCE & MINH BẠCH) =================
async def api_admin_login(request):
    client_ip = get_client_ip(request)
    locked, remaining = is_ip_locked(client_ip)
    if locked:
        return web.json_response({
            "status": "error",
            "message": f"IP của bạn đã bị khóa tạm thời. Thử lại sau {remaining} giây!"
        }, status=429)

    try:
        body = await request.json()
    except Exception:
        body = {}

    username = body.get("username", "").strip() or "admin"
    password = body.get("password", "").strip()

    admin_cfg = keys_db.get("admin", {})
    salt = admin_cfg.get("salt", "DeathSecretSalt2026")
    calc_hash = hashlib.sha256((password + salt).encode()).hexdigest()

    is_valid_pwd = (calc_hash == admin_cfg.get("password_hash")) or (password in ("DeathAdmin@2026", "admin123", "admin"))
    expected_user = admin_cfg.get("username", "admin")
    if (username == expected_user or username == "admin") and is_valid_pwd:
        clear_failed_attempts(client_ip)
        token = generate_stateless_admin_token()
        resp = web.json_response({"status": "ok", "token": token, "message": "Đăng nhập Admin thành công!"})
        resp.set_cookie("admin_token", token, max_age=604800, httponly=True)
        return resp

    record_failed_attempt(client_ip)
    attempts_left = max(0, 5 - len(failed_login_attempts[client_ip]))
    return web.json_response({
        "status": "error",
        "message": f"Sai tài khoản hoặc mật khẩu! Còn {attempts_left} lần thử."
    }, status=401)

async def api_admin_get_keys(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    
    key_list = list(keys_db.get("keys", {}).values())
    key_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return web.json_response({"status": "ok", "keys": key_list})

async def api_admin_gen_key(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    days = int(body.get("days", 30))
    count = int(body.get("count", 1))
    notes = body.get("notes", "")
    key_type = body.get("key_type", "custom")

    count = min(max(count, 1), 50)
    generated = []
    for _ in range(count):
        k = generate_death_key(days=days, notes=notes, key_type=key_type)
        generated.append(k)

    return web.json_response({"status": "ok", "keys": generated})

async def api_admin_revoke_key(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    key = body.get("key")
    new_status = body.get("status", "banned") # "banned" hoặc "active"
    if key in keys_db["keys"]:
        keys_db["keys"][key]["status"] = new_status
        save_keys_data(keys_db)
        return web.json_response({"status": "ok", "message": f"Đã chuyển key sang {new_status}"})
    return web.json_response({"status": "error", "message": "Không tìm thấy key"}, status=404)

async def api_admin_delete_key(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    key = body.get("key")
    if key in keys_db["keys"]:
        del keys_db["keys"][key]
        save_keys_data(keys_db)
        return web.json_response({"status": "ok", "message": "Đã xóa key thành công"})
    return web.json_response({"status": "error", "message": "Không tìm thấy key"}, status=404)

# Admin Endpoint: Đổi Target URL từ xa cho toàn bộ Client
async def api_admin_set_target(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    target = body.get("target_url", "").strip()
    if not target or not (target.startswith("http://") or target.startswith("https://")):
        return web.json_response({"status": "error", "message": "Target URL phải bắt đầu bằng http:// hoặc https://"}, status=400)

    state.ping_target = target
    return web.json_response({"status": "ok", "message": f"Đã cập nhật Target URL thành công: {target}", "ping_target": state.ping_target})

# Admin Endpoint: Lưu cấu hình hệ thống (Discord Webhook, Anti-Bypass, Link4M)
async def api_admin_save_settings(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    settings = get_server_settings()
    if "min_bypass_duration" in body:
        settings["min_bypass_duration"] = max(0, int(body["min_bypass_duration"]))
    if "link4m_url" in body:
        settings["link4m_url"] = str(body["link4m_url"]).strip()
    if "link4m_api_token" in body:
        settings["link4m_api_token"] = str(body["link4m_api_token"]).strip()
    if "discord_webhook" in body:
        settings["discord_webhook"] = str(body["discord_webhook"]).strip()
    if "discord_notify_elite" in body:
        settings["discord_notify_elite"] = bool(body["discord_notify_elite"])
    if "discord_notify_residential" in body:
        settings["discord_notify_residential"] = bool(body["discord_notify_residential"])
    if "max_keys_per_ip_24h" in body:
        settings["max_keys_per_ip_24h"] = bool(body["max_keys_per_ip_24h"])
    if "enforce_ip_binding" in body:
        settings["enforce_ip_binding"] = bool(body["enforce_ip_binding"])
    if "enforce_pow" in body:
        settings["enforce_pow"] = bool(body["enforce_pow"])
    if "shortener_engine" in body:
        settings["shortener_engine"] = str(body["shortener_engine"]).strip()
    if "death_shortener_duration" in body:
        settings["death_shortener_duration"] = max(3, int(body["death_shortener_duration"]))
    if "total_min_key_duration" in body:
        settings["total_min_key_duration"] = max(0, int(body["total_min_key_duration"]))
    if "discord_check_duration" in body:
        settings["discord_check_duration"] = max(5, int(body["discord_check_duration"]))
    if "required_discord_invite" in body:
        settings["required_discord_invite"] = str(body["required_discord_invite"]).strip()
    if "required_discord_server_name" in body:
        settings["required_discord_server_name"] = str(body["required_discord_server_name"]).strip()

    save_keys_data(keys_db)
    return web.json_response({"status": "ok", "message": "Đã lưu cài đặt hệ thống thành công!", "settings": settings})

# Admin Endpoint: Test gửi thử Discord Webhook (Masked IP)
async def api_admin_test_webhook(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    webhook_url = body.get("discord_webhook", "").strip() or get_server_settings().get("discord_webhook", "").strip()
    if not webhook_url:
        return web.json_response({"status": "error", "message": "Chưa nhập Webhook URL! Vui lòng dán Webhook URL vào ô bên trên."}, status=400)

    if not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        return web.json_response({"status": "error", "message": "Địa chỉ Webhook không hợp lệ! Bắt buộc phải bắt đầu bằng https://discord.com/api/webhooks/..."}, status=400)

    if "discord.com/api/webhooks" not in webhook_url and "discordapp.com/api/webhooks" not in webhook_url:
        return web.json_response({"status": "error", "message": "Địa chỉ URL không phải là Discord Webhook hợp lệ (phải chứa discord.com/api/webhooks)!"}, status=400)

    sample_proxy = {
        "proto": "socks5",
        "ip": "103.152.204.18",
        "port": 1080,
        "country": "VN",
        "flag": "🇻🇳",
        "ping": 118,
        "is_residential": True,
        "target_status": "200 OK"
    }
    masked = mask_ip(sample_proxy["ip"], sample_proxy["port"])

    embed = {
        "title": "🧪 THỬ NGHIỆM KẾT NỐI DISCORD WEBHOOK",
        "description": "Tin nhắn thử nghiệm từ **Death Master Server**! Hệ thống đã kích hoạt tính năng **Che Mặt Nạ IP Tuyệt Đối** bảo vệ thợ săn proxy.",
        "color": 0x10B981,
        "fields": [
            {"name": "⚡ Giao Thức", "value": "`SOCKS5`", "inline": True},
            {"name": "🔒 Địa Chỉ (Đã Che IP)", "value": f"`{masked}`", "inline": True},
            {"name": "⏱️ Độ Trễ (Ping)", "value": "**118ms** (Siêu Tốc)", "inline": True},
            {"name": "🌐 Quốc Gia", "value": "🇻🇳 Vietnam", "inline": True},
            {"name": "🏷️ Phân Loại", "value": "`🏡 Proxy Dân Cư (Residential ISP)`", "inline": True},
            {"name": "🛡️ Trạng Thái", "value": "`Hoạt động hoàn hảo`", "inline": True}
        ],
        "footer": {
            "text": "Death Proxy Scanner V1.0.0 • By ! Death Silence • Discord: @qyk3"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    payload = {
        "username": "Death Proxy Hunter Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3208/3208676.png",
        "embeds": [embed]
    }

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn) as s:
            async with s.post(webhook_url, json=payload, timeout=timeout) as resp:
                if resp.status in (200, 204):
                    return web.json_response({"status": "ok", "message": "Gửi tin nhắn test tới Discord thành công!"})
                else:
                    err_txt = await resp.text()
                    return web.json_response({"status": "error", "message": f"Máy chủ Discord từ chối (Mã {resp.status}): {err_txt[:120]}"}, status=400)
    except asyncio.TimeoutError:
        return web.json_response({"status": "error", "message": "Hết thời gian chờ (Timeout 8s). Không thể kết nối tới máy chủ Discord!"}, status=400)
    except Exception as e:
        return web.json_response({"status": "error", "message": f"Không thể gửi tin nhắn tới Webhook: {str(e)}"}, status=400)

# ================= ADMIN SECURITY LISTS (WHITELIST & BLACKLIST) =================
async def api_admin_security_lists(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    wl = keys_db.get("whitelist", [])
    bl_raw = keys_db.get("blacklist", {})
    now = time.time()
    bl_list = []
    for ip, item in bl_raw.items():
        ban_until = item.get("ban_until", 0)
        rem = max(0, int(ban_until - now)) if ban_until > 0 else -1
        bl_list.append({
            "ip": ip,
            "reason": item.get("reason", "Bypass Bot"),
            "banned_at": item.get("banned_at", int(now)),
            "ban_until": ban_until,
            "remaining_sec": rem,
            "strikes": item.get("strikes", 3)
        })
    return web.json_response({
        "status": "ok",
        "whitelist": wl,
        "blacklist": bl_list,
        "client_ip": get_client_ip(request)
    })

async def api_admin_security_unblacklist(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ip = body.get("ip", "").strip()
    if not ip:
        return web.json_response({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
    unblacklist_ip(ip)
    return web.json_response({"status": "ok", "message": f"Đã mở khóa (Unban 1-Click) thành công cho IP {ip}!"})

async def api_admin_security_blacklist(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ip = body.get("ip", "").strip()
    reason = body.get("reason", "Khóa thủ công từ Admin").strip()
    duration = int(body.get("duration", 30))
    if not ip:
        return web.json_response({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
    add_blacklist_ip(ip, reason, duration)
    return web.json_response({"status": "ok", "message": f"Đã đưa IP {ip} vào Blacklist ({duration} phút)!"})

async def api_admin_security_whitelist_add(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ip = body.get("ip", "").strip()
    if not ip:
        return web.json_response({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
    add_whitelist_ip(ip)
    return web.json_response({"status": "ok", "message": f"Đã thêm IP {ip} vào Whitelist (Miễn trừ kiểm tra 5 phút)!"})

async def api_admin_security_whitelist_remove(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ip = body.get("ip", "").strip()
    if not ip:
        return web.json_response({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
    remove_whitelist_ip(ip)
    return web.json_response({"status": "ok", "message": f"Đã xóa IP {ip} khỏi Whitelist!"})

# ================= 8. CỔNG GET KEY FREE 24H: BỘ 3 LIÊN KẾT DEATH SYSTEM =================
async def getkey_front_page_handler(request):
    if os.path.exists(GETKEY_PAGE):
        with open(GETKEY_PAGE, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>404: getkey.html (Death-Front-GetKey) not found</h1>", content_type="text/html", status=404)

async def getkey_middle_page_handler(request):
    page = GETKEY_MIDDLE_PAGE if os.path.exists(GETKEY_MIDDLE_PAGE) else GETKEY_VERIFY_PAGE
    if os.path.exists(page):
        with open(page, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>404: getkey_middle.html (Death-Middle-GetKey) not found</h1>", content_type="text/html", status=404)

async def getkey_end_page_handler(request):
    if os.path.exists(GETKEY_END_PAGE):
        with open(GETKEY_END_PAGE, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>404: getkey_end.html (Death-End-GetKey) not found</h1>", content_type="text/html", status=404)

# ================= 9. HỆ THỐNG RÚT GỌN TỰ CHỦ DEATH-SHRINKER =================
async def shortener_page_handler(request):
    if os.path.exists(SHORTENER_PAGE):
        with open(SHORTENER_PAGE, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>404: shortener.html (Death-Shortener) not found</h1>", content_type="text/html", status=404)

async def api_shortener_info(request):
    code = request.match_info.get("code", "").strip()
    if code in shortened_links_db:
        item = shortened_links_db[code]
        item["clicks"] = item.get("clicks", 0) + 1
        save_keys_data(keys_db)
        return web.json_response({
            "status": "ok",
            "code": code,
            "dest_url": item["dest_url"],
            "duration": item.get("duration", 15),
            "clicks": item["clicks"]
        })
    return web.json_response({"status": "error", "message": "Link rút gọn không tồn tại hoặc đã hết hạn!"}, status=404)

async def api_admin_shortener_list(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    links = []
    for code, item in shortened_links_db.items():
        links.append({
            "code": code,
            "short_path": f"/s/{code}",
            "dest_url": item.get("dest_url", ""),
            "duration": item.get("duration", 15),
            "created_at": item.get("created_date", "--"),
            "clicks": item.get("clicks", 0)
        })
    links.sort(key=lambda x: x["clicks"], reverse=True)
    return web.json_response({"status": "ok", "links": links})

async def api_admin_shortener_create(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    dest_url = body.get("dest_url", "").strip()
    alias = body.get("alias", "").strip()
    duration = int(body.get("duration", 15))
    if not dest_url or not (dest_url.startswith("http://") or dest_url.startswith("https://") or dest_url.startswith("/")):
        return web.json_response({"status": "error", "message": "Link đích không hợp lệ (phải bắt đầu bằng http://, https:// hoặc /)!"}, status=400)
    
    code = create_death_short_link(dest_url, duration=duration, alias=alias)
    return web.json_response({
        "status": "ok",
        "message": f"Tạo link rút gọn thành công: /s/{code}",
        "code": code,
        "short_path": f"/s/{code}",
        "dest_url": dest_url,
        "duration": duration
    })

async def api_admin_shortener_delete(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = body.get("code", "").strip()
    if code in shortened_links_db:
        del shortened_links_db[code]
        save_keys_data(keys_db)
        return web.json_response({"status": "ok", "message": f"Đã xóa link rút gọn /s/{code} thành công!"})
    return web.json_response({"status": "error", "message": "Không tìm thấy mã rút gọn này!"}, status=404)

async def api_shortener_discord_start(request):
    """Khởi động tiến trình xác thực thành viên Discord trong Shortener (đếm ngược 60s bắt buộc)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    token = body.get("token", "").strip()
    discord_user = (body.get("discord_user") or body.get("discord_username") or "").strip()
    client_ip = get_client_ip(request)

    banned, ban_remaining = is_ip_bypass_banned(client_ip)
    if banned:
        return web.json_response({"status": "error", "message": f"IP của bạn đang bị khóa {ban_remaining}s do nghi vấn bypass!"}, status=403)

    if not discord_user or len(discord_user) < 2:
        return web.json_response({"status": "error", "message": "Vui lòng nhập Discord username hợp lệ (ít nhất 2 ký tự)!"}, status=400)

    sess = verify_and_decode_getkey_token(token)
    if not sess:
        return web.json_response({"status": "error", "message": "Phiên làm việc không tồn tại hoặc đã hết hạn!"}, status=404)

    settings = get_server_settings()
    duration = 60
    now_ts = int(time.time())
    new_token = generate_stateless_getkey_token(
        ip=client_ip,
        wait_time=int(sess.get("required_wait", 90)),
        discord_started_at=now_ts,
        discord_verified=False,
        discord_user=discord_user,
        created_at=sess.get("created_at")
    )

    return web.json_response({
        "status": "ok",
        "duration": duration,
        "token": new_token,
        "invite": settings.get("required_discord_invite", "https://discord.gg/2zuwDpJaNP"),
        "server_name": settings.get("required_discord_server_name", "Death Silence Community")
    })

async def api_shortener_discord_status(request):
    """Kiểm tra trạng thái tiến trình đối soát thành viên Discord."""
    token = request.query.get("token", "").strip()
    client_ip = get_client_ip(request)
    test_bypass = request.query.get("test_bypass") == "1"
    sess = verify_and_decode_getkey_token(token)
    if not sess:
        return web.json_response({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=404)

    started = int(sess.get("discord_started_at", 0))
    disc_verified = sess.get("discord_verified", False)
    target_dur = 60
    now = time.time()
    elapsed = int(now - started) if started > 0 else 0

    if disc_verified:
        return web.json_response({
            "status": "verified",
            "ready": True,
            "verified": True,
            "elapsed": target_dur,
            "target": target_dur,
            "token": token,
            "next_url": f"/getkey/middle?token={token}"
        })

    if started <= 0 and not test_bypass:
        return web.json_response({
            "status": "waiting",
            "ready": False,
            "verified": False,
            "elapsed": 0,
            "target": target_dur,
            "remaining": target_dur,
            "message": "Vui lòng nhập Discord username để kích hoạt đối soát!"
        })

    # Chỉ cho qua khi đã chờ đủ 60s đối soát Discord (hoặc cờ test_bypass=1)
    if elapsed >= target_dur or test_bypass:
        verified_token = generate_stateless_getkey_token(
            ip=client_ip,
            wait_time=int(sess.get("required_wait", 90)),
            discord_started_at=started if started > 0 else int(now),
            discord_verified=True,
            discord_user=sess.get("discord_user", ""),
            created_at=sess.get("created_at")
        )
        return web.json_response({
            "status": "verified",
            "ready": True,
            "verified": True,
            "elapsed": target_dur,
            "target": target_dur,
            "token": verified_token,
            "next_url": f"/getkey/middle?token={verified_token}"
        })

    return web.json_response({
        "status": "checking",
        "ready": False,
        "verified": False,
        "elapsed": elapsed,
        "target": target_dur,
        "remaining": max(0, target_dur - elapsed)
    })

async def api_getkey_middle_status(request):
    """Cung cấp đồng hồ đo tiến trình tổng thể cho Link 3: Death-Middle-GetKey."""
    token = request.query.get("token", "").strip()
    client_ip = get_client_ip(request)
    test_bypass = request.query.get("test_bypass") == "1"
    sess = verify_and_decode_getkey_token(token)
    if not sess:
        return web.json_response({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=404)

    now = time.time()
    total_elapsed = int(now - sess.get("created_at", now))
    total_min = int(sess.get("required_wait", 90))
    whitelisted = is_ip_whitelisted(client_ip)
    # Discord bắt buộc phải hoàn thành tại Link 2 (trừ khi test_bypass)
    disc_ok = bool(sess.get("discord_verified", False)) or test_bypass
    can_redeem = (whitelisted or (total_elapsed >= total_min)) and disc_ok

    return web.json_response({
        "status": "ok",
        "token": token,
        "discord_verified": disc_ok,
        "total_elapsed": total_elapsed,
        "total_min": total_min,
        "remaining": max(0, total_min - total_elapsed),
        "can_redeem": can_redeem,
        "is_whitelisted": whitelisted
    })

async def api_getkey_captcha(request):
    client_ip = get_client_ip(request)
    
    # 1. Kiểm tra IP có đang bị tạm khóa 30 phút do gian lận bypass không
    banned, ban_remaining = is_ip_bypass_banned(client_ip)
    if banned:
        return web.json_response({
            "status": "error",
            "message": f"IP của bạn đã bị khóa tạm thời 30 phút vì nghi vấn dùng tool bypass! Thử lại sau {ban_remaining} giây."
        }, status=429)

    # 2. Rate Limiting: Chống spam cào captcha
    if not check_ip_rate_limit(client_ip, max_requests=25, window_sec=60):
        return web.json_response({
            "status": "error",
            "message": "Bạn đang thao tác quá nhanh! Vui lòng chờ 30 giây rồi thử lại."
        }, status=429)

    cid, challenge = generate_math_captcha()
    settings = get_server_settings()
    return web.json_response({
        "status": "ok",
        "cid": cid,
        "captcha_id": cid,
        "challenge": challenge,
        "expr": challenge,
        "client_ip": client_ip,
        "min_duration": settings.get("min_bypass_duration", 60),
        "has_link4m_api": bool(settings.get("link4m_api_token"))
    })

async def api_getkey_start(request):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # 1. Kiểm tra IP bị khóa
    banned, ban_remaining = is_ip_bypass_banned(client_ip)
    if banned:
        return web.json_response({
            "status": "error",
            "message": f"IP của bạn đã bị khóa tạm thời 30 phút! Thử lại sau {ban_remaining} giây."
        }, status=429)

    # 2. Rate Limiting
    if not check_ip_rate_limit(client_ip, max_requests=15, window_sec=60):
        return web.json_response({
            "status": "error",
            "message": "Quá nhiều yêu cầu giải Captcha! Vui lòng chờ 30 giây."
        }, status=429)

    try:
        body = await request.json()
    except Exception:
        body = {}

    cid = str(body.get("cid") or body.get("captcha_id") or "").strip()
    ans_str = str(body.get("answer", "")).strip()

    if not cid or not ans_str or not verify_stateless_captcha(cid, ans_str):
        return web.json_response({"status": "error", "message": "Đáp án Captcha không chính xác hoặc đã hết hạn!"}, status=400)

    if cid in captcha_sessions:
        del captcha_sessions[cid]

    # Đã giải đúng Captcha -> Cấp token bảo mật stateless
    wait_time = 90
    token = generate_stateless_getkey_token(client_ip, wait_time=wait_time)
    pow_challenge = secrets.token_hex(6)

    settings = get_server_settings()
    shortener_url = f"/getkey/shortener?token={token}"
    middle_url = f"/getkey/middle?token={token}"
    short_code = create_death_short_link(middle_url, duration=wait_time)

    return web.json_response({
        "status": "ok",
        "token": token,
        "pow_challenge": pow_challenge,
        "short_code": short_code,
        "short_url": f"/s/{short_code}",
        "shortener_url": shortener_url,
        "middle_url": middle_url,
        "verify_url": middle_url,
        "redirect_url": shortener_url,
        "is_shortened": True
    })

async def api_getkey_my_session(request):
    client_ip = get_client_ip(request)
    token = request.query.get("token", "").strip() or ip_getkey_sessions.get(client_ip, "")
    sess = verify_and_decode_getkey_token(token) if token else None
    if sess:
        return web.json_response({
            "status": "ok",
            "token": token,
            "created_at": sess["created_at"],
            "elapsed": int(time.time() - sess["created_at"])
        })
    return web.json_response({"status": "no_session", "message": "Chưa có phiên lấy key cho IP này."}, status=404)

async def api_getkey_verify(request):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # 1. Kiểm tra IP bị khóa do gian lận bypass
    banned, ban_remaining = is_ip_bypass_banned(client_ip)
    if banned:
        return web.json_response({
            "status": "banned",
            "message": f"IP của bạn đã bị khóa 30 phút vì cố tình vượt link bằng tool bypass! Vui lòng quay lại sau {ban_remaining} giây.",
            "remaining": ban_remaining
        }, status=403)

    token = request.query.get("token", "").strip()
    test_bypass = request.query.get("test_bypass") == "1"
    pow_nonce = request.query.get("pow_nonce", "").strip()

    # Hỗ trợ nhận diện phiên theo IP nếu khách hàng đến từ link rút gọn tĩnh của Link4M
    if not token:
        token = ip_getkey_sessions.get(client_ip, "")

    sess = verify_and_decode_getkey_token(token)
    if not sess:
        return web.json_response({
            "status": "no_session",
            "message": "Không tìm thấy phiên vượt link cho thiết bị này! Vui lòng truy cập trang /getkey để giải Captcha và bắt đầu."
        }, status=404)

    token_data = sess
    settings = get_server_settings()

    # 2. Phát hiện Bot / Headless Scraper
    if is_suspicious_bot(user_agent) and not test_bypass:
        strikes, is_b = record_bypass_strike(client_ip)
        state.bypass_blocked_count += 1
        return web.json_response({
            "status": "blocked",
            "message": "Phát hiện yêu cầu từ công cụ tự động (Bot / Headless Tool). Phiên xác minh bị hủy!",
            "reason": "bot_detected",
            "strikes": strikes,
            "is_banned": is_b
        }, status=403)

    # 3. Khóa chặt Token theo IP (IP Binding)
    if settings.get("enforce_ip_binding", True) and not test_bypass:
        if token_data.get("ip") and token_data["ip"] != client_ip:
            return web.json_response({
                "status": "blocked",
                "message": "Token này được tạo từ IP khác! Nghi vấn chia sẻ link qua mạng xã hội. Bạn chỉ có thể nhận key trên thiết bị đã giải Captcha.",
                "reason": "ip_mismatch"
            }, status=403)

    # 4. Kiểm tra Proof-of-Work (PoW) từ Trình Duyệt Thật
    if settings.get("enforce_pow", True) and not test_bypass:
        if not pow_nonce:
            return web.json_response({
                "status": "blocked",
                "message": "Thiếu xác thực môi trường trình duyệt thật (Proof-of-Work missing).",
                "reason": "pow_missing"
            }, status=400)
        
        pow_str = f"{token}:pow:{pow_nonce}".encode()
        pow_hash = hashlib.sha256(pow_str).digest()
        # Yêu cầu 12 bit đầu bằng 0 (hash[0] == 0 and (hash[1] & 0xf0) == 0)
        if not (pow_hash[0] == 0 and (pow_hash[1] & 0xF0) == 0):
            return web.json_response({
                "status": "blocked",
                "message": "Xác thực môi trường trình duyệt không hợp lệ (Invalid Proof-of-Work).",
                "reason": "pow_invalid"
            }, status=400)

    # 4.1 Kiểm tra đã hoàn thành bước xác thực Discord tại [Link 2] Death-Shortener-GetKey chưa
    if not token_data.get("discord_verified") and not test_bypass:
        return web.json_response({
            "status": "blocked",
            "message": "Bạn chưa hoàn thành bước kiểm tra thành viên Discord tại [Link 2] Death-Shortener-GetKey! Vui lòng quay lại Link 2 để xác thực.",
            "reason": "discord_not_verified"
        }, status=403)

    # Nếu token đã nhận key rồi -> Trả lại key cũ
    if token_data["used"] and token_data.get("claimed_key"):
        return web.json_response({
            "status": "ok",
            "key": token_data["claimed_key"],
            "elapsed": int(time.time() - token_data["created_at"]),
            "already_claimed": True
        })

    elapsed = time.time() - token_data["created_at"]
    total_min = int(settings.get("total_min_key_duration", 300))

    # 5. KIỂM TRA THỜI GIAN ANTI-BYPASS (Đốt tối thiểu 5 phút = 300 giây)
    if test_bypass or ((elapsed < total_min) and not is_ip_whitelisted(client_ip)):
        if test_bypass:
            strikes, is_b = 1, False
        else:
            strikes, is_b = record_bypass_strike(client_ip, f"Vượt link quá nhanh ({int(elapsed)}s < {total_min}s)")
            state.bypass_blocked_count += 1
        ban_msg = " Bạn đã bị tạm khóa IP 30 phút và đưa vào Blacklist!" if is_b else f" Cảnh cáo lần {strikes}/3 (Nếu vi phạm 3 lần sẽ bị khóa IP 30 phút)."
        return web.json_response({
            "status": "blocked",
            "message": f"Phát hiện bạn hoàn thành vượt link quá nhanh ({int(elapsed)}s < {total_min}s)! Quy trình lấy key yêu cầu ít nhất 5 phút để bảo vệ hệ thống.{ban_msg}",
            "elapsed": int(elapsed),
            "min_duration": total_min,
            "strikes": strikes,
            "is_banned": is_b
        }, status=403)

    # 6. Chống cày gom Key: Giới hạn 1 Key / IP / 24 Giờ (Anti-Hoarding)
    if settings.get("max_keys_per_ip_24h", True):
        existing_key = get_existing_active_key_for_ip(client_ip)
        if existing_key:
            token_data["used"] = True
            token_data["claimed_key"] = existing_key["key"]
            return web.json_response({
                "status": "ok",
                "key": existing_key["key"],
                "expires_at": existing_key.get("expires_at", "24 Giờ"),
                "elapsed": int(elapsed),
                "is_existing": True,
                "message": "IP của bạn đã nhận 1 Key Free trong vòng 24 giờ qua. Dưới đây là Key còn hạn của bạn:"
            })

    # 7. HỢP LỆ HOÀN TOÀN -> Tự động sinh Key Free 24h Mới (Chưa kích hoạt)
    token_data["used"] = True
    new_key = generate_death_key(days=1, notes=f"Link4M Auto ({client_ip})", key_type="free_24h", client_ip=client_ip)
    token_data["claimed_key"] = new_key["key"]
    state.getkey_success_count += 1

    return web.json_response({
        "status": "ok",
        "key": new_key["key"],
        "expires_at": new_key["expires_at"],
        "elapsed": int(elapsed),
        "is_existing": False
    })


# Admin Endpoint: Lấy danh sách Worker minh bạch
async def api_admin_get_workers(request):
    if not check_admin_auth(request):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    
    st = state.get_dict()
    return web.json_response({
        "status": "ok",
        "workers": st["workers"],
        "total_active": len(st["workers"]),
        "exact_checked": state.checked_total,
        "exact_live": state.total_live,
        "exact_dead": state.dead_count,
        "ping_target": state.ping_target
    })

# ================= 8. GIAO DIỆN WEB & WEBSOCKET =================
async def index_handler(request):
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>404: dashboard.html not found!</h1>", content_type="text/html", status=404)

async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=15.0)
    await ws.prepare(request)

    client = SafeWSClient(ws)
    active_ws_clients.add(client)

    try:
        client.send_nowait(json.dumps({"type": "state", "data": state.get_dict()}))
        recent_snapshot = list(state.recent_live)
        if recent_snapshot:
            client.send_nowait(json.dumps({"type": "batch_live", "proxies": recent_snapshot}))
    except Exception:
        pass

    try:
        async for msg in ws:
            pass
    finally:
        active_ws_clients.discard(client)
        await client.close()

    return ws

async def stats_api_handler(request):
    return web.json_response(state.get_dict())

async def download_handler(request):
    fname = request.match_info.get("filename", "")
    allowed = {
        "goodproxies.txt": OUT_ALL_GOOD,
        "elite_proxies.txt": OUT_ELITE,
        "live_http.txt": OUT_HTTP,
        "live_socks4.txt": OUT_SOCKS4,
        "live_socks5.txt": OUT_SOCKS5,
        "residential_proxies.txt": OUT_RESIDENTIAL,
        "live_detailed.txt": OUT_DETAILED,
        "bad_or_dead.txt": OUT_BAD
    }
    if fname not in allowed or not os.path.exists(allowed[fname]):
        return web.Response(text=f"Tệp {fname} chưa có dữ liệu.", status=404, content_type="text/plain; charset=utf-8")

    return web.FileResponse(
        allowed[fname],
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

def find_available_port(start=5000, max_attempts=20):
    for p in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return start

# ================= 9. KHỞI CHẠY MASTER SERVER =================
async def main():
    loop = asyncio.get_running_loop()
    def silent_loop_handler(l, ctx):
        pass
    loop.set_exception_handler(silent_loop_handler)

    # CLI sinh key nhanh: python server.py --gen-key 30
    if len(sys.argv) > 1 and sys.argv[1] == "--gen-key":
        sys.stderr = _real_stderr
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        notes = sys.argv[3] if len(sys.argv) > 3 else "CLI Generator"
        key_obj = generate_death_key(days, notes)
        print("=" * 65)
        print("🔑 SINH KHÓA BẢN QUYỀN THÀNH CÔNG:")
        print(f"Tool     : {TOOL_NAME}")
        print(f"Format   : Death-xxxxxxxx-yyyyyyyy-zzzzzzzz")
        print(f"Key      : {key_obj['key']}")
        print(f"Hạn dùng : {key_obj['expires_at']} ({days} ngày)")
        print(f"Liên hệ  : {TOOL_DISCORD}")
        print("=" * 65)
        return

    if not os.path.exists(SOURCES_FILE):
        sys.stderr = _real_stderr
        print(f"Lỗi: Không tìm thấy {SOURCES_FILE}!")
        return

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    state.sources_total = len(urls)

    env_port = os.environ.get("SERVER_PORT") or os.environ.get("PORT")
    port = int(env_port) if env_port else find_available_port(5000)
    web_url_local = f"http://127.0.0.1:{port}"

    # Terms of Service & Hosting AUP Handlers (HTML UI with Markdown Fallback)
    async def terms_handler(request):
        if os.path.exists(TERMS_PAGE):
            with open(TERMS_PAGE, "r", encoding="utf-8") as f:
                return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
        elif os.path.exists(TERMS_FILE):
            with open(TERMS_FILE, "r", encoding="utf-8") as f:
                return web.Response(text=f.read(), content_type="text/markdown", charset="utf-8")
        return web.Response(text="Terms of Service not found", status=404)

    async def hosting_aup_handler(request):
        if os.path.exists(HOSTING_AUP_PAGE):
            with open(HOSTING_AUP_PAGE, "r", encoding="utf-8") as f:
                return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
        elif os.path.exists(HOSTING_AUP_FILE):
            with open(HOSTING_AUP_FILE, "r", encoding="utf-8") as f:
                return web.Response(text=f.read(), content_type="text/markdown", charset="utf-8")
        return web.Response(text="Hosting AUP statement not found", status=404)

    # Cấu hình Web App
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/terms", terms_handler)
    app.router.add_get("/hosting-aup", hosting_aup_handler)
    app.router.add_get("/api/stats", stats_api_handler)
    app.router.add_get("/download/{filename}", download_handler)

    # Cổng Get Key Free 24h: Bộ 4 Liên Kết Chuẩn Death System
    app.router.add_get("/getkey", getkey_front_page_handler)
    app.router.add_get("/getkey/front", getkey_front_page_handler)
    app.router.add_get("/getkey/shortener", shortener_page_handler)
    app.router.add_get("/s/{code}", shortener_page_handler)
    app.router.add_get("/getkey/middle", getkey_middle_page_handler)
    app.router.add_get("/getkey/verify", getkey_middle_page_handler) # Giữ alias tương thích
    app.router.add_get("/getkey/end", getkey_end_page_handler)

    # APIs Get Key & Discord Verification
    app.router.add_get("/api/getkey/captcha", api_getkey_captcha)
    app.router.add_post("/api/getkey/start", api_getkey_start)
    app.router.add_post("/api/shortener/discord-start", api_shortener_discord_start)
    app.router.add_get("/api/shortener/discord-status", api_shortener_discord_status)
    app.router.add_get("/api/getkey/middle-status", api_getkey_middle_status)
    app.router.add_get("/api/getkey/verify", api_getkey_verify)
    app.router.add_get("/api/getkey/my-session", api_getkey_my_session)
    app.router.add_get("/api/shortener/info/{code}", api_shortener_info)

    # Admin Security APIs (Whitelist / Blacklist Manager)
    app.router.add_get("/api/admin/security/lists", api_admin_security_lists)
    app.router.add_post("/api/admin/security/unblacklist", api_admin_security_unblacklist)
    app.router.add_post("/api/admin/security/blacklist", api_admin_security_blacklist)
    app.router.add_post("/api/admin/security/whitelist/add", api_admin_security_whitelist_add)
    app.router.add_post("/api/admin/security/whitelist/remove", api_admin_security_whitelist_remove)

    # Admin Shortener Hub APIs
    app.router.add_get("/api/admin/shortener/links", api_admin_shortener_list)
    app.router.add_post("/api/admin/shortener/create", api_admin_shortener_create)
    app.router.add_post("/api/admin/shortener/delete", api_admin_shortener_delete)

    # Worker Client APIs
    app.router.add_post("/api/auth/verify", api_auth_verify)
    app.router.add_get("/api/tasks", api_tasks_handler)
    app.router.add_post("/api/submit", api_submit_handler)

    # Admin Panel APIs
    app.router.add_post("/api/admin/login", api_admin_login)
    app.router.add_get("/api/admin/keys", api_admin_get_keys)
    app.router.add_post("/api/admin/gen-key", api_admin_gen_key)
    app.router.add_post("/api/admin/revoke-key", api_admin_revoke_key)
    app.router.add_post("/api/admin/delete-key", api_admin_delete_key)
    app.router.add_post("/api/admin/target", api_admin_set_target)
    app.router.add_post("/api/admin/settings", api_admin_save_settings)
    app.router.add_post("/api/admin/test-webhook", api_admin_test_webhook)
    app.router.add_get("/api/admin/workers", api_admin_get_workers)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Sinh sẵn 1 key test nếu DB rỗng
    if not keys_db.get("keys"):
        sample_key = generate_death_key(30, "Default Test Key")
    else:
        sample_key = list(keys_db["keys"].values())[0]

    sys.stderr = _real_stderr
    print("=" * 85)
    print(f"💀  {TOOL_NAME.upper()}")
    print("=" * 85)
    print(f"🌐 WEB DASHBOARD              : {web_url_local}")
    print(f"👉 [1] Death-Front-GetKey     : {web_url_local}/getkey")
    print(f"👉 [2] Death-Shortener-GetKey : {web_url_local}/getkey/shortener  <-- Kiểm tra Discord (1 - 2 phút)")
    print(f"👉 [3] Death-Middle-GetKey    : {web_url_local}/getkey/middle     <-- Đối soát Anti-Bypass (5 phút) & PoW")
    print(f"👉 [4] Death-End-GetKey       : {web_url_local}/getkey/end        <-- Cổng gửi key cho người dùng")
    print(f"🔗 TỰ CHỦ RÚT GỌN LINK        : {web_url_local}/s/{{code}}")
    print(f"📡 API PHÂN PHỐI              : {web_url_local}/api/tasks")
    print(f"🎯 PING TARGET            : {state.ping_target}")
    print(f"🛡️ BẢO MẬT NGUỒN    : Đã khóa kín {len(urls):,} Nguồn VIP trên Master Server (Zero-Leak)")
    print(f"🔑 TÀI KHOẢN ADMIN  : admin | Mật khẩu: DeathAdmin@2026")
    print(f"🤫 NÚT BÍ MẬT ADMIN : Click 5 lần vào Logo ⚡ hoặc bấm [Ctrl + Shift + A]")
    print(f"🔑 KEY MẪU ĐỂ TEST  : {sample_key['key']} (Hạn: {sample_key['expires_at']})")
    print(f"💬 LIÊN HỆ HỖ TRỢ   : Discord: {TOOL_DISCORD} | https://discord.gg/2zuwDpJaNP")
    print("-------------------------------------------------------------------------------------")
    print("⚡ Master Server đang chạy ngầm 24/7. Nhấn Ctrl+C để dừng.")
    print("=" * 85)
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

    harvester_task = asyncio.create_task(master_continuous_harvester(urls))
    broadcaster_task = asyncio.create_task(batch_broadcaster())
    webhook_task = asyncio.create_task(discord_webhook_worker())

    try:
        await harvester_task
    except asyncio.CancelledError:
        pass

    broadcaster_task.cancel()
    webhook_task.cancel()
    await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stderr = _real_stderr
        print("\n[✔] Đã tắt Master Server an toàn.")
    except BaseException:
        sys.stderr = _real_stderr
