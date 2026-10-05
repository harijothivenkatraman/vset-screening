# vSET Operations Guide

## Database Backup & Restore

### Automated Nightly Backup

The PostgreSQL database is backed up via `scripts/backup_postgres.sh`, which:
- Runs `pg_dump` via `docker exec` against the `vset-db-1` container
- Stores timestamped SQL dumps in `/home/ubuntu/backups/`
- Automatically removes backups older than 7 days

**Crontab setup** (run `crontab -e` on the Lightsail host):

```cron
0 2 * * * /home/ubuntu/vset/scripts/backup_postgres.sh >> /home/ubuntu/backups/backup.log 2>&1
```

### Manual Backup

```bash
cd /home/ubuntu/vset
./scripts/backup_postgres.sh                    # default: /home/ubuntu/backups/
./scripts/backup_postgres.sh /tmp/my-backups    # custom path
```

### Restore from Backup

```bash
./scripts/restore_postgres.sh /home/ubuntu/backups/vset_backup_20261004_020000.sql
```

The script:
- Verifies the backup file exists
- Asks for confirmation before restoring
- Pipes the SQL into `psql` via `docker exec`

### Testing Backup & Restore

```bash
./scripts/test_backup_restore.sh
```

Creates a temporary `vset_test` database, restores the latest backup into it, verifies row counts match, then cleans up.

### Retention Policy

| Item | Value |
|------|-------|
| Schedule | Nightly at 02:00 UTC |
| Retention | 7 days |
| Storage | `/home/ubuntu/backups/` |
| Format | Plain SQL (`pg_dump` output) |
| Naming | `vset_backup_YYYYMMDD_HHMMSS.sql` |

### Off-Box Backup Strategy

To protect against instance failure or hypervisor loss:

1. **AWS Lightsail Automatic Snapshots (Recommended)**:
   - In AWS Lightsail Console -> Instance -> **Snapshots** tab
   - Enable **Automatic Snapshots** set to `03:00 UTC` (1 hour after the 02:00 UTC PostgreSQL dump)
   - AWS automatically keeps the 7 most recent daily snapshots off-box across AWS availability zones.
   - CLI command:
     ```bash
     aws lightsail enable-auto-snapshot \
       --resource-name <instance-name> \
       --auto-snapshot-add-on-request snapshotTimeOfDay="03:00"
     ```

2. **Encrypted Off-Box Archive (S3 / Object Storage)**:
   - Backups can be encrypted with AES-256 before shipping:
     ```bash
     openssl enc -aes-256-cbc -salt -pbkdf2 -in /home/ubuntu/backups/vset_backup_YYYYMMDD_HHMMSS.sql \
       -out /home/ubuntu/backups/vset_backup_YYYYMMDD_HHMMSS.sql.enc -pass pass:$BACKUP_ENCRYPTION_KEY
     ```
   - Sync to off-box bucket (e.g. via `aws s3 cp` or `s3cmd`):
     ```bash
     aws s3 cp /home/ubuntu/backups/vset_backup_*.sql.enc s3://vset-encrypted-backups/ --sse AES256
     ```

---

## HTTPS & Domain Setup

See [docs/deployment.md](deployment.md) for:
- Assigning a domain to the Lightsail instance
- Enabling automatic HTTPS via Caddy + Let's Encrypt
- Static IP configuration
- CORS origin configuration

### Quick Steps

1. Assign a static IP in Lightsail console
2. Point your domain's A record to the static IP
3. Edit `frontend/Caddyfile`: replace `:80` with `yourdomain.com`
4. Rebuild and restart: `docker compose up -d --build web`
5. Caddy automatically provisions a TLS certificate

---

## Security: API Key Management

### Key Types

| Key | Environment Variable | Purpose |
|-----|---------------------|---------|
| Admin | `IMPORT_API_KEY` | POST/DELETE operations (discovery, import, delete) |
| Read | `READ_API_KEY` | GET operations (optional; unset = public read) |

### Rotating Keys

1. Generate a new key: `openssl rand -base64 48`
2. Update `.env` on the Lightsail host
3. Restart the backend: `docker restart vset-backend-1`
4. Update the admin key in the discovery page's "Admin API Key" field

### Production Requirements
- `IMPORT_API_KEY` must be ≥ 32 characters
- Must not contain default/example patterns
- `READ_API_KEY` can be left unset for public read access
- Never bake keys into the frontend build

---

## Container Management

```bash
# Check container status
docker ps

# View logs
docker logs vset-backend-1 --tail 50
docker logs vset-web-1 --tail 50
docker logs vset-db-1 --tail 50

# Restart services
docker restart vset-backend-1
docker restart vset-web-1

# Full rebuild
cd /home/ubuntu/vset
docker compose up -d --build

# Check memory usage
docker stats --no-stream
free -m
```

---

## Monitoring

### Health Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health` | None | Database connectivity |
| `GET /api/v1/discovery/health` | None | LLM, disk, search provider status |

### Key Metrics to Watch

- **Memory**: `free -m` — available should stay above 50 MB
- **Disk**: `df -h` — keep > 2 GB free
- **Swap**: `vmstat 1 5` — monitor `si`/`so` columns
- **Container health**: `docker ps` — all should show `(healthy)`

---

## Persistent SSH Reverse Tunnel (Ollama LLM Bridge)

To provide LLM capabilities to the 512 MB Lightsail instance without running memory-intensive models on the host, a reverse SSH tunnel forwards port `11434` from Lightsail to the GPU/workstation running Ollama.

### 1. Workstation Loop (Windows PowerShell)

Use `scripts/keep_tunnel.ps1`:
```powershell
.\scripts\keep_tunnel.ps1 -KeyPath "$HOME\.ssh\vset-key.pem" -HostIp "13.206.229.40"
```
The script monitors the connection with `ServerAliveInterval=30` and `ExitOnForwardFailure=yes`, automatically reconnecting if disconnected.

### 2. Linux Systemd Service (`/etc/systemd/system/vset-tunnel.service`)

On an external Linux server or jump host:
```ini
[Unit]
Description=vSET Reverse SSH Tunnel for Ollama
After=network.target

[Service]
Type=simple
User=localuser
ExecStart=/usr/bin/ssh -i /home/localuser/.ssh/vset-key.pem -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -N -R 0.0.0.0:11434:127.0.0.1:11434 ubuntu@13.206.229.40
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vset-tunnel.service
```

### 3. Behavior When Office PC Is Offline

When the tunnel is disconnected or the office PC is powered off:
- `GET /api/v1/discovery/health` returns `llm_reachable: false`, `model_available: false`.
- The Discovery UI displays a non-blocking warning notice:
  *"Report will be assembled without the language model; some fields may be less complete."*
- Discovery jobs automatically proceed using **rules-first extraction**:
  - Deterministic heuristics for website structure, JSON-LD, OpenGraph tags, and meta descriptors.
  - Regex date and title segmenters for career and education timelines.
  - Primary action button remains fully enabled and screening completes end-to-end without errors.

---

## LLM Model Configuration & Evaluation

### Models Evaluated on Mysa Screening Benchmark

| Metric / Dimension | `qwen2.5:0.5b` | `qwen2.5:7b-instruct` (Default) |
| :--- | :--- | :--- |
| **Parameter Size** | 494M parameters (397 MB GGUF) | 7.6B parameters (4.7 GB GGUF) |
| **Extraction Latency** | ~2–5 seconds per section | ~15–20 seconds per section |
| **Schema Compliance** | Prone to dropping keys or emitting malformed JSON | Strict adherence to JSON schema output |
| **Timeline Accuracy** | Occasionally truncates multi-role tenures | Faithful chronological extraction of career & education |
| **Narrative Synthesis** | Brief, fragmented bullet points | Coherent executive summaries & market positioning |
| **Ground Truth Accuracy** | 6 / 9 benchmark fields matched | **9 / 9 benchmark fields matched** |

**Conclusion**: `qwen2.5:7b-instruct` is configured as the production default for rich screening reports.

### Per-Task Model Configuration

The API supports per-task override of the LLM model via `POST /api/v1/discovery/jobs`:
```json
{
  "company_name": "Mysa",
  "founder_names": ["Arpita Kapoor", "Mohit Rangaraju", "Ashutosh Panigrahi"],
  "llm_model": "qwen2.5:7b-instruct"
}
```
If omitted, it defaults to the host's configured `LLM_MODEL` environment variable.

---

## Line Endings

All shell scripts in `scripts/` must use LF line endings (not CRLF).
If editing on Windows, verify with: `file scripts/*.sh`
Convert if needed: `dos2unix scripts/*.sh`
