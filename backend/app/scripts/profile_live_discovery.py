import subprocess
import time
import requests  # type: ignore[import-untyped]
import json
import threading
import sys

API_KEY = "test_production_api_key_32_characters_long_min"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
BASE_URL = "http://localhost/api/v1"

def get_free_m() -> dict[str, int]:
    out = subprocess.check_output(["free", "-m"], text=True)
    lines = out.strip().split("\n")
    mem_parts = lines[1].split()
    swap_parts = lines[2].split()
    return {
        "total": int(mem_parts[1]),
        "used": int(mem_parts[2]),
        "free": int(mem_parts[3]),
        "shared": int(mem_parts[4]),
        "buff_cache": int(mem_parts[5]),
        "available": int(mem_parts[6]),
        "swap_total": int(swap_parts[1]),
        "swap_used": int(swap_parts[2]),
        "swap_free": int(swap_parts[3]),
    }

print("=== 1. HOST MEMORY BEFORE JOB ===")
before = get_free_m()
print(f"Mem Total: {before['total']} MB | Used: {before['used']} MB | Available: {before['available']} MB | Free: {before['free']} MB | Buff/Cache: {before['buff_cache']} MB")
print(f"Swap Total: {before['swap_total']} MB | Swap Used: {before['swap_used']} MB | Swap Free: {before['swap_free']} MB")

# Start vmstat 1
vmstat_file = open("/tmp/vmstat.log", "w")
vmstat_proc = subprocess.Popen(["vmstat", "1"], stdout=vmstat_file, stderr=subprocess.DEVNULL)

# Start memory monitoring
samples: list[dict[str, int]] = []
stop_monitor = threading.Event()
def monitor() -> None:
    while not stop_monitor.is_set():
        try:
            samples.append(get_free_m())
        except Exception:
            pass
        time.sleep(0.2)

mon_thread = threading.Thread(target=monitor, daemon=True)
mon_thread.start()

# 2. Trigger Discovery Job
print("\n=== 2. SUBMITTING DISCOVERY JOB ===")
t_start = time.perf_counter()
submit_resp = requests.post(
    f"{BASE_URL}/discovery/jobs",
    headers=HEADERS,
    json={
        "company_name": "Discovery Mysa",
        "founder_names": ["Arpita Kapoor"],
        "confirmed_urls": {"company_website": "https://mysa.io"},
        "skip_llm_validation": True,
    },
)
print(f"Submit status: {submit_resp.status_code}")
submit_data = submit_resp.json()
job_id = submit_data.get("job_id")
print(f"Job ID: {job_id}")

# Poll job
status_data = {}
while True:
    time.sleep(1.0)
    poll_resp = requests.get(f"{BASE_URL}/discovery/jobs/{job_id}", headers=HEADERS)
    if poll_resp.status_code == 200:
        status_data = poll_resp.json()
        state = status_data.get("state")
        progress = status_data.get("progress")
        stage = status_data.get("stage")
        print(f"  [{(time.perf_counter()-t_start):.1f}s] State: {state}, Stage: {stage}, Progress: {progress*100:.0f}%")
        if state in ("succeeded", "partial", "failed"):
            break
    else:
        print(f"Poll error: {poll_resp.status_code}")
        break

t_end = time.perf_counter()
job_duration = t_end - t_start

# Stop monitoring
stop_monitor.set()
mon_thread.join(timeout=1.0)
vmstat_proc.terminate()
vmstat_file.close()

# 3. Host Memory After & Peak
after = get_free_m()
min_avail = min(s["available"] for s in samples) if samples else after["available"]
max_used = max(s["used"] for s in samples) if samples else after["used"]
max_swap_used = max(s["swap_used"] for s in samples) if samples else after["swap_used"]

print("\n=== 3. MEMORY TELEMETRY RESULTS ===")
print(f"Job Duration: {job_duration:.2f} seconds")
print(f"BEFORE: Total={before['total']} MB | Used={before['used']} MB | Available={before['available']} MB | Swap Used={before['swap_used']} MB")
print(f"PEAK:   Total={before['total']} MB | Max Used={max_used} MB | Min Available={min_avail} MB | Peak Swap Used={max_swap_used} MB")
print(f"AFTER:  Total={after['total']} MB | Used={after['used']} MB | Available={after['available']} MB | Swap Used={after['swap_used']} MB")
print(f"Available Headroom Consumed: {before['available'] - min_avail} MB (out of {before['available']} MB available, {min_avail} MB remained free at peak)")

# Parse vmstat
print("\n=== 4. VMSTAT SWAP ACTIVITY ===")
swap_activity_lines = []
with open("/tmp/vmstat.log") as f:
    for line in f:
        parts = line.split()
        if len(parts) >= 16 and parts[0].isdigit():
            si = int(parts[6])  # swap in
            so = int(parts[7])  # swap out
            if si > 0 or so > 0:
                swap_activity_lines.append(f"  si={si} KB/s, so={so} KB/s | {line.strip()}")

if swap_activity_lines:
    print(f"Found {len(swap_activity_lines)} vmstat samples with active swap I/O during job:")
    for l in swap_activity_lines[:10]:
        print(l)
else:
    print("Zero swap I/O detected during job execution (si=0, so=0 throughout entire run).")

# 5. Read back from API
result_slug = status_data.get("result_slug")
print(f"\n=== 5. DISCOVERY OUTPUT READBACK (slug=\"{result_slug}\") ===")
comp_resp = requests.get(f"{BASE_URL}/companies/{result_slug}")
print(f"GET /companies/{result_slug} -> HTTP {comp_resp.status_code}")
print(f"Company details: {comp_resp.json()}")

sec_nav_resp = requests.get(f"{BASE_URL}/companies/{result_slug}/sections")
print(f"GET /companies/{result_slug}/sections -> HTTP {sec_nav_resp.status_code}")
sections = sec_nav_resp.json().get("sections", [])
print(f"Sections count: {len(sections)}")

all_block_types = {}
for s in sections:
    s_key = s["key"]
    sec_resp = requests.get(f"{BASE_URL}/companies/{result_slug}/sections/{s_key}")
    s_data = sec_resp.json()
    blocks = s_data.get("blocks", [])
    b_types = [b[0] for b in blocks if isinstance(b, list) and len(b) > 0]
    all_block_types[s_key] = b_types
    print(f"  Section \"{s_key}\" ({s['title']}): {len(blocks)} blocks -> types: {b_types}")

print("\nBlock types summary across all sections:")
unique_types = set()
for bt_list in all_block_types.values():
    unique_types.update(bt_list)
print(f"Unique block types emitted: {sorted(list(unique_types))}")

# 6. DB Row Counts
print("\n=== 6. DATABASE ROW COUNTS IN POSTGRESQL ===")
db_counts_cmd = f"""docker exec vset-db-1 psql -U vset -d vset -t -c "
SELECT 'companies: ' || count(*) FROM companies WHERE slug = '{result_slug}'
UNION ALL
SELECT 'reports: ' || count(*) FROM reports WHERE company_id IN (SELECT id FROM companies WHERE slug = '{result_slug}')
UNION ALL
SELECT 'sections: ' || count(*) FROM sections WHERE report_id IN (SELECT id FROM reports WHERE company_id IN (SELECT id FROM companies WHERE slug = '{result_slug}'))
UNION ALL
SELECT 'action_items: ' || count(*) FROM action_items WHERE report_id IN (SELECT id FROM reports WHERE company_id IN (SELECT id FROM companies WHERE slug = '{result_slug}'))
UNION ALL
SELECT 'sources: ' || count(*) FROM sources WHERE report_id IN (SELECT id FROM reports WHERE company_id IN (SELECT id FROM companies WHERE slug = '{result_slug}'))
UNION ALL
SELECT 'raw_snapshots: ' || count(*) FROM raw_snapshots WHERE report_id IN (SELECT id FROM reports WHERE company_id IN (SELECT id FROM companies WHERE slug = '{result_slug}'));
" """
db_res = subprocess.check_output(db_counts_cmd, shell=True, text=True)
for line in db_res.strip().split("\n"):
    if line.strip():
        print(f"  {line.strip()}")
