# vSET Production Deployment Guide

This directory contains automation scripts and operational guidelines for deploying and maintaining the **vSET Dashboard** on a single Ubuntu Linux server (e.g. AWS Lightsail 2 GB RAM) using Docker Compose and Caddy.

---

## 1. Quickstart (First-Time Setup)

### Prerequisites
- Ubuntu 22.04 or 24.04 LTS
- Docker and Docker Compose v2+ installed
- Domain DNS record pointed to server IP (for automatic HTTPS)

### Steps

1. **Clone the repository and enter directory:**
   ```bash
   git clone <repository_url> vset
   cd vset
   ```

2. **Configure production environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and configure:
   - `DOMAIN`: Set to your public domain (e.g. `vset.example.com`). Caddy will automatically manage TLS certificates via Let's Encrypt / ZeroSSL. (For local testing, use `http://localhost`).
   - `POSTGRES_PASSWORD`: Generate via `openssl rand -hex 24`.
   - `IMPORT_API_KEY`: Generate via `openssl rand -hex 32` (must be at least 32 characters in production).
   - `ENVIRONMENT=production`
   - `BASIC_AUTH_USER` & `BASIC_AUTH_HASH` (optional): If basic auth gate is needed.

3. **Launch the application stack:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify container health:**
   ```bash
   docker compose ps
   curl -i http://localhost/health
   ```
   Both `backend` and `db` will show `healthy`, and Caddy will route incoming web traffic securely.

---

## 2. Operations and Management

### 3 Primary Operational Commands

| Task | Command |
|---|---|
| **Deploy updates** | `./deploy/update.sh` |
| **Create backup** | `./deploy/backup.sh` |
| **Restore database** | `./deploy/restore.sh backups/vset_YYYYMMDD_HHMMSS.sql.gz` |

### Backups & Retention
- `./deploy/backup.sh` dumps the Postgres database via `pg_dump`, compresses it with `gzip`, and stores it under `./backups/`.
- It automatically cleans up backup files older than 7 days.
- You can automate daily backups via cron:
  ```bash
  0 2 * * * /path/to/vset/deploy/backup.sh >> /var/log/vset-backup.log 2>&1
  ```

### Restoring a Backup
- To test restoration in an isolated database without touching production:
  ```bash
  ./deploy/restore.sh backups/vset_20260930_120000.sql.gz vset_restore_test
  ```
- To restore directly into production (`vset`), the script prompts for interactive confirmation:
  ```bash
  ./deploy/restore.sh backups/vset_20260930_120000.sql.gz
  ```

---

## 3. Ingesting New Company Reports

To import a new company screening report into the running database without restarting or redeploying:

Send an authenticated HTTP POST request to the import route:

```bash
curl -X POST "https://vset.yourdomain.com/api/v1/reports/import" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <YOUR_SECURE_32_CHAR_IMPORT_API_KEY>" \
  -d @path/to/company_screen.json
```

### Security & Idempotency Notes
- The endpoint is protected with `X-API-Key`. In production, keys shorter than 32 characters or default passwords will be rejected with HTTP 500.
- Key comparison uses constant-time `hmac.compare_digest` to prevent timing attacks.
- The import operation is idempotent: re-importing the identical report content returns `"status": "unchanged"`.
