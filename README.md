# U.S. Drought Monitor (USDM) Spatio-Temporal Data Lakehouse
## Kiến trúc Medallion 3 Tầng: Bronze → Silver → Gold (2020 – 2022)

Kho dữ liệu không gian – thời gian chuẩn hóa phục vụ phân tích, trực quan hóa và mô hình hóa dự báo hạn hán trên toàn lãnh thổ Hoa Kỳ (CONUS).

---

## 1. Sơ đồ Tổng quan Hệ thống (System Architecture)

Toàn bộ dữ liệu và mã nguồn xử lý được tích hợp đồng bộ theo từng tầng kiến trúc Medallion:

```text
D:\Trực quan hóa\data_crawl_USDM/
│
├── 🥉 bronze/                    # TẦNG DỮ LIỆU THÔ (RAW INGESTION)
│   ├── data/                     # shp/ (130 tuần M), impacts/ (I), oconus/ (O), manifest
│   ├── scripts/                  # crawl_usdm_gis.py, inspect_data.py
│   └── README.md                 # Hướng dẫn chi tiết tầng Bronze
│
├── 🥈 silver/                    # TẦNG DỮ LIỆU CHUẨN HÓA (CONFORMED GEOPARQUET)
│   ├── data/                     # drought_polygons/ (130 phân vùng tuần + tệp hợp nhất)
│   │                             # quality_reports/ (báo cáo kiểm định JSON/CSV)
│   │                             # manifests/ (lineage manifest.json)
│   ├── scripts/                  # usdm_bronze_to_silver.py, verify_silver_to_gold.py,
│   │                             # test_silver_pipeline.py, requirements.txt
│   └── README.md                 # Hướng dẫn chi tiết tầng Silver
│
├── 🥇 gold/                      # TẦNG DỮ LIỆU TINH LUYỆN (ML-READY MART)
│   ├── data/                     # usdmfinal.csv (423.670 dòng), A.csv (ma trận kề),
│   │                             # USDMRasterized.rda, validation.txt, comparison_reports/
│   ├── scripts/                  # RasterizeUSDM_2020_2022.R, input_manifest.csv, sessionInfo.txt
│   └── README.md                 # Hướng dẫn chi tiết tầng Gold
│
├── 📚 references/                # DỮ LIỆU & TÀI LIỆU THAM CHIẾU
│   ├── USDMDataAvg.csv           # Dataset tham chiếu lịch sử (~1.5 GB)
│   ├── RasterizeUSDMforDryad.R   # Script nghiên cứu gốc (Dryad repository)
│   └── Ý tưởng paper 1.pdf       # Tài liệu nghiên cứu khoa học
│
├── ⚙️ .r_runtime/                # Môi trường R portable phục vụ Gold
└── 📄 README.md                  # TÀI LIỆU KIẾN TRÚC TỔNG THỂ
```

---

## 2. Bảng đối chiếu các tầng dữ liệu (Data Pipeline Matrix)

| Tiêu chí | 🥉 Bronze Layer | 🥈 Silver Layer | 🥇 Gold Layer |
| :--- | :--- | :--- | :--- |
| **Thư mục tích hợp** | `bronze/` | `silver/` | `gold/` |
| **Dữ liệu (`data/`)** | Shapefiles (`.shp`, `.dbf`, `.shx`) | GeoParquet (`.parquet`, Snappy) | Bảng phẳng CSV (`usdmfinal.csv`) |
| **Mã nguồn (`scripts/`)** | `crawl_usdm_gis.py`, `inspect_data.py` | `usdm_bronze_to_silver.py`, `verify_silver_to_gold.py` | `RasterizeUSDM_2020_2022.R` |
| **Độ chi tiết (Granularity)**| Đa giác hạn hán nguyên bản theo tuần | Đa giác hạn hán đã làm sạch topology | Lưới đều 0.5° (3.259 ô) × 130 tuần |
| **Hệ tọa độ (CRS)** | WGS 84 (`EPSG:4326`) | WGS 84 (`EPSG:4326`) | WGS 84 (`EPSG:4326`) |
| **Kiểm tra chất lượng** | Lưu nguyên trạng lỗi nguồn | Sửa 100% 61 invalid geometries | Cố định 423.670 dòng, không null |
| **Mục đích sử dụng** | Lưu trữ bất biến (Immutable raw) | Single Source of Truth cho GIS | Huấn luyện mô hình học máy (GNN, LSTM) |

---

## 3. Hướng dẫn vận hành nhanh (Quickstart)

Tất cả các script đều được thiết kế **tự động nhận diện đường dẫn gốc** (`repo_root`), có thể chạy trực tiếp từ thư mục gốc `data_crawl_USDM`:

```bash
cd "D:\Trực quan hóa\data_crawl_USDM"

# --- 1. TẦNG BRONZE: Kiểm tra metadata shapefile ---
python bronze/scripts/inspect_data.py

# --- 2. TẦNG SILVER: Kiểm thử và chạy pipeline Bronze -> Silver ---
# Chạy Unit Tests kiểm định logic sửa hình học
python silver/scripts/test_silver_pipeline.py -v

# Chạy pipeline tạo dữ liệu Silver GeoParquet (idempotent, hỗ trợ --overwrite)
python silver/scripts/usdm_bronze_to_silver.py --overwrite

# Kiểm chứng độ tương đồng 100% giữa Silver và Gold usdmfinal.csv
python silver/scripts/verify_silver_to_gold.py --weeks 20200107 20210601 20220628

# --- 3. TẦNG GOLD: Tái tạo lưới học máy (nếu chạy lại R) ---
powershell -Command "& '.\.r_runtime\R\bin\Rscript.exe' --vanilla 'gold\scripts\RasterizeUSDM_2020_2022.R'"
```
