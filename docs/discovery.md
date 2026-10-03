# Company Discovery Guide

The **Company Discovery** feature automatically gathers a startup's public footprint across LinkedIn, company websites, and news coverage, extracts structured evidence without hallucination, and compiles it into a standard 9-tab investor screening report.

---

## 1. Quick Start

1. Start the backend:
   ```bash
   cd backend
   .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
   ```
2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:5173/discover` or click **"Discover Company"** in the top navigation bar.

---

## 2. Configuration & Environment Variables

Add the following to your backend `.env` file:

```env
# ── Discovery Feature ──
DISCOVERY_ENABLED=true
SEARCH_PROVIDERS=["searxng","duckduckgo"]   # Ordered fallback search chain
SEARXNG_BASE_URL=http://100.x.x.x:8888     # Tailscale IP of SearXNG instance (optional)
LLM_BASE_URL=http://100.x.x.x:11434/v1    # Tailscale IP of Ollama server
LLM_MODEL=qwen2.5:7b-instruct
LLM_TIMEOUT_SECONDS=300
LLM_PROFILE=light
CACHE_TTL=3600
SCRAPER_MIN_INTERVAL=3.0
IMAGE_PROXY_ALLOWED_HOSTS=media.licdn.com,static.licdn.com
DISCOVERY_MAX_JOBS_STORED=20
DISCOVERY_MAX_EVIDENCE_SIZE_MB=5
DISCOVERY_RATE_LIMIT_PER_HOUR=5
DISCOVERY_MIN_FREE_DISK_GB=2.0
```

---

## 3. Self-Hosted SearXNG (Office PC via Tailscale)

To run SearXNG locally with JSON API enabled without rate limits, use the following `docker-compose.yml`:

```yaml
version: '3.8'

services:
  searxng:
    image: docker.io/searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8888:8080"
    environment:
      - SEARXNG_BASE_URL=http://100.x.x.x:8888/
    volumes:
      - ./searxng:/etc/searxng:rw
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

In your `./searxng/settings.yml`, make sure JSON format is enabled:
```yaml
search:
  formats:
    - html
    - json
server:
  secret_key: "generate-a-random-secret-key-here"
  limiter: false
```

---

## 4. Ollama Remote LLM Setup

To host Ollama on an office GPU workstation and allow Lightsail to connect over Tailscale:

1. Install Ollama and pull the recommended model:
   ```bash
   ollama pull qwen2.5:7b-instruct
   ```
2. Bind Ollama to listen on all interfaces or your Tailscale IP:
   ```bash
   export OLLAMA_HOST=0.0.0.0:11434
   ollama serve
   ```
3. Set `LLM_BASE_URL=http://<tailscale-ip>:11434/v1` on your Lightsail instance.

---

## 5. Security Architecture

- **SSRF Protection**: Outbound page fetching validates resolved IP addresses to block AWS metadata endpoints (`169.254.169.254`), loopback (`127.0.0.1`), and internal RFC-1918 subnets (`10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`).
- **Image Proxy**: External profile photos from LinkedIn are streamed through `/api/v1/image-proxy` with strict host allowlisting and image type checks.
- **Resource Bounds**: Single uvicorn worker, max 20 jobs stored in memory, 2MB max page stream size, ensuring Lightsail RAM (~412MB) is never exceeded.

---

## 6. LinkedIn Datacenter vs. Residential IP Behavior

- **Residential IPs**: Public LinkedIn pages (`/company/<slug>`, `/in/<slug>`) return rich HTML containing Schema.org JSON-LD (`Organization`, `Person`) and OpenGraph metadata without authentication.
- **Datacenter IPs (AWS Lightsail, EC2, GCP)**: Datacenter IP ranges are recognized and blocked by Cloudflare bot protection (HTTP 403, `challenges.cloudflare.com`, Turnstile / "Just a moment...").
- **Best-Effort & Circuit Breaker**:
  - The pipeline never attempts to bypass or solve Cloudflare challenges.
  - When Cloudflare bot protection is detected, the diagnostic outcome is recorded as `blocked_by_bot_protection` with no retries beyond one.
  - After 3 consecutive blocks, an automated circuit breaker pauses LinkedIn requests for 30 minutes (`circuit_breaker_open`).
  - Screening reports plainly state in Tab 9 limitations: `"LinkedIn could not be retrieved from this server."`
- **Fallback**: The multi-source pipeline gathers company and founder details from official website deep crawls (sitemap, /team, /about), ICANN RDAP registration records, news/GDELT, and user-supplied manual evidence.
