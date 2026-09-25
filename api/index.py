import os
import sys
import json
import re
import time
import base64
import random
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

# Thêm thư mục server vào sys.path để import toàn bộ module server.py
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if "server" in sys.modules and hasattr(sys.modules["server"], "task_buffer"):
    server = sys.modules["server"]
else:
    import importlib.util
    server_file = os.path.join(SERVER_DIR, "server.py")
    if not os.path.exists(server_file):
        server_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

    try:
        if os.path.exists(server_file):
            spec = importlib.util.spec_from_file_location("server", server_file)
            server = importlib.util.module_from_spec(spec)
            sys.modules["server"] = server
            spec.loader.exec_module(server)
        else:
            import server
    except Exception:
        import server

def normalize_req_path(raw):
    """Chuẩn hóa đường dẫn sạch sẽ, loại bỏ double-slashes và netloc anomalies."""
    if not raw:
        return "/"
    cleaned = re.sub(r'/+', '/', str(raw).strip())
    if not cleaned.startswith('/'):
        cleaned = '/' + cleaned
    
    parsed = urllib.parse.urlparse(cleaned)
    p = parsed.path
    if parsed.netloc:
        p = '/' + parsed.netloc + p
    p = re.sub(r'/+', '/', p).rstrip('/')
    return p if p else '/'

def find_static_file(filename_or_path):
    """Tìm kiếm file an toàn trong mọi môi trường (Vercel Serverless Lambda, Docker, VPS, Local)."""
    if not filename_or_path:
        return None
    if os.path.isfile(filename_or_path):
        return filename_or_path
    
    basename = os.path.basename(filename_or_path)
    candidates = [
        filename_or_path,
        os.path.join(SERVER_DIR, basename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", basename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), basename),
        os.path.join(os.getcwd(), basename),
        os.path.join("/var/task", basename),
        os.path.join("/tmp", basename),
        basename
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None

def get_req_client_ip(headers, client_address=None):
    """Bóc tách IP thực tế của máy khách khi chạy sau Vercel / Cloudflare Reverse Proxy."""
    check_headers = [
        "x-vercel-forwarded-for", "X-Vercel-Forwarded-For",
        "x-real-ip", "X-Real-IP",
        "cf-connecting-ip", "CF-Connecting-IP",
        "x-forwarded-for", "X-Forwarded-For"
    ]
    for h in check_headers:
        val = headers.get(h)
        if val:
            ip = val.split(",")[0].strip()
            if ip and ip.lower() != "unknown":
                return ip
    if client_address and len(client_address) > 0:
        return client_address[0]
    return "127.0.0.1"

MASTER_SECRET_SALT = (
    os.environ.get("MASTER_SECRET_SALT")
    or getattr(server, "keys_db", {}).get("secret_salt")
    or "DeathSuperSecretHMACSalt998877"
)

def _resolve_test_bypass(raw_flag, client_ip):
    """Ủy quyền cho server.resolve_test_bypass; nếu server.py cũ thiếu hàm này thì luôn từ chối."""
    resolver = getattr(server, "resolve_test_bypass", None)
    if resolver is None:
        return False
    return resolver(raw_flag, client_ip)

def get_admin_secret():
    return MASTER_SECRET_SALT

def generate_stateless_admin_token():
    ts = int(time.time())
    secret = get_admin_secret()
    payload = f"dadmin_session_{ts}".encode("utf-8")
    sig = server.hmac.new(secret.encode("utf-8"), payload, server.hashlib.sha256).hexdigest()
    token = f"dadmin_{ts}_{sig}"
    if hasattr(server, "active_admin_sessions"):
        server.active_admin_sessions.add(token)
    return token

def verify_admin_token(token):
    if not token or not isinstance(token, str):
        return False
    token = token.strip()

    # 1. In-memory Set (cho local dev & cùng session)
    if hasattr(server, "active_admin_sessions") and token in server.active_admin_sessions:
        return True

    # 3. Stateless HMAC-SHA256 Token (hoạt động độc lập trên mọi Lambda/Serverless container)
    if token.startswith("dadmin_"):
        parts = token.split("_")
        if len(parts) == 3:
            _, ts_str, sig = parts
            try:
                ts = int(ts_str)
                # Cho phép token có hiệu lực 7 ngày (7 * 86400s)
                if abs(time.time() - ts) < 7 * 86400:
                    secret = get_admin_secret()
                    payload = f"dadmin_session_{ts}".encode("utf-8")
                    expected_sig = server.hmac.new(secret.encode("utf-8"), payload, server.hashlib.sha256).hexdigest()
                    if server.hmac.compare_digest(sig, expected_sig):
                        return True
            except Exception:
                pass
    return False

def make_stateless_captcha():
    """Sinh phép tính ngẫu nhiên (Cộng hoặc Trừ dễ hiểu, kết quả luôn dương) & chữ ký HMAC chống bot."""
    ts = int(time.time())
    secret = get_admin_secret()
    op = random.choice(["+", "-"])
    if op == "+":
        a = random.randint(12, 49)
        b = random.randint(11, 39)
        ans = a + b
        expr = f"{a} + {b}"
    else:
        a = random.randint(35, 75)
        b = random.randint(10, 24)
        ans = a - b
        expr = f"{a} - {b}"
    
    sig = server.hmac.new(secret.encode("utf-8"), f"dcap_{ans}_{ts}".encode("utf-8"), server.hashlib.sha256).hexdigest()[:16]
    cid = f"dcap_{ts}_{sig}"
    
    if hasattr(server, "captcha_sessions"):
        server.captcha_sessions[cid] = {
            "challenge": expr,
            "answer": ans,
            "created_at": ts
        }
    return cid, expr, ans

def verify_stateless_captcha(cid, user_ans):
    """Xác thực phép tính captcha thông minh (hỗ trợ nhập số, khoảng trắng, dấu bằng, phép tính)."""
    if not cid or user_ans is None:
        return False
    cid = str(cid).strip()
    raw_str = str(user_ans).strip().lstrip("=").lstrip("?").strip()
    if not cid or not raw_str:
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

    # 1. In-memory check (nếu cùng process hoặc local server.py)
    if hasattr(server, "captcha_sessions") and cid in server.captcha_sessions:
        expected = str(server.captcha_sessions[cid].get("answer", "")).strip()
        if expected and any(expected == cand for cand in candidate_answers):
            return True

    # 2. Stateless HMAC check
    if cid.startswith("dcap_"):
        parts = cid.split("_")
        if len(parts) == 3:
            _, ts_str, sig = parts
            try:
                ts = int(ts_str)
                # Cho phép giải trong vòng 15 phút (900s)
                if abs(time.time() - ts) < 900:
                    secret = get_admin_secret()
                    for cand in candidate_answers:
                        expected_sig = server.hmac.new(secret.encode("utf-8"), f"dcap_{cand}_{ts}".encode("utf-8"), server.hashlib.sha256).hexdigest()[:16]
                        if server.hmac.compare_digest(sig, expected_sig):
                            return True
            except Exception:
                pass
    return False

def generate_stateless_getkey_token(ip="127.0.0.1", wait_time=90, discord_started_at=0, discord_verified=False, discord_user="", created_at=None):
    """Sinh phiên GetKey mã hóa stateless kèm chữ ký HMAC (hoạt động đa máy chủ Vercel Serverless)."""
    ts = int(created_at) if (created_at and float(created_at) > 0) else int(time.time())
    secret = get_admin_secret()
    nonce = server.secrets.token_hex(4)
    disc_flag = 1 if discord_verified else 0
    clean_user = discord_user.replace(":", "_")[:24]
    raw = f"{ts}:{int(wait_time)}:{ip}:{int(discord_started_at)}:{disc_flag}:{clean_user}:{nonce}"
    data_b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = server.hmac.new(secret.encode("utf-8"), f"dgk_{data_b64}".encode("utf-8"), server.hashlib.sha256).hexdigest()[:16]
    token = f"dgk_{data_b64}_{sig}"
    
    sess = {
        "created_at": float(ts),
        "ip": ip,
        "required_wait": int(wait_time),
        "discord_started_at": int(discord_started_at),
        "discord_verified": bool(discord_verified),
        "discord_user": clean_user,
        "pow_solved": True,
        "claimed_key": "",
        "used": False
    }
    if hasattr(server, "getkey_tokens"):
        server.getkey_tokens[token] = sess
    if hasattr(server, "ip_getkey_sessions"):
        server.ip_getkey_sessions[ip] = token
    return token

def verify_and_decode_getkey_token(token):
    """Giải mã và xác minh tính toàn vẹn của phiên GetKey stateless."""
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    
    # 1. In-memory check
    if hasattr(server, "getkey_tokens") and token in server.getkey_tokens:
        return server.getkey_tokens[token]
        
    # 2. Stateless HMAC check
    if token.startswith("dgk_"):
        parts = token.split("_")
        if len(parts) == 3:
            _, data_b64, sig = parts
            try:
                secret = get_admin_secret()
                expected_sig = server.hmac.new(secret.encode("utf-8"), f"dgk_{data_b64}".encode("utf-8"), server.hashlib.sha256).hexdigest()[:16]
                if server.hmac.compare_digest(sig, expected_sig):
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
                        # Token có hiệu lực tối đa 3 giờ (10800s)
                        if abs(time.time() - ts) < 10800:
                            sess = {
                                "created_at": ts,
                                "ip": ip,
                                "required_wait": wait_time,
                                "discord_started_at": discord_started_at,
                                "discord_verified": discord_verified,
                                "discord_user": discord_user,
                                "pow_solved": True,
                                "claimed_key": "",
                                "used": False
                            }
                            if hasattr(server, "getkey_tokens"):
                                server.getkey_tokens[token] = sess
                            return sess
            except Exception:
                pass
    return None

FAST_HARVEST_SOURCES = [
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "http"),
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt", "socks4"),
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "socks5"),
    ("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", "socks5"),
    ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt", "http"),
    ("https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt", "http"),
    ("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt", "socks5"),
    ("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all", "http"),
    ("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all", "socks4"),
    ("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all", "socks5"),
]

def serverless_harvest_tasks(needed=400):
    """Cào nhanh proxy trực tiếp cho Vercel Serverless khi kho task rỗng."""
    if len(server.task_buffer) >= needed:
        return

    # 1. Nạp tức thì từ kho SEED_PROXIES đóng gói sẵn trong 0ms (Chống nghẽn / timeout trên Vercel)
    try:
        try:
            from server.seeds import SEED_PROXIES
        except ImportError:
            try:
                from seeds import SEED_PROXIES
            except ImportError:
                SEED_PROXIES = []
        if SEED_PROXIES:
            shuffled = list(SEED_PROXIES)
            random.shuffle(shuffled)
            for item in shuffled:
                server.task_buffer.append(item)
                if len(server.task_buffer) >= max(needed * 2, 1200):
                    break
    except Exception:
        pass

    if len(server.task_buffer) >= needed:
        if hasattr(server.state, "queue_size"):
            server.state.queue_size = len(server.task_buffer)
        return

    # 2. Nếu vẫn thiếu thì cào nhẹ thêm từ các nguồn nhanh
    candidates = list(FAST_HARVEST_SOURCES)
    random.shuffle(candidates)
    added = 0
    if not hasattr(server, "seen_proxies"):
        server.seen_proxies = set()
    
    for url, proto in candidates[:3]:
        if len(server.task_buffer) >= max(needed * 2, 1200):
            break
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.8) as r:
                text = r.read().decode("utf-8", errors="ignore")
                matches = re.findall(r"(\b(?:\d{1,3}\.){3}\d{1,3}\b)[:\s\t]+(\d{2,5})\b", text)
                for ip, port in matches:
                    if 1 <= int(port) <= 65535:
                        key = f"{ip}:{port}"
                        if key not in server.seen_proxies:
                            server.seen_proxies.add(key)
                            server.task_buffer.append((key, proto))
                            added += 1
        except Exception:
            continue
    if hasattr(server.state, "total_scraped"):
        server.state.total_scraped += added
        server.state.queue_size = len(server.task_buffer)
        server.state.sources_done = min(len(candidates), 10)
        server.state.stage = f"Kho nhiệm vụ có {len(server.task_buffer):,} proxy. Đang phân phối cho Worker..."

class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function Handler - Hỗ trợ toàn diện 100% Web Pages & REST APIs."""

    def __init__(self, request=None, client_address=("127.0.0.1", 80), server=None, _is_mock=False):
        if _is_mock or getattr(request, "_is_mock", False) or request is None:
            self.request = request
            self.client_address = client_address
            self.server = server
        else:
            super().__init__(request, client_address, server)

    def log_message(self, format, *args):
        pass

    def send_cors_and_headers(self, status=200, content_type="application/json; charset=utf-8", extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-License-Key, X-Admin-Token, Authorization")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()

    def send_json(self, data, status=200, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_cors_and_headers(status, "application/json; charset=utf-8", extra_headers)
        self.wfile.write(body)

    def send_html_file(self, file_path):
        resolved = find_static_file(file_path)
        if resolved and os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read().encode("utf-8")
            self.send_cors_and_headers(200, "text/html; charset=utf-8")
            self.wfile.write(content)
        else:
            fname = os.path.basename(file_path) if file_path else "file"
            self.send_json({"error": f"Page '{fname}' not found"}, status=404)

    def do_OPTIONS(self):
        self.send_cors_and_headers(204)

    def read_json_body(self):
        content_len = int(self.headers.get("Content-Length", 0) or self.headers.get("content-length", 0) or 0)
        if content_len > 0:
            try:
                raw = self.rfile.read(content_len).decode("utf-8")
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    def get_header(self, name, default=None):
        low_name = name.lower()
        for k, v in self.headers.items():
            if k.lower() == low_name:
                return v
        return default

    def check_admin_auth(self):
        token = self.get_header("X-Admin-Token")
        if not token:
            cookie_hdr = self.get_header("Cookie", "") or ""
            for part in cookie_hdr.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    if k == "admin_token":
                        token = v
                        break
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            orig = query.get("__orig_path", [""])[0]
            if orig:
                orig_parsed = urllib.parse.urlparse(orig)
                orig_query = urllib.parse.parse_qs(orig_parsed.query)
                token = orig_query.get("token", [""])[0]
            if not token:
                token = query.get("token", [""])[0]
        return verify_admin_token(token)

    def parse_url_parts(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = normalize_req_path(parsed.path)

        # 1. Trích xuất đường dẫn gốc từ query parameter __orig_path (do vercel.json rewrite chuyển qua)
        if "__orig_path" in query:
            raw_orig = query["__orig_path"][0]
            if raw_orig:
                parsed_orig = urllib.parse.urlparse(raw_orig)
                path = normalize_req_path(parsed_orig.path)
                if parsed_orig.query:
                    orig_qs = urllib.parse.parse_qs(parsed_orig.query)
                    for k, v in orig_qs.items():
                        query[k] = v

        # 2. Kiểm tra các header của Vercel / Edge Router nếu path đang là file handler
        if path in ("/", "/api/index.py", "/api/index", "/api"):
            for h in [
                "x-matched-path",
                "x-vercel-original-path",
                "x-original-uri",
                "x-forwarded-uri",
                "x-invoke-path",
                "x-real-path"
            ]:
                val = self.get_header(h)
                if val:
                    val_norm = normalize_req_path(val)
                    if val_norm and val_norm not in ("/api/index.py", "/api/index", "/api"):
                        path = val_norm
                        break

        # 3. Loại bỏ prefix /api/index.py hoặc /api/index
        for prefix in ["/api/index.py", "/api/index"]:
            if path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break

        # 4. Khi path là chính file handler hoặc rỗng thì đó là Root "/"
        if path in ("/api/index.py", "/api/index", "/api", ""):
            path = "/"

        return path, query

    def do_GET(self):
        try:
            return self._do_GET_impl()
        except Exception as e:
            return self.send_json({"status": "error", "message": f"Lỗi máy chủ nội bộ: {str(e)}"}, status=500)

    def _do_GET_impl(self):
        path, query = self.parse_url_parts()
        client_ip = get_req_client_ip(self.headers, self.client_address)

        # 1. Web Pages
        if path in ("/", "/index.html"):
            return self.send_html_file(server.DASHBOARD_FILE)

        if path in ("/terms", "/terms.html"):
            p = find_static_file(server.TERMS_PAGE) or find_static_file("terms.html")
            if p:
                return self.send_html_file(p)
            doc = find_static_file(server.TERMS_FILE) or find_static_file("TERMS_OF_SERVICE.md")
            if doc:
                with open(doc, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_cors_and_headers(200, "text/markdown; charset=utf-8")
                return self.wfile.write(content)
            return self.send_json({"error": "Terms page not found"}, status=404)

        if path in ("/hosting-aup", "/hosting_aup.html"):
            p = find_static_file(server.HOSTING_AUP_PAGE) or find_static_file("hosting_aup.html")
            if p:
                return self.send_html_file(p)
            doc = find_static_file(server.HOSTING_AUP_FILE) or find_static_file("HOSTING_AUP.md")
            if doc:
                with open(doc, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_cors_and_headers(200, "text/markdown; charset=utf-8")
                return self.wfile.write(content)
            return self.send_json({"error": "Hosting AUP page not found"}, status=404)

        if path in ("/getkey", "/getkey/front"):
            return self.send_html_file(server.GETKEY_PAGE)

        if path in ("/getkey/shortener",) or path.startswith("/s/"):
            return self.send_html_file(server.SHORTENER_PAGE)

        if path in ("/getkey/middle", "/getkey/verify"):
            return self.send_html_file(server.GETKEY_MIDDLE_PAGE)

        if path in ("/getkey/end",):
            return self.send_html_file(server.GETKEY_END_PAGE)

        # 2. Public REST APIs
        if path in ("/api/stats", "/stats"):
            server.load_server_state()
            if server.state.total_scraped == 0 or len(server.task_buffer) < 200:
                serverless_harvest_tasks(needed=400)
            data = server.state.get_dict()
            return self.send_json(data)

        if path in ("/api/tasks", "/tasks"):
            key = self.get_header("X-License-Key") or query.get("key", [None])[0]
            valid, msg = server.verify_death_key(key, client_ip)
            if not valid:
                return self.send_json({"status": "error", "message": msg}, status=401)
            
            count_str = query.get("count", ["400"])[0]
            try:
                count = min(max(int(count_str), 50), 1200)
            except Exception:
                count = 400

            worker_id = f"{client_ip}:{key[-8:]}" if key else client_ip
            now = time.time()
            if worker_id not in server.state.active_workers:
                server.state.active_workers[worker_id] = {
                    "id": worker_id,
                    "ip": client_ip,
                    "key": key or "--",
                    "connected_at": time.strftime("%H:%M:%S"),
                    "checked": 0,
                    "live": 0,
                    "speed": 0,
                    "last_seen": now
                }
            else:
                server.state.active_workers[worker_id]["last_seen"] = now

            # Tự động nạp kho proxy siêu tốc nếu kho đang cạn (Dành riêng cho Vercel Serverless)
            if len(server.task_buffer) < count:
                serverless_harvest_tasks(needed=count)

            tasks = []
            for _ in range(count):
                if server.task_buffer:
                    tasks.append(server.task_buffer.popleft())
                else:
                    break

            return self.send_json({
                "status": "ok",
                "tasks": tasks,
                "target_url": server.state.ping_target,
                "remaining_pool": len(server.task_buffer)
            })

        if path in ("/api/getkey/captcha", "/getkey/captcha"):
            cid, expr, ans = make_stateless_captcha()
            return self.send_json({
                "status": "ok",
                "cid": cid,
                "captcha_id": cid,
                "challenge": expr,
                "expr": expr,
                "min_duration": 90,
                "client_ip": client_ip,
                "has_link4m_api": False
            })

        if path in ("/api/shortener/discord-status", "/shortener/discord-status"):
            token = query.get("token", [""])[0]
            sess = verify_and_decode_getkey_token(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            
            disc_verified = sess.get("discord_verified", False)
            disc_started_at = int(sess.get("discord_started_at", 0))
            wait_time = int(sess.get("required_wait", 90))
            disc_duration = 60

            if disc_verified:
                return self.send_json({
                    "status": "verified",
                    "verified": True,
                    "elapsed": disc_duration,
                    "remaining": 0,
                    "required": disc_duration,
                    "token": token,
                    "next_url": f"/getkey/middle?token={token}"
                })

            if disc_started_at <= 0:
                return self.send_json({
                    "status": "waiting",
                    "verified": False,
                    "elapsed": 0,
                    "remaining": disc_duration,
                    "required": disc_duration,
                    "message": "Vui lòng nhập Discord username để kích hoạt đối soát!"
                })

            disc_elapsed = int(time.time() - disc_started_at)
            disc_remaining = max(0, disc_duration - disc_elapsed)

            if disc_remaining > 0:
                return self.send_json({
                    "status": "checking",
                    "verified": False,
                    "elapsed": disc_elapsed,
                    "remaining": disc_remaining,
                    "required": disc_duration
                })
            else:
                verified_token = generate_stateless_getkey_token(
                    ip=client_ip,
                    wait_time=wait_time,
                    discord_started_at=disc_started_at,
                    discord_verified=True,
                    discord_user=sess.get("discord_user", ""),
                    created_at=sess.get("created_at")
                )
                return self.send_json({
                    "status": "verified",
                    "verified": True,
                    "elapsed": disc_duration,
                    "remaining": 0,
                    "required": disc_duration,
                    "token": verified_token,
                    "next_url": f"/getkey/middle?token={verified_token}"
                })

        if path in ("/api/getkey/middle-status", "/getkey/middle-status"):
            token = query.get("token", [""])[0]
            sess = verify_and_decode_getkey_token(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            elapsed = int(time.time() - sess["created_at"])
            wait_time = int(sess.get("required_wait", 90))
            remaining = max(0, wait_time - elapsed)
            test_bypass = _resolve_test_bypass(query.get("test_bypass", ["0"])[0], client_ip)
            is_wl = server.is_ip_whitelisted(client_ip) if hasattr(server, "is_ip_whitelisted") else False
            is_disc_ok = bool(sess.get("discord_verified", False)) or test_bypass
            return self.send_json({
                "status": "ok",
                "elapsed": elapsed,
                "total_elapsed": elapsed,
                "remaining": remaining,
                "required": wait_time,
                "total_min": wait_time,
                "can_redeem": (is_disc_ok and (remaining <= 0 or is_wl)),
                "discord_verified": is_disc_ok,
                "is_whitelisted": is_wl,
                "pow_solved": sess.get("pow_solved", True),
                "pow_challenge": sess.get("pow_challenge", "")
            })

        if path in ("/api/getkey/verify", "/getkey/verify"):
            token = query.get("token", [""])[0]
            sess = verify_and_decode_getkey_token(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            
            elapsed = int(time.time() - sess["created_at"])
            wait_time = int(sess.get("required_wait", 90))
            test_bypass = _resolve_test_bypass(query.get("test_bypass", ["0"])[0], client_ip)
            is_wl = server.is_ip_whitelisted(client_ip) if hasattr(server, "is_ip_whitelisted") else False
            
            if not sess.get("discord_verified", False) and not test_bypass:
                return self.send_json({
                    "status": "blocked",
                    "message": "Chưa hoàn thành xác thực Discord tại Link 2! Vui lòng không bypass.",
                    "redirect": f"/getkey/shortener?token={token}"
                }, status=403)

            if elapsed < wait_time and not is_wl:
                strikes = 1
                is_banned = False
                if hasattr(server, "record_bypass_strike"):
                    strikes, is_banned = server.record_bypass_strike(client_ip, f"Bypass Link (Đốt thiếu {wait_time - elapsed}s)")
                return self.send_json({
                    "status": "blocked",
                    "message": "Vượt link quá nhanh (Bypass detected)!",
                    "elapsed": elapsed,
                    "min_duration": wait_time,
                    "strikes": strikes,
                    "is_banned": is_banned
                }, status=403)

            # Kiểm tra xem IP này đã có key trong 24h chưa
            if hasattr(server, "get_existing_active_key_for_ip"):
                existing = server.get_existing_active_key_for_ip(client_ip)
                if existing:
                    return self.send_json({
                        "status": "ok",
                        "message": "Bạn đã có Key còn hạn trong 24h!",
                        "key": existing.get("key"),
                        "elapsed": elapsed,
                        "is_existing": True
                    })

            if not sess.get("claimed_key"):
                new_key_data = server.generate_death_key(days=1, notes="Link Free 24h", key_type="free_24h", client_ip=client_ip)
                sess["claimed_key"] = new_key_data["key"]
                sess["used"] = True
                if hasattr(server.state, "getkey_success_count"):
                    server.state.getkey_success_count += 1

            return self.send_json({
                "status": "ok",
                "message": "Xác thực thành công!",
                "key": sess["claimed_key"],
                "elapsed": elapsed,
                "is_existing": False
            })

        if path in ("/api/getkey/my-session", "/getkey/my-session"):
            token = server.ip_getkey_sessions.get(client_ip) if hasattr(server, "ip_getkey_sessions") else None
            sess = verify_and_decode_getkey_token(token) if token else None
            if sess and not sess.get("used"):
                elapsed = int(time.time() - sess["created_at"])
                wait_time = int(sess.get("required_wait", 90))
                return self.send_json({
                    "status": "ok",
                    "has_session": True,
                    "token": token,
                    "elapsed": elapsed,
                    "total_elapsed": elapsed,
                    "remaining": max(0, wait_time - elapsed),
                    "required": wait_time,
                    "total_min": wait_time,
                    "discord_verified": True
                })
            return self.send_json({"status": "ok", "has_session": False})

        if path.startswith("/api/shortener/info/") or path.startswith("/shortener/info/"):
            code = path.split("/")[-1].strip()
            item = server.shortened_links_db.get(code)
            if item:
                item["clicks"] = item.get("clicks", 0) + 1
                server.save_keys_data(server.keys_db)
                return self.send_json({
                    "status": "ok",
                    "dest_url": item["dest_url"],
                    "duration": item.get("duration", 15)
                })
            return self.send_json({"status": "error", "message": "Liên kết rút gọn không tồn tại!"}, status=404)

        # 3. Admin GET Endpoints
        if path in ("/api/admin/login", "/admin/login"):
            # Health check / status check cho Admin
            is_auth = self.check_admin_auth()
            return self.send_json({
                "status": "ok",
                "authenticated": is_auth,
                "message": "Admin API Active. Gửi POST với username và password để đăng nhập."
            })

        if path in ("/api/admin/keys", "/admin/keys"):
            if not self.check_admin_auth():
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            keys_list = list(server.keys_db.get("keys", {}).values())
            keys_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return self.send_json({"status": "ok", "keys": keys_list})

        if path in ("/api/admin/workers", "/admin/workers"):
            if not self.check_admin_auth():
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            st = server.state.get_dict()
            return self.send_json({
                "status": "ok",
                "workers": st["workers"],
                "total_active": len(st["workers"]),
                "exact_checked": server.state.checked_total,
                "exact_live": server.state.total_live,
                "exact_dead": server.state.dead_count,
                "ping_target": server.state.ping_target
            })

        if path in ("/api/admin/security/lists", "/admin/security/lists"):
            if not self.check_admin_auth():
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            wl = server.keys_db.get("whitelist", [])
            bl_raw = server.keys_db.get("blacklist", {})
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
            return self.send_json({
                "status": "ok",
                "whitelist": wl,
                "blacklist": bl_list,
                "client_ip": client_ip
            })

        if path in ("/api/admin/shortener/links", "/admin/shortener/links"):
            if not self.check_admin_auth():
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            links = []
            for code, item in server.shortened_links_db.items():
                links.append({
                    "code": code,
                    "short_path": f"/s/{code}",
                    "dest_url": item.get("dest_url", ""),
                    "duration": item.get("duration", 15),
                    "created_at": item.get("created_date", "--"),
                    "clicks": item.get("clicks", 0)
                })
            links.sort(key=lambda x: x["clicks"], reverse=True)
            return self.send_json({"status": "ok", "links": links})

        if path.startswith("/download/"):
            filename = os.path.basename(path)
            target_f = os.path.join(server.WRITABLE_DIR, filename)
            resolved = find_static_file(target_f) or (target_f if os.path.exists(target_f) else None)
            if resolved and os.path.exists(resolved):
                with open(resolved, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_cors_and_headers(200, "text/plain; charset=utf-8")
                return self.wfile.write(content)
            return self.send_json({"error": "File not found"}, status=404)

        return self.send_json({"error": f"Endpoint {path} not found"}, status=404)

    def do_POST(self):
        try:
            return self._do_POST_impl()
        except Exception as e:
            return self.send_json({"status": "error", "message": f"Lỗi máy chủ nội bộ: {str(e)}"}, status=500)

    def _do_POST_impl(self):
        path, query = self.parse_url_parts()
        client_ip = get_req_client_ip(self.headers, self.client_address)
        body = self.read_json_body()

        # 1. Public POST APIs
        if path in ("/api/auth/verify", "/auth/verify"):
            key = body.get("key") or self.get_header("X-License-Key")
            valid, msg = server.verify_death_key(key, client_ip)
            if valid:
                record = server.keys_db["keys"].get(key, {})
                exp_display = record.get("expires_at", "Vĩnh viễn (Lifetime)")
                days_left = record.get("days", 30)
                return self.send_json({
                    "status": "ok",
                    "message": msg,
                    "key": key,
                    "expires_at": exp_display,
                    "days_left": days_left,
                    "key_status": record.get("status", "active"),
                    "notes": record.get("notes", ""),
                    "contact": server.TOOL_DISCORD,
                    "tool_name": server.TOOL_NAME,
                    "target_url": server.state.ping_target
                })
            return self.send_json({"status": "error", "message": msg}, status=401)

        if path in ("/api/submit", "/submit"):
            key = self.get_header("X-License-Key") or body.get("key")
            valid, msg = server.verify_death_key(key, client_ip)
            if not valid:
                return self.send_json({"status": "error", "message": msg}, status=401)

            live_proxies = body.get("live_proxies", [])
            delta_checked = int(body.get("delta_checked", body.get("checked_count", 0)))
            client_total_checked = int(body.get("total_checked", 0))
            client_total_live = int(body.get("total_live", 0))
            worker_speed = int(body.get("speed", 0))

            if client_total_checked > 0:
                server.state.checked_total = max(server.state.checked_total, client_total_checked)
            else:
                server.state.checked_total += delta_checked

            server.state.dead_count += max(0, delta_checked - len(live_proxies))

            # Cập nhật số liệu minh bạch của từng worker node
            worker_id = f"{client_ip}:{key[-8:]}" if (key and len(key) >= 8) else client_ip
            now = time.time()
            if worker_id not in server.state.active_workers:
                server.state.active_workers[worker_id] = {
                    "id": worker_id,
                    "ip": client_ip,
                    "key": key or "--",
                    "connected_at": time.strftime("%H:%M:%S"),
                    "checked": client_total_checked or delta_checked,
                    "live": client_total_live or len(live_proxies),
                    "speed": worker_speed,
                    "last_seen": now
                }
            else:
                w = server.state.active_workers[worker_id]
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
            if key and key in server.keys_db.get("keys", {}):
                k_rec = server.keys_db["keys"][key]
                if client_total_live > 0:
                    k_rec["total_submitted"] = max(k_rec.get("total_submitted", 0), client_total_live)
                else:
                    k_rec["total_submitted"] = k_rec.get("total_submitted", 0) + len(live_proxies)

                if client_total_checked > 0:
                    k_rec["total_checked"] = max(k_rec.get("total_checked", 0), client_total_checked)
                else:
                    k_rec["total_checked"] = k_rec.get("total_checked", 0) + delta_checked

                k_rec["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")

            for p in live_proxies:
                server.save_live_proxy_record(p)

            # Đồng bộ state xuống disk (bền vững đa container serverless)
            server.save_server_state()

            return self.send_json({
                "status": "ok",
                "accepted": len(live_proxies),
                "total_checked": server.state.checked_total,
                "total_live": server.state.total_live
            })

        if path in ("/api/getkey/start", "/getkey/start"):
            cid = str(body.get("cid") or body.get("captcha_id") or "").strip()
            ans = str(body.get("answer") or "").strip()
            if not cid or not ans or not verify_stateless_captcha(cid, ans):
                return self.send_json({"status": "error", "message": "Đáp án phép tính không chính xác hoặc phiên đã hết hạn!"}, status=400)
            
            wait_time = 90
            token = generate_stateless_getkey_token(client_ip, wait_time)
            code = server.create_death_short_link(f"/getkey/middle?token={token}", duration=wait_time)

            return self.send_json({
                "status": "ok",
                "token": token,
                "redirect_url": f"/getkey/shortener?token={token}",
                "shortener_url": f"/getkey/shortener?token={token}",
                "middle_url": f"/getkey/middle?token={token}",
                "short_url": f"/s/{code}",
                "short_code": code,
                "wait_seconds": wait_time
            })

        if path in ("/api/shortener/discord-start", "/shortener/discord-start"):
            token = body.get("token")
            username = str(body.get("username") or body.get("discord_user") or "").strip()
            sess = verify_and_decode_getkey_token(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            
            if not username or len(username) < 2:
                return self.send_json({"status": "error", "message": "Vui lòng nhập Discord username hợp lệ (ít nhất 2 ký tự)!"}, status=400)

            now_ts = int(time.time())
            wait_time = int(sess.get("required_wait", 90))
            new_token = generate_stateless_getkey_token(
                ip=client_ip,
                wait_time=wait_time,
                discord_started_at=now_ts,
                discord_verified=False,
                discord_user=username,
                created_at=sess.get("created_at")
            )
            return self.send_json({
                "status": "ok",
                "message": "Đã bắt đầu đối soát Discord!",
                "duration": 60,
                "token": new_token
            })

        if path in ("/api/control", "/control"):
            action = body.get("action", "")
            return self.send_json({"status": "ok", "action": action})

        if path in ("/api/update", "/update"):
            return self.send_json({"status": "ok", "message": "Cập nhật thành công!"})

        # 2. Admin POST APIs
        if path in ("/api/admin/login", "/admin/login"):
            username = body.get("username", "").strip() or "admin"
            password = body.get("password", "").strip()
            admin_cfg = server.keys_db.get("admin", {})
            salt = os.environ.get("ADMIN_SALT") or admin_cfg.get("salt", "DeathSecretSalt2026")
            expected_hash = os.environ.get("ADMIN_PASSWORD_HASH") or admin_cfg.get("password_hash", "")
            calc_hash = server.hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

            # Chỉ nhận mật khẩu khớp hash cấu hình (đã xoá toàn bộ mật khẩu mặc định hard-code)
            is_valid_pwd = bool(expected_hash) and server.hmac.compare_digest(calc_hash, expected_hash)
            expected_user = os.environ.get("ADMIN_USERNAME") or admin_cfg.get("username", "admin")
            if username == expected_user and is_valid_pwd:
                token = generate_stateless_admin_token()
                cookie_str = f"admin_token={token}; Path=/; Max-Age=604800; HttpOnly; SameSite=Lax"
                return self.send_json(
                    {"status": "ok", "token": token, "message": "Đăng nhập Admin thành công!"},
                    extra_headers={"Set-Cookie": cookie_str}
                )
            return self.send_json({"status": "error", "message": "Tài khoản hoặc mật khẩu không chính xác!"}, status=401)

        # Toàn bộ API bên dưới yêu cầu Admin Auth
        if not self.check_admin_auth():
            return self.send_json({"status": "error", "message": "Unauthorized (Vui lòng đăng nhập lại Admin)"}, status=401)

        if path in ("/api/admin/gen-key", "/admin/gen-key"):
            days = int(body.get("days", 30))
            count = min(max(int(body.get("count", 1)), 1), 50)
            notes = body.get("notes", "Admin Generated")
            key_type = body.get("key_type", "custom")
            generated = []
            for _ in range(count):
                k = server.generate_death_key(days=days, notes=notes, key_type=key_type)
                generated.append(k)
            return self.send_json({"status": "ok", "keys": generated, "key": generated[0] if generated else {}})

        if path in ("/api/admin/revoke-key", "/admin/revoke-key"):
            key = body.get("key")
            new_status = body.get("status", "banned")
            if key in server.keys_db.get("keys", {}):
                server.keys_db["keys"][key]["status"] = new_status
                server.save_keys_data(server.keys_db)
                return self.send_json({"status": "ok", "message": f"Đã chuyển key sang {new_status}"})
            return self.send_json({"status": "error", "message": "Không tìm thấy key"}, status=404)

        if path in ("/api/admin/delete-key", "/admin/delete-key"):
            key = body.get("key")
            if key in server.keys_db.get("keys", {}):
                del server.keys_db["keys"][key]
                server.save_keys_data(server.keys_db)
                return self.send_json({"status": "ok", "message": "Đã xóa key thành công"})
            return self.send_json({"status": "error", "message": "Không tìm thấy key"}, status=404)

        if path in ("/api/admin/target", "/admin/target"):
            target = body.get("target_url", "").strip()
            if not target or not (target.startswith("http://") or target.startswith("https://")):
                return self.send_json({"status": "error", "message": "Target URL phải bắt đầu bằng http:// hoặc https://"}, status=400)
            server.state.ping_target = target
            return self.send_json({"status": "ok", "message": f"Đã cập nhật Target URL thành công: {target}", "ping_target": server.state.ping_target})

        if path in ("/api/admin/settings", "/admin/settings"):
            settings = server.get_server_settings()
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

            server.save_keys_data(server.keys_db)
            return self.send_json({"status": "ok", "message": "Đã lưu cài đặt hệ thống thành công!", "settings": settings})

        if path in ("/api/admin/test-webhook", "/admin/test-webhook"):
            webhook_url = body.get("discord_webhook", "").strip() or server.get_server_settings().get("discord_webhook", "").strip()
            if not webhook_url:
                return self.send_json({"status": "error", "message": "Chưa nhập Webhook URL!"}, status=400)
            if not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
                return self.send_json({"status": "error", "message": "Địa chỉ Webhook không hợp lệ!"}, status=400)
            
            # Gửi thử nghiệm đồng bộ an toàn trên Serverless
            try:
                import urllib.request
                test_payload = {
                    "username": "Death Proxy Hunter Bot",
                    "avatar_url": "https://cdn-icons-png.flaticon.com/512/3208/3208676.png",
                    "embeds": [{
                        "title": "🧪 THỬ NGHIỆM KẾT NỐI DISCORD WEBHOOK",
                        "description": "Tin nhắn thử nghiệm từ **Death Master Server trên Vercel**! Tính năng che IP đã kích hoạt.",
                        "color": 0x10B981,
                        "fields": [
                            {"name": "⚡ Môi Trường", "value": "`Vercel Cloud Serverless`", "inline": True},
                            {"name": "🔒 Che Mặt Nạ IP", "value": "`103.152.***.***:1080`", "inline": True},
                            {"name": "🛡️ Trạng Thái", "value": "`Hoạt động hoàn hảo`", "inline": True}
                        ]
                    }]
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(test_payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'DeathSilence/1.0'}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 204):
                        return self.send_json({"status": "ok", "message": "Gửi tin nhắn test tới Discord thành công!"})
                    return self.send_json({"status": "error", "message": f"Discord trả về mã: {resp.status}"}, status=400)
            except Exception as e:
                return self.send_json({"status": "error", "message": f"Không thể gửi tin nhắn tới Webhook: {str(e)}"}, status=400)

        if path in ("/api/admin/security/unblacklist", "/admin/security/unblacklist"):
            ip = body.get("ip", "").strip()
            if not ip:
                return self.send_json({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
            server.unblacklist_ip(ip)
            return self.send_json({"status": "ok", "message": f"Đã mở khóa (Unban 1-Click) thành công cho IP {ip}!"})

        if path in ("/api/admin/security/blacklist", "/admin/security/blacklist"):
            ip = body.get("ip", "").strip()
            reason = body.get("reason", "Khóa thủ công từ Admin").strip()
            duration = int(body.get("duration", 30))
            if not ip:
                return self.send_json({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
            server.add_blacklist_ip(ip, reason, duration)
            return self.send_json({"status": "ok", "message": f"Đã đưa IP {ip} vào Blacklist ({duration} phút)!"})

        if path in ("/api/admin/security/whitelist/add", "/admin/security/whitelist/add"):
            ip = body.get("ip", "").strip()
            if not ip:
                return self.send_json({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
            server.add_whitelist_ip(ip)
            return self.send_json({"status": "ok", "message": f"Đã thêm IP {ip} vào Whitelist!"})

        if path in ("/api/admin/security/whitelist/remove", "/admin/security/whitelist/remove"):
            ip = body.get("ip", "").strip()
            if not ip:
                return self.send_json({"status": "error", "message": "Thiếu địa chỉ IP!"}, status=400)
            server.remove_whitelist_ip(ip)
            return self.send_json({"status": "ok", "message": f"Đã xóa IP {ip} khỏi Whitelist!"})

        if path in ("/api/admin/shortener/create", "/admin/shortener/create"):
            dest_url = body.get("dest_url", "").strip()
            alias = body.get("alias", "").strip()
            duration = int(body.get("duration", 15))
            if not dest_url or not (dest_url.startswith("http://") or dest_url.startswith("https://") or dest_url.startswith("/")):
                return self.send_json({"status": "error", "message": "Link đích không hợp lệ!"}, status=400)
            
            code = server.create_death_short_link(dest_url, duration=duration, alias=alias)
            return self.send_json({
                "status": "ok",
                "message": f"Tạo link rút gọn thành công: /s/{code}",
                "code": code,
                "short_path": f"/s/{code}",
                "dest_url": dest_url,
                "duration": duration
            })

        if path in ("/api/admin/shortener/delete", "/admin/shortener/delete"):
            code = body.get("code", "").strip()
            if code in server.shortened_links_db:
                del server.shortened_links_db[code]
                server.save_keys_data(server.keys_db)
                return self.send_json({"status": "ok", "message": f"Đã xóa link rút gọn /s/{code} thành công!"})
            return self.send_json({"status": "error", "message": "Không tìm thấy mã rút gọn này!"}, status=404)

        return self.send_json({"error": f"Endpoint {path} not found"}, status=404)
