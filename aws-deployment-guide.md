# vSET — Detailed AWS Lightsail Setup (Click-by-Click)

---

## Phase 1: AWS Account (Skip if you already have one)

### 1.1 Create an AWS Account

1. Open your browser and go to **https://aws.amazon.com**
2. Click the orange **"Create an AWS Account"** button (top-right)
3. Fill in:
   - **Email address**: your email
   - **AWS account name**: anything (e.g. `vset-production`)
4. Click **Verify email address** → check your inbox for the verification code → enter it
5. Set a **Root user password** (save it in a password manager)
6. Choose **Personal** account type
7. Fill in your name, phone number, and address
8. **Payment method**: enter a credit or debit card (you won't be charged for Lightsail's free-tier eligible plans for the first 3 months)
9. **Identity verification**: AWS will call or text your phone with a code → enter it
10. **Support plan**: select **Basic support — Free**
11. Click **Complete sign up**
12. Wait 1–2 minutes, then click **Go to the AWS Management Console**
13. Sign in with the email and password you just created

---

## Phase 2: Create the Lightsail Instance

### 2.1 Open Lightsail

1. In the AWS Console, click the **search bar** at the top
2. Type **`Lightsail`**
3. Click **Amazon Lightsail** from the results
4. You'll land on the Lightsail home page. If this is your first time, click **"Let's get started"** or you'll see the instances dashboard directly.

### 2.2 Select Region — Mumbai

1. Look at the **top-right** of the Lightsail page — you'll see a region name (e.g. "Virginia")
2. Click it to open the region dropdown
3. Select **Asia Pacific (Mumbai)**
4. Under Availability Zone, leave the default (e.g. `ap-south-1a`) — it doesn't matter

### 2.3 Create an Instance

1. Click the **"Create instance"** button

2. **Select a platform:**
   - You'll see two options: `Linux/Unix` and `Microsoft Windows`
   - Click **Linux/Unix** (it should already be selected — the box will have an orange border)

3. **Select a blueprint:**
   - You'll see two tabs: `Apps + OS` and `OS Only`
   - Click the **"OS Only"** tab
   - You'll see icons for Amazon Linux, Ubuntu, Debian, etc.
   - Click **Ubuntu 24.04 LTS**
   - (If 24.04 isn't shown, **Ubuntu 22.04 LTS** works too)

### 2.4 Create an SSH Key Pair

1. Scroll down to the **"SSH key pair manager"** section
2. You'll see either "Default" or a key listed
3. Click **"Change SSH key pair"**
4. Click **"Create new"**
5. In the popup:
   - **Region**: should show `ap-south-1` (Mumbai) — don't change it
   - **Key pair name**: type **`vset-key`**
6. Click **"Generate key pair"**
7. A yellow box appears with the private key text
8. **Click "Download key"** — this saves `vset-key.pem` to your Downloads folder
   
> [!CAUTION]
> **You can only download this key ONCE.** If you lose it, you'll need to create a new key pair. Save it safely.

9. Click the **"X"** or **"Close"** to close the popup
10. Verify that `vset-key` now appears as the selected SSH key

### 2.5 Choose an Instance Plan

Scroll down to **"Choose your instance plan"**. You'll see pricing tiers:

| Plan | RAM | vCPU | SSD | Price | Free Tier |
|---|---|---|---|---|---|
| $3.50/mo | 512 MB | 1 | 20 GB | Too small | 3 months free |
| **$5/mo** | **1 GB** | **1** | **40 GB** | **Minimum viable** | **3 months free** |
| **$10/mo ★** | **2 GB** | **1** | **60 GB** | **Recommended** | **3 months free** |
| $20/mo | 4 GB | 2 | 80 GB | Overkill | 3 months free |

**Click the $10/month plan** (2 GB). The Docker build needs ~1.5 GB during compilation. The $5 plan can work but may run into memory pressure during the initial build.

> [!NOTE]
> Plans marked "First 3 months free" mean you pay $0 for the first 90 days if your AWS account is new. After that it's $10/month (~₹830/month).

### 2.6 Name Your Instance

1. Scroll down to **"Identify your instance"**
2. Delete the default name
3. Type: **`vset-server`**

### 2.7 Create It

1. Click the orange **"Create instance"** button at the bottom
2. You'll be taken back to the instances page
3. You'll see `vset-server` with status **"Pending"**
4. Wait ~60 seconds — it will change to **"Running"** with a green dot

---

## Phase 3: Static IP + Firewall

### 3.1 Attach a Static IP

Without a static IP, your server's IP address changes every time it reboots.

1. Click on **"vset-server"** to open its detail page
2. Click the **"Networking"** tab
3. Under **"IPv4 networking"**, you'll see the section "Public IPv4 address"
4. Click **"Attach static IP"** (or **"Create static IP"**)
5. In the popup:
   - **Static IP name**: type **`vset-static-ip`**
   - **Instance**: should show `vset-server` already selected
6. Click **"Create and attach"**
7. You'll now see a static IP address displayed, e.g. **`13.232.45.67`**

**Write this IP address down** — you'll need it for SSH and DNS.

> [!TIP]
> The static IP is free as long as it's attached to a running instance. If you delete the instance but keep the static IP floating (unattached), AWS charges ~$0.005/hour.

### 3.2 Configure the Firewall

Still on the **"Networking"** tab, scroll down to **"IPv4 Firewall"**.

You should see SSH (port 22) already listed. Add HTTP and HTTPS:

1. Click **"+ Add rule"**
2. In the dropdown, select **HTTP** → this auto-fills port **80**
3. Click **"Create"**
4. Click **"+ Add rule"** again
5. Select **HTTPS** → this auto-fills port **443**
6. Click **"Create"**

Your firewall should now show:

| Application | Protocol | Port | Source |
|---|---|---|---|
| SSH | TCP | 22 | Any IPv4 address |
| HTTP | TCP | 80 | Any IPv4 address |
| HTTPS | TCP | 443 | Any IPv4 address |

---

## Phase 4: (Optional) Point a Domain

### If you have a domain

Go to your domain's DNS management (Cloudflare, Namecheap, GoDaddy, Route53, etc.):

1. **Add an A record:**
   - **Type**: `A`
   - **Name**: `vset` (this creates `vset.yourdomain.com`) — or `@` for the root domain
   - **Value**: your static IP (e.g. `13.232.45.67`)
   - **TTL**: 300 (or "Auto")
   - **Proxy**: OFF / DNS Only (if using Cloudflare, set the cloud icon to grey/DNS-only)
2. Click **Save**
3. DNS propagation takes 1–30 minutes

### If you don't have a domain

That's fine. You'll use `DOMAIN=http://<your-static-ip>` in the config. You won't get HTTPS, but everything else works.

---

## Phase 5: Connect to the Server via SSH

### 5.1 From Windows PowerShell

Open **PowerShell** on your Windows PC and run these commands:

```powershell
# Step 1: Move the key to your .ssh folder (run once)
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force
Move-Item -Path "$env:USERPROFILE\Downloads\vset-key.pem" -Destination "$env:USERPROFILE\.ssh\vset-key.pem" -Force

# Step 2: Fix file permissions (required by SSH)
icacls "$env:USERPROFILE\.ssh\vset-key.pem" /inheritance:r /grant:r "${env:USERNAME}:(R)"

# Step 3: Connect (replace YOUR_IP with the static IP from step 3.1)
ssh -i "$env:USERPROFILE\.ssh\vset-key.pem" ubuntu@YOUR_IP
```

The first time it asks `Are you sure you want to continue connecting?` → type **`yes`** and press Enter.

**Success looks like:**
```
Welcome to Ubuntu 24.04 LTS ...
ubuntu@ip-172-26-5-123:~$
```

You are now on the server. All remaining commands run here.

### 5.2 Alternative: Browser SSH

If PowerShell SSH gives trouble, use the **Lightsail browser terminal**:

1. Go to the Lightsail instances page
2. Click the orange **terminal icon** (⬛) next to `vset-server`
3. A black terminal window opens in your browser — no key file needed

---

## Phase 6: Install Docker on the Server

Run these commands **on the server** (in the SSH terminal):

### 6.1 Install Docker Engine and Compose v2

```bash
curl -fsSL https://get.docker.com | sudo sh
```

This takes ~30 seconds. You'll see output ending with something like:
```
Client: Docker Engine - Community
 Version:           29.x.x
...
```

### 6.2 Add your user to the docker group

```bash
sudo usermod -aG docker ubuntu
```

### 6.3 Apply the group change (log out and back in)

```bash
exit
```

Then reconnect:

```powershell
ssh -i "$env:USERPROFILE\.ssh\vset-key.pem" ubuntu@YOUR_IP
```

(Or reopen the browser terminal.)

### 6.4 Verify Docker works

```bash
docker version
```

You should see both **Client** and **Server** sections (no error). If you see "permission denied", you didn't log out and back in after step 6.2.

```bash
docker compose version
```

Should show `Docker Compose version v2.x.x`.

---

## Phase 7: Deploy the vSET Application

### 7.1 Clone the repository

```bash
git clone https://github.com/harijothivenkatraman/vset-screening.git vset
cd vset
```

### 7.2 Generate secrets

Run these two commands and **copy each output** (select the text, it's a long hex string):

```bash
echo "=== POSTGRES_PASSWORD ==="
openssl rand -hex 24

echo "=== IMPORT_API_KEY ==="
openssl rand -hex 32
```

Example output (yours will be different):
```
=== POSTGRES_PASSWORD ===
a3f9c1d28e7b4a5601f2d83c7e9b6a4d01285f73e9c4d2a1
=== IMPORT_API_KEY ===
7c2e9f4a81b3d56072e8c1a943f7b2d50618e3c9a4f2b7d831c5e0a692f4d8b1
```

### 7.3 Create the .env file

```bash
cp .env.example .env
nano .env
```

In `nano`, edit each line. Here is what the file should look like when you're done:

**If you HAVE a domain** (e.g. `vset.yourdomain.com`):
```ini
DOMAIN=vset.yourdomain.com
POSTGRES_PASSWORD=a3f9c1d28e7b4a5601f2d83c7e9b6a4d01285f73e9c4d2a1
IMPORT_API_KEY=7c2e9f4a81b3d56072e8c1a943f7b2d50618e3c9a4f2b7d831c5e0a692f4d8b1
CORS_ORIGINS=[]
ENVIRONMENT=production
WEB_CONCURRENCY=1
BASIC_AUTH_USER=
BASIC_AUTH_HASH=
```

**If you DON'T have a domain** (using raw IP):
```ini
DOMAIN=http://13.232.45.67
POSTGRES_PASSWORD=a3f9c1d28e7b4a5601f2d83c7e9b6a4d01285f73e9c4d2a1
IMPORT_API_KEY=7c2e9f4a81b3d56072e8c1a943f7b2d50618e3c9a4f2b7d831c5e0a692f4d8b1
CORS_ORIGINS=[]
ENVIRONMENT=production
WEB_CONCURRENCY=1
BASIC_AUTH_USER=
BASIC_AUTH_HASH=
```

> [!IMPORTANT]
> - Replace the sample hex strings above with YOUR actual outputs from step 7.2.
> - For `DOMAIN` with a raw IP, you MUST include `http://` prefix. For a real domain name, do NOT include `https://` — Caddy adds it automatically.

**How to edit in nano:**
- Use arrow keys to move the cursor
- Delete characters with Backspace
- Type new text normally
- When done: press **Ctrl+O** (that's the letter O, not zero), then **Enter** to save
- Press **Ctrl+X** to exit nano

### 7.4 Build and start everything

```bash
docker compose up -d --build
```

**This is the big step.** It will:
1. Pull base images (`postgres:16-alpine`, `python:3.12-slim`, `node:20-alpine`, `caddy:2-alpine`)
2. Build the backend container (install Python dependencies)
3. Build the frontend container (install npm packages, compile TypeScript, bundle with Vite)
4. Start all three services

**First run takes 3–8 minutes.** You'll see lots of output. Wait until you see:
```
 ✔ Network vset_default       Created
 ✔ Volume "vset_db_data"      Created
 ✔ Volume "vset_caddy_data"   Created
 ✔ Volume "vset_caddy_config" Created
 ✔ Container vset-db-1        Healthy
 ✔ Container vset-backend-1   Healthy
 ✔ Container vset-web-1       Started
```

### 7.5 Verify all services are healthy

```bash
docker compose ps
```

**What you want to see:** All three services listed, `db` and `backend` showing `(healthy)`:

```
NAME              SERVICE    STATUS                    PORTS
vset-db-1         db         Up X minutes (healthy)    5432/tcp
vset-backend-1    backend    Up X minutes (healthy)    8000/tcp
vset-web-1        web        Up X minutes              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

> [!WARNING]
> If `backend` shows `(health: starting)`, wait 30 seconds and run `docker compose ps` again. It needs time for the healthcheck.
>
> If `backend` shows `(unhealthy)`, check logs:
> ```bash
> docker compose logs backend
> ```

### 7.6 Quick health test

```bash
curl http://localhost/health
```

**Expected output:**
```json
{"status":"ok","environment":"production"}
```

### 7.7 Verify both companies are loaded

```bash
curl -s http://localhost/api/v1/companies | python3 -m json.tool
```

**Expected:** JSON response showing both TerraSpark and Mysa companies.

---

## Phase 8: Access the Dashboard in Your Browser

### With a domain
Open: **`https://vset.yourdomain.com`**

The first request takes ~10 seconds while Caddy obtains the TLS certificate from Let's Encrypt. After that, it's instant.

### Without a domain (raw IP)
Open: **`http://YOUR_STATIC_IP`** (e.g. `http://13.232.45.67`)

---

## What to Tell Me Next

Once you've completed these steps, come back and tell me:

1. ✅ or ❌ — did `docker compose ps` show all three healthy?
2. ✅ or ❌ — did `curl http://localhost/health` return `{"status":"ok"}`?
3. ✅ or ❌ — can you see the dashboard in your browser?
4. Your server's static IP or domain

I'll then walk you through the **full 8-step live verification suite** (health failover, import idempotency, persistence, backup/restore, basic auth) using real commands on your running server.

---

## Troubleshooting Quick Reference

| Problem | Fix |
|---|---|
| `docker: permission denied` | You forgot to log out and back in after `sudo usermod -aG docker ubuntu` |
| Backend `unhealthy` | Run `docker compose logs backend` and share the output |
| `curl: (7) Failed to connect to localhost port 80` | Web container isn't running — check `docker compose ps` and `docker compose logs web` |
| Browser shows "connection refused" | Firewall ports 80/443 not open in Lightsail Networking tab |
| Browser shows "SSL error" / certificate warning | DNS not propagated yet (wait 5–30 min), or `DOMAIN` in `.env` doesn't match your actual domain |
| Build fails with "killed" or OOM | Instance has too little RAM — upgrade to the $10/month (2 GB) plan |
| `nano` not found | Run `sudo apt update && sudo apt install nano -y` |
