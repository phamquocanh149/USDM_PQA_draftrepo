#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USDM GIS Data Crawler
Source: https://droughtmonitor.unl.edu/DmData/GISData.aspx
Downloads weekly shapefile packages for:
  1. SHP (shapefiles_m): Drought areas D0 to D4 (USDM_{date}_M.zip)
  2. Impacts (shapefiles_i): Drought impacts (USDM_{date}_I.zip)
  3. OCONUS (shapefiles_o): Outside CONUS (USDM_{date}_O.zip, starts from 2019-02-12)
Target range: 2000-01-04 to 2022-06-28 (1,174 weekly releases).
"""

import os
import sys
import json
import time
import zipfile
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BASE_URL = "https://droughtmonitor.unl.edu"
API_WEEKS_URL = f"{BASE_URL}/DmData/GISData.aspx/ReturnDMWeeks"

CATEGORIES = {
    "shp": {
        "folder": "shp",
        "url_template": f"{BASE_URL}/data/shapefiles_m/USDM_{{date}}_M.zip",
        "file_template": "USDM_{date}_M.zip",
        "description": "USDM Drought Severity (D0 - D4) Shapefiles"
    },
    "impacts": {
        "folder": "impacts",
        "url_template": f"{BASE_URL}/data/shapefiles_i/USDM_{{date}}_I.zip",
        "file_template": "USDM_{date}_I.zip",
        "description": "USDM Drought Impacts Shapefiles"
    },
    "oconus": {
        "folder": "oconus",
        "url_template": f"{BASE_URL}/data/shapefiles_o/USDM_{{date}}_O.zip",
        "file_template": "USDM_{date}_O.zip",
        "description": "USDM OCONUS Shapefiles (available from 2019-02-12)"
    }
}


def get_available_weeks(session):
    """Fetch all available weeks from USDM API."""
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = session.get(API_WEEKS_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    weeks = data.get("d", [])
    # Return sorted ascending YYYYMMDD
    return sorted(weeks)


def is_valid_zip(file_path):
    """Verify if the downloaded file is a valid non-empty zip archive."""
    if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
        return False
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            # test zip integrity
            bad_file = z.testzip()
            return bad_file is None
    except Exception:
        return False


def download_file(session, url, target_path, max_retries=3):
    """Download a file with retry and zip validation. Returns (status, size, error_msg)."""
    # Check if already successfully downloaded
    if is_valid_zip(target_path):
        return "EXISTS", os.path.getsize(target_path), ""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    temp_path = str(target_path) + ".tmp"

    for attempt in range(1, max_retries + 1):
        try:
            with session.get(url, headers=headers, stream=True, timeout=30) as r:
                if r.status_code == 404:
                    return "NOT_FOUND", 0, "404 Not Found"
                r.raise_for_status()

                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)

            # Check downloaded zip integrity
            if is_valid_zip(temp_path):
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.replace(temp_path, target_path)
                return "DOWNLOADED", os.path.getsize(target_path), ""
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if attempt == max_retries:
                    return "CORRUPTED", 0, "Invalid ZIP archive received"
                time.sleep(1 * attempt)

        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            if attempt == max_retries:
                return "ERROR", 0, str(e)
            time.sleep(1.5 * attempt)

    return "ERROR", 0, "Max retries exceeded"


def main():
    parser = argparse.ArgumentParser(description="Crawl USDM Drought Monitor GIS shapefiles")
    parser.add_argument("--output-dir", default=".", help="Root directory to save crawled files")
    parser.add_argument("--start-date", default="20000104", help="Start date (YYYYMMDD), default: 20000104")
    parser.add_argument("--end-date", default="20220628", help="End date (YYYYMMDD), default: 20220628")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent download threads (default: 10)")
    args = parser.parse_args()

    base_dir = Path(args.output_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("USDM GIS Data Crawler")
    print(f"Target date range: {args.start_date} -> {args.end_date}")
    print(f"Output directory:  {base_dir}")
    print(f"Concurrent workers: {args.workers}")
    print("=" * 70)

    # Prepare directories
    for cat_key, info in CATEGORIES.items():
        cat_dir = base_dir / info["folder"]
        cat_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=args.workers * 2,
        pool_maxsize=args.workers * 2,
        max_retries=3
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    print("Fetching week list from USDM API...")
    all_weeks = get_available_weeks(session)
    target_weeks = [w for w in all_weeks if args.start_date <= w <= args.end_date]
    print(f"Found {len(target_weeks)} target weeks in range (expected: 1174).")

    if not target_weeks:
        print("No weeks found for the specified date range!")
        return

    # Build task list
    download_tasks = []
    for dt in target_weeks:
        for cat_key, info in CATEGORIES.items():
            filename = info["file_template"].format(date=dt)
            target_path = base_dir / info["folder"] / filename
            url = info["url_template"].format(date=dt)
            download_tasks.append({
                "date": dt,
                "category": cat_key,
                "url": url,
                "target_path": target_path,
                "filename": filename
            })

    total_tasks = len(download_tasks)
    print(f"Total download tasks queued: {total_tasks} ({len(target_weeks)} weeks x 3 categories)")

    # Execute downloads with ThreadPoolExecutor
    stats = {
        "DOWNLOADED": 0,
        "EXISTS": 0,
        "NOT_FOUND": 0,
        "CORRUPTED": 0,
        "ERROR": 0
    }
    manifest_records = []

    start_time = time.time()
    completed_count = 0

    def worker_func(task):
        status, size, err = download_file(session, task["url"], task["target_path"])
        return task, status, size, err

    print("\nStarting downloads...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(worker_func, t): t for t in download_tasks}
        for future in as_completed(futures):
            task, status, size, err = future.result()
            stats[status] = stats.get(status, 0) + 1
            completed_count += 1

            manifest_records.append({
                "date": task["date"],
                "category": task["category"],
                "filename": task["filename"],
                "url": task["url"],
                "status": status,
                "size_bytes": size,
                "error": err
            })

            # Print progress every 50 tasks or on completion
            if completed_count % 50 == 0 or completed_count == total_tasks:
                elapsed = time.time() - start_time
                rate = completed_count / elapsed if elapsed > 0 else 0
                pct = (completed_count / total_tasks) * 100
                print(f"[{completed_count:4d}/{total_tasks:4d}] {pct:5.1f}% | "
                      f"Downloaded: {stats['DOWNLOADED']} | Exists: {stats['EXISTS']} | "
                      f"404: {stats['NOT_FOUND']} | Err: {stats['ERROR']} | {rate:.1f} tasks/s")

    elapsed_total = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"Download finished in {elapsed_total:.2f} seconds ({elapsed_total/60:.2f} minutes).")
    print("Download Summary:")
    for k, v in stats.items():
        print(f"  - {k:12s}: {v}")
    print("=" * 70)

    # Save manifest CSV
    manifest_csv_path = base_dir / "manifest_download.csv"
    print(f"Writing manifest to {manifest_csv_path}...")
    import csv
    with open(manifest_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "category", "filename", "url", "status", "size_bytes", "error"])
        writer.writeheader()
        # Sort by date, then category
        manifest_records.sort(key=lambda r: (r["date"], r["category"]))
        writer.writerows(manifest_records)

    # Category summaries
    cat_summary = {}
    for r in manifest_records:
        cat = r["category"]
        if cat not in cat_summary:
            cat_summary[cat] = {"total": 0, "success": 0, "404": 0, "error": 0, "bytes": 0}
        cat_summary[cat]["total"] += 1
        if r["status"] in ("DOWNLOADED", "EXISTS"):
            cat_summary[cat]["success"] += 1
            cat_summary[cat]["bytes"] += r["size_bytes"]
        elif r["status"] == "NOT_FOUND":
            cat_summary[cat]["404"] += 1
        else:
            cat_summary[cat]["error"] += 1

    print("\nDetailed Category Breakdown:")
    for cat, info in cat_summary.items():
        mb = info["bytes"] / (1024 * 1024)
        print(f"  Category '{cat.upper()}': {info['success']}/{info['total']} valid files ({mb:.2f} MB), 404 (not published): {info['404']}, Errors: {info['error']}")

    print("\nCrawl complete!")


if __name__ == "__main__":
    main()
