# Silver Layer (Cleaned & Conformed GeoParquet)
## U.S. Drought Monitor (2020 - 2022)

Tầng dữ liệu chuẩn hóa doanh nghiệp (Single Source of Truth) lưu trữ các đa giác hạn hán đã được làm sạch topology, chuẩn hóa hệ tọa độ và schema, phục vụ cho mọi phân tích không gian.

---

## 1. Cấu trúc thư mục

```text
silver/
├── data/
│   ├── drought_polygons/
│   │   ├── week_date=2020-01-07/
│   │   │   └── data.parquet
│   │   ├── ... (130 phân vùng tuần theo chuẩn Hive)
│   │   └── all_drought_polygons.parquet    # File GeoParquet hợp nhất (625 features)
│   ├── quality_reports/
│   │   ├── quality_report.json             # Báo cáo kiểm định chất lượng chi tiết
│   │   └── quality_report.csv
│   ├── manifests/
│   │   └── manifest.json                   # Nhật ký thực thi và Data Lineage
│   └── metadata/                           # Thư mục lưu metadata & schema
├── scripts/
│   ├── usdm_bronze_to_silver.py            # Pipeline xử lý Bronze -> Silver GeoParquet
│   ├── verify_silver_to_gold.py            # Adapter kiểm chứng tương thích Silver -> Gold
│   ├── test_silver_pipeline.py             # Unit test suite kiểm tra logic làm sạch
│   └── requirements.txt                    # Thư viện Python phụ thuộc
└── README.md
```

---

## 2. Đặc tả dữ liệu

- **Định dạng**: GeoParquet (Apache Parquet + OGC GeoParquet metadata, nén Snappy).
- **Hệ quy chiếu (CRS)**: WGS 84 (`EPSG:4326`).
- **Tổng số features**: 625 features / 130 tuần (105 tuần có đủ 5 cấp DM 0-4, 25 tuần có 4 cấp DM 0-3).
- **Schema**: `week_date, time_id, dm_value, drought_category, drought_name, shape_length, shape_area, geometry, source_file, source_object_id, is_geom_repaired, processed_at`.
- **Chất lượng**: 100% hình học hợp lệ (đã sửa toàn bộ 61 lỗi self-intersection bằng `shapely.make_valid()`).

---

## 3. Cách chạy pipeline

```bash
# 1. Chạy Unit Tests
python silver/scripts/test_silver_pipeline.py -v

# 2. Chạy tái tạo toàn bộ Silver từ Bronze (tự động nhận diện đường dẫn)
python silver/scripts/usdm_bronze_to_silver.py --overwrite

# 3. Kiểm chứng độ tương đồng 100% với Gold usdmfinal.csv
python silver/scripts/verify_silver_to_gold.py --weeks 20200107 20210601 20220628
```
