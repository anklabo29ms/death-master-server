# 🛡️ HOSTING SERVICE COMPLIANCE & ACCEPTABLE USE STATEMENT
## NOTICE FOR HOSTING PROVIDERS, CLOUD PLATFORMS (VERCEL, RENDER, VPS) & SYSADMINS

**Application:** `Death Master Server (Orchestrator)`  
**Runtime:** Python 3.10+ / Vercel Serverless / ASGI / WSGI / aiohttp  
**Default Port:** `5000` (or dynamic `$PORT` assigned by host)  
**Architecture:** 100% Client-Server Distributed Task Dispatcher  
**Author:** `! Death Silence`  
**Contact:** `Discord: @qyk3` | Server: `https://discord.gg/2zuwDpJaNP`  
**Effective Date:** 2026-09-24  

---

### 1. SUMMARY FOR NETWORK & SECURITY COMPLIANCE OFFICERS:
If you are reviewing this deployment on **Vercel, Render, Railway, Pterodactyl, AWS, or VPS** for compliance with your Acceptable Use Policy (AUP):

1. **ZERO OUTBOUND PORT SCANNING OR BRUTE-FORCING:**
   * This server application **DOES NOT** perform outbound port scanning, SYN floods, ICMP sweeps, or brute-force attacks against third-party networks.
   * It **DOES NOT** connect to or benchmark candidate proxy servers from this host.
   * It operates purely as an **inbound HTTP REST API / Web dashboard** serving coordination payloads and validating HMAC-signed client license tokens.

2. **VERCEL & SERVERLESS PLATFORM FAIR USE COMPLIANCE:**
   * **Serverless Execution:** Operates under standard ephemeral HTTP request/response lifecycles (< 10s-30s execution time limit).
   * **Resource Profile:** Extremely lightweight RAM footprint (~30MB - 60MB on Serverless, ~80MB on persistent VPS), < 2% single-core CPU utilization.
   * **No Persistent Sockets Required on Serverless:** Fully supports HTTP polling fallback (`/api/stats`, `/api/tasks`, `/api/submit`) when WebSockets are unavailable or terminated on serverless edge networks.
   * **Read-Only Filesystem Safe:** Automatically defaults to `/tmp` storage when deployed in read-only container environments like Vercel Serverless.

3. **WORKLOAD DELEGATION (100% CLIENT-SIDE):**
   * All network latency benchmarks and TCP reachability tests are strictly performed **on remote user computers (`client.py`)**, completely offloaded from this cloud host.
   * Resulting live proxy files are saved locally on the client's own machine.

4. **PRIVACY & ANTI-ABUSE CONTROLS:**
   * No personally identifiable information (PII) is stored or tracked.
   * Client IP addresses broadcasted to dashboards are strictly masked (e.g., `103.152.***.***`) to prevent reconnaissance.
   * Built-in brute-force protection rate-limits and temporarily blocks abusive IP addresses.
   * Reverse proxy headers (`X-Real-IP`, `CF-Connecting-IP`, `X-Vercel-Forwarded-For`, `X-Forwarded-For`) are properly sanitized and inspected.

---

### 2. AUDIT MATRIX:

| Category | Server Host Profile (Vercel / VPS) | Client Node Profile (`client.py`) |
| :--- | :--- | :--- |
| **Outbound Port Scanning** | **0 (Zero)** | Limited to candidate IPs only |
| **TCP SYN Handshakes** | Inbound HTTP only | Client-side only |
| **Bandwidth Consumption** | Minimal (< 50MB/day) | Varies by user concurrency |
| **RAM Footprint** | ~30MB - 80MB | ~50MB - 120MB |
| **Target Pinging** | None (Orchestrator only) | Ping latency checks on client |
| **Data Storage** | Zero PII, HMAC keys only | Local `.txt` files on client |

---

### 3. CONTACT & 24/7 COOPERATION:
We cooperate fully and promptly with all hosting platforms, data centers, and network administrators. For any inquiries, verification requests, or abuse concerns, please reach out directly:
* **Discord:** `@qyk3`
* **Official Server:** `https://discord.gg/2zuwDpJaNP`
