import os
import sys
import json
import re
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Thêm thư mục server vào sys.path để import toàn bộ module server.py
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import server

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
    # Kiểm tra theo cả chữ thường lẫn định dạng chuẩn
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

class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function Handler - Hỗ trợ đầy đủ Web Pages & REST APIs."""

    def log_message(self, format, *args):
        # Bịt miệng log rác của HTTP server trên Vercel
        pass

    def send_cors_and_headers(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-License-Key, X-Admin-Token, Authorization")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_cors_and_headers(status, "application/json; charset=utf-8")
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
        """Lấy header không phân biệt hoa thường."""
        low_name = name.lower()
        for k, v in self.headers.items():
            if k.lower() == low_name:
                return v
        return default

    def parse_url_parts(self):
        parsed = urllib.parse.urlparse(self.path)
        raw_path = parsed.path.rstrip("/")
        if not raw_path:
            raw_path = "/"
        query = urllib.parse.parse_qs(parsed.query)

        path = raw_path

        # 1. Trích xuất đường dẫn gốc từ query parameter __orig_path (do vercel.json rewrite chuyển qua)
        if "__orig_path" in query:
            orig = query["__orig_path"][0]
            if orig:
                p_orig = urllib.parse.urlparse(orig).path.rstrip("/")
                path = p_orig if p_orig else "/"

        # 2. Kiểm tra các header do Vercel / Cloudflare Edge Router gắn vào nếu path đang là file handler
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
                    h_path = urllib.parse.urlparse(val).path.rstrip("/")
                    if h_path and h_path not in ("/api/index.py", "/api/index", "/api"):
                        path = h_path
                        break

        # 3. Xử lý trường hợp Vercel rewrite giữ lại prefix /api/index.py hoặc /api/index
        for prefix in ["/api/index.py", "/api/index"]:
            if path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break

        # 4. Khi path là chính file handler (/api/index.py hoặc /api/index hoặc /api hoặc rỗng) thì đó chính là Root "/"
        if path in ("/api/index.py", "/api/index", "/api", ""):
            path = "/"

        return path, query

    def do_GET(self):
        path, query = self.parse_url_parts()
        client_ip = get_req_client_ip(self.headers, self.client_address)

        # 1. Routing Web Pages
        if path in ("/", "/index.html"):
            return self.send_html_file(server.DASHBOARD_FILE)

        if path == "/terms":
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

        if path == "/hosting-aup":
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

        if path == "/getkey/shortener" or path.startswith("/s/"):
            return self.send_html_file(server.SHORTENER_PAGE)

        if path in ("/getkey/middle", "/getkey/verify"):
            return self.send_html_file(server.GETKEY_MIDDLE_PAGE)

        if path == "/getkey/end":
            return self.send_html_file(server.GETKEY_END_PAGE)

        # 2. Routing APIs
        if path == "/api/stats":
            data = server.state.get_dict()
            return self.send_json(data)

        if path == "/api/tasks":
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

        if path == "/api/getkey/captcha":
            cid, challenge = server.generate_math_captcha()
            return self.send_json({"status": "ok", "captcha_id": cid, "challenge": challenge})

        if path == "/api/shortener/discord-status":
            token = query.get("token", [""])[0]
            sess = server.getkey_tokens.get(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            elapsed = int(time.time() - sess["created_at"])
            remaining = max(0, sess["required_wait"] - elapsed)
            return self.send_json({
                "status": "ok",
                "verified": sess.get("discord_verified", False),
                "elapsed": elapsed,
                "remaining": remaining,
                "required": sess["required_wait"]
            })

        if path == "/api/getkey/middle-status":
            token = query.get("token", [""])[0]
            sess = server.getkey_tokens.get(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            elapsed = int(time.time() - sess["created_at"])
            remaining = max(0, sess["required_wait"] - elapsed)
            return self.send_json({
                "status": "ok",
                "elapsed": elapsed,
                "remaining": remaining,
                "required": sess["required_wait"],
                "pow_solved": sess.get("pow_solved", False),
                "pow_challenge": sess.get("pow_challenge", "")
            })

        if path == "/api/getkey/verify":
            token = query.get("token", [""])[0]
            sess = server.getkey_tokens.get(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ hoặc đã hết hạn!"}, status=400)
            
            elapsed = time.time() - sess["created_at"]
            if elapsed < sess["required_wait"]:
                server.record_bypass_strike(client_ip, f"Bypass Link (Đốt thiếu {int(sess['required_wait'] - elapsed)}s)")
                return self.send_json({"status": "error", "message": "Vượt link quá nhanh (Bypass detected)!"}, status=403)

            if not sess.get("claimed_key"):
                new_key_data = server.generate_death_key(1, "Link Free 24h", client_ip, key_type="free_24h")
                sess["claimed_key"] = new_key_data["key"]
                sess["used"] = True
                server.state.getkey_success_count += 1

            return self.send_json({
                "status": "ok",
                "message": "Xác thực thành công!",
                "key": sess["claimed_key"]
            })

        if path == "/api/getkey/my-session":
            token = server.ip_getkey_sessions.get(client_ip)
            sess = server.getkey_tokens.get(token) if token else None
            if sess and not sess.get("used"):
                elapsed = int(time.time() - sess["created_at"])
                return self.send_json({
                    "status": "ok",
                    "has_session": True,
                    "token": token,
                    "elapsed": elapsed,
                    "remaining": max(0, sess["required_wait"] - elapsed),
                    "required": sess["required_wait"]
                })
            return self.send_json({"status": "ok", "has_session": False})

        if path.startswith("/api/shortener/info/"):
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

        if path == "/api/admin/keys":
            token = self.get_header("X-Admin-Token")
            if token not in server.active_admin_sessions:
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            keys_list = list(server.keys_db.get("keys", {}).values())
            return self.send_json({"status": "ok", "keys": keys_list})

        if path == "/api/admin/workers":
            token = self.get_header("X-Admin-Token")
            if token not in server.active_admin_sessions:
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            workers = list(server.state.active_workers.values())
            return self.send_json({"status": "ok", "workers": workers})

        if path == "/api/admin/shortener/links":
            token = self.get_header("X-Admin-Token")
            if token not in server.active_admin_sessions:
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            links = list(server.shortened_links_db.values())
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
        path, query = self.parse_url_parts()
        client_ip = get_req_client_ip(self.headers, self.client_address)
        body = self.read_json_body()

        if path == "/api/auth/verify":
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

        if path == "/api/submit":
            key = self.get_header("X-License-Key") or body.get("key")
            valid, msg = server.verify_death_key(key, client_ip)
            if not valid:
                return self.send_json({"status": "error", "message": msg}, status=401)

            live_proxies = body.get("live_proxies", [])
            delta_checked = int(body.get("delta_checked", 0))

            if delta_checked > 0:
                server.state.checked_total += delta_checked
                server.state.dead_count += max(0, delta_checked - len(live_proxies))

            for p in live_proxies:
                server.save_live_proxy_record(p)

            return self.send_json({"status": "ok", "accepted": len(live_proxies)})

        if path == "/api/getkey/start":
            cid = body.get("captcha_id")
            ans = body.get("answer")
            sess = server.captcha_sessions.get(cid)
            if not sess or str(sess.get("answer")) != str(ans).strip():
                return self.send_json({"status": "error", "message": "Đáp án phép tính không chính xác!"}, status=400)
            
            token = server.secrets.token_urlsafe(32)
            wait_time = 90
            server.getkey_tokens[token] = {
                "created_at": time.time(),
                "ip": client_ip,
                "required_wait": wait_time,
                "discord_verified": False,
                "pow_solved": False,
                "claimed_key": "",
                "used": False
            }
            server.ip_getkey_sessions[client_ip] = token
            code = server.create_death_short_link(f"/getkey/middle?token={token}", duration=wait_time)

            return self.send_json({
                "status": "ok",
                "token": token,
                "short_url": f"/s/{code}",
                "short_code": code,
                "wait_seconds": wait_time
            })

        if path == "/api/shortener/discord-start":
            token = body.get("token")
            username = body.get("username", "").strip()
            sess = server.getkey_tokens.get(token)
            if not sess:
                return self.send_json({"status": "error", "message": "Phiên không hợp lệ!"}, status=400)
            sess["discord_username"] = username
            sess["discord_verified"] = True
            return self.send_json({"status": "ok", "message": "Đã bắt đầu đối soát Discord!"})

        if path == "/api/admin/login":
            username = body.get("username", "")
            password = body.get("password", "")
            admin_cfg = server.keys_db.get("admin", {})
            salt = admin_cfg.get("salt", "DeathSecretSalt2026")
            expected_hash = admin_cfg.get("password_hash", "")
            calc_hash = server.hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

            if username == admin_cfg.get("username", "admin") and calc_hash == expected_hash:
                token = server.secrets.token_hex(24)
                server.active_admin_sessions[token] = time.time()
                return self.send_json({"status": "ok", "token": token, "message": "Đăng nhập Admin thành công!"})
            return self.send_json({"status": "error", "message": "Tài khoản hoặc mật khẩu không chính xác!"}, status=401)

        if path == "/api/admin/gen-key":
            token = self.get_header("X-Admin-Token")
            if token not in server.active_admin_sessions:
                return self.send_json({"status": "error", "message": "Unauthorized"}, status=401)
            days = int(body.get("days", 30))
            notes = body.get("notes", "Admin Generated")
            key_data = server.generate_death_key(days, notes)
            return self.send_json({"status": "ok", "key": key_data})

        return self.send_json({"error": f"Endpoint {path} not found"}, status=404)

# ASGI Callable Wrapper để Vercel chạy native ASGI runtime
async def app(scope, receive, send):
    """ASGI 3.0 Entrypoint cho Vercel Python Runtime."""
    if scope["type"] == "http":
        # Chuyển đổi ASGI request thành BaseHTTPRequestHandler tương thích
        class DummyRequest:
            def __init__(self, rfile):
                self.rfile = rfile
            def makefile(self, *args, **kwargs):
                return self.rfile

        import io
        body_bytes = b""
        more_body = True
        while more_body:
            msg = await receive()
            body_bytes += msg.get("body", b"")
            more_body = msg.get("more_body", False)

        rfile = io.BytesIO(body_bytes)
        wfile = io.BytesIO()

        # Tạo handler giả lập để xử lý logic
        h = handler(DummyRequest(rfile), ("127.0.0.1", 80), None)
        h.path = scope.get("path", "/")
        if scope.get("query_string"):
            h.path += "?" + scope["query_string"].decode("latin1")
        h.command = scope.get("method", "GET")
        h.headers = dict((k.decode("latin1").lower(), v.decode("latin1")) for k, v in scope.get("headers", []))
        h.wfile = wfile

        status_container = [200]
        headers_container = []

        def custom_send_response(status, message=None):
            status_container[0] = status
        def custom_send_header(k, v):
            headers_container.append((k.lower().encode("latin1"), v.encode("latin1")))
        def custom_end_headers():
            pass

        h.send_response = custom_send_response
        h.send_header = custom_send_header
        h.end_headers = custom_end_headers

        if h.command == "GET":
            h.do_GET()
        elif h.command == "POST":
            h.do_POST()
        elif h.command == "OPTIONS":
            h.do_OPTIONS()

        response_body = wfile.getvalue()
        await send({
            "type": "http.response.start",
            "status": status_container[0],
            "headers": headers_container
        })
        await send({
            "type": "http.response.body",
            "body": response_body
        })
