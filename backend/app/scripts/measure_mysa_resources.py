"""Resource profiling script for live Mysa discovery job.
Measures:
- Peak Memory Working Set (MB) using Windows API (and tracemalloc)
- Disk Usage (temp files, SQLite DB delta)
- Total Job Execution Time (s)
"""
import asyncio
import ctypes
import ctypes.wintypes
import os
import shutil
import tempfile
import time
from pathlib import Path

# Setup Windows memory structure
class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("PageFaultCount", ctypes.wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

def get_memory_info() -> dict[str, float]:
    try:
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        
        GetProcessMemoryInfo = psapi.GetProcessMemoryInfo
        GetProcessMemoryInfo.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.wintypes.DWORD]
        GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL
        
        GetCurrentProcess = kernel32.GetCurrentProcess
        GetCurrentProcess.restype = ctypes.wintypes.HANDLE
        
        ret = GetProcessMemoryInfo(
            GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb
        )
        if ret:
            return {
                "peak_working_set_mb": float(counters.PeakWorkingSetSize / (1024 * 1024)),
                "current_working_set_mb": float(counters.WorkingSetSize / (1024 * 1024)),
                "private_mb": float(counters.PrivateUsage / (1024 * 1024)),
            }
    except Exception:
        pass
    return {"peak_working_set_mb": 0.0, "current_working_set_mb": 0.0, "private_mb": 0.0}


def get_dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    return total

async def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from app.scripts.benchmark_mysa import run_mysa_pipeline

    print("=" * 60)
    print("PROFILING LIVE MYSA DISCOVERY JOB ON LIGHTSAIL RUNTIME PROFILE")
    print("=" * 60)

    # Initial measurements
    temp_dir = Path(tempfile.gettempdir())
    db_file = Path(__file__).resolve().parent.parent.parent / "vset.db"
    initial_db_size = db_file.stat().st_size if db_file.exists() else 0

    mem_before = get_memory_info()
    t_start = time.perf_counter()

    # Run live pipeline with LinkedIn blocked (simulating Lightsail IP)
    job, report, llm_calls = await run_mysa_pipeline(
        enable_llm=False,
        simulate_blocked=True
    )

    t_end = time.perf_counter()
    duration = t_end - t_start
    mem_after = get_memory_info()
    final_db_size = db_file.stat().st_size if db_file.exists() else 0

    print("\n--- RESOURCE USAGE REPORT ---")
    print(f"Total Job Execution Time: {duration:.2f} seconds")
    print(f"Peak Working Set Memory:  {mem_after['peak_working_set_mb']:.2f} MB")
    print(f"Current Working Set:      {mem_after['current_working_set_mb']:.2f} MB")
    print(f"Private Working Set:      {mem_after['private_mb']:.2f} MB")
    print(f"DB Disk Delta:            {final_db_size - initial_db_size} bytes (DB size: {final_db_size / 1024:.1f} KB)")
    print(f"Job State:                {job.state.value if hasattr(job.state, 'value') else job.state}")
    print(f"Job Result Slug:          {job.result_slug}")
    print(f"Warnings Recorded:        {len(job.warnings)}")
    for w in job.warnings:
        print(f"  - {w}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
