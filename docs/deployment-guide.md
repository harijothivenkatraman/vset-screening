# Complete Step-by-Step Free-of-Cost Deployment Guide

This guide provides a comprehensive, beginner-friendly, zero-cost walkthrough to deploy the entire **vSET Startup Screening Application** (FastAPI backend + React frontend + Database) to the public internet using 100% free cloud tiers with **no credit card required**.

---

## Architecture Overview (100% Free Tier Stack)

```
┌─────────────────────────────────┐
│        Vercel (Frontend)        │  100% Free Edge CDN
│   React + TypeScript + Tailwind │  Unlimited Bandwidth (Hobby)
│  https://vset-ui.vercel.app     │  Automatic SSL & Git Previews
└────────────────┬────────────────┘
                 │
                 │ HTTPS API Calls (VITE_API_BASE_URL)
                 ▼
┌─────────────────────────────────┐
│         Render (Backend)        │  100% Free Web Service
│     Python FastAPI + Uvicorn    │  750 Free Instance Hours/Month
│ https://vset-api.onrender.com   │  Automatic SSL & Health Monitoring
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│       Database (Two Choices)    │
│  A) Built-in SQLite (Default)   │  Free, Zero Configuration
│  B) Neon.tech Serverless Postgres│  Free, 0.5 GB Serverless DB
└─────────────────────────────────┘
```

---

## Prerequisites (All Free)

1. A **GitHub Account**: [github.com](https://github.com)
2. A **Render Account**: [render.com](https://render.com) (Sign up with GitHub — *no credit card needed*)
3. A **Vercel Account**: [vercel.com](https://vercel.com) (Sign up with GitHub — *no credit card needed*)

---

## Step 1: Push Your Code to GitHub

If you haven't pushed the project to GitHub yet, follow these quick terminal commands from your project root:

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "feat: complete vSET dashboard with redesigned UI and deployment configs"

# Create a new repository on GitHub (e.g. named 'vset-screening')
# Then link your remote and push (replace YOUR_USERNAME with your GitHub handle):
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vset-screening.git
git push -u origin main
```

---

## Step 2: Deploy the Backend to Render (Free)

Render provides a permanently free tier for Python web services.

### Option 2A: Manual Setup via Render Dashboard (Recommended)

1. Log in to [dashboard.render.com](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Choose **Build and deploy from a Git repository** and connect your GitHub repository (`vset-screening`).
4. Configure the service settings:
   - **Name**: `vset-api` (or any unique name you choose)
   - **Region**: Choose the closest region (e.g., `Frankfurt (EU)` or `Ohio (US)`)
   - **Branch**: `main`
   - **Root Directory**: `backend` *(Crucial: tell Render your Python code lives in the `backend/` folder)*
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python seed.py
     ```
     *(This installs dependencies and seeds the baseline reports for TerraSpark and Mysa into SQLite automatically!)*
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: Select **Free** ($0/month).

5. Scroll down to **Environment Variables** and add the following:
   | Key | Value | Notes |
   |---|---|---|
   | `ENVIRONMENT` | `production` | Enables production mode |
   | `CORS_ORIGINS` | `["*"]` | Allows frontend requests |
   | `DATABASE_URL` | `sqlite+aiosqlite:///./vset.db` | Uses local SQLite file |
   | `IMPORT_API_KEY` | `vset-secret-admin-key-2026` | Custom admin key for `/api/v1/import` |

6. Click **Create Web Service**.
7. Wait 2–3 minutes for the build to finish. Once live, Render gives you a public URL like:
   `https://vset-api-xxxx.onrender.com`

8. **Verify your backend**:
   - Open `https://vset-api-xxxx.onrender.com/health` in your browser. You should see:
     ```json
     {"status": "ok", "environment": "production"}
     ```
   - Open `https://vset-api-xxxx.onrender.com/docs` to see the interactive Swagger API documentation.
   - Open `https://vset-api-xxxx.onrender.com/api/v1/companies` to verify that TerraSpark and Mysa are seeded!

---

## Step 3 (Optional): Add Free Serverless PostgreSQL via Neon.tech

If you want a managed cloud database that persists independently across deployments:

1. Sign up for free at [neon.tech](https://neon.tech) (*no credit card required*).
2. Click **Create Project** (e.g. named `vset-db`).
3. Neon will display your connection string, which looks like:
   `postgresql://neondb_owner:password@ep-cool-sample.aws.neon.tech/neondb?sslmode=require`
4. In your Render backend dashboard:
   - Go to **Environment** tab.
   - Update `DATABASE_URL` with your Neon connection string.
   - *(Note: Our `backend/app/config.py` automatically converts `postgresql://` to `postgresql+asyncpg://` so it works seamlessly with async SQLAlchemy!)*
5. Trigger **Manual Deploy > Clear build cache & deploy**. The build command `python seed.py` will automatically create the PostgreSQL tables and seed the initial company records.

---

## Step 4: Deploy the Frontend to Vercel (Free)

Vercel provides free, high-performance edge hosting with automatic SSL for React/Vite SPAs.

1. Log in to [vercel.com](https://vercel.com/).
2. Click **Add New... > Project**.
3. Import your GitHub repository (`vset-screening`).
4. In the configuration screen:
   - **Project Name**: `vset-dashboard` (or your choice)
   - **Framework Preset**: `Vite` (automatically detected)
   - **Root Directory**: Click **Edit** and select `frontend` *(Crucial: your React code lives in `frontend/`)*.
5. In **Build and Output Settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
6. Expand **Environment Variables** and add:
   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://vset-api-xxxx.onrender.com/api/v1` |

   *(Replace `https://vset-api-xxxx.onrender.com` with your real Render backend URL from Step 2. Make sure to append `/api/v1`!)*

7. Click **Deploy**.
8. In ~45 seconds, Vercel will complete the build and assign you a free production domain, e.g.:
   `https://vset-dashboard-xxxx.vercel.app`

*(Note: We already created `frontend/vercel.json` with SPA routing rewrites, so refreshing pages like `/companies/terraspark/competition` will load smoothly without 404 errors!)*

---

## Step 5: Test and Verify Your Live App

1. Visit your Vercel URL: `https://vset-dashboard-xxxx.vercel.app`.
2. **Company Switcher**:
   - Click the company dropdown at the top.
   - Search for **Mysa** or **TerraSpark**. Use keyboard arrows and Enter to switch.
3. **Verify Sections**:
   - **Key facts & context**: Inspect the FactGrid and chronological Timeline.
   - **Founder & team**: Inspect the 3 founder cards (TerraSpark) or 2 founder cards (Mysa) with Founder-Market fit callouts.
   - **Competitive landscape**: Inspect the 2-column comparison layout (TerraSpark) and the sticky focal matrix table (Mysa).
   - **Funding history**: Inspect the funding cards with hero amounts and comma-split investor chips.
   - **Investor questions & information to prepare**: Inspect the neutral Concerns banner and collapsible topic accordions with Expand/Collapse all.
   - **About this screen & sources**: Inspect the numbered source cards (`S1`, `S2`) with external link pills.
4. **Mobile Responsiveness**:
   - Open DevTools (F12) or open on a mobile phone: verify the hamburger navigation, stacked fact bar, and single-column cards.

---

## Alternative: 1-Click Render Blueprint (`render.yaml`)

We have included a [`render.yaml`](file:///F:/dev/Vset/render.yaml) in the root of the project. If you prefer to deploy via Render's Blueprint feature:

1. In Render, click **New + > Blueprint**.
2. Connect your GitHub repository.
3. Render will parse `render.yaml` and configure the backend service automatically.
4. Click **Apply**.

---

## Pro-Tips for Free Tier Hosting

### 1. Free Spin-Down Sleep Prevention (Optional)
Render's free tier spins down web services after 15 minutes of inactivity. When a new visitor arrives, it takes ~30 seconds for the first request ("cold start").
- **Solution (100% Free)**: Set up a free monitor on [uptimerobot.com](https://uptimerobot.com) or [cron-job.org](https://cron-job.org) to ping your backend health endpoint (`https://vset-api-xxxx.onrender.com/health`) every 10 minutes. This keeps the service warm and responsive 24/7!

### 2. Custom Domain (Free SSL)
Both Vercel and Render support adding custom domains (e.g. `screening.yourdomain.com`) completely free of charge with automatic Let's Encrypt SSL certificates.
- In Vercel: Go to **Settings > Domains** and add your domain CNAME record.
- In Render: Go to **Settings > Custom Domains** and add your domain CNAME record.

### 3. Adding New Company Reports
To ingest a new company screen report into the live database without redeploying:
Send a POST request to your backend:
```bash
curl -X POST "https://vset-api-xxxx.onrender.com/api/v1/import" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vset-secret-admin-key-2026" \
  -d @path/to/new_company_screen.json
```
The new company will immediately become searchable and selectable in your live Vercel dashboard!
