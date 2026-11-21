#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USDM GIS Data Inspector
Verifies downloaded datasets and prints summary statistics.
"""

import os
import sys
import glob
import struct
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def inspect_dbf(dbf_bytes):
    """Parse basic DBF header and records using pure Python."""
    num_records, header_len, record_len = struct.unpack('<IHH', dbf_bytes[4:12])
    fields = []
    offset = 32
    while offset < header_len - 1:
        name = dbf_bytes[offset:offset+11].split(b'\x00')[0].decode('ascii', errors='ignore')
        ftype = chr(dbf_bytes[offset+11])
        flen = dbf_bytes[offset+16]
        fields.append((name, ftype, flen))
        offset += 32

    records = []
    curr = header_len
    for _ in range(min(num_records, 10)):  # sample first 10 records
        rec = {}
        curr_offset = curr + 1  # 1 byte deletion flag
        for name, ftype, flen in fields:
            val_bytes = dbf_bytes[curr_offset:curr_offset+flen]
            curr_offset += flen
            val_str = val_bytes.decode('latin-1', errors='ignore').strip()
            rec[name] = val_str
        records.append(rec)
        curr += record_len

    return fields, records, num_records


def inspect_category(folder_path, cat_name):
    print("=" * 60)
    print(f"Kiểm tra thư mục: {cat_name} ({folder_path})")
    files = sorted(glob.glob(os.path.join(folder_path, "*.zip")))
    print(f"Tổng số tệp ZIP: {len(files)}")
    if not files:
        print("Chưa có tệp nào được tải.")
        return

    total_bytes = sum(os.path.getsize(f) for f in files)
    print(f"Tổng dung lượng: {total_bytes / (1024 * 1024):.2f} MB")
    print(f"Tệp đầu tiên: {os.path.basename(files[0])}")
    print(f"Tệp cuối cùng: {os.path.basename(files[-1])}")

    # Inspect first file
    sample_file = files[0]
    try:
        with zipfile.ZipFile(sample_file, 'r') as z:
            names = z.namelist()
            print(f"\nNội dung tệp mẫu ({os.path.basename(sample_file)}): {len(names)} tệp")
            for n in names:
                print(f"  - {n}")
            
            dbf_names = [n for n in names if n.lower().endswith('.dbf')]
            if dbf_names:
                fields, records, total_rec = inspect_dbf(z.read(dbf_names[0]))
                print(f"\nCấu trúc thuộc tính ({dbf_names[0]} - {total_rec} bản ghi):")
                field_desc = ", ".join([f"{f[0]} ({f[1]}:{f[2]})" for f in fields])
                print(f"  Các trường: {field_desc}")
                print("  Bản ghi mẫu:")
                for r in records[:5]:
                    print(f"    {r}")
    except Exception as e:
        print(f"Lỗi khi đọc tệp mẫu: {e}")


def main():
    root = Path(__file__).resolve().parent
    print("BÁO CÁO KIỂM TRA DỮ LIỆU CRAWL USDM GIS")
    print(f"Thư mục làm việc: {root}\n")

    for cat in ["shp", "impacts", "oconus"]:
        cat_dir = root / cat
        inspect_category(str(cat_dir), cat.upper())

    # Check manifest
    manifest = root / "manifest_download.csv"
    if manifest.exists():
        print("\n" + "=" * 60)
        print("Tệp nhật ký tải (manifest_download.csv) đã sẵn sàng.")
        print(f"Dung lượng manifest: {manifest.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
